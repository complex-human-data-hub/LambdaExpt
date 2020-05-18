from __future__ import print_function
from future import standard_library
standard_library.install_aliases()
from builtins import map
from builtins import str
from builtins import range
from builtins import object
import boto3
from boto3.session import Session
import hashlib
import pkgutil
import gzip
import io
import json
import re
from dateutil.parser import parse
from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request
from user_utils import nocache
import os
import random 
import threading
import queue
import time
import string 
import logging
import sys 

logger = logging.getLogger()
logger.setLevel(logging.INFO)


if False and pkgutil.find_loader("unforgettable"):
    from unforgettable.utils import _debug 
else:
    def _debug(msg):
        pass

if pkgutil.find_loader("SimpleDB"):
    from SimpleDB import Record, QuerySelect, Domain, SimpleDBKeyInUseException
elif pkgutil.find_loader("SimpleDBLambda"):
    from SimpleDBLambda import Record, QuerySelect, Domain, SimpleDBKeyInUseException
elif pkgutil.find_loader("SimpleDBLambdaTemplate"):
    from SimpleDBLambdaTemplate import Record, QuerySelect, Domain, SimpleDBKeyInUseException
else:
    raise Exception("No version of SimpleDB available")



# Regexes
re_s3 = re.compile(r'^s3://([^/]+)/(.+)$')
re_cloudfront_device = re.compile(r'^CloudFront-Is-(.+)-Viewer$')


cloudfront_devices = [
        'CloudFront-Is-Desktop-Viewer', 
        'CloudFront-Is-Mobile-Viewer',
        'CloudFront-Is-Tablet-Viewer',
        'CloudFront-Is-SmartTV-Viewer'
        ]

# Status codes
NOT_ACCEPTED = 0
ALLOCATED = 1
STARTED = 2
COMPLETED = 3
SUBMITTED = 4
CREDITED = 5
QUITEARLY = 6
BONUSED = 7

DATESTRING_FORMAT = "%Y-%m-%dT%H:%M:%S"

MAX_NUMBER_OF_THREADS = 20

class MallExperiment(Exception):
    pass

class Expt(object):
    region_name='us-west-2'
    # domain linked to SimpleDB domain, so for 
    #   researcher: mall_experiments
    #   participant: mall_experiments_participants
    domain='mall_experiments'  
    experiments_domain='mall_experiments'
    participants_domain='mall_experiments_participants'
                                
    def __init__(self, **kwargs):
        for k in kwargs:
            setattr(self, k, kwargs[k])


    def expt_common_blueprint(self, s3_data_bucket, s3_results_key, debug=False):
        """ Create a Blueprint with common functions """
        #Blueprint
        expt_common_blueprint = Blueprint('expt_common_blueprint', __name__)
        @expt_common_blueprint.route('/record-task', methods=['POST'])
        def record_task():
            if request.method == 'POST':
                uid = request.form['uid']
                logger.info("record_task: [{}]".format(uid))
                res = self.complete_expt(
                    request,
                    uid=uid,
                    results_bucket=s3_data_bucket,
                    results_key=s3_results_key.format(uid),
                    debug=debug
                    )

                logger.info("record_task response: [{}] {}".format(uid, res))
                return jsonify(res)

        return expt_common_blueprint


    def _getS3Client(self):
        session = Session(region_name=self.region_name)
        client = session.client('s3')
        return client

    def get_file(self, filename):
        if os.path.isfile(filename):
            with open(filename,'rb') as fp:
                if filename.endswith(".json"):
                    # python >= 3.6 can read binary files, so this could be
                    # return json.load(fp)
                    return json.loads(fp.read().decode('utf-8'))
                elif filename.endswith(".json.gz"):
                    fp.seek(0)
                    gzf = gzip.GzipFile(fileobj=fp, mode='rb')
                    file_content = gzf.read()
                    return json.loads(file_content.decode('utf-8'))
                else:
                    return fp.read()
        else:
            raise MallExperiment("Not a valid filename path: {}".format(filename))

    def get_participant(self, uid):
        rec = Record(domain=self.participants_domain, key=uid)
        return rec.fetch()

    def get_experiment(self, uid):
        rec = Record(domain=self.experiments_domain, key=uid)
        return rec.fetch()

    def create_unique_participant(self, request, expt_uid=None, custom_attrs={}, debug=False):
        try:
            condition = request.args.get('condition')

            rec = Record(domain=self.experiments_domain)
            expt = rec.fetch(expt_uid)
            if not expt:
                raise Exception("Unknown experiment")
                #return (None, self.return_error('404.html'))
            
            dom = Domain(domain=self.participants_domain)
            participant_n = dom.count('expt_uid', expt_uid)
            rand = "{:0>17}".format( random.randint(1e6, 9e16) )
            created = datetime.now().strftime(DATESTRING_FORMAT)   

            participant_id = "{}.{}@{}".format(participant_n, rand, created)

            participant_key = self.make_key(
                    participant_id,
                    expt['uid'],
                    expt['codeversion'],
                    (condition or expt['trial'])
                    )

            participant = Record(domain=self.participants_domain, key=participant_key)

            attrs = {
                'uid': participant_key,
                'expt_uid': expt['uid'],
                'codeversion': expt['codeversion'],
                'trial': (condition or expt['trial']),
                'created': created,
                'status': STARTED,
                'start': datetime.now().strftime(DATESTRING_FORMAT),
                'participant_id': participant_id
                }

            self.add_headers(request, attrs)


            #insert request attributes
            for key in list(custom_attrs.keys()):
                if not attrs.get(key):
                    attrs[key] = custom_attrs.get(key)

            participant.set_attributes(attrs, True)
            participant.update()

            return (participant_key, None)
        except SimpleDBKeyInUseException as e:
            return self.create_unique_participant(expt_uid, debug)

        except Exception as e:
            if debug:
                print("Debug catch error. Erros: '" + str(e) + "'. If you are writing a new experiment and this error says that you have an invalid AWS Access Key, then don't worry when you go live with the experiment Ben will use a valid key. ")
                return ('99999999', None)
            else:
                raise Exception(e)

        return (None, self.return_error('500.html'))

    def get_S3(self, s3_data_bucket="", s3_data_key=""):
        if not s3_data_key:
            # Check to see if we have been given a s3 uri (s3://bucket/key)
            m = re_s3.match(s3_data_bucket)
            if m:
                s3_data_bucket, s3_data_key = m.groups()
            else:
                raise MallExperiment("S3 Data Key not provided")

        if not s3_data_bucket:
            raise MallExperiment("S3 Data Bucket not provided")

        client = self._getS3Client()
        fp = io.BytesIO()
        client.download_fileobj(s3_data_bucket, s3_data_key, fp)
        data = None

        if s3_data_key.endswith("json.gz"):
            fp.seek(0)
            gzf = gzip.GzipFile(fileobj=fp)
            file_content = gzf.read()
            data = json.loads(file_content)
        elif s3_data_key.endswith("json"):
            value = fp.getvalue()
            try:
                data = json.loads( value )
            except:
                # File was mislabelled and not really in json format
                data = value
        else:
            data = fp.getvalue()

        return data


    def save_S3(self, bucket, key, data):
        client = self._getS3Client()
        client.put_object(Key=key, Body=data, Bucket=bucket)


    def make_key(self, user, experiment, codeversion=0, trial=0, internal=False):
        """ 
        Use to make unique key for SimpleDB for both 
        Experiments and Experiments Participants
        """
        if (internal):
            return self._make_key(user, experiment, codeversion, trial)

        rec = Record(domain=self.domain)      
        key = rec.make_key(user, experiment, codeversion, trial)
        return key  

    def _make_key(self, *argv):
        """
        Use to make unique key for SimpleDB
        """
        m = hashlib.md5()
        for arg in argv:
            m.update(str(arg).encode('utf-8'))
        key = m.hexdigest()
        return key

    def get_mturk_survey_code(self, uid, domain):
        """
        Get a code to give to the worker 
        so that they can indicate that they
        have finished the experiment
        """
        mturk_code = random.randint(1e7,9e7)
        participant = Record(domain=domain, key=uid)
        attrs = {
                'mturk_survey_code': mturk_code
                }

        participant.set_attributes(attrs, True)
        participant.update()
        return mturk_code 


    def check_set_participant_attrs(self, uid, data, debug=False):
        """
        Searchs data for the dictionary '_participant_attrs',
        which if present will be set in the participant database for 'uid'

        Returns the data object so you can use the method inline
        """
        participant_attrs = data.get('_participant_attrs')
        if participant_attrs and isinstance(participant_attrs, dict):
            self.set_participant_attrs(uid, participant_attrs, debug=debug)
        return data


    def set_participant_attrs(self, uid, attrs, debug=False):
        try:
            participant = Record(domain=self.participants_domain, key=uid)
            participant.set_attributes(attrs, True)
            participant.update()
        except Exception as e:
            if debug:
                print("Can't set participant record, but you're debugging so let's keep going on")
            else:
                raise e



    def return_error(self, template, reason=""):
        return {
            'template': template,
            'reason': reason
                }


    def check_exclude_experiments_mturk(self, request):
        """
        Return True if participant HAS NOT particpated in 'exclude_expt'
        """
        #print "in check_exclude_experiments_mturk"
        worker_id = request.args.get('workerId')
        expt_uid = request.args.get('expt_uid')
    
        expt = self.get_experiment(expt_uid)
        if 'exclude_expt' not in expt:
            #print "returning True exclude_expt not in expt"
            # User is okay no excludes have been defined
            return True
        else:
            exclude_expt = expt.get('exclude_expt')

        #print "Excluding: {}".format(exclude_expt)
        #exclude_expt is a comma separated 
        #string of expt_uids to exclude
        excludes = ", ".join( map( "'{}'".format, list(map(string.strip,  exclude_expt.split(",") )) ) )
        query = "SELECT count(*) FROM {} WHERE worker_id = '{}' AND expt_uid IN ({}) ".format(self.participants_domain, worker_id, excludes)  
       
        
        #print query
        qs = QuerySelect() 
        res = qs.sql(query)
        #print json.dumps(res, indent=4)
        if int(res[0]['Count']) > 0:
            #print "Returning False Count is greater the 0"
            return False
       
        #print "returning True"
        return True

        
        

    def check_unique_participant(self, request, expt_uid=None, domain=None):
        try:
            #print "check_unique_participant"
            hit_id = request.args.get('hitId')
            worker_id = request.args.get('workerId')
            assignment_id = request.args.get('assignmentId')
            condition = request.args.get('condition') 
            if not (hit_id or worker_id or assignment_id):
                #print "return False: not (hit_id or worker_id or assignment_id)"
                return False, None

            rec = Record(domain='mall_experiments')
            expt = rec.fetch(expt_uid)
            if not expt:
                #print "return False: not expt"
                return False, None

            # Will throw SimpleDBKeyInUseException 
            # if participant has already done this experiment
            participant_key = self.make_key(
                    worker_id,
                    expt['uid'],
                    expt['codeversion'],
                    (condition or expt.get('trial'))        
                    )
            #print "return True: can make key"
            return True, None

        except SimpleDBKeyInUseException as e:
            #print "SimpleDBKeyInUseException exception"
            #Return participant object so that we can 
            #do something useful with it (i.e., check if they have submitted results)

            participant_key = self.make_key(worker_id, expt['uid'], expt['codeversion'], (condition or expt.get('trial')), internal=True)
            participant = self.get_participant(participant_key)
            return False, participant

        except Exception as e:
            #print "Other exception {}".format(str(e))
            return False, None
        
        #print "Not sure how I ended up here!!"
        return False, None

    def get_client_ip(self, request):
        remote_addr = "127.0.0.1"
        x_forwarded_for = request.headers.get('X-Forwarded-For', '')

        if not x_forwarded_for:
            remote_addr = request.remote_addr
        else:
            remote_addr = x_forwarded_for.split(', ')[-2]

        return remote_addr

    
    def get_cloudfront_device(self, request):
        device = ''
        for x in cloudfront_devices:
            if request.headers.get(x) == 'true':
                m = re_cloudfront_device.match(x)
                if m:
                    return m.groups()[0]
        return device


    def add_headers(self, request, attrs):
        """ Add informative headers to participant record """
        attrs['ua'] = request.headers.get('User-Agent', '')
        attrs['language'] = request.headers.get('Accept-Language', '')
        attrs['cloudfront_country'] = request.headers.get('CloudFront-Viewer-Country', '') 
        attrs['cloudfront_device'] = self.get_cloudfront_device(request)
        attrs['ip'] = self.get_client_ip(request)


    def start_mturk_expt(self, request, expt_uid=None, domain=None, debug=False, request_attrs=[]):
        try:
            if not domain:
                domain = self.participants_domain

            condition = request.args.get('condition')

            hit_id = request.args.get('hitId')
            worker_id = request.args.get('workerId')
            assignment_id = request.args.get('assignmentId')

            if not (hit_id or worker_id or assignment_id):
                return (None, self.return_error('worker-accept-hit.html'))

            rec = Record(domain='mall_experiments')
            expt = rec.fetch(expt_uid)
            if not expt:
                return (None, self.return_error('404.html'))


            participant_key = self.make_key(
                    worker_id,
                    expt['uid'],
                    expt['codeversion'],
                    (condition or expt['trial'])
                    )
            
            
            participant = Record(domain=domain, key=participant_key)
            attrs = {
                'uid': participant_key,
                'expt_uid': expt['uid'],
                'codeversion': expt['codeversion'],
                'trial': (condition or expt['trial']),
                'created': datetime.now().strftime(DATESTRING_FORMAT),
                'start': datetime.now().strftime(DATESTRING_FORMAT),
                'status': STARTED,
                'worker_id': worker_id,
                'assignment_id': assignment_id,
                'hit_id': hit_id
                    }

            self.add_headers(request, attrs)

            #insert custom attributes
            for key in request_attrs:
                if not attrs.get(key):
                    value = request.args.get(key)
                    if value:
                        attrs[key] = value

            participant.set_attributes(attrs, True)
            participant.update()

            return (participant_key, None)


        except SimpleDBKeyInUseException as e:
            if debug:
                print("Debug ({}) has already attempted this study".format(str(e)))
                return (str(e), None)
            else:
                return (None, self.return_error("worker-error.html", "study_repeat"))

        except Exception as e:
            if debug:
                print("Debug catch error. Erros: '" + str(e) + "'. If you are writing a new experiment and this error says that you have an invalid AWS Access Key, then don't worry when you go live with the experiment Ben will use a valid key. ")
            else:
                raise Exception(e)

        return (None, self.return_error('500.html'))


    def start_expt(self, request, uid=None, expt_uid=None, domain=None, debug=False, allow_redos=False, custom_attrs={}, request_attrs=[]):
        try:
            if not domain:
                domain = self.participants_domain
            if not uid:
                return "404.html"

            rec = Record(domain=domain)
            participant = rec.fetch(uid)

            if not participant:
                return "404.html"

            if participant['expt_uid'] != expt_uid:
                return "noredo.html"

        

            if int(participant['status']) != ALLOCATED and not (debug or allow_redos):
                return "noredo.html"

            attrs = {
                'start': datetime.now().strftime(DATESTRING_FORMAT),
                'status': STARTED
                }

            self.add_headers(request, attrs)

            #insert request attributes
            for key in list(custom_attrs.keys()):
                if not attrs.get(key):
                    attrs[key] = custom_attrs.get(key)

            #insert request attributes
            for key in request_attrs:
                if not attrs.get(key):
                    value = request.args.get(key)
                    if value:
                        attrs[key] = value

            rec.set_attributes(attrs, True)
            rec.update()

        except Exception as e:
            if debug:
                print("Debug catch error. Erros: '" + str(e) + "'. If you are writing a new experiment and this error says that you have an invalid AWS Access Key, then don't worry when you go live with the experiment Ben will use a valid key. ")
            else:
                raise Exception(e)

        return None


    def complete_expt(self, request, uid=None, results_bucket=None, results_key=None, domain=None, debug=False):
        mturk = False
        logger.info("complete_expt: [{}]".format(uid))
        try:
            if not domain:
                domain = self.participants_domain
            if not uid:
                return self.error_response("Unknown participant")

            start_date_local = parse( request.form['start_date_local'] )
            end_date_local = parse( request.form['end_date_local'] )
            date_offset = request.form['date_offset']

            message = "complete_expt: [{}] {}".format(
                    uid, 
                    json.dumps( {
                        'start_date_local':start_date_local, 
                        'end_date_local':end_date_local, 
                        'date_offset':date_offset}, indent=4, default=str)
                    )
            logger.info(message)

            if date_offset:
               td = timedelta(minutes=int(date_offset))
               start_date_local = start_date_local - td
               end_date_local = end_date_local - td


            results =  request.form['results']
            
            if not (uid and start_date_local and end_date_local and results):
                return self.error_response("Incomplete data")

            if not (results_bucket and results_key):
                return self.error_response("No results location set")

            rec = Record(domain=domain)
            participant = rec.fetch(uid)
            if participant.get("worker_id"):
                mturk = True

            if not participant:
                return self.error_response("Unknown participant")

            self.save_S3(results_bucket, results_key, results)

            attrs = {
                's3_results': "s3://{}/{}".format(results_bucket, results_key),
                'start_date_local': start_date_local.strftime(DATESTRING_FORMAT),
                'end_date_local': end_date_local.strftime(DATESTRING_FORMAT),
                'end': datetime.now().strftime(DATESTRING_FORMAT),
                'status': str(COMPLETED)
                }
               

            rec.set_attributes(attrs)    
            rec.update()
        except Exception as e:
            if debug:
                print("Debug catch error. " + str(e) + " If you are writing a new experiment and this error says that you have an invalid AWS Access Key, then don't worry when you go live with the experiment Ben will use a valid key. ")
            else:
                logger.error("complete_expt Exception: [{}] {}".format(uid, str(e)))
                raise Exception(e)

        return {"status":"success", "uid": uid, "mturk": mturk}

    def error_response(self, error):
        logger.info("error response: {}".format(error))
        return {'status': 'failed', 'msg': error}


    def fetch_results(self, expt_uid, ignore={}):
        query = "SELECT * FROM {} WHERE expt_uid = '{}' ".format(self.participants_domain, expt_uid)
        results = []
        qs = QuerySelect()
        for item in qs.sql(query):
            if item['uid'] in ignore:    
                continue
            if "s3_results" in item:
                try: 
                    item['results'] = self.get_S3(item['s3_results']) 
                    results.append(item)
                except Exception as e:
                    print("Could not retreive result for item {}".format(item['uid']))
                    print(item)

        return results


    def fetch_result_from_key(self, expt_uid, key, value):
        query = "SELECT * FROM {} WHERE expt_uid = '{}' AND {} = '{}' ".format(self.participants_domain, expt_uid, key, value)
        results = []
        qs = QuerySelect()
        for item in qs.sql(query):
            if "s3_results" in item:
                try:
                    item['results'] = self.get_S3(item['s3_results'])
                    results.append(item)
                except Exception as e:
                    print("Could not retreive result for item {}".format(item['uid']))
                    print(item)

        return results
    

    def debug(self, msg):
        now = datetime.now()
        msg = "[{}] {}".format(now.strftime("%Y-%m-%dT%H:%M:%S"), msg)
        _debug(msg)

    def fetch_results_threaded(self, expt_uid, ignore={}):
        query = "SELECT * FROM {} WHERE expt_uid = '{}' ".format(self.participants_domain, expt_uid)
        results = []
        self.debug("Fetch results")
        qs = QuerySelect()
        for item in qs.sql(query):
            if item['uid'] in ignore:    
                continue
            if "s3_results" in item:
                results.append(item)

        self.debug("...done")
        if not results:
            return []

        num_threads = min(MAX_NUMBER_OF_THREADS, len(results))
        self.debug( "NUMBER OF THREADS: {}".format(num_threads))            
        in_queue = queue.Queue()
        out_queue = queue.Queue()
        self.debug("Setup queues")
        for i in range(num_threads):
            self.debug("start: {}".format(i))
            worker = S3ResultsThreadJob(i, in_queue, out_queue)
            worker.start()
            self.debug("...done: {}".format(i))
        self.debug("Started workers")
        for item in results:
            in_queue.put(item)
        self.debug("added jobs")
        in_queue.join()
        self.debug("joined in_queue")

        self.debug("Get out_queue")
        ret = []
        while not out_queue.empty():
            data = out_queue.get()
            if data:
                ret.append(data)
            out_queue.task_done()
        self.debug("out_queue done")
        out_queue.join()
        self.debug("out_queue joined")

        return ret
        

class S3ResultsThreadJob(threading.Thread):
    """Retreive S3 results"""
    region_name = 'us-west-2'

    def __init__(self, i, in_queue, out_queue):
        threading.Thread.__init__(self)
        self.name = "Thread {}".format(i)
        self.queue = in_queue
        self.out_queue = out_queue
        self.client = self._getS3Client()
        self.me_expt = Expt() 

    def debug(self, msg):
        _debug("In thread: " + self.name + " " + str(msg) )

    def _getS3Client(self):
        session = Session(region_name=self.region_name)
        client = session.client('s3')
        return client

    def run(self):
        time.sleep(2) #Give jobs a chance to load
        while True:
            if self.queue.empty():
                break
            item = self.queue.get()
            
            try:
                if "s3_results" in item:
                    self.debug("Fetching {} ".format(item['s3_results']))
                    results = self.me_expt.get_S3(item['s3_results']) 
                    self.debug("...done")
                    item['results'] = results
                    self.out_queue.put( item )
            except Exception as e:
                pass


            self.queue.task_done()
        return True



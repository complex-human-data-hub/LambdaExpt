from __future__ import print_function
from builtins import str
from flask import Flask, render_template, request, jsonify
from user_utils import nocache, restrictions
import json
import MallExperiment as me
from flask_s3 import FlaskS3
#from flask_compress import Compress
import os
from expt_config import get_data, s3_results_key
import expt_config
import config
import requests
import xmltodict
import os

DEBUG = config.DEBUG
expt_uid = config.EXPT_UID

static_folder = "static_{}".format(expt_uid)
if DEBUG and not os.path.isdir(static_folder):
    if os.path.isdir('static'):
        static_folder = 'static'
    else:
        raise(Exception('Static Directory not on path'))



s3_static_bucket = "chdhstatic"
s3_data_bucket = "chdhexpt"

me_expt = me.Expt(domain=config.SDB_EXPERIMENTS_PARTICIPANTS)



app = Flask("Experiment_Server", static_folder=static_folder)

if not DEBUG:
    app.config['FLASKS3_BUCKET_NAME'] = s3_static_bucket
    app.config['FLASKS3_FORCE_MIMETYPE'] = True
    s3 = FlaskS3(app)

expt_common_blueprint = me_expt.expt_common_blueprint(s3_data_bucket, s3_results_key, debug=DEBUG)
app.register_blueprint(expt_common_blueprint)

#Compress(app)

if hasattr(expt_config, 'custom_code'):
    from expt_config import custom_code
    app.register_blueprint(custom_code)



@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.route('/unique-expt', methods=['GET'])
@nocache
@restrictions
def unique_start_exp():
    # Record particpant starting experiment
    (uid, error) = me_expt.create_unique_participant(
            request,
            expt_uid=expt_uid,
            debug=DEBUG
            )
    if error:
        return render_template(error['template'], **error)

    data = me_expt.check_set_participant_attrs( uid, get_data( request.args ), DEBUG )

    if data.get('_error') != None:
        return render_template('error-page.html',error=data['_error'])
    
    return render_template(
        'exp.html',
        uid=uid,
        data=json.dumps( data )
        )


@app.route('/mturk-expt', methods=['GET'])
@nocache
@restrictions
def mturk_start_exp():
    if not 'workerId' in request.args:
        raise Exception("Unique ID not provided")

    # Record particpant starting experiment
    (uid, error) = me_expt.start_mturk_expt(
            request,
            expt_uid=expt_uid,
            debug=DEBUG
            )

    if error:
        print(error)
        return render_template(error['template'], **error)

    data = me_expt.check_set_participant_attrs( uid, get_data( request.args ), DEBUG ) 

    if data.get('_error') != None:
        return render_template('error-page.html',error=data['_error'])

    return render_template(
        'exp.html',
        uid=uid,
        mturk=1,
        data=json.dumps( data )
        )


# the API to mark REP as done
@app.route('/mark-rep-as-done', methods=['GET'])
@nocache
@restrictions
def mark_rep_as_done():
    survey_code = request.args.get('survey_code')
    uid = request.args.get('uid')

    try:
        response = requests.get(config.REP_URL.format(survey_code))
        print(response)
        result = xmltodict.parse(response.content)
        print(result)
        attrs = {
            'uid': uid,
            'survey_code': survey_code,
            'rep_credit_response': json.dumps(result, default=str)
        }
        me_expt.set_participant_attrs(uid, attrs)
        # if crediting is successful, there should be no error
        no_error = result['WebstudyCreditResponse']['WebstudyCreditResult'].get('a:Errors').get('@i:nil')
        # if there is error, throw it so the participant can see
        if no_error != 'true':
            error= result['WebstudyCreditResponse']['WebstudyCreditResult'].get('a:Errors')
            return error.get('b:string'), 500
        else:
            return "updated", 200
    except Exception:
        return str(Exception), 500


@app.route('/rep-expt', methods=['GET'])
@nocache
@restrictions
def enter_rep_expt():
    survey_code = request.args.get('survey_code')
    if survey_code == None:
        return render_template('error-page.html',
                               error="Please supply a survey code if you want to proceed with REP mode")

    custom_attrs = {'REP': True, 'survey_code': survey_code}

    # Record particpant starting experiment
    (uid, error) = me_expt.create_unique_participant(
        request,
        expt_uid=expt_uid,
        custom_attrs=custom_attrs,
        debug=DEBUG
    )

    if error:
        return render_template(error['template'], **error)
    data = me_expt.check_set_participant_attrs(uid, get_data(request.args), DEBUG)

    if data.get('_error') != None:
        return render_template('error-page.html', error=data['_error'])

    return render_template(
        'exp.html',
        uid=uid,
        rep=1,
        survey_code=survey_code,
        rep_on_consent=int(config.REP_ON_CONSENT),  # converting python boolean to integer to avoid ambiguity
        data=json.dumps(data)
    )


# deprecated
@app.route('/rep-start-expt', methods=['GET'])
@nocache
def rep_start_expt():
    if not 'uid' in request.args:
        raise Exception("Unique ID not provided")
    uid = request.args['uid']

    if 'email' in request.args and not DEBUG:
        me_expt.set_participant_attrs(uid, {
            'email': request.args['email']
        })

    data = me_expt.check_set_participant_attrs(uid, get_data(request.args), DEBUG)
    return render_template(
        'exp.html',
        uid=uid,
        rep=1,
        data=json.dumps(data)
    )


@app.route('/expt', methods=['GET'])
@nocache
@restrictions
def start_exp():
    if not 'uid' in request.args:
        raise Exception("Unique ID not provided")
    uid = request.args['uid']

    # Record particpant starting experiment
    error = me_expt.start_expt(
            request,
            uid=uid,
            expt_uid=expt_uid,
            debug=DEBUG
            )

    if error:
        return render_template(error['template'], **error)

    data = me_expt.check_set_participant_attrs( uid, get_data( request.args ), DEBUG )

    if data.get('_error') != None:
        return render_template('error-page.html',error=data['_error'])

    return render_template(
        'exp.html',
        uid=uid,
        data=json.dumps( data )
        )


@app.route('/update-queue', methods=['GET'])
@nocache
def update_queue():
    ret = expt.update_queue()
    return jsonify(ret)



@app.route('/poll-queue', methods=['GET'])
@nocache
def poll_queue():
    ret = expt.poll_queue()
    return jsonify(ret)



     
def run_webserver():
    ''' Run web server '''
    host = "0.0.0.0"
    port = 5000
    print("Serving on ", "http://" +  host + ":" + str(port))
    app.run(debug=True, host=host, port=port)



    
if __name__ == '__main__':
    run_webserver()



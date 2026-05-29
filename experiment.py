from __future__ import print_function
from builtins import str
from flask import Flask, render_template, request, jsonify
from user_utils import nocache, restrictions
import json
import time
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

EXPT_TYPE = getattr(config, 'EXPT_TYPE', 'jspsych')   # 'jspsych' | 'psiturk'
if EXPT_TYPE == 'psiturk':
    exp_html_template = 'exp-psiturk.html'
elif not config.jsPsychCurrent:
    exp_html_template = 'exp-legacy.html'
else:
    exp_html_template = 'exp.html'


app = Flask("Experiment_Server", static_folder=static_folder)

if not DEBUG:
    app.config['FLASKS3_BUCKET_NAME'] = s3_static_bucket
    app.config['FLASKS3_FORCE_MIMETYPE'] = True
    s3 = FlaskS3(app)

expt_common_blueprint = me_expt.expt_common_blueprint(s3_data_bucket, s3_results_key, debug=DEBUG)
app.register_blueprint(expt_common_blueprint)


# Expose DEBUG to every template (e.g. exp-psiturk.html uses it to pick
# psiTurk's `mode = "debug" | "live"`, which controls the beforeunload prompt).
@app.context_processor
def inject_debug_flag():
    return {'debug': DEBUG}

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
        exp_html_template,
        uid=uid,
        jsPsychCurrent=config.jsPsychCurrent,
        data=json.dumps( data )
        )


@app.route('/prolific', methods=['GET'])
@nocache
@restrictions
def prolific_start_exp():
    if not 'PROLIFIC_PID' in request.args:
        raise Exception("Unique ID not provided")

    # Record particpant starting experiment
    (uid, error) = me_expt.start_prolific_expt(
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
        exp_html_template,
        uid=uid,
        prolific=1,
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
        exp_html_template,
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
        exp_html_template,
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
        exp_html_template,
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
        exp_html_template,
        uid=uid,
        data=json.dumps( data )
        )


@app.route('/prohibit-reload-expt', methods=['GET'])
@nocache
def prohibit_reload_expt():
    print("Prohibit reload endpoint called")
    uid = request.args.get('uid')
    if not uid:
        return "UID not provided", 400
    # Implement logic to prohibit reload for the experiment with the given UID
    # This could involve setting a flag in the database or in-memory store
    # For now, just return success
    me_expt.prohibit_reload_expt(uid)
    print(f"Prohibit reload set for UID: {uid}")
    return "Prohibit reload set", 200



@app.route('/update-queue', methods=['GET'])
@nocache
def update_queue():
    ret = expt_config.update_queue()
    return jsonify(ret)



@app.route('/poll-queue', methods=['GET'])
@nocache
def poll_queue():
    ret = expt_config.poll_queue()
    return jsonify(ret)


# ---- psiTurk routes ---------------------------------------------------------
# These are used when config.EXPT_TYPE == 'psiturk'. They are always-on but
# inert for jsPsych projects (psiTurk's TaskData model is the only thing that
# PUTs to /sync/<uid>).

@app.route('/inexp', methods=['POST'])
@nocache
@restrictions
def inexp():
    ret = {}
    if request.method == 'POST':
        uid = request.form['uniqueId']
        ret['uid'] = uid
    print(ret)
    return jsonify(ret)


@app.route('/quitter', methods=['POST'])
@nocache
@restrictions
def quitter():
    ret = {}
    if request.method == 'POST':
        uid = request.form['uniqueId']
        ret['uid'] = uid
    print(ret)
    # Maybe add complete_expt here
    return jsonify(ret)


@app.route('/sync', methods=['POST'])
@nocache
@restrictions
def sync():
    ret = {}
    if request.method == 'POST':
        print("POST request", request.form)
        uid = request.form['uid']
        ret['uid'] = uid
    elif request.method == 'GET':
        print("GET request")
        print(request.args)
    elif request.method == 'PUT':
        print("POST request", request.form)
        uid = request.form['uid']
        ret['uid'] = uid

    print(ret)
    return jsonify(ret)


@app.route('/sync/<uid>', methods=['GET', 'PUT'])
@nocache
@restrictions
def sync_uid(uid):
    # psiTurk's TaskData model PUTs the full serialised model here every saveData().
    # The model's `data` is the trial array — what gets persisted to S3.
    # `questiondata` (where recordUnstructuredData writes) is rescued by
    # appending it as a synthetic trialdata row so it survives the round-trip.
    ret = {}
    print("Syncing", uid)
    if request.method == 'PUT':
        print("PUT request", request.form)
        data_json = request.json
        data = data_json.get('data', [])
        qdata = data_json.get('questiondata', {})
        if qdata:
            data = data + [{
                'uniqueid': uid,
                'current_trial': len(data),
                'dateTime': int(time.time() * 1000),
                'trialdata': {'phase': 'questiondata', **qdata},
            }]
        form_data = {
            'results': json.dumps(data),
        }
        request_like_obj = me.MyObject(form=form_data)
        res = me_expt.complete_expt(
                    request_like_obj,
                    uid=uid,
                    results_bucket=s3_data_bucket,
                    results_key=s3_results_key.format(uid),
                    debug=DEBUG
                    )
        print("Form data", form_data)
        print("Form data_json", data_json)
        print("Save Res", res)

    elif request.method == 'GET':
        print("GET request", uid)

    print(ret)
    return jsonify(ret)


# ---- end psiTurk routes -----------------------------------------------------


def run_webserver():
    ''' Run web server '''
    host = "0.0.0.0"
    port = 5001
    print("Serving on ", "http://" +  host + ":" + str(port))
    app.run(debug=True, host=host, port=port)



    
if __name__ == '__main__':
    run_webserver()



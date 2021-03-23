from __future__ import print_function
from builtins import range
from MallExperiment import Expt
from user_utils import nocache
from random import shuffle
import random
from flask import render_template, Blueprint, request
import copy
import config
import json
import requests
# If you are developing your experiment
# then set the DEBUG flag to True
DEBUG = config.DEBUG

s3_results_key = config.RESULTS_DIR + "/{}.json" # Must have formatting space ({}) for Participant Unique ID 

# Every experiment needs a unique ID
expt_uid = config.EXPT_UID

#########################################################################
### (0) Get condition parameters
#########################################################################
## >> the parts for all combinations
##  theCondition = {1:'interleaved', 2:'block-fam', 3:'block-novel'}
### but we aren't using the above dictionary.....!!!



#########################################################################
### (1) Server stuff - don't touch!
#########################################################################


# Other global Experimental Variables
study_list_length = 5
test_list_length = 10

stimulus_file = "word-list.json"




# Using Expt to fetch stimulus data from S3
me_expt = Expt()

# Flask Blueprints can be used to add routes for custom_code
custom_code = Blueprint('expt_custom_code', __name__)
@custom_code.route('/debrief', methods=['post'])
@nocache
def debrief():
    data = request.form.get('data')
    uid = request.form.get('uid')
    mturk = request.form.get('mturk')

    mturk_survey_code = None
    if mturk:
        if DEBUG:
            mturk_survey_code = 9999
        else:
            mturk_survey_code = me_expt.get_mturk_survey_code(uid, 'mall_experiments_participants')

    return render_template(
        'debrief-short.html',
        mturk_survey_code=mturk_survey_code,
        )


@custom_code.route('/full-debrief', methods=['get'])
@nocache
def full_debrief():
    return render_template(
            'debrief-long.html'
            )
# All experiments must provide a 'get_data' function that
# returns any stimulus data which will be used in the HTML templates  
# 
# opts: a dictionary of parameters that were passed in the GET request
#       e.g., https://yourexpt/expt?condition=1&debug=0
#             opts = {
#                'condition': '1',
#                'debug': '0'
#                }



#########################################################################
### (2) Organize stimuli
#  The only thing we need is get_data()
#########################################################################


def get_data(opts):
    # Setup experiment tasks
    print(opts)
    word_list = fetch_word_list()

    #Set document order
    study_document_order = list(range(3)) # 8 Documents (3 in lorem)
    shuffle(study_document_order)

    #Create Study List
    study_list = get_word_list(word_list, study_list_length)
    test_list = get_word_list(word_list, test_list_length, study_list)
    return {
            'study_list': study_list,
            'test_list': test_list,
            'study_document_order': study_document_order
        }

def fetch_word_list():
    #word_list = me_expt.get_S3(s3_data_bucket, s3_data_key)
    word_list = me_expt.get_file(stimulus_file)
    return word_list


def get_word_list(word_list, list_length, study_list=None):
    skip_words = {}
    mylist = []
    # If we have a study list
    # then create a test list that
    # contains the study list words
    # and then add distractor words in
    # the while loop below
    if study_list:
        for x in study_list:
            skip_words[x['token']] = 1
        mylist = copy.deepcopy(study_list)


    # Shuffle words and
    # Get an balanced number of high and low frequency words
    words = copy.deepcopy(word_list)
    shuffle(words)
    last_freq = ""
    while len( mylist ) < list_length and words:
        w = words.pop()
        if w['token'] not in skip_words and last_freq != w['frequency']:
            mylist.append(w)
            last_freq = w['frequency']

    # Shuffle the test list
    if study_list:
        shuffle(mylist)

    return mylist


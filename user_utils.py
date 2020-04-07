# -*- coding: utf-8 -*-
""" This module provides additional tools for psiTurk users. """

from builtins import object
from functools import wraps, update_wrapper
from flask import request, Response, make_response, current_app, render_template
import config
import re

restricted = {
        'IE': {
            'type': 'header',
            'header':'User-Agent',
            'regex': [r'MSIE ([0-9]{1,}[\.0-9]{0,})', r'Trident/([0-9]{1,}[\.0-9]{0,})'],
            'reason': 'Using Internet Explorer browser',
            },
        'mobile': {
            'type': 'header',
            'header': 'CloudFront-Is-Mobile-Viewer',
            'regex' : [r'true'],
            'reason': 'Using a mobile device',
            },
        'tablet': {
            'type': 'header',
            'header': 'CloudFront-Is-Tablet-Viewer',
            'regex' : [r'true'],
            'reason': 'Using a tablet device',
            },
        'tv': {
            'type': 'header',
            'header': 'CloudFront-Is-SmartTV-Viewer',
            'regex' : [r'true'],
            'reason': 'Using a Smart TV',
            },
        }


# Decorator to check restrictions in config
# =========================================

def check_restrictions(request):
    if config.DEBUG or not hasattr(config, 'RESTRICTIONS'):
        return None
    for key in config.RESTRICTIONS:
        checker = restricted.get(key)
        if checker.get('type') == 'header':
            for r in checker.get('regex', []):
                regex = re.compile(r)
                if regex.search( request.headers.get( checker.get('header', ''), '') ):
                    return checker.get('reason')


def restrictions(func):
    """Check any device/browser restriction from config"""
    @wraps(func)
    def wrapped(*args, **kwargs):
        restricted_reason = check_restrictions(request)
        if restricted_reason:
            return render_template(
                    'restricted.html',
                    reason=restricted_reason
                    )
        return func(*args, **kwargs)
    return wrapped



        
# provides easy way to print to log in custom.py
# =========================================
def print_to_log(stuff_to_print):
    current_app.logger.info(stuff_to_print)


# Decorator for turning off browser caching
# =========================================

def nocache(func):
    """Stop caching for pages wrapped in nocache decorator."""
    def new_func(*args, **kwargs):
        ''' No cache Wrapper '''
        resp = make_response(func(*args, **kwargs))
        resp.cache_control.no_cache = True
        return resp
    return update_wrapper(new_func, func)






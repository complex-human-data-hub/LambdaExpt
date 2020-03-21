#!/usr/bin/env bash
expt_uid=`python config.py`
xdg-open https://researcher.mall-lab.com/expt?uid=$expt_uid

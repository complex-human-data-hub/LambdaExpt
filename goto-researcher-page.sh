#!/usr/bin/env bash
expt_uid=`python config.py`
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux
    xdg-open https://researcher.mall-lab.com/expt?uid=$expt_uid
elif [[ "$OSTYPE" == "darwin"* ]]; then
    # Mac OSX
    open https://researcher.mall-lab.com/expt?uid=$expt_uid
fi

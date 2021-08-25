LambdaExpt is a simple framework for running Psychology Experiments on Amazon Web Services Lambdas. These lambdas allow us to both run experiments cheaply and at scale. This framework has been developed by the Complex Human Data Hub at the University of Melbourne. It can be used to run individual experiments, experiments on Mechanical Turk, and Research For Experience (REP) experiments.

Below gives you a brief over of how to use the framework, <b>please read the wiki for more detailed documentation</b>:
https://github.com/complex-human-data-hub/LambdaExpt/wiki

## INSTALLATION
### Linux or Mac
```
python3 -m venv venv
source venv/bin/activate
pip install pip --upgrade
pip install -r requirements.txt
```

### Windows
```
python3 -m venv venv
.\venv\Scripts\activate
pip install pip --upgrade
pip install -r requirements.txt
```

## STARTING THE LOCAL SERVER
### To develop run flask server locally
#### Linux
```
FLASK_APP=experiment.py flask run
```

#### Windows 
```
python experiment.py
```

## ACCESSING YOUR EXPERIMENT
If you are developing locally the change to a localhost address, for example:
```http://localhost:5000/unique-expt```

or in production:
```https://example.com/unique-expt```


## ADDING PARAMETERS TO PASS TO PYTHON
You can also add parameters to pass to the get_data(opts) function mentioned below:
http://localhost:5000/expt?unique-expt?foo=bar&foo2=bar2
or
https://example.com/unique-expt?foo=bar&foo2=bar2


## BASIC STRUCTURE OF YOUR EXPERIMENT
* expt_config.py - this is where your python code goes. You will setup your experimental stimuli in this file. 

You can optionally provide a flask Blueprint using the 'custom_code' variable. Flask Blueprints allow you to define your own routes. 

### Functions in expt_config.py:
```
  get_data(opts)
    foo = opts.get('foo')
    return object_to_pass_to_javascript
```

* templates/exp.html
This is were you will create your experiments HTML

* static
  This is a directory for you static files: images, css, js







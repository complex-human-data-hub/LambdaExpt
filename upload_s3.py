import os
os.environ["ExptEnv"] = "Production"

from experiment import app
import flask_s3

flask_s3.create_all(app)


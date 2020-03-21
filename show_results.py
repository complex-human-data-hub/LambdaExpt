from __future__ import print_function
from SimpleDB import Record, QuerySelect
import json
import sys
import config 

if sys.argv < 1:
    print("Please supply a participant UID")
    print("Usage: python show_results.py 72b61c874c8ae464967b8bb896e29d67")

query = "SELECT * FROM {} WHERE uid='{}' ".format(config.SDB_EXPERIMENTS_PARTICIPANTS, sys.argv[0])
print(query)
sys.exit()
qs = QuerySelect()
for item in qs.sql(query):
    print(json.dumps(item, indent=4))


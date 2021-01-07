import sys
import json

json.dump(['foo'] + list(range(1000)) * 3, sys.stdout)

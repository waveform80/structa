import sys
import json

json.dump(['foo'] + [str(i) for i in range(1000)] * 3, sys.stdout)

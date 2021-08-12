import sys
import json

json.dump([str(i) for i in range(1000)] * 3, sys.stdout)

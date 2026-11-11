#!/usr/bin/env python3
import json, sys, glob
P = json.load(open(sys.argv[1])); n = 0
for f in sorted(glob.glob(sys.argv[3])):
    r = json.load(open(f)); P['partition_types'][r['type']]['clock']['landing_contract']['bands'] = r['bands']; n += len(r['report'])
json.dump(P, open(sys.argv[2], 'w'), indent=1); open(sys.argv[2], 'a').write('\n'); print('merged bands', n)

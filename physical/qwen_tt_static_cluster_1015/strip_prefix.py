# Renames the regrouped instance prefix u_hr. away so flattened gate state names equal the original body's.
import json,sys
d=json.load(open(sys.argv[1])); m=d['modules'][sys.argv[3]]
fix=lambda n: n.replace('\\u_hr.','').replace('u_hr.','')
m['cells']={fix(k):v for k,v in m['cells'].items()}
m['netnames']={fix(k):v for k,v in m['netnames'].items()}
json.dump(d,open(sys.argv[2],'w'))

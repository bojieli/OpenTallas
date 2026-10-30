#!/usr/bin/env python3
import json,sys
from pathlib import Path
from layer_prog.emitted_leaf_routes import collect
inv,lat,out=map(Path,sys.argv[1:]);r=collect(inv,lat)
raw=json.loads(lat.read_text());b=next(b for b in raw['buses']if b['lane']=='up_s_0S_L0')
original=b['source_bits'][33];b['source_bits'][33]=['leaf',original[1],original[2],1]
controls={}
for name in ('wrong_partial_bit','wrong_lane_age'):
    if name=='wrong_lane_age':b['source_bits'][33]=original;b['bound_stages']+=1
    bad=out.parent/(name+'.json');bad.write_text(json.dumps(raw))
    try:collect(inv,bad)
    except ValueError as exc:controls[name]=str(exc)
    else:raise ValueError('selected route control escaped: '+name)
r['controls_caught']=controls
out.write_text(json.dumps(r,indent=1)+'\n')
print(r['verdict'],len(r['leaves']),'leaves',controls)

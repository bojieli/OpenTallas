#!/usr/bin/env python3
"""DIE-KV-31-SRC DIAGNOSTIC ONLY: overlay copy without the 3,908 M7 BLOCK OBS (die_trial.band_share_obs ft-band
capacity-share stripes, GRT capacity model, not metal). Measures whether they are the only PG-access blocker. Not adoptable."""
import json,sys,collections
ov=json.load(open(sys.argv[1]));keep=[];drop=collections.Counter()
for o in ov['obstructions']:
  if o[0]=='BLOCK' and o[1]=='M7':drop[round((o[4]-o[2])/1000,2)]+=1;continue
  keep.append(o)
ov['obstructions']=keep;ov['whatif']='M7 BLOCK band-share OBS removed (diagnostic)';json.dump(ov,open(sys.argv[2],'w'),separators=(',',':'));print(dict(drop))

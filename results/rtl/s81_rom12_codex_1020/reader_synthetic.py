import json,os,sys
from pathlib import Path
sys.path.insert(0,str(Path.cwd()/'tools/s81_dv/layer_prog'))
import xs_field_calendar as F
from xs_calendar_pack import dedup_stream
out=Path(sys.argv[1])
cals=[]
for op in F.FLOORS:
 p,s=F._synthetic(op,6,nb=80 if op in ('ffn.experts_gu','ffn.shared_gu') else 64)
 p,s=dedup_stream(p,s)
 cals.append(F.op_calendar(op,p,s,range(6)))
lc=F.layer_calendar(cals)
F.write_layer_images(lc,p,s,out)
(out/'segments.json').write_text(json.dumps({k:v for k,v in lc.items() if k not in ('packed','iss')},indent=1)+'\n')
print('SYNTHETIC_PACK',sum(len(c['packed']) for c in cals),'->',lc['rows'],'intervals',len(lc['segments']),flush=True)

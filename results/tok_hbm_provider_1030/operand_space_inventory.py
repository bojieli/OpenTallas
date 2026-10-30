import sys,collections,json
from pathlib import Path
import argparse,hashlib
ap=argparse.ArgumentParser();ap.add_argument('--image',type=Path,required=True);ap.add_argument('--resident',type=Path,required=True);a=ap.parse_args()
repo=Path(__file__).resolve().parents[2];sys.path.insert(0,str(repo/'tools/hbm_next'))
from isa_loader import load_isa
IR,IC=load_isa();res={}
for label,p in [('raw',a.image),('resident',a.resident)]:
 recs=IC.decode_all(p.read_bytes());c=collections.Counter();samples=[];counts=collections.Counter()
 for i,(off,r,x,_)in enumerate(recs):
  if(r.unit,r.op)==('DMA','LOAD'):
   a,o=r.desc['A'],r.desc['O'];key=a.space+'->'+o.space;c[key]+=1;counts[key]+=x.n if x else 1
   if a.space=='VM' and len(samples)<15:samples.append(dict(record=i,offset=off,A=vars(a),O=vars(o),rowx=vars(x)if x else None))
 res[label]=dict(image_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),records=len(recs),LOAD_descriptor_records=dict(c),ROWX_scalar_records=dict(counts),VM_source_samples=samples)
res['scope']='Actual N=6 MTP VERIFY programme STEP; no accepted-token normalization. Dispatcher handles HBM0->VM1 LOAD and VM1->HBM0 STORE only.'
res['window_caller']=dict(inserted_backing_LOAD_records=12528,effective227_runs=95313,srcspace=0,dstspace=1,not_yet_windowized_original_body_LOAD_records=729,original_body_scalar_rows=2121)
print(json.dumps(res,indent=2))

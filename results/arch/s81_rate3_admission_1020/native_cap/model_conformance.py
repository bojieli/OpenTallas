"""Calibrate source-derived C5c offsets against actual native RET replay, including preserved failure."""
import json,re,sys
from pathlib import Path
R=Path.cwd();sys.path.insert(0,str(R/'tools/s81_slice'));import cap_model as C
B=Path('/srv/opentallas-scratch/codex/s81-rate3-admission-1020/out');O=Path(sys.argv[1]);O.mkdir(parents=True,exist_ok=False)
results=[]
for frames,native in [('aproj_rank_tags','native_cap_diag'),('aproj_cap_plan','native_cap_plan_replay')]:
 for fr in ['u_f_0R03','u_f_7R00']:
  d=B/native/(fr+'_gold');check=json.loads((d/'check.json').read_text());cfg=check['contract']['cfg'];lane=check['physical_lane']
  trace=(B/frames/fr/'gold/run.log').read_text();lanes=[{} for _ in range(8)]
  # Native stimulus captures observed trace on the next pin edge(+1), then actual face flop(+1) and cw/ce->rt landing(+3).
  off=5+(16 if lane==3 else 0)+(24 if lane>=4 else 0)
  for t,w in re.findall(r'^RET (\d+) ([0-9a-f]+)',trace,re.M):
   w=int(w,16);lanes[lane][int(t)+off]=((w>>1)&0xffffffff,(w>>33)&0xffffffff,(w>>65)&1,[(fr,int(t))])
  model=C.model(lanes,[(205,cfg)])
  # rt->rn/rs landing(+3), final actual N/S face flop(+1).
  expected=sorted((e+4,l,p,a,v) for e,l,p,a,v,*_ in model['writes'])
  actual=sorted(tuple(int(x,16 if i==4 else 10) for i,x in enumerate(m)) for m in re.findall(r'^CAP_WRITE (\d+) (\d+) (\d+) (\d+) ([0-9a-f]+)',(d/'run.log').read_text(),re.M))
  result=dict(frame=fr,producer_case=frames,native_case=native,actual=actual,predicted=expected,model_faults=model['faults'],exact=actual==expected,source_offsets=dict(observation_to_pin=1,input_face=1,to_rt_landing=3,from_rt_landing=3,output_face=1),scope='exact private pin replay only; not current die transport/physical clock/whole-slice admission')
  results.append(result);print('CAP_MODEL_NATIVE',frames,fr,result['exact'],model['faults'][:3],flush=True)
  assert result['exact'],result
(O/'model_conformance.json').write_text(json.dumps(dict(PASS=True,source='de1ee5768+Fdc702',full_stage_qualified=False,results=results),indent=1)+'\n')

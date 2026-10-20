"""Production-shape eight-frame pin-arrival model from actual isolated RTL producers.
No current die transport or physical qualification; grouped schedule is prospective.
"""
import hashlib,json,re,sys
from pathlib import Path
R=Path.cwd();sys.path.insert(0,str(R/'tools/s81_dv/layer_prog'));sys.path.insert(0,str(R/'tools/s81_slice'))
import lower_xs as L
import dv_layer_compile as D
import cap_model as C
B=Path('/srv/opentallas-scratch/codex/s81-rate3-admission-1020/out');assert (B/'aproj_slice_frames/summary.json').exists()
die=D.Die(D.die_tree(None,'/srv/opentallas-scratch/claude/toksim-s81b-fwoa/dieref'));fx=L.load_fixture('/srv/opentallas-scratch/claude/s81-calpipe/fixtures/L0')
O=Path(sys.argv[1]);O.mkdir(parents=True,exist_ok=False);sl='u_s_0S';frames=die.frames_of(sl);assert len(frames)==8
inputs={};trace=[];expected={}
for lane,fr in enumerate(frames):
 v=B/('aproj_cap_plan' if fr=='u_f_0R03' else 'aproj_slice_frames')/fr/'gold';m=json.loads((v/'meta.json').read_text());text=(v/'run.log').read_text()
 inputs[fr]=dict(meta_sha256=hashlib.sha256((v/'meta.json').read_bytes()).hexdigest(),run_sha256=hashlib.sha256((v/'run.log').read_bytes()).hexdigest(),ret_words=len(m['plan']['ret']))
 for r,x in m['rows'].items():expected[int(r)]=int(x['bf16'])<<16
 for t,w in re.findall(r'^RET (\d+) ([0-9a-f]+)',text,re.M):trace.append((lane,int(t),int(w,16)))
assert len(expected)==32 and set(expected)==set(range(32))
results=[]
for groups,P in [(1,0),(4,146),(4,224)]:
 lanes=[{} for _ in range(8)];first={}
 for lane,t,w in trace:
  group=lane%4 if groups==4 else 0;shift=group*P;flags=(group+1)&3;tag=(w>>1)&0xffffffff
  if groups==4:tag=(tag&~(3<<27))|(flags<<27) # prospective global GO epoch on each subgroup; requires NOP-source proof
  edge=t+shift+5+(16 if lane==3 else 0)+(24 if lane>=4 else 0)
  lanes[lane][edge]=(tag,(w>>33)&0xffffffff,(w>>65)&1,[(frames[lane],t)])
  first[group]=min(first.get(group,10**9),edge+40)
 cfgs=[];contract={}
 for group in range(groups):
  flags=(group+1)&3;c=L.aproj_capture_contract(die,sl,fx,flags);contract[group]=c
  cfgs.append((first[group]-4,c['cfg']))
 model=C.model(lanes,cfgs);writes=model['writes'];seen={};bad=[]
 for e,l,p,a,v,row,pos,src,port in writes:
  rank=row&0x3fff;seen[rank]=seen.get(rank,0)+1
  if expected.get(rank)!=v:bad.append([rank,v,expected.get(rank)])
 missing=sorted(set(expected)-set(seen));dup={r:n for r,n in seen.items() if n!=1}
 r=dict(groups=groups,period=P,added_producer_phases=groups-1,conditional_extra_launch_edges=(groups-1)*P,
  PASS=not(model['faults'] or bad or missing or dup),faults=model['faults'],wrong_values=bad,missing_rows=missing,duplicates=dup,
  writes=[list(w[:7]) for w in writes],cfg_pin_edges=[e-5 for e,c in cfgs],last_output_edge=max((w[0]+4 for w in writes),default=None),
  source_scope='one-go observed producers' if groups==1 else 'PROSPECTIVE grouped launch/epoch model: empty-config source/actual prefix not implemented or measured')
 results.append(r);print('SLICE_PIN_MODEL',groups,P,r['PASS'],'faults',len(model['faults']),'writes',len(writes),'missing',len(missing),'badvalues',len(bad),flush=True)
(O/'slice_model.json').write_text(json.dumps(dict(scope='ACTUAL_EIGHT_PRODUCERS_PLUS_CALIBRATED_CAP_PIN_MODEL; NOT_FULL_STAGE_ADMISSION',source='de1ee5768+Fdc702',full_stage_qualified=False,transport='zero external links; native pin-replay schedule, not current die source ages',physical='F/E clock and GRT FAIL unchanged',inputs=inputs,expected_rows=32,results=results),indent=1)+'\n')

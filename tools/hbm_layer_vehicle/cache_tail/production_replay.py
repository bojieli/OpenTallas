"""Replay exact failed production events; recover golden operands, never recompile a schedule."""
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

root=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(root/'tools/hbm_layer_vehicle'))
import toksim_smhbm as T

base=Path('/srv/opentallas-scratch/claude/hbm-smxl-1019')
case=os.environ.get('SMXL_CASE','xl_dsA_6a')
assert case.replace('_','').isalnum(), case
run=base/'work'/('run_'+case)
original=base/'out'/(case+'.json')
out=root.parent/'production'/case;out.mkdir(parents=True,exist_ok=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
old=json.loads(original.read_text());events=old['events']
gold=[]
for name in dict.fromkeys(op['layer'] for op in old['ops']):
 for n in ['records.json','operands.npz']:gold.append(root/'results/rtl/hbm_ds_layer_tput_1018/fixtures'/name/n)
 for n in ['weights.json','weights.npz']:gold.append(base/'smw'/name/n)
files=list(dict.fromkeys(T.SM_FILES+T.SVC_FILES+T.SAFE_FILES+[T.TB]))
manifest=dict(source_commit='ecec735b6',base_source='fff9933b',
              source_sha256={p:sha(root/p) for p in files},
              golden_sha256={str(p):sha(p) for p in gold},
              replay_checker_sha256=sha(Path(__file__)),
              validation_tools_sha256={str(p):sha(Path(p)) for p in [T.__file__,T.S.__file__,T.S.MV.__file__]},
              original_json_sha256=sha(original),event_sha256={n:sha(run/n) for n in ['ing.hex','xw.hex','ids.hex','mem.hex']},
              defines=['TOKSIM_SAFE_PC','XSLOT','OPEN_IL','CACHE_TRACE'],events=events,
              scope='Exact source3 legacy SAFE controller mechanism replay; not current MC3c production rate or physical qualification')
(out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
exe=T.build(root.parent/'work',root,['XSLOT','OPEN_IL','CACHE_TRACE'])
args=[str(exe),f'+ING={run}/ing.hex',f'+XW={run}/xw.hex',f'+IDS={run}/ids.hex',f'+MEM={run}/mem.hex',
      *[f'+{k}={events[k]}' for k in ['NI','NX','ND','END']]]
manifest.update(executable_sha256=sha(exe),argv=args,argv_sha256=hashlib.sha256(json.dumps(args).encode()).hexdigest())
(out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
p=subprocess.run(args,cwd=out,text=True,capture_output=True)
log=p.stdout+p.stderr;(out/'run.log').write_text(log)
res,gos,runs,fault,done=T.S.parse(log)
# Decode immutable descriptor-table writes, not a freshly generated schedule.
desc={}
for line in (run/'ing.hex').read_text().splitlines():
 v=int(line,16);target=(v>>309)&255;addr=(v>>297)&4095;data=(v>>41)&((1<<256)-1)
 if ((v>>319)&1) and target==64 and ((addr>>10)&3)==1 and data>>240==0x5d15:
  desc[addr&1023]=data
assert len(desc)==old['budget']['descriptors'], (len(desc),old['budget']['descriptors'])
expected_go=[(desc[k]>>119)&((1<<24)-1) for k in sorted(desc)]
go_ok=len(gos)==len(expected_go) and all(g[2]==e for g,e in zip(gos,expected_go))
# Original JSON operation windows plus original fixture golden arrays. No new
# ingress, x-load schedule, weight image, or compiler pacing is generated.
kinds=[]
for name in dict.fromkeys(op['layer'] for op in old['ops']):
 recs=T.S.layer_records(root/'results/rtl/hbm_ds_layer_tput_1018/fixtures'/name,base/'smw'/name)
 R={op['k']:op['R'] for op in old['ops'] if op['layer']==name}
 for r in recs:
  if r['k'] in R:r['R']=R[r['k']]
 kinds.append(dict(name=name,recs=recs))
ops,numeric=T.S.check(dict(ops=old['ops'],kinds=kinds),res)
ok=p.returncode==0 and fault is None and done is not None and numeric and go_ok and len(runs)==len(kinds)
doc=dict(verdict='PASS_MECHANISM_ONLY' if ok else 'FAIL',run_rc=p.returncode,fault=fault,done=done,
         results=len(res),ops=ops,numeric_all=numeric,go_slots_exact=go_ok,gos=len(gos),expected_gos=len(expected_go),
         runs_done=runs,manifest_sha256=sha(out/'manifest.json'),run_log_sha256=sha(out/'run.log'),
         price_qualified=False,current_controller_qualified=False,physical_qualified=False)
(out/'result.json').write_text(json.dumps(doc,indent=2,default=str)+'\n')
print(json.dumps({k:v for k,v in doc.items() if k!='ops'},indent=2,default=str))
raise SystemExit(0 if ok else 1)

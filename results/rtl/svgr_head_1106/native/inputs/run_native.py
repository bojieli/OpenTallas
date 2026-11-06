#!/usr/bin/env python3
from pathlib import Path
import os,sys,json,subprocess,hashlib,re,time
root=Path(__file__).resolve().parent
src=root/'src'; hist=Path('/srv/opentallas-scratch2/claude/hbm-gaps-5-lec/bench')
os.environ['SMB_SOURCE_ROOT']=str(src)
sys.path.insert(0,str(src/'tools/hbm_layer_vehicle'))
import smb_unit as m
work=root/'work';work.mkdir(exist_ok=True)
exe=m.build(work,hist/'bundle',['OT_SVGR_OWN_RF1'])
comp=m.compile_all(src/'results/rtl/hbm_ds_layer_tput_1018/fixtures',hist/'smw',m.parse_layers('L00:0'),'')
events=root/'events'; n=m.write_events(comp,events)
(root/'events.json').write_text(json.dumps(n,indent=2)+'\n')
go_at=[b['go_at'] for k in comp['kinds'] for b in comp['descs'][k['d0']:k['d1']]]
args=[str(exe),f'+ING={events}/ing.hex',f'+XW={events}/xw.hex',f'+IDS={events}/ids.hex',f'+MEM={events}/mem.hex',f'+NI={n["NI"]}',f'+NX={n["NX"]}',f'+ND={n["ND"]}',f'+END={n["END"]}']
reports=[]; caught=set()
for case,extra in [('ordinary',[]),('stalled',['+STALLTEST']),('stalled_reset',['+STALLTEST','+RESET_REPLAY'])]:
 t=time.time();r=subprocess.run(args+extra,capture_output=True,text=True,cwd=events)
 log=r.stdout+r.stderr;(root/f'{case}.log').write_text(log)
 caseok=r.returncode==0
 for epoch,part in enumerate(log.split('RESET_REPLAY_BEGIN')):
  res,gos,runs,fault,done=m.parse(part)
  ops,ok=m.check(comp,res)
  gok=len(gos)==len(go_at) and all(g[2]==ga for g,ga in zip(gos,go_at))
  ok=ok and gok and fault is None and done is not None and len(runs)==len(comp['kinds'])
  caseok=caseok and ok
  reports.append(dict(case=case,epoch=epoch,run_rc=r.returncode,verdict='PASS' if ok else 'FAIL',ops=len(ops),ops_pass=sum(o['verdict']=='PASS' for o in ops),gos=len(gos),go_slots_exact=gok,fault=fault,done=done,elapsed_s=round(time.time()-t,2)))
 for match in re.finditer(r'HEAD_MUTANT PC=(\d+) MUT=(\d+) caught=(\d+) accepted_checks=(\d+)',log):
  if int(match[3]):caught.add(int(match[2]))
 print(case,'PASS' if caseok else 'FAIL',reports[-1],flush=True)
 if not caseok:
  (root/'summary.json').write_text(json.dumps(dict(verdict='FAIL',cases=reports,mutants_caught=sorted(caught)),indent=2)+'\n')
  raise SystemExit(1)
 miter=re.search(r'HEAD_RING_PASS checks=(\d+) accepted_words=(\d+) resets=(\d+) extra_edges=0',log)
 if not miter or int(miter[2])<100:raise SystemExit('missing/vacuous old/new miter')
expected={8,9,10};ok=caught==expected
summary=dict(verdict='PASS' if ok else 'FAIL',extra_edges=0,cases=reports,mutants_caught=sorted(caught),exe_sha256=hashlib.sha256(exe.read_bytes()).hexdigest(),binary=str(exe))
(root/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print('NATIVE_SMB_HEAD',summary['verdict'],'mutants_caught',sorted(caught),flush=True)
if not ok:raise SystemExit(1)

#!/usr/bin/env python3
"""Preserve progressing full948 repairs; queue named immutable artifact continuations.

Neither the failed original job nor any running repair is edited or stopped.
A completion marker and four real final artifacts are required. The continuation
verifies source/constraint/file hashes, runs corner STA and its own loop re-STA,
and can close only after the original exact gate, TT/FF and actual ECO DRC pass.
"""
import argparse, hashlib, json, pathlib, re, subprocess, time

SOURCE='948dc49b1117040aae4ba7c98c9eda2016e2a5cf'
ORIGINAL='/srv/opentallas-scratch/claude/closure-loop/bfa_full_a_948dc49b1-cl'
MACRO='physical/asap7_memory_macros_v2/ot_rom_4096x274_m8'
CANDIDATES={'hm30orphan':'eco/pass1','sca':'eco-sca','scb':'eco-scb','codex4':'eco-codex4'}
PROBE=r'''
import hashlib,json,pathlib,re,sys
r=pathlib.Path(sys.argv[1]);rel=sys.argv[2];e=r/'cl'/rel
# A live sidecar's wrapper still owns its corner collection and later passes.
# Wait for the selected final positive result; the dead original wrapper is
# the sole exception, and its completed raw pass is recovered independently.
if rel!='eco/pass1':
 rc=r/'cl'/(rel+'.rc');result=e/'result.json'
 if not rc.exists() or not result.exists():raise SystemExit(3)
 if rc.read_text().strip() not in ('0','rc=0'):raise SystemExit(3)
 d=json.loads(result.read_text())
 if not all(d.get(k,-1)>=0 for k in ('score','ss_ps','ff_ps')) or d.get('drc',1)!=0:raise SystemExit(3)
 actual=(e/'orfs').resolve();e=actual.parent
log=e/'eco_mm.log'
if not log.is_file():log=e/'eco_ff.log'
if not log.is_file() or 'OT_ECO done' not in log.read_text():raise SystemExit(3)
text=log.read_text();drc=re.findall(r'Number of violations = (\d+)',text)
if not drc:raise SystemExit(4)
base=next((e/'orfs/results/asap7').glob('*/base'))
def record(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return dict(path=str(p),bytes=p.stat().st_size,sha256=h.hexdigest())
files={n:record(base/n) for n in ['6_final.odb','6_final.sdc','6_final.spef','6_final.v']}
assert all(v['bytes']>0 for v in files.values())
print(json.dumps(dict(original_run=str(r),relative_output=rel,source_commit=(r/'src/SOURCE_COMMIT').read_text().strip(),
 files=files,completed_log=record(log),drc=int(drc[-1]),constraints={p:record(r/p) for p in ['src/physical/s81_native_bf/margin/signoff_ref.sdc','cl/io_ref_routed.sdc']},
 original_wrapper_rc=(r/'cl/hold_eco.a1.rc').read_text().strip())))
'''
COPY=r'''
import hashlib,json,pathlib,shutil,sys
m=ARTIFACT_MANIFEST
proof=ORIGINAL_EXACT_PROOF
src=pathlib.Path(sys.argv[1]);dst=pathlib.Path(sys.argv[2]);cl=pathlib.Path(sys.argv[3]);old=pathlib.Path(m['original_run'])
assert (src/'SOURCE_COMMIT').read_text().strip()==m['source_commit']=='948dc49b1117040aae4ba7c98c9eda2016e2a5cf'
assert (old/'src/SOURCE_COMMIT').read_text().strip()==m['source_commit']
def verify(v):
 p=pathlib.Path(v['path']);h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 assert p.stat().st_size==v['bytes'] and h.hexdigest()==v['sha256'],str(p)
for v in list(m['files'].values())+list(m['constraints'].values())+[m['completed_log']]:verify(v)
assert m['drc']==0
assert proof['pass'] and proof['source_commit']=='948dc49b1' and proof['cases']['positive']['ok']
assert all(proof['cases'][k]['ok'] and any('DIFF' in s for s in proof['cases'][k]['markers']) for k in ['mutant_dp','mutant_recut','mutant_fxst','mutant_xst','mutant_tcg'])
old_orfs=next((old/'routes').glob('*/work/orfs'));name=next((old_orfs/'results/asap7').glob('*/base')).parent.name
orfs=dst/'work/orfs';base=orfs/'results/asap7'/name/'base';base.mkdir(parents=True,exist_ok=True);cl.mkdir(parents=True,exist_ok=True)
for n,v in m['files'].items():shutil.copy2(v['path'],base/n)
for n in ['config.mk','constraint.sdc']:
 if (old_orfs/n).exists():shutil.copy2(old_orfs/n,orfs/n)
shutil.copy2(old/'cl/io_ref_routed.sdc',cl/'artifact_io_ref_routed.sdc')
(cl/'artifact_manifest.json').write_text(json.dumps(m,indent=2)+'\n')
(cl/'original_full948_exact.json').write_text(json.dumps(proof,indent=2)+'\n')
(cl/'artifact_drc.json').write_text(json.dumps({'detailedroute__route__drc_errors':m['drc'],'evidence':m['completed_log']},indent=2)+'\n')
(dst/'STATUS').write_text('Named artifact continuation; original wrapper rc137 and job verdict remain immutable. No PNR.\n')
print('VERIFIED source948, unchanged constraints, actual completed DB/SDC/SPEF/verilog hashes, original exact gate and ECO DRC')
'''


def continuation(name, manifest, proof):
    copy=COPY.replace('ARTIFACT_MANIFEST',repr(manifest)).replace('ORIGINAL_EXACT_PROOF',repr(proof))
    cmd="set -e\npython3 - '{SRC}' '{RUN}/routes/{LABEL}' '{CL}' <<'BF_ARTIFACT_COPY'\n"+copy+"\nBF_ARTIFACT_COPY\ncd {SRC}\n"
    cmd+=f"python3 tools/w18/corner_sta.py --orfs-dir {{RUN}}/routes/{{LABEL}}/work/orfs --macro {MACRO} --post-sdc physical/s81_native_bf/margin/signoff_ref.sdc --output {{RUN}}/routes/{{LABEL}}/corner_sta.json\n"
    cmd+="python3 {CL}/meas_resta.py --orfs {RUN}/routes/{LABEL}/work/orfs --src {SRC} --out {CL}/artifact_loop_resta.json --append {CL}/artifact_io_ref_routed.sdc\nprintf 'recovery_rc=0\\ncorner_rc=0\\n' > {RUN}/routes/{LABEL}/exit\n"
    check="python3 -c \"import json;d=json.load(open('{CL}/artifact_loop_resta.json'));assert all(d[k].get('rc',1)==0 and not d[k].get('errors') and d[k].get('worst_slack_ps') is not None and d[k]['worst_slack_ps']>=0 for k in ['setup_tt','hold_ff'])\""
    return dict(name=name,block='ot_s81_bf_native',owner='Codex:bf-deadline',
      purpose='Named postroute-only continuation of completed full948 repair. Original wrapper137/NEEDS_RTL untouched; verify immutable source948, constraints and four actual final artifact hashes. No PNR; own loop routed-insertion re-STA plus original full exact gate and actual completed ECO DRC required before closure.',
      hosts=['ot-agidock128'],threads=4,peak_ram_gb=16,source=dict(branch='claude/bf-arch-20261009',commit=SOURCE),
      stages=dict(bench=[],calibrate=dict(enabled=False,reason='actual completed route, preserve source948 signoff and measured routed IO'),
        route=dict(cmd=cmd,ok="grep -q '^recovery_rc=0' {RUN}/routes/{LABEL}/exit",logs=['{CL}/artifact_manifest.json','{CL}/artifact_loop_resta.json'],threads=4,peak_ram_gb=16),
        collect=dict(cmd="mkdir -p {RUN}/record; cp {RUN}/routes/{LABEL}/corner_sta.json {RUN}/routes/{LABEL}/exit {RUN}/routes/{LABEL}/STATUS {CL}/artifact_manifest.json {CL}/artifact_loop_resta.json {CL}/artifact_drc.json {CL}/original_full948_exact.json {RUN}/record/")),
      verdict=dict(corner_sta='{RUN}/routes/{LABEL}/corner_sta.json',drc_metrics='{CL}/artifact_drc.json',
        checks=[dict(name='own_loop_resta_positive_actual_routed_IO',cmd=check)],
        post_sdc=['physical/s81_native_bf/margin/signoff_ref.sdc'],macros=[MACRO]),
      hold_eco=dict(enabled=False,reason='completed repair consumed; never duplicate or restart progressing repairs'),
      budget=dict(enabled=False,reason='same native full948 physical and cycle contract'),
      record=[dict(**{'from':'{RUN}/record','to':'results/rtl/s81_bf_artifact_continuations_20261010/'+name})],
      cycles_added='same full948 +2 partial edges versus flatQZE; zero new edges/hardware from artifact continuation',
      merge_target=None,no_bench_reason='Original source948 full exact456/912 positive and all5 true DIFF mutants embedded in immutable source-pinned continuation specification.')


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=pathlib.Path,required=True);p.add_argument('--state',type=pathlib.Path,required=True);p.add_argument('--inbox',type=pathlib.Path,required=True);a=p.parse_args()
    a.state.mkdir(parents=True,exist_ok=True)
    assets=a.root/'tools/s81/bf_artifact_recovery';expected=json.loads((assets/'constraint_hashes.json').read_text());proof=json.loads((assets/'full948_exact.json').read_text())
    while True:
      for suffix,relative in CANDIDATES.items():
        marker=a.state/(suffix+'.json')
        if marker.exists():continue
        try:
          remote=['ssh','-o','ControlPath=none','-o','ConnectTimeout=15','ot-agidock128','python3 - '+ORIGINAL+' '+relative]
          r=subprocess.run(remote,input=PROBE,text=True,capture_output=True,timeout=45)
          if r.returncode in (3,4):continue
          r.check_returncode();m=json.loads(r.stdout);assert m['source_commit']==SOURCE
          assert all(m['constraints'][k]['sha256']==v for k,v in expected.items()),'source/signoff constraints changed'
          if m['drc']!=0:
            marker.write_text(json.dumps(dict(result='completed DRC failure, no continuation queued',manifest=m),indent=2)+'\n');continue
          digest=m['files']['6_final.odb']['sha256'][:10];name=f'bfa_full948_{suffix}_{digest}-artifact'
          spec=continuation(name,m,proof)
          # The immutable completed artifact and recipe are recorded before inbox publication.
          (a.state/(name+'.spec.json')).write_text(json.dumps(spec,indent=2)+'\n')
          record=a.root/'results/rtl/s81_bf_artifact_continuations_20261010'/name/'manifest.json'
          record.parent.mkdir(parents=True,exist_ok=True)
          if record.exists():assert json.loads(record.read_text())==m,'immutable manifest differs'
          else:record.write_text(json.dumps(m,indent=2)+'\n')
          job=a.root/'tools/closure_loop/jobs'/(name+'.json')
          if job.exists():assert json.loads(job.read_text())==spec,'immutable spec differs'
          else:job.write_text(json.dumps(spec,indent=2)+'\n')
          branch=subprocess.check_output(['git','branch','--show-current'],cwd=a.root,text=True).strip()
          assert branch=='codex/bf-tcg-pinlat-20261010'
          subprocess.run(['git','add','--sparse',str(record.relative_to(a.root)),str(job.relative_to(a.root))],cwd=a.root,check=True)
          if subprocess.run(['git','diff','--cached','--quiet'],cwd=a.root).returncode:
            subprocess.run(['git','commit','-m','Preserve completed full948 repair and queue verified named artifact continuation'],cwd=a.root,check=True)
          subprocess.run(['git','push','origin',branch],cwd=a.root,check=True,timeout=120)
          a.inbox.mkdir(parents=True,exist_ok=True);target=a.inbox/job.name
          if target.exists():assert target.read_bytes()==job.read_bytes(),'inbox spec differs'
          else:
            tmp=a.inbox/(job.name+'.tmp');tmp.write_bytes(job.read_bytes());tmp.replace(target)
          marker.write_text(json.dumps(dict(result='source-pinned named continuation queued; own-loop reSTA required',name=name,manifest=m),indent=2)+'\n')
          print('ARTIFACT READY',name,'original failure untouched; own-loop reSTA mandatory',flush=True)
          # Only the named continuation changes registry state. The failed
          # original job and every still-progressing process remain untouched.
        except Exception as e:print(time.strftime('%Y-%m-%d %H:%M:%S'),suffix,repr(e),flush=True)
      time.sleep(60)

if __name__=='__main__':main()

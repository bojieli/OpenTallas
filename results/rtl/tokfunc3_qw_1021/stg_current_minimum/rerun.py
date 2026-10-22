import os,shlex,subprocess,json,hashlib
from pathlib import Path
src=Path('/srv/opentallas-scratch/claude/codex-tok-qw-2000/stg_portable/stg4')
out=Path('/srv/opentallas-scratch/claude/codex-tok-qw-2000/stg4_current_portable_rerun2');out.mkdir(exist_ok=True,parents=True)
names={'L0_qk','L0_od','lm','emb','LGPOS_qk_roperx_ropelate'};records={}
for line in (src/'runlist.txt').read_text().splitlines():
 a=shlex.split(line.replace('/srv/opentallas-scratch/claude/tokfunc-qw-1021/stg4',str(src)));cfg,name=a[:2]
 if cfg!='pos' or name not in names:continue
 d=out/name;d.mkdir();(d/'obj_n12').symlink_to(src/'pos/build/obj_n12',target_is_directory=True)
 env=dict(os.environ,DV_LOWER_VFLAGS=(src/'pos/vflags.txt').read_text().strip())
 r=subprocess.run(['python3',*a[2:],'--work',str(d)],env=env,capture_output=True,text=True)
 (d/'bench.out').write_text(r.stdout+r.stderr+'\nrc='+str(r.returncode)+'\n')
 expected=1 if 'ropelate' in name else 0
 records[name]={'exit':r.returncode,'expected_failure':bool(expected),'matched':((r.returncode!=0)==bool(expected) and ('DV_LOWER_VEC qk FAIL' in r.stdout if expected else ' PASS ' in r.stdout))}
 print(name,records[name],flush=True)
(out/'result.json').write_text(json.dumps({'current_revision':'2eaaa79c7','grade':'minimum current component rerun; exact28input match to stg4pos','binary_sha256':hashlib.sha256((src/'pos/build/obj_n12/Vtb').read_bytes()).hexdigest(),'cases':records,'verdict':'PASS' if len(records)==len(names) and all(x['matched'] for x in records.values()) else 'FAIL'},indent=1)+'\n')
raise SystemExit(0 if len(records)==len(names) and all(x['matched'] for x in records.values()) else 1)

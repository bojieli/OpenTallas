#!/usr/bin/env python3
"""Resume exact generated r3 objects after confirmed32GiB OOM; no RTL generation."""
import hashlib,json,subprocess,sys
from pathlib import Path
root=Path.cwd();out=root.parent/'run_r3';images=out/'images';obj=out/'obj'
fx=Path('/srv/opentallas-scratch/claude/codex-tok-s81-layers/fixtures/L2')
identity=json.loads((out/'identity.json').read_text());pins=identity['source_sha256'];src=list(pins)
assert pins=={p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in src}
cmd=json.loads((out/'argv.json').read_text())
meta=[json.loads((root.parent/f'vectors/{n}/meta.json').read_text()) for n in ('f','f2')]
frozen_images={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in images.iterdir() if p.is_file()}
resume={'prior_unit':'oth-ubuntu-3409076-1792646082','prior_result':'oom-kill','prior_peak_bytes':34359738368,'prior_memory_max_bytes':34359738368,'new_memory_gib':64,'compile_parallelism':2,'frontend_regenerated':False,'source_sha256':pins,'runtime_images_sha256':frozen_images,'resume_script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'original_identity_sha256':hashlib.sha256((out/'identity.json').read_bytes()).hexdigest()}
(out/'identity_before_resume.json').write_text(json.dumps(identity,indent=2)+'\n')
(out/'resume1.json').write_text(json.dumps(resume,indent=2)+'\n')
make_cmd=['make','-C',str(obj),'-f','Vtb_cap_sukv.mk','-j','2']
with (out/'build_resume1.log').open('w') as f:r=subprocess.run(make_cmd,stdout=f,stderr=subprocess.STDOUT)
resume['make_returncode']=r.returncode;(out/'resume1.json').write_text(json.dumps(resume,indent=2)+'\n')
if r.returncode:sys.exit(r.returncode)
assert frozen_images=={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in images.iterdir() if p.is_file()}
identity['compile_resume']=dict(memory_gib=64,command=make_cmd,prior_unit=resume['prior_unit'],prior_result='oom-kill',frontend_regenerated=False)
guard_dir=Path.home()/'.local/opentallas-tools/verilator-5.050/share/ot_nba_guard'
sys.path.insert(0,str(guard_dir));import verilator_nba_guard as G
guard=G.scan(str(obj));(out/'nba_guard.json').write_text(json.dumps(guard,indent=2)+'\n')
if guard['findings']:sys.exit(86)
identity['binary_sha256']=hashlib.sha256((obj/'Vtb_cap_sukv').read_bytes()).hexdigest()
identity['runtime_images_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in images.iterdir() if p.is_file()}
identity['actual_fixture_inputs_sha256']={name:hashlib.sha256((fx/name).read_bytes()).hexdigest() for name in ['weights/kv_norm.bin','weights/wkv.bin','weights/wkv.scale.bin','ops/attn.norm.scale.bin']}
identity['producer_mapping']={n:dict(frame=m['die_frame'],slice=m['slice'],rows={r:{k:v[k] for k in ('src','out_index')} for r,v in m['rows'].items()},fixture=m['fixture'],images=m['images']) for n,m in zip(('f','f2'),meta)}
identity['scoreboard_only_files']=['expect_pair.hex','meta.json','return_plan.json']
identity['reference_source_files_sha256']={p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in ['tools/hdc_golden_v41.py','tools/hdc_golden.py','tools/s81_dv/layer_prog/kv_bank_contract.py','tools/s81_dv/layer_prog/lower_vs.py']}
identity['argv']=cmd
(out/'identity.json').write_text(json.dumps(identity,indent=2)+'\n')
checks={}
for mut in (0,1):
 with (out/f'run_mut{mut}.log').open('w') as f:r=subprocess.run([str(obj/'Vtb_cap_sukv'),f'+OT_ROM_DIR={images}',f'+MUT={mut}'],stdout=f,stderr=subprocess.STDOUT)
 text=(out/f'run_mut{mut}.log').read_text();print(mut,r.returncode,text[-1500:],flush=True)
 checks[str(mut)]=(r.returncode==0 and 'CAP_SUKV_PASS' in text) if mut==0 else (r.returncode!=0 and 'PAIR_MISMATCH' in text and 'CAP_SUKV_FAIL' in text)
 if mut==0:
  with (out/'events.jsonl').open('w') as f:
   f.write(json.dumps(identity)+'\n')
   for s in text.splitlines():
    if s.startswith('JSON '):f.write(s[5:]+'\n')
assert pins=={p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in src}

(out/'result.json').write_text(json.dumps(dict(status='PASS' if all(checks.values()) else 'FAIL',checks=checks,scope='Eight ordinary L2 WKV values; Four real D4 K2 lane landings; physical flight/absolute epoch open; no full arithmetic consumer or gain lease'),indent=2)+'\n')
sys.exit(0 if all(checks.values()) else 1)

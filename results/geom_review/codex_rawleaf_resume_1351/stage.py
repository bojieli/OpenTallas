#!/usr/bin/env python3
"""Stage only static kit inputs and the reviewed placement; never launch a build."""
import argparse,hashlib,json,shutil
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--base',required=True);p.add_argument('--successor',required=True);p.add_argument('--out',required=True);p.add_argument('--src',required=True);a=p.parse_args()
b=Path(a.base).resolve();s=Path(a.successor).resolve();o=Path(a.out).resolve()
if o.exists():raise SystemExit('refuse existing output directory')
if o==b or b in o.parents:raise SystemExit('output must be separate from original kit')
o.mkdir(parents=True)
# No previous run, reports, formal scratch, failures or signoff objects are copied.
for f in b.iterdir():
 if f.is_file() and (f.suffix in {'.tcl','.py','.mk','.sdc','.json','.txt','.sh'}):
  if f.name in {'image.txt','placed.csv','run_place.log'}:continue
  shutil.copy2(f,o/f.name)
for n in ['rtl','macros','cf']:
 if (b/n).is_dir():shutil.copytree(b/n,o/n)
if (b/'lec/lec.json').is_file():
 (o/'base_lec').mkdir();shutil.copy2(b/'lec/lec.json',o/'base_lec/lec.json')
base_results=b/'run/results/asap7/kq_ot_qwen_tile_lsl_rawfault_m3_a0k/base';res=o/'run/results/asap7/kq_ot_qwen_tile_lsl_rawfault_m3_a0k/base';res.mkdir(parents=True)
shutil.copy2(s,res/'3_place.odb');shutil.copy2(base_results/'3_place.sdc',res/'3_place.sdc')
h=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
manifest=dict(schema='opentallas.rawleaf.reviewed-placement-resume.v1',tag='QC-A0-KITS-RAWLEAF rst145 continuation',source=a.src,base_kit=str(b),base_source='claude/qc-a0-kits-rawleaf-1027@9618e14b5b + rtl_lint3ea5f941bc',anchor_source=['95444301f','924a35894'],geometry_receipt='codex/pv-review-1351-1027@1110109e1 results/geom_review/codex_pv_review_1351/rawleaf_successor_review.md',goal_scope=['cts','grt'],placement='run/results/asap7/kq_ot_qwen_tile_lsl_rawfault_m3_a0k/base/3_place.odb',placement_sha256=h(res/'3_place.odb'),sdc_sha256=h(res/'3_place.sdc'),period_ps=833,uncertainty_ps=dict(setup=60,hold=25),status='PREPARED_NOT_QUEUED',pending=['root source integration/review','normal exact-source QC canary','current QC plan/slice/source preflight','fresh matching GEOM tag before AP submission'])
manifest['static_inputs_sha256']={str(f.relative_to(o)):h(f)for f in sorted(o.rglob('*'))if f.is_file()and 'run'not in f.relative_to(o).parts}
freeze=json.load(open(o/'freeze.json'));freeze['base_repo_rev']=freeze.get('repo_rev');freeze['repo_rev']=a.src.split('@')[-1];freeze['kit']=o.name;freeze['base_kit_hash']=freeze.get('kit_hash');freeze['kit_hash']=hashlib.sha256((json.dumps(manifest,sort_keys=True)).encode()).hexdigest()[:16];freeze['continuation_manifest']='RAWLEAF_RESUME.json';json.dump(freeze,open(o/'freeze.json','w'),indent=1)
# freeze is intentionally updated for this fresh recipe; retain its resulting digest.
manifest['static_inputs_sha256']['freeze.json']=h(o/'freeze.json');json.dump(manifest,open(o/'RAWLEAF_RESUME.json','w'),indent=1)
shutil.copy2(Path(__file__).with_name('resume.sh'),o/'resume.sh');(o/'resume.sh').chmod(0o755)
print(json.dumps(dict(kit=str(o),kit_hash=freeze['kit_hash'],placement_sha256=manifest['placement_sha256'],status=manifest['status'])))

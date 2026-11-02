"""Copy a fresh owned coupon; no CAD, proof, placement or route execution."""
import argparse,hashlib,json,re,shutil
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--source-kit',type=Path,required=True);p.add_argument('--tools',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
r=Path(__file__).resolve().parent;m=json.loads((r/'candidate_manifest.json').read_text());src=a.source_kit.resolve();o=a.out.resolve()
assert not o.exists() and o!=src,'fresh owned output required'
base=src/'run/results/asap7/kq_qfd_qc_su_lane_w_l1_w0e61bf/base';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(base/'5_1_grt.odb')==m['source_odb_sha256'],'actual immutable GRT snapshot mismatch'
protected=[x for x in src.glob('rtl/**/*') if x.is_file()]+[src/n for n in ['config.mk','constraint.sdc','clock_family.tcl','vclk_ff.sdc','vclk_measured_hold.tcl','setRC_rcx.tcl','freeze.json','core.json']]
protected += [x for x in (src/'macros').glob('*') if x.is_file()]
protected={str(x.relative_to(src)):sha(x)for x in protected}
shutil.copytree(src,o)
for n in ['apply_candidate.tcl','run_candidate.sh','load_candidate.tcl','candidate_manifest.json','lib_master_contract.json','combined_post.tcl','guide_coverage.py']:
 shutil.copy2(r/n,o/n)
(o/'snapshot').mkdir();shutil.copy2(base/'5_1_grt.odb',o/'snapshot/5_1_grt.odb');shutil.copy2(base/'5_1_grt.sdc',o/'snapshot/5_1_grt.sdc');shutil.copy2(base/'route.guide',o/'snapshot/route.guide')
# Native MM calls its route-stage slot4_cts; alias retains FINAL5_1 SDC bytes exactly.
shutil.copy2(base/'5_1_grt.sdc',o/'snapshot/4_cts.sdc')
toolhash={}
for x in a.tools.glob('*.py'):
 if x.name.startswith('test_') or x.name in {'lec.py','rtl_lint.py'}:continue
 shutil.copy2(x,o/x.name);toolhash[x.name]=sha(x)
for n in ['postcts_gate.tcl','pinreg_measure.tcl','geom_dump.tcl']:
 shutil.copy2(a.tools/n,o/n);toolhash[n]=sha(a.tools/n)
for n in ['orfs_hold_mm.py','orfs_hold_mm.tcl']:
 x=a.tools.parent/n;shutil.copy2(x,o/n);toolhash[n]=sha(x)
lib=json.loads((r/'selected_library_receipt.json').read_text())
(o/'selected_library_receipt.json').write_text(json.dumps(lib,indent=2)+'\n')
(o/'candidate_protected.json').write_text(json.dumps({'files':protected,'source':str(src),'source_5_1_odb_sha256':m['source_odb_sha256'],'source_final_sdc_sha256':sha(base/'5_1_grt.sdc'),'tool_overlay':toolhash,'executed':False},indent=2)+'\n')
for n,h in protected.items():assert sha(o/n)==h,n
print(o)

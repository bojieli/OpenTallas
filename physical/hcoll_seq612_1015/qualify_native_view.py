"""Check the actual native timing context and parent-accessible exported hardleaf before verdict."""
import argparse,hashlib,json,shutil,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--src',type=Path,required=True);p.add_argument('--label',required=True);a=p.parse_args()
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
corner=a.run/'routes'/a.label/'corner_sta.json';x=json.loads(corner.read_text())
tt=x['setup_tt']['worst_slack_ps'];ff=x['hold_ff']['worst_slack_ps'];odb_hash=x['setup_tt']['odb_sha256']
root=a.run/'native_views'/odb_hash[:16];raw=root/'raw';post=root/'processed';root.mkdir(parents=True,exist_ok=True)
cell='ot_hgi_coll_static_pinreg_store';macro=a.src/'physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2'
cmd=['python3',str(a.run/'cl/view_export.py'),'--orfs-dir',x['orfs_dir'],'--name',cell,'--out',str(raw),'--no-verdict','--src',str(a.src),'--post-sdc',str(a.src/'physical/qwen_die_masters/signoff/hcoll_pinreg_store141_south.sdc'),'--post-sdc',str(a.src/'physical/common_flow/io_ref_routed.sdc'),'--expect-tt',str(tt),'--expect-ff',str(ff),'--macro-view',str(macro),'--signal-max-layer','M7','--pg-max-layer','M7','--signal-audit-tcl',str(a.src/'tools/ref_tile/signal_layer_audit.tcl'),'--require-check']
subprocess.run(cmd,check=True)
post.mkdir(parents=True,exist_ok=True)
for c in ['tt','ff','ss']:shutil.copy2(raw/f'{cell}_{c}.lib',post/f'{cell}_{c}.lib')
subprocess.run(['python3',str(a.src/'tools/hier_contract/abstract_pin_stub.py'),str(raw/f'{cell}.lef'),str(post/f'{cell}.lef')],check=True)
with (root/'child_lint.json').open('w') as f:r=subprocess.run(['python3',str(a.src/'tools/hier_contract/child_lint.py'),str(post/f'{cell}.lef'),'--libs',str(post),'--cap','M7','--strict-pockets','--json'],stdout=f)
report=json.loads((root/'child_lint.json').read_text());print(json.dumps(report))
receipt={'cell':cell,'native_corner_sha256':sha(corner),'odb_sha256':odb_hash,'spef_sha256':x['setup_tt']['spef_sha256'],'native_macro_directory':str(macro),'TT_setup_ps':tt,'FF_hold_ps':ff,'SS_sensitivity_ps':x['setup_ss']['worst_slack_ps'],'raw_export':str(raw),'processed_view':str(post),'raw_LEF_sha256':sha(raw/f'{cell}.lef'),'processed_LEF_sha256':sha(post/f'{cell}.lef'),'postprocessor_sha256':sha(a.src/'tools/hier_contract/abstract_pin_stub.py'),'child_lint':report['verdict'],'timing_pass':x['closes_signoff'],'scope':'Single nativeW141 hardleaf; final routed DRC and whole endpoint qualification remain separate verdict obligations.'}
(root/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');(a.run/'native_views/latest.json').write_text(json.dumps(receipt,indent=2)+'\n')
if r.returncode:raise SystemExit(r.returncode)

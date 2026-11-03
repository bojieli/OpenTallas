from pathlib import Path
import json,shutil,sys
sys.path.insert(0,str(Path(__file__).parent))
from reset_d_mask_review import review
k=Path('/srv/opentallas-scratch2/claude/codex-bfqg-residual-guides-prep-2350/kit');r=Path(__file__).parent;t=r/'cache_control_kit';t.mkdir(exist_ok=False)
for p in k.iterdir():
 if p.name not in ['run','rtl']:(t/p.name).symlink_to(p,target_is_directory=p.is_dir())
(t/'rtl').mkdir()
for p in (k/'rtl').iterdir():
 if p.name=='ot_hgi_sm_xload_bfqg.sv':shutil.copy2(p,t/'rtl'/p.name)
 else:(t/'rtl'/p.name).symlink_to(p,target_is_directory=p.is_dir())
mapped=next(k.glob('run/results/asap7/*/base/1_2_yosys.v'));m=t/mapped.relative_to(k);m.parent.mkdir(parents=True);shutil.copy2(mapped,m)
dump=(r/'geom.tsv').read_text();typed=r/'typed.json';positive=review(dump,t,typed);assert len(positive['candidates'])==9
results=[]
for label,p in [('mapped_input',m),('source_input',t/'rtl/ot_hgi_sm_xload_bfqg.sv')]:
 before=p.read_bytes();p.write_bytes(before+b'\n// independent cache-join negative control\n')
 try:
  review(dump,t,typed)
 except ValueError as e:results.append(dict(control=label,status='REJECTED',reason=str(e)))
 else:raise AssertionError('modified input accepted: '+label)
 finally:p.write_bytes(before)
assert len(results)==2
(r/'CACHE_CONTROLS.json').write_text(json.dumps(dict(actual_native_positive=9,controls=results,original_kit_changed=False,registration_release=False),indent=2)+'\n');print('CACHE_INPUT_CONTROLS_PASS2_NATIVE_POSITIVE9')

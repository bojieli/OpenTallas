#!/usr/bin/env python3
"""Stage a new Q2NF CFG_CASE source form from the reviewed periphery geometry.
Only stage files; no automatic P&R. Usage: build_candidate.py BASE_KIT NEW_KIT
"""
from pathlib import Path
import sys,shutil,importlib.util,json,hashlib
src,out=map(lambda p:Path(p).resolve(),sys.argv[1:]);assert not out.exists()
here=Path(__file__).resolve().parent;repo=here.parents[1]
spec=importlib.util.spec_from_file_location('q2nf_cfg_patch',here/'patch_source.py');patch=importlib.util.module_from_spec(spec);spec.loader.exec_module(patch)
skip={'run','lec','views','signoff','__pycache__','face_shell_work','PLACE_DONE.txt','SOURCE_REUSE.json'}
shutil.copytree(src,out,ignore=lambda p,ns:[n for n in ns if n in skip or n.startswith('FAIL_')or n.endswith(('.log','.rc'))])
rtl=out/'rtl/ot_q2nf_rest.sv';old=rtl.read_bytes();rtl.write_text(patch.patch(old.decode()))
helper=repo/'rtl/hbm_accel/cores_split/reform_1105b/ot_q2nf_cfg_case.sv';shutil.copy2(helper,rtl.with_name(helper.name))
with(out/'config.mk').open('a')as f:f.write('\n# Same-cycle CFG_CASE class: actual native20-assignment/1615input miter PASS + wrong-data mutant killed.\noverride export VERILOG_FILES += /work/rtl/ot_q2nf_cfg_case.sv\noverride export VERILOG_DEFINES += -DOT_Q2NF_CFG_CASE\n')
(out/'SOURCE_FORM.json').write_text(json.dumps(dict(kind='Q2NF_CFG_CASE',base_kit=str(src),rtl_before=hashlib.sha256(old).hexdigest(),rtl_after=hashlib.sha256(rtl.read_bytes()).hexdigest(),opt_in='OT_Q2NF_CFG_CASE',registers_unchanged=True,pin_cycles=0,proof='actual_cfg_ref.sv:20assignments/1615freeinputs; good SAT PASS; wrong-data-word mutant FAIL',counting='DO_NOT_COUNT until current-tag signoff + exact physical plan event'),indent=1)+'\n')
for n in['DO_NOT_COUNT','HOLD_CTS','HOLD_ROUTE','PLACE_ONLY']:(out/n).write_text('Own source+geometry candidate; no CTS/route/count released.\n')
print('STAGED',out,'CFG_CASE enabled, same37-bit output register/reset/clock,0newcycles; fresh synthesis required')

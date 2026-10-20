from pathlib import Path
import re,json,subprocess,hashlib
root=Path('/work');libs=sorted(set(re.findall(r'^read_liberty (\S+)',Path('/gate/cts.log').read_text(),re.M)))
assert libs
cmd=['read_liberty '+p for p in libs]+['read_db /gate/routes/gate/work/orfs/results/asap7/order/base/5_1_grt.odb','write_verilog /work/final.v']
(root/'export.tcl').write_text('\n'.join(cmd)+'\n')
with (root/'export.log').open('w') as log:subprocess.run(['/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad','-no_init','-exit','/work/export.tcl'],stdout=log,stderr=subprocess.STDOUT,check=True)
cmd=['python3','/helpers/native_census.py','--netlist','/work/final.v','--top','qkd_hr_core_order_n32','--out','/work/final_native.json']
for p in libs:cmd+=['--liberty',p]
rc=subprocess.run(cmd).returncode
(root/'native_rc.txt').write_text(str(rc))
cmd=['python3','/helpers/textbook_lint.py','check','--netlist','/work/final.v','--top','qkd_hr_core_order_n32','--balanced-reset-profile','/gate/reset_landing.json','--out','/work/final_textbook.json','--mode','refuse']
with (root/'textbook.log').open('w') as log:r=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT)
(root/'textbook_rc.txt').write_text(str(r.returncode))
print('FINAL_AUX native_rc',rc,'textbook_rc',r.returncode)

import hashlib,json,subprocess
from pathlib import Path
R=Path('/srv/opentallas/repos/einstein-hbm-su-parent-a6e322f55')
J=Path('/srv/opentallas/jobs-overflow/einstein-hbm-su-parent-owner-a6e322f55-r1')
P=['rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv','rtl/hbm_accel/su/ot_hbm_accel_su_parent_borrow.sv','rtl/gpu_sys/ds_hbm_full20/ot_ds_hbm_cmdproc20.sv','rtl/link/ot_link_afifo.sv','rtl/gpu_sys/ot_gpu_cdc_fifo.sv','rtl/gpu_sys/ot_gpu_mreq_cdc.sv','rtl/gpu_sys/ot_gpu_xbar.sv','rtl/gpu_sys/ot_gpu_l2_slice.sv','rtl/gpu_sys/ot_gpu_hbm_partition.sv','rtl/gpu_sys/ot_gpu_memsys.sv','rtl/hdc/kv/ot_hdc_hbm_model.sv','rtl/test/tb_hbm_accel_su_parent.sv']
V=Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator'
cmd=[str(V),'--binary','--timing','-O2','-Wno-fatal','-Wno-WIDTH','--top-module','tb_hbm_accel_su_parent','-GOWNER_ONLY=1','-Mdir',str(J/'obj'),'-j','16',*map(str,[R/p for p in P])]
record={'source_commit':'a6e322f55','source_sha256':{p:hashlib.sha256((R/p).read_bytes()).hexdigest() for p in P},'command':cmd,'scope':'changed borrower grant-edge only actual CP/NC4/AW3/NS2/NPC2 backend; no engine elaboration, no synthetic completion','actual_numeric_comparison':'separate original pin15a4762ad still live; no coverage borrowed','SSFF':False,'adopted':False}
(J/'source.json').write_text(json.dumps(record,indent=2)+'\n')
with (J/'build.log').open('w') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
(J/'build.rc').write_text(str(r.returncode)+'\n')
if r.returncode:raise SystemExit(r.returncode)
rows=[]
for name,args,match in [('late_prior',['+MODE=0'],'BORROW_RACE_PASS '),('foreign_prior',['+MODE=0','+FOREIGN=1'],'PARENT_FOREIGN_PASS ')]:
 with (J/(name+'.log')).open('w') as f:r=subprocess.run([str(J/'obj/Vtb_hbm_accel_su_parent'),*args],cwd='/srv/opentallas/jobs-overflow/einstein-hbm-su-parent-15a4762ad-r1/fixture_source',stdout=f,stderr=subprocess.STDOUT)
 lines=(J/(name+'.log')).read_text().splitlines()
 rows.append({'case':name,'rc':r.returncode,'pass':r.returncode==0 and any(x.startswith(match) for x in lines)})
 if not rows[-1]['pass']:break
record.update(runs=rows,pass_exact=len(rows)==2 and all(x['pass'] for x in rows),binary_sha256=hashlib.sha256((J/'obj/Vtb_hbm_accel_su_parent').read_bytes()).hexdigest())
(J/'result.json').write_text(json.dumps(record,indent=2)+'\n')
raise SystemExit(0 if record['pass_exact'] else 1)

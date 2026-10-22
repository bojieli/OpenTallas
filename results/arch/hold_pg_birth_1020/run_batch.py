import pathlib,subprocess,os
b=pathlib.Path.cwd();old='/srv/opentallas-scratch/claude/ref_gate/hcoll_fj3_r128u-20261020-013704'
for case in ['positive','unknown','wrong','protected','wrongprotected']:
 cmd=['docker','run','--rm','-v',str(b/'hold_pg_fix')+':/fix:ro','-v',old+':/old:ro','-e','CASE='+case,'-e','BASE_ODB=/old/routes/gate/work/orfs/results/asap7/opentallas_ot_hgi_coll_fj_n2s1_r128_asap7_ref_gate/base/2_4_floorplan_pdn.odb','openroad/orfs:latest','bash','-lc','source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit /fix/batch_test.tcl']
 r=subprocess.run(cmd,capture_output=True,text=True);out=r.stdout+r.stderr;(b/f'batch_{case}.log').write_text(out);print(case,r.returncode,out[-1100:],flush=True)
 if r.returncode or 'HOLD_PG_' not in out or 'PASS' not in out:raise SystemExit(1)

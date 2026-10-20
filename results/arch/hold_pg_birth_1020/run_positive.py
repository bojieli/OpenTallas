import subprocess,pathlib
b=pathlib.Path.cwd();old=pathlib.Path('/srv/opentallas-scratch/claude/ref_gate/hcoll_fj3_r128u-20261020-013704')
for case,src in [('old',old/'src'),('fixed',b/'fixed_src')]:
 cmd=['docker','run','--rm','-v',str(b)+':/fix','-v',str(old)+':/old:ro','-v',str(src)+':/src:ro','-e',f'RESULTS_DIR=/fix/positive_{case}','-e',f'STATE_FILE=/fix/state_{case}.tcldict','openroad/orfs:latest','bash','-lc','source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit /fix/positive_hooks.tcl']
 r=subprocess.run(cmd,capture_output=True,text=True);out=r.stdout+r.stderr;(b/f'positive_{case}.log').write_text(out);print(case,r.returncode,out[-1800:],flush=True)
 if r.returncode:raise SystemExit(r.returncode)
a=sorted((b/'state_old.tcldict').read_text().splitlines());z=sorted((b/'state_fixed.tcldict').read_text().splitlines());print('ACTUAL_HOLD_NONPG_FLAGS_GEOMETRY_IDENTITY',a==z,'instances',len(a),flush=True)
if a!=z:raise SystemExit(1)
if 'unbound_protected_pg_iterms=0' not in (b/'positive_fixed.log').read_text():raise SystemExit(1)

from pathlib import Path
import subprocess
r=Path.cwd();f=r/'cand/results/arch/hold_pg_birth_1020'
t=(f/'batch_test.tcl').read_text().replace('read_db $::env(BASE_ODB)',"""set P /OpenROAD-flow-scripts/flow/platforms/asap7
read_lef $P/lef/asap7_tech_1x_201209.lef
read_lef $P/lef/asap7sc7p5t_28_R_1x_220121a.lef
foreach l [glob $P/lib/NLDM/*RVT_TT*] {read_liberty $l}
read_verilog /fix/fixture.v
link_design fixture
initialize_floorplan -die_area {0 0 40 40} -core_area {5.4 5.4 34.56 34.56} -site asap7sc7p5t
set b [ord::get_db_block]
foreach {n t} {VDD POWER VSS GROUND} {set pn [odb::dbNet_create $b $n];$pn setSpecial;$pn setSigType $t}
add_global_connection -net VDD -pin_pattern {^VDD$} -power
add_global_connection -net VSS -pin_pattern {^VSS$} -ground
""").replace('/fix/physical/common_flow/', '/src/physical/common_flow/')
(f/'fixture.v').write_text('module fixture(input a, output y); assign y=a; endmodule\n');(f/'fresh_batch.tcl').write_text(t)
for case in ('positive','unknown','wrong','protected','wrongprotected'):
 c=['docker','run','--rm','-v',str(f)+':/fix','-v',str(r/'cand')+':/src:ro','-e','CASE='+case,'openroad/orfs:latest','bash','-lc','source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit /fix/fresh_batch.tcl']
 z=subprocess.run(c,capture_output=True,text=True);out=z.stdout+z.stderr;(r/f'pg_{case}.log').write_text(out);print(case,z.returncode,out[-1200:],flush=True)
 if z.returncode or 'PASS' not in out:raise SystemExit(1)

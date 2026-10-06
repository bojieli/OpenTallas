#!/usr/bin/env python3
"""Reuse actual full32 mapped cells for source-clock/load diagnosis, not routed signoff."""
import hashlib,json,subprocess,sys,shutil
from pathlib import Path
import run_abi3_physical as D
src=Path(sys.argv[1]);out=Path(sys.argv[2]);assert src.is_absolute() and out.is_absolute() and not out.exists()
r=json.loads((src/'result.json').read_text());assert r['exit']==0 and r['shape']['NSM']==32
out.mkdir(parents=True);mapped=src/'work/orfs/results/asap7/opentallas_item9_loaded32_synth_r5/base/1_2_yosys.v'
assert hashlib.sha256(mapped.read_bytes()).hexdigest()==r['artifacts'][str(mapped.relative_to(src))]['sha256']
normal=D.normalise_netlist(mapped,out/'mapped.v');shutil.copy2(src/'work/orfs/constraint.sdc',out/'constraint.sdc')
results=[]
for corner,lib in [('ss','SS'),('ff','FF')]:
 tcl=f'''read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
foreach f [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*_RVT_{lib}_*.lib*] {{ read_liberty $f }}
read_verilog /work/mapped.v
link_design ot_gpu_coll_item9_context32_txctrl
read_sdc /work/constraint.sdc
puts "OT_CORNER {corner} IDEAL_CLOCKS_NO_WIRE_RC_NOT_SIGNOFF"
puts "OT_CORE_INPUTS [llength $core_inputs]"
puts "OT_INGRESS_INPUTS [llength $ingress_inputs]"
puts "OT_ALL_INPUTS [llength [all_inputs]]"
puts "OT_ALL_OUTPUTS [llength [all_outputs]]"
puts "OT_CLOCK_COUNT [llength [all_clocks]]"
puts "OT_WS [sta::worst_slack_cmd max]"
set regdata [all_registers -data_pins]
set outputs [all_outputs]
puts "OT_REGDATA_COUNT [llength $regdata]"
set n [expr [llength $regdata]+[llength $outputs]]
puts OT_DETAILED_SETUP
report_checks -path_delay max -group_path_count 20 -endpoint_path_count 1 -slack_max 0 -format full_clock_expanded
puts OT_ALL_FAILING_SETUP
report_checks -path_delay max -group_path_count $n -endpoint_path_count 1 -slack_max 0 -format summary
puts OT_DETAILED_HOLD
report_checks -path_delay min -group_path_count 20 -endpoint_path_count 1 -slack_max 0 -format full_clock_expanded
puts OT_ALL_FAILING_HOLD
report_checks -path_delay min -group_path_count $n -endpoint_path_count 1 -slack_max 0 -format summary
report_check_types -max_slew -max_capacitance -max_fanout -violators
exit
'''
 (out/f'{corner}.tcl').write_text(tcl)
 command=['docker','run','--rm','-v',f'{out}:/work','-w','/OpenROAD-flow-scripts/flow',D.ORFS_IMAGE,'bash','-lc',f'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit -no_init -threads 2 /work/{corner}.tcl']
 with (out/f'{corner}.log').open('w') as log:rc=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT).returncode
 results.append(dict(corner=corner,exit=rc))
 if rc:break
(out/'result.json').write_text(json.dumps(dict(source_result=r['source_commit'],source_mapped_sha256=hashlib.sha256(mapped.read_bytes()).hexdigest(),normalization=normal,results=results,ideal_clocks=True,wire_parasitics=False,physical_signoff=False,adopted=False),indent=2)+'\n')
raise SystemExit(0 if len(results)==2 and all(x['exit']==0 for x in results) else 1)

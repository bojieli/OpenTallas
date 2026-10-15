#!/usr/bin/env python3
"""Decompose the three actual routed launch failures before any next ECO."""
import subprocess
from pathlib import Path
r=Path('/srv/opentallas-scratch/codex/s81-norm-physical-1015/ctnl2-surplus-v2');v=r/'views/ot_s81_hc_ctnl_l2';out=r/'launch_probe';out.mkdir(exist_ok=True)
for c in ['tt','ff']:
 t=(v/f'export_{c}.tcl').read_text().split('write_timing_model')[0]
 t+='report_checks -to [get_ports {hrq[214] hrq[146] hrq[5]}] -path_delay max -group_path_count 3 -endpoint_path_count 1 -format full_clock_expanded -fields {slew cap fanout input_pin nets} -digits 4\n'
 t+='report_checks -to [get_ports {hrq[214] hrq[146] hrq[5]}] -path_delay min -group_path_count 3 -endpoint_path_count 1 -format full_clock_expanded -fields {slew cap fanout input_pin nets} -digits 4\nexit\n';(out/f'{c}.tcl').write_text(t)
 with (out/f'{c}.log').open('w') as log:
  p=subprocess.run(['docker','run','--rm','-v',f'{r}/orfs:/in:ro','-v',f'{r}/src:/src:ro','-v',f'{out}:/probe','-v',f'{r}/src/physical/ref_tile/s81hc_ctnl_l2_native_ref/signoff.sdc:/post0.sdc:ro','-v',f'{r}/src/physical/common_flow/io_ref_routed.sdc:/post1.sdc:ro','openroad/orfs:latest','/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad','-no_init','-exit',f'/probe/{c}.tcl'],stdout=log,stderr=subprocess.STDOUT)
  if p.returncode:raise SystemExit(p.returncode)
 print(c,'actual final ODB/SPEF path reports completed',flush=True)

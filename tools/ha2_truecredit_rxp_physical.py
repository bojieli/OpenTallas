#!/usr/bin/env python3
"""drive-1043-timing: pipelined rx (ot_ha2_truecredit_rx_p_phys) calibration/route; same shape, pins, SDC as the signal-pin rx."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]
HERE=ROOT/'physical/ha2_truecredit_20261007'


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--part',default='rx',choices=['rx'])
    # credit-ready 2026-10-08: c = ot_ha2_truecredit_rx_c_phys (CREDIT=1 receiver_ready = credit pulses), same pins/SDC
    p.add_argument('--variant',default='p',choices=['p','c'])
    p.add_argument('--run',required=True,type=Path)
    p.add_argument('--threads',type=int,default=8)
    p.add_argument('--cts-only',action='store_true')
    p.add_argument('--prepare-only',action='store_true')
    a=p.parse_args()
    run=a.run.resolve();run.mkdir(parents=True,exist_ok=False)
    model=json.loads((HERE/'model.json').read_text());part=model['parts'][a.part]
    part=dict(part,top=f'ot_ha2_truecredit_rx_{a.variant}_phys')
    manifest=dict(variant=f'rx_{a.variant}',sources=(HERE/f'rx_{a.variant}_sources.txt').read_text().splitlines())
    # hbm-blocks 2026-10-07: the CTS-only calibration run has no measurement yet; vclk latency 0 there made CTS repair
    # an input hold of -(insertion) on every data pin (rx/tx d7a64a321: hold -583, setup -1,281, 73,998 violators) and
    # the calibration never finished.  Calibrate against a nominal leaf insertion; the route uses the measured mean.
    insertion=float(os.environ.get('CK_SS_MEAN') or os.environ.get('HA2_CAL_INSERTION','650'))
    sdc=run/'screening_route.sdc'
    sdc.write_text(f'''# UNBOUND PARENT: screening assumptions only.
create_clock -name core_clk -period 833.333 [get_ports clk]
create_clock -name vclk -period 833.333
set_clock_latency {insertion} [get_clocks vclk]
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
set ot_in [all_inputs -no_clocks]
catch {{unset_input_delay $ot_in}}
catch {{unset_output_delay [all_outputs]}}
set_input_delay -max 316.6666 -clock vclk $ot_in
set_input_delay -min 0 -clock vclk $ot_in
set_output_delay -max 316.6666 -clock vclk [all_outputs]
set_output_delay -min 0 -clock vclk [all_outputs]
set_input_transition 150 $ot_in
set_load 4 [all_outputs]
''')
    sources=(HERE/f'rx_{a.variant}_sources.txt').read_text().splitlines()
    cmd=['python3','tools/run_abi3_physical.py','--view','asap7','--top',part['top']]
    for source in sources:cmd+=['--source',source]
    w,h=part['width_um'],part['height_um']
    cmd+=['--clock-period-ns','0.833333','--clock-uncertainty-ns','0.06',
          '--clock-uncertainty-hold-ns','0.025','--orfs-corner','WC','--hold-corners','WC,BC',
          '--io-delay-fraction','0.2','--sdc-append',str(sdc),'--stages','synth,pnr',
          '--die-area','0','0',str(w),str(h),'--core-area','1.08','1.08',str(w-1.08),str(h-1.08),
          '--place-density','0.55','--hold-margin-ns','0.015','--orfs-var','ADDER_MAP_FILE=',
          '--step-tcl',f'POST_IO_PLACEMENT=physical/ha2_truecredit_20261007/{a.part}_pins_signal_only.tcl',
          '--purpose','signoff_target','--nickname-tag',f'ha2_tc{a.variant}_rx',
          '--synth-timeout-seconds','unlimited','--flow-timeout-seconds','unlimited',
          '--keep-workdir',str(run/'work'),'--output',str(run/'physical.json')]
    if a.cts_only:cmd+=['--pnr-stop-after','cts']
    record=dict(part=a.part,command=cmd,source_manifest=manifest,model=model,
                route_virtual_clock_insertion_ps=insertion,parent_qualified=False,adopted=False)
    (run/'launch.json').write_text(json.dumps(record,indent=2)+'\n')
    if a.prepare_only:
        print('PREPARED_ONLY: no build, no physical verdict')
        return 0
    env=dict(os.environ,OT_ORFS_NUM_CORES=str(a.threads),NUM_CORES=str(a.threads),
             OT_SYNTH_TIMEOUT_SECONDS='unlimited',OT_FLOW_TIMEOUT_SECONDS='unlimited')
    with (run/'run.log').open('w') as log:
        build=subprocess.run(cmd,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
    (run/'build.exit').write_text(str(build.returncode)+'\n')
    if build.returncode or a.cts_only:return build.returncode
    cmd=['python3','tools/w18/corner_sta.py','--orfs-dir',str(run/'work/orfs'),
         '--post-sdc','physical/ha2_truecredit_20261007/screening_signoff.sdc',
         '--post-sdc',f'physical/ha2_truecredit_20261007/{a.part}_check_pins_signal_only.tcl',
         '--output',str(run/'corner_sta.json')]
    with (run/'corner.log').open('w') as log:
        sta=subprocess.run(cmd,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
    (run/'corner.exit').write_text(str(sta.returncode)+'\n')
    return sta.returncode


if __name__=='__main__':
    raise SystemExit(main())

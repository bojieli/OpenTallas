#!/usr/bin/env python3
"""Full64x8bit EW/NS delay-bank physical screen; run through host admission guard.

Requires a pinned clean source snapshot. Does not publish adopted die views.
Actual regional clock arrival and IO budgets remain separate qualification gates.
"""
import argparse,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def command(orientation,out):
    top=f'hfd_result_delay64x8_{orientation}'
    return ['python3','tools/run_abi3_physical.py','--view','asap7','--top',top,
      '--source','rtl/hbm_accel/result_delay_bank_20261007/ot_hbm_result_delay_bank.sv',
      '--source','rtl/hbm_accel/result_delay_bank_20261007/hfd_result_delay64x8.sv',
      '--clock-port','clk','--clock-period-ns','0.833333333','--clock-uncertainty-ns','0.060',
      '--clock-uncertainty-hold-ns','0.025','--orfs-corner','WC','--hold-corners','WC,BC',
      '--io-delay-fraction','.2','--sdc-append','physical/hbm_result_delay_bank_20261007/screening.sdc',
      '--stages','pnr','--die-area','0','0','32.4','32.4','--core-area','0','.54','32.4','31.86',
      '--place-density','.55','--routing-layers','M2','M7',
      '--orfs-var','PDN_TCL=/src/physical/hbm_accel_die_views/common/pdn_view.tcl',
      '--orfs-var',f'IO_CONSTRAINTS=/src/physical/hbm_result_delay_bank_20261007/{orientation}/pins.tcl',
      '--orfs-var','ADDER_MAP_FILE=','--orfs-var','CTS_ARGS=-apply_ndr none',
      '--step-tcl','PRE_CTS=physical/abi3/v41x_karb_repair_buffer_cap.tcl',
      '--step-tcl','PRE_GLOBAL_ROUTE=physical/abi3/v41x_karb_repair_buffer_cap.tcl',
      '--slew-margin-percent','60','--hold-margin-ns','.015','--purpose','characterization',
      '--nickname-tag',f'result_delay64x8_{orientation}',
      '--synth-timeout-seconds','unlimited','--flow-timeout-seconds','unlimited',
      '--keep-workdir',str(out/'work'),'--output',str(out/'physical.json')]

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--orientation',choices=['ew','ns'],required=True)
    ap.add_argument('--out',type=Path,required=True);ap.add_argument('--prepare-only',action='store_true');a=ap.parse_args()
    model=json.loads((ROOT/'results/uarch/hbm_result_delay_bank_20261007/model.json').read_text());a.out.mkdir(parents=True,exist_ok=False)
    args=command(a.orientation,a.out.resolve())
    (a.out/'screening_contract.json').write_text(json.dumps(dict(status='delay-bank-screen-only-not-adoptable',
      model=model,command=args,actual_clock_and_IO_binding='OPEN',protection_and_consumer_gate='OPEN',
      global_replication_fit='OPEN',acceptance_after_actual_binding='SS>=15ps,FF>=15ps,DRC0'),indent=2)+'\n')
    if a.prepare_only:
        print(json.dumps(args))
        return 0
    with (a.out/'route.log').open('w') as f:rc=subprocess.run(args,cwd=ROOT,stdout=f,stderr=subprocess.STDOUT).returncode
    (a.out/'route.exit').write_text(str(rc)+'\n')
    if rc:return rc
    with (a.out/'corner.log').open('w') as f:
      rc=subprocess.run(['python3','tools/w18/corner_sta.py','--orfs-dir',str(a.out/'work/orfs'),
         '--output',str(a.out/'corner_sta.json')],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT).returncode
    (a.out/'corner.exit').write_text(str(rc)+'\n');return rc
if __name__=='__main__':raise SystemExit(main())

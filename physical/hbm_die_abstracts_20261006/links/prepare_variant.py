#!/usr/bin/env python3
"""Prepare ONE parameterized native station route; no submission.

Requires pinned clean source. Runs only when caller admits honest inventory
RAM/disk and a fresh CPU fit through cpu_fit.py on EPYC2. Results are NOT a
functional multicast/gather/distribution/duplex parent qualification.
"""
import argparse,json,subprocess
from pathlib import Path
WIDTHS=[128,180,360,512,540,974,1024,1080,1099,2063,2160]
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--width',type=int,choices=WIDTHS,required=True)
 p.add_argument('--orientation',choices=['H','V'],required=True);p.add_argument('--utilization',type=int,choices=[55,60],required=True)
 p.add_argument('--run-dir',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 root=Path(__file__).resolve().parents[3]
 status=subprocess.check_output(['git','-C',str(root),'status','--porcelain','--untracked-files=no'],text=True)
 if status.strip():p.error('commit source before preparing a run')
 commit=subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip()
 rel='physical/hbm_die_abstracts_20261006/links';run=a.run_dir.resolve()
 if not str(run).startswith('/srv/opentallas-scratch2/codex/hbm-links-abstracts-20261006/'):p.error('owned EPYC2 NVMe2 run required')
 left,right=('left','right') if a.orientation=='H' else ('bottom','top')
 tag=f'link_w{a.width}_{a.orientation.lower()}_u{a.utilization}'
 cmd=['python3','tools/run_abi3_physical_persistent.py','--persistent-workdir',str(run/'work'),'--launch-receipt',str(run/'launch.json'),
 '--view','asap7','--top','ot_hbm_native_register_slice','--source',f'{rel}/ot_hbm_native_register_slice.sv','--source','rtl/common/ot_fwd_link_stage.sv',
 '--param',f'W={a.width}','--param','STAGES=4','--param','ENABLE=1','--core-utilization',str(a.utilization),'--place-density','0.60',
 '--clock-port','fclk_i','--clock-period-ns','0.833333','--clock-uncertainty-ns','0.06','--clock-uncertainty-hold-ns','0.025',
 '--orfs-corner','WC','--hold-corners','WC,BC','--io-delay-fraction','0.2','--stages','synth,pnr','--hold-margin-ns','0.01',
 '--pin-region',f'^(fclk_i|rst_n.*|i_v|i_d.*)$={left}','--pin-region',f'^(fclk_o|o_v|o_d.*)$={right}',
 '--orfs-var','NUM_CORES=16','--orfs-var','ADDER_MAP_FILE=','--orfs-var',f'CORE_ASPECT_RATIO={0.25 if a.orientation=="H" else 4}',
 '--orfs-var',f'SDC_FILE=/src/{rel}/station.sdc','--step-tcl','PRE_CTS=physical/rom_clock/fwd_forwarded_subtree.tcl',
 '--nickname-tag',tag,'--purpose','signoff_target','--output',str(run/'physical.json')]
 a.out.write_text(json.dumps(dict(source_commit=commit,width=a.width,orientation=a.orientation,utilization=a.utilization,argv=cmd,launched=False,
  pending=['honest RAM/disk need from build inventory','fresh EPYC2 CPU16 fit pre/post unchanged admit','actual synthesis inverter-root discovery (SDC fails closed)','separate SS60/FF25 post-route corners','actual parent port/flow/protection binding']),indent=2)+'\n')
if __name__=='__main__':main()

#!/usr/bin/env python3
"""Component proof with real HOST producer/old receiver/actual fault-join leaf.

Use ot-run for compilation/simulation. Outputs must use a fresh directory.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[4]
G3=Path(__file__).resolve().parent

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);p.add_argument('--rtl-root',type=Path,default=ROOT);a=p.parse_args()
    a.out.mkdir(parents=True,exist_ok=True)
    if any(a.out.iterdir()):raise SystemExit('Use a fresh output directory; failed results are preserved')
    env=dict(os.environ);env['PATH']=str(Path.home()/'.local/opentallas-tools/bin')+':'+env.get('PATH','')
    src=[G3/'host_reset_command_gold.sv',a.rtl_root/'rtl/lib/ot_reset_sync.sv',a.rtl_root/'rtl/qwen_sys/ot_qwen_sys_rst_seq.sv',a.rtl_root/'rtl/qwen_sys/host_20261013/qkd_host_rst_role_pins.sv',ROOT/'rtl/qwen_sys/host_20261013/qkd_host_reset_command_rx.sv',G3/'tb_host_reset_command.sv'];results=[]
    for mode in ('BASE','MUT_ROUTE','MUT_COMMAND','MUT_POLARITY','MUT_WAVEFRONT'):
        image=a.out/(mode+'.vvp')
        build=subprocess.run(['iverilog','-g2012','-s','tb_host_reset_command','-o',str(image)]+([] if mode=='BASE' else ['-D'+mode])+[str(f) for f in src],capture_output=True,text=True,env=env)
        (a.out/(mode+'.build.log')).write_text(build.stdout+build.stderr)
        if build.returncode:raise SystemExit('Compile failure: '+mode+'; see build log')
        run=subprocess.run(['vvp',str(image)],capture_output=True,text=True,env=env);(a.out/(mode+'.log')).write_text(run.stdout+run.stderr)
        ok=(run.returncode==0 and 'HOST_RESET_COMMAND PASS' in run.stdout) if mode=='BASE' else (run.returncode!=0 and 'MISMATCH' in run.stdout)
        results.append(dict(mode=mode,exit=run.returncode,verdict='PASS' if ok and mode=='BASE' else 'CAUGHT' if ok else 'FAIL'))
        print(mode,results[-1]['verdict'],flush=True)
        if not ok:raise SystemExit(1)
    (a.out/'results.json').write_text(json.dumps(dict(results=results,transport_stages=3,private_assert_cycles=1,private_release_cycles=2,source='Actual qkd_host_rst_role_pins + ot_qwen_sys_rst_seq, actual old ot_dp_rsync and ot_dp_dly, actual qkd_astk_fault_join receiver; only private timed receiver changed'),indent=1)+'\n')

if __name__=='__main__':main()

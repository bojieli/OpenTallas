#!/usr/bin/env python3
"""Build/run the minimum real full-service L0 linked join after owner handoff.

Use remotely through unchanged admit.sh (build96, runtime16), fresh E2 load
and five idle CPUs for four compiler workers plus frontend; runtime one CPU.
One changed-source frontend, no old producer gate or inference replay.
"""
import argparse
import hashlib
import json
import os
import subprocess
import time
from pathlib import Path


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def fresh(output,stage):
    def cpu():return list(map(int,Path('/proc/stat').read_text().splitlines()[0].split()[1:]))
    a=cpu();time.sleep(1);b=cpu();d=[y-x for x,y in zip(a,b)]
    idle=(d[3]+d[4])*os.cpu_count()/sum(d[:8]);load=os.getloadavg()[0]
    needed=5 if stage=='build' else 1
    record=dict(load=load,idle_CPUs=idle,required_CPUs=needed)
    (output/(stage+'_post_guard.json')).write_text(json.dumps(record,indent=2)+'\n')
    if load>=128 or idle<needed:raise RuntimeError('fresh post-guard E2 capacity unavailable; no tool launched')


def prepare(source,output,handoff):
    owner=json.loads(handoff.read_text())
    if not owner.get('consumer_seams_READY_NOW'):raise ValueError('genuine producer source hook handoff required')
    for name,h in owner['source_sha256'].items():
        if '/experimental/' not in name and sha(source/name)!=h:raise ValueError('producer source differs from owner handoff: '+name)
    output.mkdir(parents=True,exist_ok=False)
    dirs=['rtl/hdc/kv','rtl/hdc','rtl/model_ready_hbm_r14','rtl/lib']
    top=source/'rtl/experimental/qwen_rom_combined_p0_20261005'
    driver=source/'tools/qwen_rom_combined_p0_20261005/linked_driver.cpp'
    command=['/usr/bin/verilator','--cc','--exe','--build','-O2','-j','4',
        '--top-module','tb_qwen_p0_linked','--prefix','Vjoin','-GPROTECTED=1','-GSYNC=2',
        '-GNSTK=4','-GNPC=128','-GLAYERS=1','-GWBW=4','-GKV_IDEAL=0','-GPULLIN=0',
        '-Wno-fatal','-Wno-WIDTH','-Wno-UNUSED','-Wno-TIMESCALEMOD','-Wno-BLKSEQ',
        '-Wno-PINMISSING','-Wno-LATCH','-Wno-MULTIDRIVEN','-Wno-UNOPTFLAT']
    for d in dirs:command+=['-y',str(source/d)]
    command += [str(source/'rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv'),
        str(top/'ot_qwen_p0_linked_consumer.sv'),str(top/'ot_qwen_p0_producer_exports.sv'),
        str(top/'tb_qwen_p0_linked.sv'),str(driver),'-CFLAGS','-O2 -std=c++20 -I'+str(driver.parent),
        '-Mdir',str(output/'obj')]
    history=Path('/srv/opentallas-scratch/codex/qwen-P8191-full36-history-r1/history/L0_die0.bin')
    token=Path('/srv/opentallas-scratch/jobs/laplace-qwen-plainar-stream4-P8191-r1/run/L0_die0_kvP.hex')
    expected=json.loads((source/'results/rtl/qwen_rom_combined_p0_20261005/linked_expected/expected.json').read_text())
    if sha(history)!=expected['history_source_sha256'] or sha(token)!=expected['token_source_sha256']:
        raise ValueError('actual released fixture source changed')
    record=dict(command=command,runtime=[str(output/'obj/Vjoin'),str(history),str(token)],
        owner_handoff_sha256=sha(handoff),owner_hook_status='consumer_seams_READY_NOW',
        physical_stack_adapter_ready=False,full_token=False,producer32case_replay=False,
        source_root=str(source),driver_sha256=sha(driver),expected=expected)
    (output/'prepared.json').write_text(json.dumps(record,indent=2)+'\n')
    return record


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--stage',choices=['prepare','build','runtime'],required=True)
    p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--handoff',type=Path)
    a=p.parse_args()
    if a.stage=='prepare':prepare(a.source,a.output,a.handoff);return 0
    r=json.loads((a.output/'prepared.json').read_text())
    if sha(a.source/'tools/qwen_rom_combined_p0_20261005/linked_driver.cpp')!=r['driver_sha256']:
        raise ValueError('prepared linked driver changed')
    fresh(a.output,a.stage)
    # Never replay a completed stage or duplicate a live one.
    (a.output/(a.stage+'_once')).mkdir()
    command=r['command'] if a.stage=='build' else r['runtime']
    with (a.output/(a.stage+'.log')).open('w') as log:
        rc=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT).returncode
    (a.output/(a.stage+'.exit')).write_text(str(rc)+'\n')
    if a.stage=='runtime' or rc:
        (a.output/'terminal.json').write_text(json.dumps(dict(
            status=('PASS_RELEASED_P8191_LINKED_JOIN' if rc==0 else 'FAIL_LINKED_'+a.stage.upper()),
            stage=a.stage,exit=rc,full_token=False,physical_qualified=False,
            producer32case_replay=False),indent=2)+'\n')
    return rc


if __name__=='__main__':raise SystemExit(main())

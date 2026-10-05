#!/usr/bin/env python3
"""Build the existing CKV C8 service only, with four actual DIE_ID variants.

No executable/testbench, custom ABI, HBM backend, AG stand-in, or native run.
Generated models take the enclosing runtime's VerilatedContext* constructor.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
TOP = 'ot_chip_v41x_ckv_die_service_c8'
SOURCES = ['rtl/dsrom_sys/c8/' + TOP + '.sv'] + [
    'rtl/chip/ot_chip_v41x_ckv_' + name + '.sv' for name in
    ['sel_ids', 'row_encoder', 'sel_fetch', 'selected_dma', 'fp4_decode', 'stream_merge']]
PARAMETERS = dict(C8_PUBLICATION=1, K=512, POS_W=21, AW=30, VWA=15,
                  HAW=30, TAGW=16, CKV_BASE=4194304, CKV_SECTORS=589824, NSLOT=64)


def write(path, data):
    path.write_text(json.dumps(data, indent=2) + '\n')


def headroom(path):
    memory = {}
    for line in Path('/proc/meminfo').read_text().splitlines():
        name, value = line.split(':', 1)
        if name in ['MemTotal', 'MemAvailable', 'SwapFree']:
            memory[name] = int(value.split()[0]) * 1024
    return dict(memory_bytes=memory, disk_free_bytes=shutil.disk_usage(path).free,
                CPUs=os.cpu_count(), load=os.getloadavg())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--jobs', type=int, required=True)
    args = parser.parse_args()
    if args.jobs < 1:
        raise ValueError('measured CPU concurrency required')
    if subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT).strip():
        raise RuntimeError('build requires clean pinned source')
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    tool = Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator'
    record = dict(scope='existing CKV C8 service native header/archive only',
                  supervisor_pid=os.getpid(), source_commit=subprocess.check_output(
                      ['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                  source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
                                 for p in SOURCES},
                  verilator=str(tool), version=subprocess.check_output(
                      [str(tool), '--version'], text=True).strip(),
                  parameters=PARAMETERS, actual_ranks=[0, 1, 2, 3],
                  initial_headroom=headroom(out), jobs=args.jobs,
                  runtime_context='construct each model with EXISTING Runtime.context; no own context/runtime',
                  limits='No wall/CPU time, file size or address-space caps; preserve completed objects',
                  ranks=[])
    write(out/'start.json', record)
    for rank in range(4):
        directory = out/f'rank{rank}'
        directory.mkdir()
        model = f'VDsromS81CkvRank{rank}'
        obj = directory/'obj'
        params = dict(PARAMETERS, DIE_ID=rank)
        frontend = [str(tool), '--cc', '--top-module', TOP, '--prefix', model,
                    '--Mdir', str(obj), '--output-split', '20000',
                    '--output-split-cfuncs', '200', '-Wno-fatal',
                    '-CFLAGS', '-O0 -fPIC'] + [f'-G{k}={v}' for k,v in params.items()] + [
                        str(ROOT/p) for p in SOURCES]
        compile_cmd = ['make', '-C', str(obj), '-f', model+'.mk',
                       '-j'+str(args.jobs), 'OPT_FAST=-O0', 'OPT_SLOW=-O0', model+'__ALL.a']
        item = dict(rank=rank, model=model, parameters=params,
                    header=str(obj/(model+'.h')), archive=str(obj/(model+'__ALL.a')),
                    stages=[], headroom=headroom(out))
        for phase, command in [('frontend', frontend), ('archive', compile_cmd)]:
            started = time.monotonic()
            with (directory/(phase+'.log')).open('w') as log:
                process = subprocess.Popen(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
                write(out/'progress.json', dict(supervisor_pid=os.getpid(),rank=rank,
                      phase=phase,child_pid=process.pid,header=item['header'],archive=item['archive']))
                rc = process.wait() # No deadline. Host capacity sampled between stages.
            item['stages'].append(dict(phase=phase, pid=process.pid, exit=rc,
                                      seconds=time.monotonic()-started, command=command))
            if rc:
                item['verdict']='FAIL_PRESERVED_NO_RETRY'
                write(directory/'FAILED.json', item)
                record['ranks'].append(item)
                record['verdict']='FAIL_PRESERVED_NO_RETRY'
                write(out/'FAILED.json', record)
                return rc
        item['verdict']='PASS_NATIVE_ARCHIVE_ONLY'
        write(directory/'ready.json', item) # immediately consumable before next rank finishes
        record['ranks'].append(item)
        write(out/'ready_ranks.json', record['ranks'])
    record['verdict']='PASS_FOUR_ACTUAL_RANK_ARCHIVES_ONLY'
    record['final_headroom']=headroom(out)
    write(out/'ready.json', record)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

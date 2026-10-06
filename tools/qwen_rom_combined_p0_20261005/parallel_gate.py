#!/usr/bin/env python3
"""One changed32-PC topology build/run, remotely under unchanged admission.

No fulltoken build, leaf gate replay or substitute endpoint. Preparation
requires the actual Descartes sector-protected RSEL1 adapter source.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fresh(out, stage):
    def cpu():
        return list(map(int, Path('/proc/stat').read_text().splitlines()[0].split()[1:]))
    a = cpu(); time.sleep(1); b = cpu()
    d = [y-x for x,y in zip(a,b)]
    idle = (d[3]+d[4])*os.cpu_count()/sum(d[:8])
    load = os.getloadavg()[0]
    needed = 5 if stage == 'build' else 1
    memory = int(next(s.split()[1] for s in Path('/proc/meminfo').read_text().splitlines() if s.startswith('MemAvailable:')))*1024
    fs = os.statvfs(out); disk = fs.f_bavail*fs.f_frsize
    r = dict(load=load, idle_CPUs=idle, required_CPUs=needed,
             memory_available_bytes=memory, disk_available_bytes=disk,
             memory_inventory_estimate_bytes=(16 if stage=='build' else 2)*2**30,
             estimate_is_not_process_limit=True, projected_load_limit=110)
    (out/(stage+'_fresh.json')).write_text(json.dumps(r, indent=2)+'\n')
    if load+needed>110 or idle<needed or memory<r['memory_inventory_estimate_bytes'] or disk<8*2**30:
        raise RuntimeError('fresh priority CPU/RAM/NVMe fit unavailable; no child launched')


def prepare(source, out, history, verilator):
    leaf = source/'rtl/hdc/kv/ot_qwen_s4_parallel_protected_pc.sv'
    if not leaf.is_file():
        raise FileNotFoundError('genuine owner parallel protected RSEL1 adapter required')
    # Structural recipe check only; owner numerical/negative results remain
    # separate evidence. Never use the former full504 leaf as a rawCDC alias.
    if 'ot_qwen_stream4_cdc_pc' not in leaf.read_text():
        raise ValueError('owner requested actual ot_qwen_stream4_cdc_pc RSEL1 instance absent')
    version = subprocess.check_output([str(verilator), '--version'], text=True).strip()
    if not version.startswith('Verilator 5.050 '):
        raise ValueError('canonical matching5.050 tool required')
    out.mkdir(parents=True, exist_ok=False)
    helper=source/'tools/qwen_rom_combined_p0_20261005/parallel_fixture.py'
    subprocess.run(['python3', str(helper), '--history', str(history), '--output', str(out/'fixture')], check=True)
    exp=source/'rtl/experimental/qwen_rom_combined_p0_20261005'
    files=[source/'rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv', leaf,
           exp/'ot_qwen_p0_parallel_bank.sv', exp/'tb_qwen_p0_parallel_bank.sv']
    command=[str(verilator), '--binary', '--timing', '--threads', '1',
             '-O3', '-j', '4', '--top-module', 'tb_qwen_p0_parallel_bank',
             '--prefix', 'Vparallel', '-Wno-fatal', '-Wno-TIMESCALEMOD',
             '--Mdir', str(out/'obj')]
    dirs=['rtl/hdc/kv','rtl/hdc/v41x','rtl/hdc','rtl/lib','rtl/experimental/w2_nc6_protection_20261003']
    for directory in dirs:
        command+=['-y', str(source/directory)]
    command += list(map(str, files))
    # Pin all source files in the search libraries, not only explicit roots.
    inventory={str(p):sha(p) for directory in dirs for p in (source/directory).glob('*.sv')}
    inventory.update({str(p):sha(p) for p in files})
    record=dict(status='PREPARED_CHANGED_PARALLEL32_ONLY', source_sha256=inventory,
                version=version, build=command,
                runtime=[str(out/'obj/Vparallel'), '+GOLD='+str(out/'fixture/gold.hex')],
                full_token=False, physical_qualified=False, leaf_gate_replayed=False,
                requires_external_unchanged_admission=True)
    (out/'prepared.json').write_text(json.dumps(record, indent=2)+'\n')


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--stage', choices=['prepare','build','runtime'], required=True)
    ap.add_argument('--source', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--history', type=Path)
    ap.add_argument('--verilator', type=Path)
    args=ap.parse_args()
    if args.stage=='prepare':
        prepare(args.source,args.output,args.history,args.verilator);return 0
    r=json.loads((args.output/'prepared.json').read_text())
    for p,h in r['source_sha256'].items():
        if sha(Path(p))!=h:
            raise ValueError('prepared source changed: '+p)
    fresh(args.output,args.stage)
    (args.output/(args.stage+'_once')).mkdir()
    command=r['build' if args.stage=='build' else 'runtime']
    with (args.output/(args.stage+'.log')).open('x') as log:
        rc=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT).returncode
    (args.output/(args.stage+'.exit')).write_text(str(rc)+'\n')
    if rc or args.stage=='runtime':
        passed=rc==0 and 'PASS parallel32 releasedK/V' in (args.output/'runtime.log').read_text()
        status='PASS_RELEASED_PARALLEL32_COMPONENT' if passed else 'FAIL_PARALLEL32_'+args.stage.upper()
        (args.output/'terminal.json').write_text(json.dumps(dict(status=status, exit=rc,
            scope='32PC independent protected landing/WR/ACK/warm component only',
            source_sha256=r['source_sha256'], full_token=False, physical_qualified=False),indent=2)+'\n')
        if rc==0 and not passed:return 1
    return rc


if __name__=='__main__':
    raise SystemExit(main())

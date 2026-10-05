#!/usr/bin/env python3
"""Resource-bounded unchanged full-geometry attention compiler probe.

Default is plan-only. --run executes front-end hierarchy generation; it does
NOT establish that the C++ build, RTL numeric simulation or timing passes.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import time

FILES = [
    'rtl/hdc/v41x/ot_hdc_v41x_attn_tile.sv',
    'rtl/hdc/v41x/ot_hdc_v41x_attn.sv',
    'rtl/hdc/v41x/ot_hdc_v41x_attn_staging.sv',
    'physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v',
    'rtl/hdc/ot_hdc_fastfp.sv',
    'rtl/test/tb_hdc_v41x_attn.sv',
]
PARAMS = dict(H=16, D=512, TD=32, NL=4, TROWS=640)

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def command(root, verilator, out, hierarchy):
    return [str(verilator), '--cc', '--top-module', 'tb_hdc_v41x_attn',
            '--prefix', 'Vtb', '-Mdir', str(out / 'obj'), '-j', '1',
            '-Wno-fatal', '-Wno-WIDTH', '-Wno-TIMESCALEMOD',
            '--output-split', '20000', '--output-split-cfuncs', '2000',
            '--unroll-count', '1', '--unroll-limit', '131072',
            *[f'-G{k}={v}' for k, v in PARAMS.items()],
            *(['--hierarchical', str(hierarchy)] if hierarchy else []),
            *[str(root / p) for p in FILES]]

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root', type=Path, required=True)
    ap.add_argument('--verilator', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--flat', action='store_true')
    ap.add_argument('--run', action='store_true')
    ap.add_argument('--seconds', type=int, default=180)
    ap.add_argument('--memory-gib', type=int, default=8)
    args = ap.parse_args()
    if not 1 <= args.seconds <= 180 or not 1 <= args.memory_gib <= 8:
        ap.error('Probe limited to 180 seconds and 8 GiB per process; larger work requires a new review')
    root, out = args.root.resolve(), args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    hierarchy = None if args.flat else Path(__file__).with_name('v41_attention_hierarchy.vlt').resolve()
    pins = {p: sha(root / p) for p in FILES}
    cmd = command(root, args.verilator.resolve(), out, hierarchy)
    record = dict(schema='opentallas.v41-attention-compile-probe.v1',
                  status='plan_only', parameters=PARAMS, tile_instances=64,
                  source_sha256=pins, command=cmd,
                  hierarchy_sha256=sha(hierarchy) if hierarchy else None,
                  claim_boundary='Full D512/T640 geometry. Compiler front-end only; no built executable, numeric verdict, schedule or rate claim.',
                  memory_limit_kind='per-process RLIMIT_AS; compiler jobs=1, not a cgroup aggregate cap',
                  memory_gib=args.memory_gib, wall_limit_seconds=args.seconds)
    if args.run:
        def limits():
            lim = args.memory_gib * 1024**3
            resource.setrlimit(resource.RLIMIT_AS, (lim, lim))
            resource.setrlimit(resource.RLIMIT_CPU, (args.seconds, args.seconds + 1))
        start = time.monotonic()
        with (out / 'frontend.log').open('w') as log:
            process = subprocess.Popen(cmd, cwd=root, stdout=log, stderr=subprocess.STDOUT,
                                       start_new_session=True, preexec_fn=limits)
            try:
                rc = process.wait(timeout=args.seconds)
                record['status'] = 'frontend_returned_zero' if rc == 0 else 'frontend_failed'
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                rc = process.wait()
                record['status'] = 'wall_limit'
        record.update(returncode=rc, elapsed_seconds=round(time.monotonic()-start,3),
                      max_child_rss_kib=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
                      source_stable=pins == {p: sha(root / p) for p in FILES},
                      log_sha256=sha(out / 'frontend.log'),
                      generated_cpp=len(list((out/'obj').glob('*.cpp'))))
    (out / 'result.json').write_text(json.dumps(record, indent=2)+'\n')
    print(json.dumps({k:record[k] for k in ('status','parameters','claim_boundary')}))
    if args.run and record['status'] != 'frontend_returned_zero':
        raise SystemExit(1)

if __name__ == '__main__':
    main()

"""DS-V4.1 HBM accelerator / baseline at 1M: the STATIC load stream of one die on the real DRAM path (RTL, Verilator).

Every byte one die reads for a token except the routed experts (attention / gate / shared-expert / head weight
slices, index keys, window and gathered compressed-KV rows: results/rtl/dshbm_baseline_measured_20261004) is known
from the static program, so it is stored in HBM as ONE stream in consumption order and fetched ahead of the SMs
by the HA8 prefetch stream (rtl/hbm_accel/qwen/ot_hbmacc_qwen_wstream.sv) over the die's 4 stacks of the
streaming controller on main (rtl/model_ready_hbm_r14/ot_hbm_r14_stream_pc.sv), refresh live.  The bench
(rtl/test/hbm_accel_qwen/tb_hbmacc_wstream_bw.sv, always-ready consumer) runs that many bytes, rounded up to
98,304-B stream words; the word size only sets the descriptor granularity, not the DRAM pattern.

    python3 tools/dshbm_static_stream_bw.py --work DIR --out RECORD.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERILATOR = os.environ.get('VERILATOR', str(Path.home() / '.local/opentallas-tools/verilator-5.050/bin/verilator'))
SOURCES = ['rtl/model_ready_hbm_r14/ot_hbm_r14_stream_pc.sv', 'rtl/hbm_accel/qwen/ot_hbmacc_qwen_wstream.sv',
           'rtl/test/hbm_accel_qwen/tb_hbmacc_wstream_bw.sv']
TOP = 'tb_hbmacc_wstream_bw'
WORD_B = 98_304
BASE = 'results/rtl/dshbm_baseline_measured_20261004/measured.json'
ROUTED_B = 46_903_680          # program.json: expert slots 0-5 row slices of die 0, 40 layers (fetched after the router)


def build(work, ref, words):
    d = work / f'ref{ref}'
    exe = d / 'obj' / f'V{TOP}'
    if not exe.exists():
        d.mkdir(parents=True, exist_ok=True)
        cmd = [VERILATOR, '--binary', '--timing', '-Wno-fatal', '-Wno-WIDTH', '-j', '8', '-O2', '--top-module', TOP,
               '--Mdir', str(d / 'obj'), f'-GREF_MODE={ref}', f'-GWORDS={words}'] + [str(ROOT / s) for s in SOURCES]
        with open(d / 'build.log', 'w') as log:
            subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, check=True)
    out = subprocess.run([str(exe)], capture_output=True, text=True).stdout
    (d / 'run.log').write_text(out)
    line = [l for l in out.splitlines() if l.startswith('RESULT')]
    if not line:
        return dict(ref_mode=ref, verdict='FAIL', raw=out[-1500:])
    r = {k: (float(v) if '.' in v else int(v)) for k, v in re.findall(r'(\w+)=([\d.]+)', line[0])}
    r['verdict'] = 'PASS'
    return r


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--work', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args(argv)
    if a.out.exists():
        raise SystemExit('fresh record path required')
    base = json.loads((ROOT / BASE).read_text())['hbm']
    static_b = base['bytes_per_die']['total'] - ROUTED_B
    words = math.ceil(static_b / WORD_B)
    with ThreadPoolExecutor(2) as ex:
        runs = list(ex.map(lambda r: build(a.work, r, words), (1, 0)))
    git = lambda *c: subprocess.run(['git', *c], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    sel = runs[0]
    die_tbs = sel['TBps_per_stack'] * 4
    rec = dict(schema='opentallas.hbm_path_audit.dshbm_static_stream.v1', source_commit=git('rev-parse', 'HEAD'),
               source_dirty=bool(git('status', '--porcelain', '--untracked-files=no', '--', *SOURCES)),
               input_sha256={s: hashlib.sha256((ROOT / s).read_bytes()).hexdigest() for s in SOURCES + [BASE]},
               simulator=subprocess.run([VERILATOR, '--version'], capture_output=True, text=True).stdout.strip(),
               bytes_per_die=dict(total=base['bytes_per_die']['total'], routed=ROUTED_B, static=static_b,
                                  stream_words=words, stream_bytes=words * WORD_B),
               peak_tbs_per_die=4.0, runs=runs,
               selected=dict(ref_mode=1, tbs_per_stack=sel['TBps_per_stack'], tbs_per_die=round(die_tbs, 4),
                             fraction_of_peak=round(die_tbs / 4.0, 4),
                             static_stream_us=round(static_b / (die_tbs * 1e12) * 1e6, 3)))
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rec, indent=2) + '\n')
    print(json.dumps(rec['selected'], indent=2), [r.get('TBps_per_stack') for r in runs])


if __name__ == '__main__':
    main()

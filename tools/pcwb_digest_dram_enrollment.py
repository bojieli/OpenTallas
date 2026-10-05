#!/usr/bin/env python3
"""One retained DSwb DRAM case, matched WA_LATE1 baseline/digest successor.

Keep the donor checker, stimulus, clocks, paths and golden-byte packer unchanged.
This enrolls the PC source; it does not compose rates or qualify physical timing.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import hbm_accel_dskv_wb as donor

ROOT = Path(__file__).resolve().parents[1]
BENCH = 'rtl/test/hbm_accel/tb_hbm_accel_dskv_wb.sv'
BASE = ('results/rtl/hbm_accel_fmax_inventory_20261004/svc/closure_handoff_20261004/'
        'source_snapshots/9b1d561d10fd_ot_hbm_accel_stream_pc_wb.sv')
CAND = 'rtl/hbm_accel/service/ot_hbm_accel_stream_pc_wb_digest.sv'
HASHES = {BASE: '9b1d561d10fd6feee452df10dc87d173b90f17f5d6284af823240f6418935f20',
          CAND: '59746a2ffc9171fbba702f35ce002f08d1b4845c2cb66698012c4816f4df0d55'}
SELECT = 'ot_hbm_accel_stream_pc_wb #(.ENABLE(1), .REF_MODE(1), .PC(p), .CRED(1 << LAW), .WB_EN(1),'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--work', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--golden-dir', type=Path, required=True)
    ap.add_argument('--jobs', type=int, default=16)
    a = ap.parse_args()
    if a.out.exists() or not 1 <= a.jobs <= 16:
        raise SystemExit('Fresh record path and 1..16 build jobs required')
    for source, expected in HASHES.items():
        if digest(ROOT / source) != expected:
            raise SystemExit(f'Pinned source mismatch: {source}')
    donor.REF = a.golden_dir
    a.work.mkdir(parents=True, exist_ok=True)
    inp = a.work / 'inputs'
    inputs = donor.write_inputs(inp, 20, 31, 1)
    retained = json.loads((ROOT / 'results/rtl/dshbm_kv_writeback_1m_20261004/kv_writeback_rtl.json').read_text())
    if inputs != retained['inputs']['L20_owner_stack1_ckv_key']:
        raise SystemExit('Retained golden-byte plan mismatch')
    text = (ROOT / BENCH).read_text()
    if text.count(SELECT) != 1:
        raise SystemExit('Cannot preserve donor checker: selection site changed')
    source_hashes = {s: digest(ROOT / s) for s in
                     [BASE, CAND, BENCH, 'tools/hbm_accel_dskv_wb.py',
                      'rtl/hbm_accel/service/ot_hbm_accel_cdc_fifo.sv',
                      'rtl/hbm_accel/service/ot_hbm_accel_dskv_wb.sv',
                      'tools/pcwb_digest_dram_enrollment.py']}
    records = {}
    for name, source, module, extra in [
        ('baseline', BASE, 'ot_hbm_accel_stream_pc_wb', ''),
        ('candidate', CAND, 'ot_hbm_accel_stream_pc_wb_digest', ', .DIGEST_CUT(1)')]:
        selected = (f'{module} #(.ENABLE(1), .REF_MODE(1), .PC(p), .CRED(1 << LAW), '
                    f'.WB_EN(1), .WA_LATE(1){extra},')
        generated = text.replace(SELECT, selected)
        assert generated.replace(selected, SELECT) == text
        bench = a.work / f'{name}.sv'
        bench.write_text(generated)
        obj = a.work / name
        obj.mkdir(exist_ok=True)
        command = [donor.VERILATOR, '--binary', '--timing', '-Wno-fatal', '-Wno-WIDTH',
                   '-j', str(a.jobs), '-O2', '--top-module', donor.TOP, '--Mdir', str(obj),
                   '-GSTACK=1', str(ROOT / donor.SOURCES[0]), str(ROOT / source),
                   str(ROOT / donor.SOURCES[2]), str(bench)]
        with (a.work / f'{name}_build.log').open('w') as log:
            subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True)
        exe = obj / f'V{donor.TOP}'
        runs = []
        # One actual owner CKV/key path and the donor's relevant negative controls.
        for mut in range(5):
            nbg = 0 if mut in (2, 4) else donor.NBG
            result = donor.run(exe, inp, 31, donor.T_BG, nbg=nbg, mut=mut)
            runs.append(result)
            (a.work / f'{name}_mut{mut}.json').write_text(json.dumps(result, indent=1) + '\n')
        records[name] = {'generated_bench_sha256': digest(bench), 'runs': runs}
    mismatches = []
    for mut, (base, cand) in enumerate(zip(records['baseline']['runs'], records['candidate']['runs'])):
        for key in sorted(base.keys() | cand.keys()):
            if base.get(key) != cand.get(key):
                mismatches.append({'mut': mut, 'field': key, 'baseline': base.get(key), 'candidate': cand.get(key)})
    gates = {name: runs['runs'][0]['verdict'] == 'PASS'
             and all(r['verdict'] == 'FAIL' for r in runs['runs'][1:]) for name, runs in records.items()}
    passed = all(gates.values()) and not mismatches
    record = dict(schema='opentallas.pcwb_digest.dram_enrollment.v1',
                  source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                  input_sha256=source_hashes, golden_npz_sha256=digest(a.golden_dir / 'ctx1048576_L20.npz'),
                  packed_input_sha256={p.name: digest(p) for p in sorted(inp.iterdir())}, inputs=inputs,
                  selection=dict(WA_LATE=1, DIGEST_CUT=1, WQ=8, CRED=64, STACK=1, layer=20, die=31,
                                 position=1048575, phase_points=1, controller_clock_ps=1024),
                  records=records, gates=gates, mismatches=mismatches, verdict='PASS' if passed else 'FAIL',
                  scope='Actual retained DRAM eligibility and golden bytes; no physical/rate/adoption claim')
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(record, indent=1) + '\n')
    print(json.dumps({'verdict': record['verdict'], 'gates': gates, 'mismatches': mismatches}))
    return 0 if passed else 1


if __name__ == '__main__':
    sys.exit(main())

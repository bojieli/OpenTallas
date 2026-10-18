#!/usr/bin/env python3
"""KVJ-SMALL (a) 2026-10-17: gate of the attention service result face (qkd_attn_result_face).

Bench rtl/test/qwen_split/tb_qkd_attn_result_face.sv: actual qkd_native_attention_programme (consumer) + actual
qkd_attn_service_root (context) + the face behind RELAY registered edges; the final join is the declared stimulus.
Expected: MUT0 passes MODE 0 and detects MODE 1..5; face mutants 1, 2 fail MODE 0; mutant 3 (unit faults not folded)
fails MODE 3.  RELAY 0 and 2.

    python3 tools/qwen_kv_die/attn_result_face_gate.py [--out receipt.json]
"""
import argparse
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
S = 'rtl/qwen_sys/split_20261014/'
SOURCES = [S + m + '.sv' for m in ('qkd_native_attention_programme', 'qkd_native_attention_static_ctl',
                                   'qkd_native_attention_record', 'qkd_native59_command_guard',
                                   'qkd_native59_descriptor_producer', 'qkd_attn_service_root', 'qkd_attn_result_face')]
SOURCES += ['rtl/test/qwen_split/tb_qkd_attn_result_face.sv']
TB = 'tb_qkd_attn_result_face'
CASES = [(0, m, True) for m in range(6)] + [(1, 0, False), (2, 0, False), (3, 0, True), (3, 3, False)]


def run(root=ROOT):
    rows = []
    with tempfile.TemporaryDirectory(prefix='qkd-attn-face-') as td:
        for relay in (0, 2):
            for mut, mode, ok in CASES:
                b = str(Path(td) / f'f{mut}{relay}')
                subprocess.run(['iverilog', '-g2012', '-s', TB, f'-P{TB}.MUT={mut}', f'-P{TB}.RELAY={relay}', '-o', b,
                                *[str(root / s) for s in SOURCES]], check=True)
                r = subprocess.run(['vvp', '-n', b, f'+MODE={mode}'], text=True, capture_output=True)
                passed = r.returncode == 0 and 'PASS' in r.stdout
                rows.append(dict(relay=relay, mutant=mut, mode=mode, expect_pass=ok, passed=passed,
                                 line=(r.stdout + r.stderr).strip().splitlines()[-1]))
                if passed != ok:
                    raise RuntimeError(f'unexpected outcome relay{relay} mut{mut} mode{mode}: {r.stdout}{r.stderr}')
    return dict(schema='opentallas.qwen_kv.attn_result_face_gate.v1', verdict='PASS',
                sources={s: hashlib.sha256((root / s).read_bytes()).hexdigest() for s in SOURCES}, cases=rows)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--out', type=Path)
    a = ap.parse_args()
    r = run()
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps(r, indent=2) + '\n')
    print(json.dumps(dict(verdict=r['verdict'], cases=len(r['cases']))))


if __name__ == '__main__':
    main()

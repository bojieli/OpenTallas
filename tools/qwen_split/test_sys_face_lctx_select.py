#!/usr/bin/env python3
"""Bounded source selector proof, without a calendar table or programme claim.

Icarus -i intentionally omits child engines: this vehicle drives the actual
calendar-event wires of the full successor and checks only context/start decode.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'rtl/qwen_split/qfd_sys_face_ovl_lctx1.sv'
TB = ROOT / 'tools/qwen_split/tb_sys_face_lctx_select.sv'


def main():
    original = SRC.read_text()
    variants = {
        'selected': original,
        'mutant_wrong_context': original.replace("ta[5:0] >= 6'd2 && ta[5:0] <= 6'd36", "ta[5:0] >= 6'd1 && ta[5:0] <= 6'd36", 1),
        'mutant_invalid_launch': original.replace('ev_lay && !l_context_bad', 'ev_lay', 1),
    }
    results = []
    with tempfile.TemporaryDirectory(prefix='sysface-lctx-') as td:
        for name, source in variants.items():
            p = Path(td) / (name + '.sv'); p.write_text(source)
            exe = Path(td) / (name + '.vvp')
            subprocess.run(['iverilog', '-g2012', '-i', '-s', 'tb_sys_face_lctx_select', '-o', str(exe), str(p), str(TB)], check=True)
            r = subprocess.run(['vvp', str(exe)], text=True, capture_output=True)
            expected = 0 if name == 'selected' else 1
            if r.returncode != expected:
                raise RuntimeError(f'{name}: unexpected return {r.returncode}: {r.stdout} {r.stderr}')
            results.append(dict(case=name, returncode=r.returncode, output=r.stdout.strip()))
    print(json.dumps(dict(scope='context/start selector only; omitted child engines; no programme playback or physical claim', source_sha256=hashlib.sha256(SRC.read_bytes()).hexdigest(), results=results), indent=2))


if __name__ == '__main__':
    main()

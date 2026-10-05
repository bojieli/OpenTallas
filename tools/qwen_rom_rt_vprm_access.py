#!/usr/bin/env python3
"""rm_access.hpp for the DSpark verify REAL_MEM die (ot_qwen_rom_rt_die_w12_vprm).

tools/qwen_rom_rt_rm_access.py (unchanged) finds the die arrays under the module name
ot_qwen_rom_rt_die_w12_rm; this successor runs it on a copy of the Verilated die header with the
vprm module prefix renamed, then restores the prefix in the generated accessors, and appends
RM_VM_ELEMS.  Every check of the parent tool (each array present exactly once) applies.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
A, B = 'ot_qwen_rom_rt_die_w12_vprm__DOT__', 'ot_qwen_rom_rt_die_w12_rm__DOT__'


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--die-header', type=Path, required=True)
    ap.add_argument('--vm-elems', type=int, required=True)
    ap.add_argument('--out', type=Path, required=True)
    a, rest = ap.parse_known_args()
    text = a.die_header.read_text()
    if B in text or A not in text:
        raise SystemExit('unexpected die header (module prefix)')
    with tempfile.TemporaryDirectory() as td:
        hdr = Path(td) / a.die_header.name
        hdr.write_text(text.replace(A, B))
        p = subprocess.run([sys.executable, str(ROOT / 'tools/qwen_rom_rt_rm_access.py'), '--die-header', str(hdr),
                            '--out', str(a.out), *rest], capture_output=True, text=True)
        if p.returncode:
            raise SystemExit(p.stdout + p.stderr)
    out = a.out.read_text().replace(B, A)
    out += f'constexpr size_t RM_VM_ELEMS = {a.vm_elems};\n'
    a.out.write_text(out)
    print(p.stdout.strip())


if __name__ == '__main__':
    main()

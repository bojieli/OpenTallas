#!/usr/bin/env python3
"""el1013-qwen-kvstrips: the two narrow SRAM macros of the aggregator strip's engine slice (qkd_astk_ep).

The slice is a 108 um column leaf with pins on both vertical faces, so a macro must stay >= 20 um from each: <= ~64 um
wide.  The catalog's 1R1W macros are 94.8 um (128x256) and wider.  This runs the SAME compiler with the SAME track
alignment rules as the pinned v2 library (tools/mem_compiler/build_aligned_v2.py: aligned_outline / aligned_write_lef,
verified by its verify_lef) for two new specs and writes their views (LEF, TT/FF/SS libs, model, black box, sheet) to
physical/qkd_astk_strip/macros/<name>/.  The pinned v1 / v2 sets are not touched.

    ot_sram_1r1w_256x128_m1_r2c2   57.048 x 42.120   the scores of one pass g (address {k, gam}), two a slice
    ot_sram_1r1w_64x128_m1_r2c2    55.320 x 22.440   a quarter of the e rows (address {g, k, gam[3]}), four a slice

    python3 tools/qwen_kv_die/astk_macro_gen.py [--check]
"""
import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools' / 'mem_compiler'))
sys.path.insert(0, str(ROOT / 'tools'))
import build_aligned_v2 as B      # noqa: E402
import sram_gen                    # noqa: E402

OUT = ROOT / 'physical' / 'qkd_astk_strip' / 'macros'
SPECS = [dict(name='ot_sram_1r1w_256x128_m1_r2c2', words=256, bits=128, mux=1, banks=1, ports='1r1w', spare_rows=2, spare_cols=2),
         dict(name='ot_sram_1r1w_64x128_m1_r2c2', words=64, bits=128, mux=1, banks=1, ports='1r1w', spare_rows=2, spare_cols=2)]


def build(out: Path) -> dict:
    res = {}
    with B.patched(sram_gen, macro_outline=B.aligned_outline, write_lef=B.aligned_write_lef,
                   GENERATOR_VERSION=f'{sram_gen.GENERATOR_VERSION}+{B.ALIGN_VERSION}'):
        for s in SPECS:
            sram_gen.compile_macro(sram_gen.SramSpec(**s), out)
            d = out / s['name']
            v = B.verify_lef((d / f"{s['name']}.lef").read_text(), str(d))[s['name']]
            assert v['pass'], (s['name'], v)
            res[s['name']] = v['size_um']
    return res


if __name__ == '__main__':
    if '--check' in sys.argv:
        with tempfile.TemporaryDirectory() as t:
            build(Path(t))
            bad = [str(f.relative_to(t)) for f in sorted(Path(t).rglob('*')) if f.is_file()
                   and (not (OUT / f.relative_to(t)).exists() or (OUT / f.relative_to(t)).read_bytes() != f.read_bytes())]
        print('CHECK', 'PASS' if not bad else f'FAIL {bad[:8]}')
        sys.exit(1 if bad else 0)
    for s in SPECS:
        if (OUT / s['name']).exists():
            shutil.rmtree(OUT / s['name'])
    OUT.mkdir(parents=True, exist_ok=True)
    print(json.dumps(build(OUT)))

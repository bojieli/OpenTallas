#!/usr/bin/env python3
"""RTLGAP-POOL 10-22: emit the census-safe pool successors (MAIN / ALTERNATE) from pool_safe_template.sv.

The ln2 table bits are taken from the unchanged shared source rtl/hdc/v41x/ot_hdc_v41x_sfu.sv (ln2_nk case), so the
successor's table is the original's table, default zeros included.  MAIN: copy factor 1, 2 table bits per kept
decode copy.  ALTERNATE: copy factor 2 (every select copy count doubled), 1 table bit per kept decode copy.
"""
import hashlib
import json
import re
from pathlib import Path

R = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
TPL = HERE / 'pool_safe_template.sv'
SFU = R / 'rtl/hdc/v41x/ot_hdc_v41x_sfu.sv'
OUT = R / 'rtl/dsrom_sys/s81_dv/slice'


def ln2_table():
    src = SFU.read_text()
    m = re.search(r'function automatic \[63:0\] ln2_nk.*?endfunction', src, re.S)
    rows = re.findall(r"8'd(\d+)\s*: ln2_nk = \{32'h([0-9A-Fa-f]+), 32'h([0-9A-Fa-f]+)\}", m[0])
    vals = {int(k): int(h + l, 16) for k, h, l in rows}
    assert len(vals) == 254 and all(0 <= k < 256 for k in vals)
    return vals


def ln2_module(vals):
    word = 0
    for bit in range(64):
        for k in range(256):
            if (vals.get(k, 0) >> bit) & 1:
                word |= 1 << (256 * bit + k)
    return ('// {n LN2_HI, RN(n LN2_LO)} by the low 8 bits of n (from ot_hdc_v41x_sfu.sv ln2_nk, default 0): bit\n'
            '// 256 b + k = bit b of entry k\n'
            'module ot_psf_ln2_bits (output wire [64*256-1:0] b);\n'
            f"    assign b = 16384'h{word:04096x};\nendmodule\n")


def main():
    vals = ln2_table()
    tpl = TPL.read_text()
    mod = ln2_module(vals)
    for variant, x, tb in (('main', 1, 2), ('alternate', 2, 1)):
        text = (tpl.replace('@@VARIANT@@', variant).replace('@@PSFX@@', str(x)).replace('@@PSFTB@@', str(tb))
                .replace('@@LN2_BITS@@', mod))
        assert '@@' not in text
        # every register is kept: a plain register with the same D as a kept copy would otherwise be folded INTO that
        # copy by opt_merge and hand it all of its loads (measured: mul p[47] -> top copy 0, 43 loads)
        text = re.sub(r'\(\* keep \*\) reg\b', 'reg', text)
        text = re.sub(r'(?<![\w$])reg\b', '(* keep *) reg', text)
        text = text.replace('output (* keep *) reg', '(* keep *) output reg')
        out = OUT / f'pool_safe_{variant}.sv'
        out.write_text(text)
        manifest = dict(
            variant=variant, top='ot_s81sl_cmp_pool', copy_factor=x, table_bits_per_copy=tb,
            generator=str(Path(__file__).relative_to(R)),
            inputs_sha256={str(p.relative_to(R)): hashlib.sha256(p.read_bytes()).hexdigest() for p in (TPL, SFU)},
            generated_sha256=hashlib.sha256(text.encode()).hexdigest(),
            unit_latency=dict(add=6, mul=7, div=35, exp='7 LM + 8 LA + 6'),
            original_unit_latency=dict(add=4, mul=5, div=33, exp='7 LM + 8 LA + 4'),
            qualification='UNQUALIFIED until numeric (positive + swap_kv) and native census outcomes')
        out.with_suffix('.json').write_text(json.dumps(manifest, indent=2) + '\n')
        print(out, manifest['generated_sha256'])


if __name__ == '__main__':
    main()

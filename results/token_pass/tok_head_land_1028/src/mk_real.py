#!/usr/bin/env python3
"""TOK-HEAD-LAND-1 ROM mutant vehicle: tile tE3b4 (rank-0 argmax tile) runs the REAL ot_s81hd_bundle_native (5 ROM
elements reading the released images via OT_ROM_DIR) instead of the measured view; the other 263 tiles keep the
measured view.  Type copies with a _real suffix (tile_p -> tile_native -> bundle_native); nothing else changes.
  mk_real.py W R  -> R/real/{s81_head_top.sv, ot_s81hd_tile_p_real.sv, ot_s81hd_tile_native_real.sv,
                              ot_s81hd_bundle_native_real.sv}, R/die_TTreal.f"""
import re, sys
from pathlib import Path
W, R = Path(sys.argv[1]), Path(sys.argv[2])
O = R / 'real'; O.mkdir(exist_ok=True)
G = R / 'land/gen'
top = (G / 's81_head_top.sv').read_text()
assert top.count('    ot_s81hd_tile_p tE3b4 (') == 1
(O / 's81_head_top.sv').write_text(top.replace('    ot_s81hd_tile_p tE3b4 (', '    ot_s81hd_tile_p_real tE3b4 ('))
tp = (G / 'ot_s81hd_tile_p.sv').read_text()
assert tp.count('module ot_s81hd_tile_p (') == 1 and tp.count('ot_s81hd_tile_native #(') == 1
# The tile keeps its default INSTANCE "h", so the scope ROM model asks for <tile>/hh<a0_0..b_1>.viamap.hex (it prefixes
# "h" for the measured-view dies; an empty untyped parameter prints as " ").  The run's image dir carries hh* links for
# tE3b4 (found: without them all 10 ROMs read dark -> wrong argmax, row 3352).
tp = tp.replace('module ot_s81hd_tile_p (', 'module ot_s81hd_tile_p_real (').replace('ot_s81hd_tile_native #(', 'ot_s81hd_tile_native_real #(')
tp = re.sub(r'endmodule\s*:\s*ot_s81hd_tile_p\b', 'endmodule : ot_s81hd_tile_p_real', tp)
tp = re.sub(r'^\s*`timescale[^\n]*\n', '', tp, flags=re.M)
(O / 'ot_s81hd_tile_p_real.sv').write_text(tp)
tn = (W / 'rtl/dsrom_sys/s81_head/ot_s81hd_tile_native.sv').read_text()
assert tn.count('module ot_s81hd_tile_native #(') == 1 and tn.count('    ot_s81hd_bundle_native #(') == 1
tn = tn.replace('module ot_s81hd_tile_native #(', 'module ot_s81hd_tile_native_real #(').replace('    ot_s81hd_bundle_native #(', '    ot_s81hd_bundle_native_real #(')
tn = re.sub(r'endmodule\s*:\s*ot_s81hd_tile_native\b', 'endmodule : ot_s81hd_tile_native_real', tn)
tn = re.sub(r'`ifndef\s+(\w+)\s*\n\s*`define\s+\1[^\n]*\n', '', tn)   # include guards, if any
(O / 'ot_s81hd_tile_native_real.sv').write_text(tn)
bn = (W / 'rtl/dsrom_sys/s81_head/ot_s81hd_bundle_native.sv').read_text()
i = bn.index('module ot_s81hd_kreg ')
body = bn[:i]
assert body.count('module ot_s81hd_bundle_native #(') == 1
body = re.sub(r'endmodule\s*:\s*ot_s81hd_bundle_native\b', 'endmodule : ot_s81hd_bundle_native_real', body)
(O / 'ot_s81hd_bundle_native_real.sv').write_text(body.replace('module ot_s81hd_bundle_native #(', 'module ot_s81hd_bundle_native_real #('))
f = (R / 'die_TT.f').read_text().splitlines()
out = []
for l in f:
    if l.endswith('land/gen/s81_head_top.sv'):
        l = str(O / 's81_head_top.sv')
    out.append(l)
    if l.endswith('land/gen/ot_s81hd_tile_p.sv'):
        out.append(str(O / 'ot_s81hd_tile_p_real.sv'))
    if l == 'rtl/dsrom_sys/s81_head/ot_s81hd_tile_native.sv':
        out += [str(O / 'ot_s81hd_bundle_native_real.sv'), str(O / 'ot_s81hd_tile_native_real.sv')]
assert len(out) == len(f) + 3, (len(out), len(f))
(R / 'die_TTreal.f').write_text('\n'.join(out) + '\n')
print('REAL_OK', len(out))

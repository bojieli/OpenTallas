#!/usr/bin/env python3
"""Opt-in structural seam replacement; does not mutate pinned predecessor RTL."""
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
L=ROOT/'rtl/dsrom_sys/s81_link'
text=(L/'lp/ot_s81_kp4_dec_native_flat_lp.sv').read_text()
text=text.replace('module ot_s81_kp4_dec_native_flat_lp', 'module ot_s81_kp4_dec_edge3')
pattern=re.compile(r'    ot_pl_land_w #\(\.W\((.*?)\), \.D\(4\)\) u_lpl_(\d+)_w \(\.ck\((\w+)\), \.rsi\((\w+)\), \.i\((\w+)\), .*?\);\n    ot_pl_land_r .*? u_lpl_\2_r \(\.ck\((\w+)\), \.rsi\((\w+)\), .*?\.o\((\w+)\)\);')
def seam(m):
    width, n, src, srst, data, dst, drst, out=m.groups()
    late='((MUT == 2) ? 1 : 0)' if n=='0' else '0'
    return f'    ot_s81_edge3 #(.W({width}), .LATE({late})) u_edge_{n} (.src_ck({src}), .dst_ck({dst}), .src_rsi({srst}), .dst_rsi({drst}), .i({data}), .o({out}));'
text, count=pattern.subn(seam,text)
assert count==11, count
# Remove the old bank metadata wires; retain payload and output wire decls.
text=re.sub(r'wire \[4\*.*? lpl_\d+_bank;  wire \[11:0\] lpl_\d+_epo;  wire \[3:0\] lpl_\d+_vld;  ', '', text)
assert 'ot_pl_land_' not in text
text='// Candidate only: all 11 seams use ordinary edge-timed registers. No SDC exceptions.\n'+text
(L/'ot_s81_kp4_dec_edge3.sv').write_text(text)
wrapper=(L/'col/ot_pdie_serdes_col.sv').read_text().replace('ot_s81_kp4_dec_native_flat_lp #', 'ot_s81_kp4_dec_edge3 #')
(L/'col/ot_pdie_serdes_edge3.sv').write_text('// BENCH CANDIDATE ONLY: edge-timed seams; physical integration remains blocked.\n'+wrapper)
bench=(ROOT/'tools/s81_link/run_serdes_col_bench.sh').read_text()
bench=bench.replace('"$L/lp/ot_s81_kp4_dec_native_flat_lp.sv"', '"$L/ot_s81_edge3.sv" "$L/ot_s81_kp4_dec_edge3.sv"')
bench=bench.replace('"$L/col/ot_pdie_serdes_col.sv"', '"$L/col/ot_pdie_serdes_edge3.sv"')
(ROOT/'tools/s81_link/run_serdes_edge3_bench.sh').write_text(bench)
print('EDGE3_GENERATED seams=11 added_edges_vs_predecessor=0 qualification=PENDING')

#!/usr/bin/env python3
"""HEAD-BIND-4 2026-10-27: RTL LEC of the hd_tile strap change against every per-instance variant.

    python3 tools/s81_head/head_strap_lec.py --old OLD_GEN_DIR --new NEW_GEN_DIR --top NEW_GEN_DIR/s81_head_top.sv --out DIR
    (OLD/NEW_GEN_DIR = gen.py rtl --types hd_tile of the plan before / after head_bind4_plan_delta.py; repo root cwd)

gold = the OLD hd_tile wrapper (ot_s81hd_strap u_strap #(ROW0, TEN) inside: the mask-variant form) with the strap
       parameters lifted to wrapper parameters, one instance per die-top hd_tile instance at THAT instance's values;
gate = the NEW wrapper (strap_row0 / strap_ten input ports) with exactly the literals the generated die top ties on that
       instance (parsed from s81_head_top.sv, not recomputed).
ot_s81hd_tile (the tile logic below both forms, unchanged) is the same OBSERVER stub on both sides (o = i ^ {ten, row0}),
so every compare point is a boundary / relay flop and every tile input pin (incl. row0 / ten) is observed through it.  Yosys equiv_make / equiv_simple / equiv_induct,
equiv_status -assert.  OT_YOSYS = the yosys command (e.g. docker run ... openroad/orfs yosys).  Exit 0 = EQUIVALENT for all instances."""
import argparse
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, 'tools/die_plan')
import gen_rtl  # noqa: E402

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument('--old', required=True); ap.add_argument('--new', required=True)
ap.add_argument('--top', required=True); ap.add_argument('--out', required=True)
ap.add_argument('--mutant', action='store_true', help='negative control: gate instance 0 gets row0 + 1 (must FAIL)')
ap.add_argument('--limit', type=int, default=0, help='first N instances only (0 = all)')
a = ap.parse_args()
out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
old = (Path(a.old) / 'ot_s81hd_tile_p.sv').read_text()
new = (Path(a.new) / 'ot_s81hd_tile_p.sv').read_text()
m = re.search(r'ot_s81hd_strap #\(\.ROW0\((\d+)\), \.TEN\((\d+)\)\) u_strap', old)
assert m, 'old wrapper has no u_strap'
old = old.replace(m.group(0), 'ot_s81hd_strap #(.ROW0(P_ROW0), .TEN(P_TEN)) u_strap')
old = old.replace('module ot_s81hd_tile_p (', 'module ot_s81hd_tile_p_old #(parameter integer P_ROW0 = 0, parameter integer P_TEN = 1) (', 1)
new = new.replace('module ot_s81hd_tile_p (', 'module ot_s81hd_tile_p_new (', 1).replace('endmodule : ot_s81hd_tile_p', 'endmodule : ot_s81hd_tile_p_new')
old = old.replace('endmodule : ot_s81hd_tile_p', 'endmodule : ot_s81hd_tile_p_old')
src = Path('rtl/dsrom_sys/s81_head/ot_s81hd_tile.sv').read_text()
hp = gen_rtl.parse_leaf_ports(src, 'ot_s81hd_tile')
pm = re.search(r'module\s+ot_s81hd_tile\s*#\((.*?)\)\s*\(', src, re.S).group(1)
pm = re.sub(r'//[^\n]*', '', pm)
assert set(hp) == {'ck', 'rst_n', 'i', 'o', 'row0', 'ten'}, sorted(hp)
# the tile logic is replaced on BOTH sides by the same observer: its input pins i / row0 / ten reach its output o
# injectively (o = i ^ {ten, row0} on the low 18 bits), so every black-box input bit is a compare point via the wrapper's
# out boundary flop (a plain (* blackbox *) made the pins unobservable: the --mutant control then passed, 10-27)
stub = 'module ot_s81hd_tile #(' + pm + ') (\n' + ',\n'.join(
    f'    {d} wire {w} {n}' for n, (d, w) in hp.items()) + \
    '\n);\n    assign o = {i[564:18], i[17:0] ^ {ten, row0}};\nendmodule\n'
ports = gen_rtl.parse_leaf_ports(new, 'ot_s81hd_tile_p_new')
top = Path(a.top).read_text()
insts = re.findall(r'^    ot_s81hd_tile_p (\w+) \((.*?)\n    \);', top, re.S | re.M)
rows = []
for name, body in insts:
    r0 = re.search(r"\.strap_row0\((\d+)'d(\d+)\)", body); te = re.search(r"\.strap_ten\((\d+)'d(\d+)\)", body)
    rows.append((name, int(r0.group(2)), int(te.group(2))))
if a.limit:
    rows = rows[:a.limit]
io = [(n, d, w) for n, (d, w) in ports.items() if not n.startswith('strap_')]
hdr = ',\n'.join(f'    {d} wire {w} {n}' if d == 'input' else f'    {d} wire [{len(rows)}-1:0][{w[1:-1] if w else "0:0"}] {n}'
                 for n, d, w in io)


def top_mod(name, body):
    return f'module {name} (\n{hdr}\n);\n' + body + 'endmodule\n'


gb, nb = '', ''
for k, (name, r0, te) in enumerate(rows):
    conn = ', '.join(f'.{n}({n}[{k}])' if d == 'output' else f'.{n}({n})' for n, d, w in io)
    gb += f'    ot_s81hd_tile_p_old #(.P_ROW0({r0}), .P_TEN({te})) {name} ({conn});\n'
    nb += f"    ot_s81hd_tile_p_new {name} ({conn}, .strap_row0(17'd{r0 + (1 if a.mutant and k == 0 else 0)}), .strap_ten(1'd{te}));\n"
TIES = ('module TIELOx1_ASAP7_75t_R (output wire L); assign L = 1\'b0; endmodule\n'
        'module TIEHIx1_ASAP7_75t_R (output wire H); assign H = 1\'b1; endmodule\n')   # ASAP7 liberty functions
(out / 'gold.sv').write_text(gen_rtl.CELLS + stub + TIES + Path('rtl/dsrom_sys/s81_head/ot_s81hd_strap.sv').read_text() + old
                             + top_mod('lec_top', gb))
(out / 'gate.sv').write_text(gen_rtl.CELLS + stub + new + top_mod('lec_top', nb))
ys = f"""read_verilog -sv {out}/gold.sv
hierarchy -top lec_top
setattr -mod -unset keep_hierarchy *
proc; flatten; async2sync; opt_clean
rename lec_top gold
design -stash gold
read_verilog -sv {out}/gate.sv
hierarchy -top lec_top
setattr -mod -unset keep_hierarchy *
proc; flatten; async2sync; opt_clean
rename lec_top gate
design -stash gate
design -copy-from gold -as gold gold
design -copy-from gate -as gate gate
equiv_make gold gate equiv
hierarchy -top equiv
equiv_simple -seq 2
equiv_induct
equiv_status -assert
"""
(out / 'lec.ys').write_text(ys)
import os, shlex
r = subprocess.run(shlex.split(os.environ.get('OT_YOSYS', 'yosys')) + ['-q', '-l', str(out / 'yosys.log'), '-s', str(out / 'lec.ys')], capture_output=True, text=True)
st = [ln for ln in (out / 'yosys.log').read_text().split('\n') if 'equivalent' in ln.lower() or 'unproven' in ln.lower()][-4:]
verdict = 'EQUIVALENT' if r.returncode == 0 else 'NOT EQUIVALENT / ERROR'
vals = sorted({(r0, te) for _, r0, te in rows})
(out / 'lec.txt').write_text(f'HEAD_STRAP_LEC {verdict} instances={len(rows)} distinct_variants={len(vals)} '
                             f'ten1={sum(te for _, _, te in rows)} rc={r.returncode}\n' + '\n'.join(st) + '\n'
                             + r.stderr[-2000:])
print((out / 'lec.txt').read_text())
sys.exit(r.returncode)

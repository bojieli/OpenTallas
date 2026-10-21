#!/usr/bin/env python3
"""QW-H16T 10-20: single-region head netlist for kit qfd_tt_head_static_h16u.

h16t (bound_r4 native32) took the eight head SRAMs on two raw clock entries ck_pm0 / ck_pm1 while every flop sits on
ck_head; the gate measured direct reg<->SRAM crossings between the three roots (TT -111 / -21.8 / -378.1 / -137.1 ps)
which the owner clock rule (10-20 08:55) forbids.  The parent (rtl/qwen_dv/qfd_tt_ctlm_dv.sv u_hr) already drives all
three entries from the same `ck`, so the SRAM 'regions' carry no physical purpose: this transform deletes the two raw
entries and clocks the SRAMs from ck_head, making the head ONE clock region (one CTS root, SRAM clock pins balanced
with the flops, 80 ps spread inside it).  No region crossing remains, so no landing ring is needed and no edge is added.

Pure text transform of the committed bound_r4/native32_param.v (cell netlist unchanged byte for byte apart from the
module header, two port declarations and the two clock assigns); output sha recorded in record.json.
"""
import hashlib, json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
SRC = HERE.parent / 'bound_r4' / 'native32_param.v'
OUT = HERE / 'native32_1r_param.v'
OLD, NEW = 'ot_qfd_tt_ctlm_static_hr_safe32_native32', 'ot_qfd_tt_ctlm_static_hr_safe32_native32_1r'
t = SRC.read_text()
edits = [
    (f'module {OLD} #(', f'module {NEW} #('),
    ('native_ret,ck_head,ck_pm0,ck_pm1,rst_n,', 'native_ret,ck_head,rst_n,'),
    ('input wire [0:0] ck_pm0;\ninput wire [0:0] ck_pm1;\n', ''),
    ('assign n_1146 = ck_pm0;\nassign n_1147 = ck_pm1;\n', 'assign n_1146 = ck_head;\nassign n_1147 = ck_head;\n'),
]
for a, b in edits:
    if t.count(a) != 1:
        sys.exit(f'make_1r: expected exactly one {a!r}, found {t.count(a)}')
    t = t.replace(a, b)
if 'ck_pm0' in t or 'ck_pm1' in t:
    sys.exit('make_1r: ck_pm0/ck_pm1 still referenced')
OUT.write_text(t)
rec = {'schema': 'qw_h16u.make_1r.v1', 'source': str(SRC.relative_to(HERE.parents[3])),
       'source_sha256': hashlib.sha256(SRC.read_bytes()).hexdigest(),
       'output': str(OUT.relative_to(HERE.parents[3])), 'output_sha256': hashlib.sha256(OUT.read_bytes()).hexdigest(),
       'top': NEW, 'edits': len(edits), 'clock_regions': 1, 'edges_added': 0}
(HERE / 'record.json').write_text(json.dumps(rec, indent=1) + '\n')
print(json.dumps(rec))

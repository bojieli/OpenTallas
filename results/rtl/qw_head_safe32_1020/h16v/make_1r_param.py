#!/usr/bin/env python3
"""QW-H16V: native32.v -> native32_1r_param.v = prepare_native_parent.py's STAGE_ME1/SEGCAL1 parameter header plus the
h16u single clock region (make_1r.py: raw ck_pm0/ck_pm1 entries deleted, the SRAM clocks driven from ck_head)."""
import re, sys
from pathlib import Path
src, out = Path(sys.argv[1]), Path(sys.argv[2]); v = src.read_text()
OLD = 'ot_qfd_tt_ctlm_static_hr_safe32_native32'; NEW = OLD + '_1r'
needle = 'module ' + OLD + '('; assert v.count(needle) == 1
v = v.replace(needle, 'module ' + NEW + ' #(parameter integer STAGE_ME=1, parameter integer SEGCAL=1) (')
end = v.rfind('endmodule'); assert end > 0
v = v[:end] + 'initial if(STAGE_ME!=1 || SEGCAL!=1) $error("native32 candidate is specialized STAGE_ME1 SEGCAL1");\n' + v[end:]
for a, b in [('ck_head,ck_pm0,ck_pm1,rst_n,', 'ck_head,rst_n,'), ('input wire [0:0] ck_pm0;\n', ''), ('input wire [0:0] ck_pm1;\n', '')]:
    assert v.count(a) == 1, a; v = v.replace(a, b)
n = 0
for pm in ('ck_pm0', 'ck_pm1'):
    v, k = re.subn(r'assign (n_\d+) = ' + pm + ';\n', r'assign \1 = ck_head;\n', v); assert k == 1, pm; n += k
assert 'ck_pm0' not in v and 'ck_pm1' not in v
out.write_text(v); print('make_1r_param ok', out)

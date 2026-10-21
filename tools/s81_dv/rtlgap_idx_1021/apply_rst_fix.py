#!/usr/bin/env python3
"""S81-RTLGAP/RG-IDX (10-21): reset-polarity fix of the IDX readers / query-frame node in the S81 die bind table.

tools/s81_dv/recovery_idx4_1021/overlay.json binds dsdv_idx_rg3 (and its chain-end variant dsdv_idx_rg3_nq) and
dsdv_idx_qf with rst = ["rst", "high"], so dv_bind inserts an inverter (die.v G3: INVx2 rinv_irg_00..07 / rinv_iqf
between the active-LOW reset-station net rs_* and the unit).  The RTL `rst` of all three is active-LOW
(`always @(posedge ck or negedge rst) if (!rst) ...`, dsdv_idx_rg3.sv l.56, dsdv_idx_tree.sv l.420): with the inverter
the readers and the qf node sit in reset whenever the die runs.  Run AFTER recovery_idx4_1021/apply_overlay.py on the
same table:  python3 tools/s81_dv/rtlgap_idx_1021/apply_rst_fix.py <bind_table.json>
Effect on die.v: the 9 rinv_* cells disappear, .rst() takes the rs_* station net directly (as every other active-low
master, e.g. dsfd_ctrl_rg3 rst_n).  Evidence: results/rtl/s81_rtlgap_idx_1021 (asis_tt FAIL vs rstfix_tt).
"""
import json
import sys
from pathlib import Path

p = Path(sys.argv[1])
t = json.loads(p.read_text())
fixed = []
for m in ('dsdv_idx_rg3', 'dsdv_idx_qf'):
    e = t.get('masters', {}).get(m)
    if e is None:
        raise SystemExit(f'apply_rst_fix: master {m} not in {p} (apply recovery_idx4_1021/apply_overlay.py first)')
    if e.get('rst') != ['rst', 'low']:
        e['rst'] = ['rst', 'low']
        fixed.append(m)
p.write_text(json.dumps(t, indent=1) + '\n')
print('apply_rst_fix: rst -> low for', fixed or 'nothing (already low)')

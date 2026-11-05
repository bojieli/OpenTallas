#!/usr/bin/env python3
"""Tests for b2o_tgt_table.py on a synthetic top: defaults, overrides, shared ids, calendar roles, bad override."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import b2o_tgt_table as T  # noqa: E402

SRC = """
module hub #(
    parameter [7:0] S_u_calendar_Q_q0_tgt = 8'b01100000,
    parameter [7:0] S_u_calendar_Q_q1_tgt = 8'b01100010,
    parameter [7:0] S_u_smw_Q_q0_tgt = 8'b10100010,
    parameter [7:0] S_u_smw_Q_q1_tgt = 8'b10100010
) (input clk);
endmodule
module top (input clk);
    hub #(.S_u_calendar_Q_q0_tgt(8'b01100001), .S_u_calendar_Q_q1_tgt(8'b01100011)) NE_hub (
        .clk(clk));
    hub NW_hub (
        .clk(clk));
endmodule
"""

r = T.build(SRC, 'top')
rows = {(x['instance'], x['leaf']): x['tgt'] for x in r['rows']}
assert rows[('NE_hub', 'u_calendar_Q_q0')] == 0x61 and rows[('NW_hub', 'u_calendar_Q_q0')] == 0x60, rows
assert r['shared'] == {'a2': ['NE_hub.u_smw_Q_q0', 'NE_hub.u_smw_Q_q1', 'NW_hub.u_smw_Q_q0', 'NW_hub.u_smw_Q_q1']}, r['shared']
assert sorted((c['instance'], c['role']) for c in r['calendar_roles']) == [('NE_hub', 'N'), ('NE_hub', 'S'), ('NW_hub', 'N'), ('NW_hub', 'S')]
try:
    T.build(SRC.replace(".S_u_calendar_Q_q1_tgt(", ".S_u_bogus_tgt("), 'top')
    raise SystemExit('undeclared override accepted')
except ValueError:
    pass
print('PASS 4 checks')

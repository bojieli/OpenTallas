# DIE-LAYOUT-HBM 11-12: scorer rows re-derived on the d6e q_b001 layout

CPL-HBM-B1 d6e (q_b001 + pv1 L15_o fix, deltas/d6e_q001_l15_cplb1_1112.json sha b351dafd) moved the r1c0 hcol
frames of q_b001, so the scorer rows of 01356ae3f9 (../scorer/) were re-run with the same tool, unchanged
(../scorer/scorer_rows.py, apply_scorer.py, trace_readers.py), on the t19 bound RTL
(epyc4 /srv/opentallas-scratch3/claude/cpl-hbm-b1/rtl19).

Order: base0 (d49a + d6d, fc8d47cd26a1) -> d6e (6b34609a) -> sc_d6e (this, 9fadbce8bb2c).
sc_d6e.json.gz is a compose.py delta (4 ops: whole-list set of internal_stations of q_b001, q_b001__physical_v1,
q_b000, q_b000__physical_v1); it must be applied AFTER d6e (same lists, so compose `conflicts` reports a prefix
overlap with d6e by design; sequential apply is the intended order).

| type | bus | scorer group | bits | site (um) | depth | max hop |
|---|---|---|---|---|---|---|
| q_b001 | L14_i | hb_idx_s_SE_scorer_ge_1_gc_0_leaf | 2777 | (1564.70, 1313.28) (d6: 1334.88) | 10 (= bus) | 71.0 |
| q_b001__physical_v1 | L14_i | hb_idx_s_SW_scorer_ge_1_gc_0_leaf | 2777 | (1660.61, 1300.32) (d6: 1624.32) | 10 (= bus) | 54.1 |
| q_b000 | L14_o | hb_idx_s_SE_scorer | 2777 | (237.60, 3248.08) unchanged | 9 (= bus) | 107.7 |
| q_b000__physical_v1 | L14_o | hb_idx_s_SW_scorer | 2777 | (237.60, 3208.77) unchanged | 9 (= bus) | 107.7 |

0 cycles, no RTL change, bus depth unchanged (EQ by construction). Other rows of the bus keep their positions;
their bits are rescaled so the bus total is unchanged (L14_i 4392 -> 1616 + 2777; L14_o 4110 -> 1335 + 2777).

G0 (tools/die_plan/check.py): base0 551 -> base0+d6e 550 -> +scorer 550, 0 new findings vs base0+d6e.
Renders: sc_q_b001.png, sc_q_b001__physical_v1.png (scorer row red, other L14_i rows blue).
Strict bind (bind_esc.sh, two-pass R8): BIND_OK, see bind_esc.receipt.

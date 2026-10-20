# KV-PC6 PC / PC_H native32 through normal synthesis (10-20)

Source claude/kv-pc6-1020 a155e93e5 (RTL; 026024361 = + main gate tools, sr8b kits). Base: Codex integrated A/B/C
codex/kv-hostpc-takeover-1020 a88b67879 (i4 census PC FAIL 5 / PC_H FAIL 8, max 2518).

Root cause of the 2518: physical/common_flow/ot_rst_copies.py REFUSED the 192-copy hgo_qv family (24 per-group kept
ot_kvpc5_and2 set leaves -> different EN nets), so copy 0 kept every load. Fix: (1) the family proof sees through
kept-hierarchy, purely combinational leaf cells with equivalent inputs (5 unit tests); (2) one shared strap compare
for the 24 leaves (a compare inside the generate loop elaborated 24 $eq cells). Small residues fixed in RTL
(desc_acc row lo/hi, s_hit 3 copies, c_oh / bsel one-hot via predecode + kept AND leaves, bsel 2 copies, lead_qv 5,
head_first 2 copies under an enable, observer opened per pw copy, up-FIFO rd_valid 2 kept leaves -> erk_q).
Same function, no added edge.

Mapped native census (normal ORFS synthesis + ot_rst_copies, sr8 kits, ep6 ref_gate *-20261020-051159):
PC PASS max 32 / 0 violations; PC_H PASS max 32 / 0 violations; hgo_qv 3854 loads -> 21 per copy, every family OK.

Benches, Verilator 5.050, 20000 edges, seed 1 (logs here; positives PASS, mutants FAIL):
tile pc m0 PASS 528046 / m4 m5 FAIL; tile pc_h m0 PASS 491757 / m4 m5 FAIL; sched m0 PASS / m5 FAIL;
ctrl m0 PASS / m1 FAIL; path m0 PASS / m2 FAIL; cdc m0 PASS (e_v_k compared) / m1 m2 m3 FAIL; tq m0 PASS / m1 FAIL.
tq / cdc m1 m2 at aea5f1217 (those units unchanged by a155e93e5), the rest at a155e93e5.

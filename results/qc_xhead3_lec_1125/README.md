# QC xhead3 tid / a_pr width contract (QC-XHEAD3-LEC 2026-11-25)

Failure (CHECKED): routed LEC NOT EQUIVALENT on both slw_hc2 kits, cl6bcaba89 (E11, lec.json on epyc7
private/QC-ALLFIX/slw_hc2__cl6bcaba89_1124054316/gen/slw_hc2__cl6bcaba89/lec_routed_autopilot_1795597506890491053) and
cla3497502__cl16607c7a (E8): 191326/191501 proved, 175 differ, 3 hard points b_emin[1][85..87] (gold widened names =
row 11 bits 13..15), cone gold-only a_pr[1][58..60] (row 11 bits 13..15).

Cause: the tile-id strap registered the 16-bit integer result of tid(cid_q, r) in tids / tid_q (no reset). Its row bits
(dr fields, bits 1/3/4/5) and top bits (10..15, tid <= 1023) are constants only through tid()'s arithmetic. Synthesis
removed those constant flops and the matching r_q bits (netlist r_q[11] = bits 0 2 4 6 7 8 9) and a_pr bits 17..18.
The LEC re-established only tid_q[15:10], r_q[11:10] and a_pr[17:18] as reset-reloaded constants
(noreset_constants.reloaded), not the per-row dr bits, so gold r_q[11][1,3,5] stayed free and a_pr row 11 bits 13..15
could not be paired. The constant-ness is real: tid(c, r) = {6'b0, c[5:2], dr[3:2], dr[1], c[1], dr[0], c[0]} exactly for
every 6-bit c, after the 2-edge strap pipeline fills (no reset on these flops in either version).

Fix (rtl/qwen_dv/s5/qfd_dv_s5_xhead3.sv): only the six cid bits are registered per row; row bits and zero top bits are
literal constants; r_q is a plain vector with a kept flop only for bits that can be non-zero; a_pr is a plain vector of
the product's reachable bits [16:3] (14 per row; 4 k q <= 128 * 1023 < 2^17, k even), zero-extended into b_emin.
Function unchanged for every input; 0 added cycles. No LEC hint needed.

Register set (yosys 0.68, LEC gold front end vs plain synth, standalone xhead3, cone tid/r_q/a_pr):
old gold a_pr 384 / r_q 192 / tid_q 192 / tids 192 (memory-widened, constant bits included);
new gold a_pr 224 / r_q 128 / tid_q 96 / tids 96 = the kit netlist's set (a_pr 16 x [3..16], r_q 6 cid bits + row ones).
Plain synth flop count old 8160 = new 8160.

Bench (verilator 5.050, rtl/test/qwen_dv/s5/xhead3/run.sh, E10): see bench.txt.

Status: HELD, not merged (COORD ruling 11-25 19:45, FABLE-RC-QC item 1: fix the tool first). LEC-AUTOFILL lec.py
e6d2675979 (no-reset-dropped gold register may join its partner sibling class) is rerun on sle_hc0 pv48712631, epyc11
unit oth-ubuntu-2292631-1795661253. Merge this commit only if that rerun is NOT EQUIVALENT on a_pr / b_emin.
If merged: every type binding qfd_dv_s5_xhead3 (sle_hc0..3, slw_hc0..3 in bind/bound and bound_r8) re-synthesises.
The RTL change alters register names (r_q -> g_rq[r].g_b[b].v.q, a_pr / r_q packed), so the existing routed DBs cannot
be re-checked with LEC only: a full kit rebuild is needed.

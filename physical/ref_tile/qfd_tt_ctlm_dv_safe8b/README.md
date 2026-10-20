# qfd_tt_ctlm_dv_safe8b -- QW-SUVM9/CTLM8 structural redesign of the safe7/safe7c terminal FAIL (10-20)

Branch claude/qw-ctlm8-1020. Netlist rtl/qwen_dv/lp8_np (candidate8, bounded native32 construct of the CTLM8 RTL; same
construct recipe as CTLM7: tools/qwen_dv/ctlm6_bound_macro.py, no X refinement). Parallel pair: safe8 (main, 777.6 x 648)
and safe8b (fallback, 777.6 x 604.8). Not on critical_tiles.txt.

safe7 FAIL (Codex packet d9d9158b3): GPL-0307 RePlAce divergence before CTS; four zero-gap SRAM row channels (two abutted
3-high p192 stacks); in-flow depth 848.5 ps / 27 lv; cf reg->out 5 lv.

## Changes (RTL: all exact except cf, which is +1 edge and priced)
| # | Cone (safe7 -> candidate8) | Fix | Edges |
|---|---|---|---|
| 1 | FIREDQ head rp_oh -> fq_word -> dq_n KS -> dq (27 lv) | next-slot bit from the one-hot pointer; dq_n / fire_n / nh_t computed per source (w, b, r, dlt0, none) in parallel, the late pop / bypass conditions only select | 0 |
| 2 | dh_q -> start range -> start_bad -> dn - 1 -> completion (27 lv) | run completions from registers; start refusal only selects any / collision / last index | 0 |
| 3 | XPF cfg w_ok = fw < arm + T (26 lv) | X0 = fw - arm - T, X1 = X0 + 2^32 (3:2 + carry tree each, parallel), overflow select | 0 |
| 4 | dhuser header check from rq (24 lv) | twin qfd_sys_face_mu_dhuser_p: h_good registered from rom_q beside rq (rq <= rom_q every edge) | 0 |
| 5 | seal_bad next-state through dw / pw decode muxes (24 lv) | header / segment checks per candidate word, decode only selects | 0 |
| 6 | PW observer serial OR accumulation (16-deep AO21) | per-bit reduction trees; exactly-one without a decrement | 0 |
| 7 | dq_lo + run then - x (two KS in series) | one 3:2 + one 14-b KS | 0 |
| 8 | cf reg->out 5 lv (checklist 1) | cf pin register in u_go | +1 (cf offset 6 -> 7 in the landed record; fault visibility C_cf + 1, sticky fault, die monitor reads it one edge later) |

Proof per round (OLD Codex fullsrc6 flat RTL vs NEW bounded netlist, Verilator 5.050, tb_np8 = tb_np7 with cf at +7):
r1..r6 LP_LOCKSTEP PASS 186,922 compares / 10,000 cycles / 2 resets, mutants MUT1 FAIL 9,838, MUT2 FAIL 4,748
(results/rtl/qw_tok_1019/ctlm8, remote ep7:/srv/opentallas-scratch/claude/qw-ctlm8r{,3..7}-1020). r7 bench: see lane file.

## Pre-gate native census (mapped ASAP7 RVT TT, native7.sh recipe), candidate8 r7
native strict PASS max 32 loads, 0 violations (reset included; rst_n 1 sink); std area 11,970.9 um2 (+470 vs safe7);
FF 15,825 (ck_core 11,199, ck_hr 4,626); in->out 0, in->reg 2 lv, reg->out 3 lv (cf fixed); textbook depth 686.8 ps /
23 lv (safe7 848.5 / 27; remaining cone: dh_q pin landing -> start decode in lpf_parts -> start range KS -> start_bad ->
do_clear -> selector clear, crosses lpf_parts / cal_mu: next RTL round).

## Floorplan (checklist 6)
outline 777.6 x 604.8 (was 561.6; die GEN re-slot owed; N pins keep x and move with the face, E / S pins keep their offsets).
SRAM rows y 43.2 / 217.728 / 392.256 (8.64 track lattice; x on 43.2), N/S row channels 20.6 um; fill 50.0 %. W/E pin-face channel between the SRAM columns 44.7 um (both faces 5.2 pins/um <= 6, halo 5.4); u_hr (h16c) at
475.2 / 43.2 and the three OPROMs at y 302.4 unchanged; core / hr region boxes extended to y = H - 43.2.

## SAFE checklist
1 Pins PASS (lp landings + cf pin register; reset 2-stage regional) | 2 Reach: gate wire_reach decides (outline +43.2 um
height) | 3 Fanout PASS (census max 32) | 4 Depth IMPROVED 848.5 -> 686.8 ps, 27 -> 23 lv (> 600 open, named cone above) |
5 Storage PASS (6 SRAM + 3 ROM) | 6 Floorplan PASS (channels >= 20 um, lattice, fill 40-60 %, aspect 1.29) |
7 Clock: regional ck_core / ck_hr + landed crossings (ck_hr own-entry still not in this kit) | 8 Schedule static; +1 cf priced.

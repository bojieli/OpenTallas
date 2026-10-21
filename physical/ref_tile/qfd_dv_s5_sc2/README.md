# qfd_dv_s5_sc2 -- slice2 scalar face sc2 (QW-S5-SCRED 10-21, Q.STA.SLICE.2 / QW-SLICE2E6 part 3)

Successor of qfd_dv_s5_sc / qfd_dv_s5_scb, whose mapped census failed (reset 740-3064 loads, depth 821-1030 ps; the earlier
sc2_79 bounded netlist 821.8 ps). Outline 248.4 x 248.4 (util 0.52, aspect 1.0). Main kit qfd_dv_s5_sc2, fallback qfd_dv_s5_sc2b.

RTL: top `qfd_dv_s5_sc2_leaf` (rtl/test/qwen_dv/s5_scred2/gen_leaf.py) = `rtl/qwen_dv/s5/qfd_dv_s5_sc2_k79.sv` (+ _helpers, helper
prefix qfd_s2_bmath_), the bounded constructor netlist of `qfd_dv_s5_sc2 #(LA 7, LM 9)` (rtl/qwen_dv/s5/qfd_dv_s5_sc2.sv) built by
tools/qwen_dv/bound_math_netlist.py --load-cap 8 --transparent-inverters --retain-mux --shared-helpers --retain-keep --reuse-copies
(rtl/test/qwen_dv/s5_scred2/native_k.sh, XF=--reuse-copies). Structural changes vs the previous sc2:
* sc_cfg lands in two face stages (cfg_v needs >32 kept copies; one stage put them on the raw pin);
* reset: rst_n 2-stage landing (qfd_dv_s5_rst2) + async-chained relay stages rc, rd, re, rf;
* argmax: the gated edge candidates land in a register before the three parallel 57-b compares (was 643.5 ps / 22 lv);
* new opt-in constructor flag --reuse-copies: overflow fills spare slots of existing copies (no 1-load copy cascade).

## Pre-gate native census (ASAP7 RVT TT mapped, results/arch/qw_slice6_1019/scred2_1020/native_sc2_k79/)
0 non-clock roots > 32 (raw inputs + reset included), max 23 loads, raw rst_n 2 loads; TT stage estimate 590.1 ps / 18 levels;
43,058 FF; Liberty area 32,110 um2; in->out 0. Mapped SHA256 a9368b5ba7b73eaf3fd7c3c7fce08ea630320813d71397a53e5c76ba9eed1078.

## Benches (Verilator 5.050, fleet)
RTL (run_sc2.sh): sc2 LA7/LM9 vs ORIGINAL qfd_dv_s5_sc (MU_NU 4), 40 rounds x 2 seeds PASS at OFF0 2 / argmax +2 / DT 20 / DR 96;
OT_S5_SC2_MUT (broadcast tap reads window 10) FAIL. Kit: run_kit.sh sc eq|mut 79 (this netlist vs original; constructed mutant
netlist) -- witnesses results/arch/qw_slice6_1019/scred2_1020/kitbench/sc79_{eq,mut}.log.

## SAFE-DESIGN checklist
1 Pins: PASS -- every input lands in a face register (sc_cfg two), every output leaves a face register (kit flow wrapper off,
  same in+1/out+1 as the old kit); rst_n 2-stage landing + relays; census boundary levels 0.
2 Reach: PASS -- leaf side <= 345.6 um < 405 um; slice distances are parent landings.
3 Fanout: FIXED -- bounded constructor cap 8 + reuse-copies, census 0 roots > 32 (max 23) incl. reset and raw ports.
4 Depth: FIXED -- FP add LAT 7 / mul LAT 9 with retained prefix levels, argmax edge landing: 590.1 ps / 18 lv.
5 Storage: PASS -- 32 root slots x 32 b = 1 kb flops (< 2 kb); rsqrt delay lines are kept exact-age rings (<= 2 kb each).
6 Floorplan: no macros; one full-width std-cell band; outline from mapped area at 0.52 / 0.41 util; pins W/N/E faces, S ck/rst_n.
7 Clock: one centre-fed root (43,058 sinks, <= 0.35 mm tile); judged on pin-flop spread <= 80 ps TT+FF; io_hold_margin 0.03.
8 Schedule: static. PRICE vs the old kit qfd_dv_s5_sc: chain pass words / own PSUM-AMI-AMV-RB words / RB taps / non-root TOK
  latch +0; root argmax -> tok_* and TOK broadcast +2; root total -> w1 +20; fused rsqrt -> RB broadcast + w1 +96; sc_cfg apply
  +1; boot reset release +4 (rc..rf), ring phases +2. Constraint: cfg_v not within 3 edges of root argmax / PSUM traffic.

## BIND
qfd_dv_s5b_su8p2_lp.sv (5949f90af) u_sc: replace module qfd_dv_s5_sc by qfd_dv_s5_sc2_leaf, identical ports/widths; the lp lagref
adds the edges above (sc_w1_* / tok_* / sc_dn_c / sc_up_c per class).

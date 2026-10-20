# qkd_ahub_g6b: AHUB6 native-32 hub, canonical lp.py parent (KV-AHUB7 10-20, tree K.STA.AHUB)

Source: flat rtl/hdc/nearhbm/qkd_ahub_static_dw_g6.sv (= g3 flat + KV-AHUB6 children qkd_ahub6_controls.sv) ->
tools/landed_parent/lp.py gen tools/qwen_kv_die/ahub7/lp_spec.json -> rtl/hdc/nearhbm/lp/qkd_ahub_static_dw_g6_lp.sv
(record results/arch/kv_ahub7_1020/lp/, generator lp.py, audit PASS).  New lp.py options (opt-in, defaults byte-identical,
test_safe_options vs main PASS): landing_reset_root_copies, child_reset_copies.  The generated RTL equals the codex
post-processed derivative (codex/ahub6-main-review-1020 80ac84f12) up to u_io port order and copy instance names, so the
derived-record gate helper (Gate-Rule relaxing) is not needed and not used.  Geometry: outer Z strips (Z inputs face the outline), W/E entries y106/432 (g4b geometry).  Kits: tools/qwen_kv_die/ahub7/mk_kits.py.

SAFE checklist (owner 10-19) / pre-gate native census:
1 Pins: PASS. Every pin registered in RTL (hs -> u_io pin flops, ap -> u_apw/u_ape, am/fr/hf registers); rst_n has 7 D loads
  (u_lpr_root_<region> kept copies), reset lands >= 2 stages in every region (forest depth 2 + child pads).
2 Reach: PASS by construction: every cross-region bus is an lp.py D4/K2 landing; u_rx/u_ry inside c beside core and
  reciprocal child.  Gate measures placed legs.
3 Fanout: PASS. In-gate GATE_NATIVE_CENSUS on this exact source (gate eeb5302e0, 14 Liberties, mapped netlist): max 32 loads,
  0 violations, 122,405 roots, 0 constant outputs (baseline g4: 265 drivers > 32). Codex unit oth-ubuntu-502416 agreed on the
  equivalent derivative. Golden (V5.050): m0 PASS 7 passes; m1 FAIL 11935; m19 FAIL 49 (results/rtl/qwen_kv_ahub7_1020).
4 Depth: stage boundaries unchanged vs g3 (a7 relays kept); gate measures <= 600 ps.
5 Storage: PASS per instance (no waiver).  The only runtime-indexed flop storage is the 15 lp.py landing rings (the D4
  landed crossings the clocking standard mandates; 1 writer / 1 reader each, at its own region boundary).  Largest instance
  zi0..3: 268 b x 4 slots = 1072 payload bits + 12 epoch + 4 valid logical bits = 1088 b < 2 kb.  The per-2-bit-chunk
  epoch/valid copies (zi: 1608+536 FFs) are kept FANOUT copies of those 16 logical bits (item 3), not addressable storage.
  Aggregating the 9 ck_c-written landings into one "16,340-bit family" (codex HOLD) is not a memory: they are 9 separate
  rings with 6 different reader clocks at 4 different faces; one SRAM could not serve them and an SRAM read would break the
  fixed D4/K2 landing latency.  Core LM 512 b / seen 512 b: < 2 kb each.
6 Floorplan: g4b geometry (reviewed; zh/recip macro origins = the coordinator 43.224 lattice waiver of a6, R0 re-orient
  proposal not applied); core box 324 x 149 um under its N pins; mapped band density c 32 % / w 23 % / e 16 % / Z 23 %;
  fill 41 % (children-dominated slot, exact outline).
7 Clock: 7 regional roots, landed crossings; u_rx/u_ry, u_lpr_root_<r>, u_lprc_u_io_k* now fenced in c (g4a census: the
  101 unfenced u_rx/u_ry flops were the whole 608..842 ps tail); io_hold_margin 0.03; gate checks TT+FF child-inclusive
  spread <= 80 ps.
8 Schedule: static; 0 added edges vs g3/g4 (reset age unchanged; HUB+6 / AM+3 inherited, already in the die calendar).

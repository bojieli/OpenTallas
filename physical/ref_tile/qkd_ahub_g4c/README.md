# qkd_ahub_g4c (KV-AHUB5 10-19, LEAD3-KV, tree K.STA.AHUB)

Successor of qkd_ahub_g3a / g3b (both gates FAIL clock_rule). SAME RTL as g3 (`qkd_ahub_static_dw_g3_lp`, 7 region roots,
15 landings), so every g3 die/compiler delta stands unchanged. Generator: `tools/qwen_kv_die/ahub5/mk_kits.py`; why and
the per-flop census: `results/arch/kv_ahub5_1019/README.md`.

NEW kit (KV-AHUB5 10-19, after qkd_ahub_g3a / g3b gates FAIL clock_rule, ck_c 153.9-155.0 TT and Z roots 81.7-216.8 TT): same RTL as g3; the g3a per-flop census put ck_c's tail on the N-face pin flops 240 um above the core band (band 474..526 ps, pins 549..598) and each Z root's on reset pads in a second fence strip plus a trunk repaired after balancing.  (1) the core region is ONE box under its own N pins with the reciprocal leaf directly below; (2) one fence strip per Z tree (reset pads inside); (3) z clock entries under the strip centres (S/N, g3b positions); right-column Z trees mirrored so their clock pins face E.

- Children: u_zh0 R0 at 43.2,43.2, u_zh1 MY at 518.4,43.2, u_zh2 MX at 43.2,345.6, u_zh3 R180 at 518.4,345.6, u_recip R0 at 259.2,172.8.
- Clock entries: ck_c N 356-358, ck_z2 N 118-120, ck_z3 N 594-596, ck_z0 S 118-120, ck_z1 S 594-596, ck_w W 350-352, ck_e E 304-306.
- Region fences (global placement only; released before DPL): see lp_fences.tcl.

## SAFE-DESIGN checklist (before the gate)
1 Pins: PASS. The RTL registers every pin (u_io hs/hf, u_apw/u_ape, u_amw/u_ame landing read flops, u_rw); keep_pin_regs.
  Reset: rst_n -> u_lpr_root -> per-region reset forests (depth 3), unchanged from g3.
2 Reach: PASS. Every cross-region bus is a landing (multicycle read). Longest single-cycle wires are hard-child I/O:
  u_recip y outputs -> u_ry ~230 um, z root outputs -> z->c write ring <= ~250 um (< 405; macro->reg slack +360 ps at g3a).
3 Fanout: PASS (as g3; lp.py chunked landings at 8 b, reset forest leaves <= 32).
4 Depth: PASS (g3a textbook depth 578 ps; same RTL).
5 Storage: PASS (landing rings 4 slots by contract; no runtime-indexed flop array > 2 kb outside the Z/recip macros).
6 Floorplan: PASS. Macros on the 43.2 lattice (track-shifted origins as g3); channels >= 43 um; core box 324 x 149 um
  holds 6.1k um2 of core cells (fill ~0.13), Z strips ~0.08-0.09, aspect 1.36; one std-cell band, no PDN islands.
7 Clock: FIXED (this kit's point). Core region = one compact box containing its own N pins (g3a: the band was 474..526 ps,
  only the N pin flops 240 um away reached 549..598); one fence strip per Z tree with its reset pads (g3a: pads in the
  far strip 544..546 ps); the z entry under the strip centre (g3b position);
  io_hold_margin 0.03; hard children tapped by TritonCTS on their region root (insertion refs bound).
8 Schedule: PASS. Static, no change vs g3 (HUB_RECIP / HUB_PUB +6, am +3 at the ASTK pins, reset release +10 once).

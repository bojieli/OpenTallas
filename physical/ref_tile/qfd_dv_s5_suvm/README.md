# qfd_dv_s5_suvm / qfd_dv_s5_suvmb -- QW-SLICE6 SU issue control + VM leaf (Q.STA.SLICE.2)

New leaf of the hardened one-level slice qfd_dv_slice2_{w,e} (plan claude/qw-slice5-1019 @961b2dafd, RTL
claude/qw-slice6-1019 rtl/qwen_dv/s5/qfd_dv_s5_leaves.sv `qfd_dv_s5_suvm` + `qfd_dv_s5_vm.sv`). Register-for-register cut
of qfd_dv_slice2 (SU_LT 1): the su8 issue loop, kept group relay gb/gv, stage 1 of every lane's live/offset relay, progress /
idle / fault, and qfd_dv_vm without the station's BTAB copy (that is qfd_dv_s5_btab beside station region 0).
Generator: `python3 tools/qwen_dv/s5_suvm_kit.py a|b`.

| kit | floorplan |
|---|---|
| qfd_dv_s5_suvm (main) | 483.84 x 691.2: 2 abutted N-S macro columns (5 x 1024x256 + 2 PROG 256x256 + 2 BTAB 128x256 each), pin channels W 43.2 / 43.4 / E 47.7, full-width S band 129.6 |
| qfd_dv_s5_suvmb (fallback) | 691.2 x 561.6: 3 abutted columns (5 big / 5 big / 4 PROG + 4 BTAB), S band 151.2 |

Pins: W lane answers + live/offset relay (va_q vb_q vc_q cr_q lv1 pd1, 2,056 b); E lane requests/results (1,488 b); N group relay
gb/gv (503 b); S ctl / stream / reducer side + ck / rst_n (~1,700 b).

## Price

HARD 1 (default) adds ONE register: `su_nr` (= su_go && !ready, the ctl port-fault term) -> +1 edge on a sticky status bit
(never a scheduled value).  Every other path is qfd_dv_slice2's edge for edge (VM answers 2 edges after the lane request,
program word 2 edges after c_su, su_go = c_su + 2).  0 steady-state cycles.

## SAFE-DESIGN checklist

1. Pins: PASS by construction -- lane-side inputs are lrly flop Q one hop away; outputs are flop Q (gb/gv/lv1/pd1, status) or
   VM capture flop + the qfd_dv_vm word/lane extraction mux (2:1 x 8:1, shallow); su_nr registered (HARD 1). rst_n lands in 2
   registered stages (qfd_dv_s5_rst2), then the su8 RTREE copies rc / rg. No flow pin regs (would add an unpriced edge inside
   the ML 1 / RD 2 lane read round trip).
2. Reach: tile <= 691 um; macros in abutted columns with logic in the pin channels beside the macro pins; gate wire_reach.
3. Fanout: gb is a kept 500-b register driving 8 lane relays (fanout 8); lane offsets per lane (8 x 4 adders); issue state fans
   to <= 8 lanes x 4 offsets. Gate high_fanout confirms (kept copies if a cone exceeds 32).
4. Depth: issue loop / offset adders 24 b, VM write merge (3-source per bank), read extraction mux; gate logic_depth / --cts classes.
5. Storage: all > 2 kb state in 18 SRAM macros (VM 6, CROM 4, BTAB 4, PROG 4); flop state = capture registers + control.
6. Floorplan: macros at_exact abutted stacks (pitch h + 0.024, pins W/E only), every macro >= 43.2 um from a pin face,
   full-width S std-cell band, outline 334 k / 388 k um2 (macro-dominated: low std density by construction), aspect 1.43 / 1.23.
7. Clock: one centre-fed TritonCTS root from the S-face ck pin; judged on pin-flop spread <= 80 ps TT+FF (clock_span WARN:
   > 600 um span, rule is spread); io_hold_margin 0.03.
8. Schedule: static, no credits / backpressure; +1 only on su_nr (above).

## Open issue (parent RTL)

The lane-facing buses are packed 8-lane ports (va_q[255:0], va_addr[191:0], ...), so one port cannot be split over the W and
E faces: the right-side lane cells reach the W answers across the block. A per-side port split (lanes 0-3 / 4-7) in
qfd_dv_s5_suvm + gen_slice5_flat.py would put every lane pin on its own side (parent decision, QW-SLICE6).

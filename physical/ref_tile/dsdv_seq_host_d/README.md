# dsdv_seq_host_d / dsdv_seq_host_d43 -- S81 seq_host compact core, re-packed for the s10f lk (DIAGNOSTIC kits)

S81-SVCSEQ-1021, branch `claude/s81-svcseq-1021`. Specs `tools/ref_tile/specs_pl_seq/dsdv_seq_host_d{,43}.json` (built from
`dsdv_seq_host_c.json`); same wires-only parent RTL `rtl/dsrom_sys/s81_dv/unit/dsdv_seq_host_c.sv` (top `dsdv_seq_host_c`, RL 1).

| inst | child | view | d (A, 21.6 ch) | d43 (B, 43.2 ch) | size |
|---|---|---|---|---|---|
| u_l0 | dsdv_sh_lk | STAND-IN `standin/dsdv_sh_lk` (s10f regate 4e02f8a41 --cts odb, `STANDIN_NOT_A_VIEW`) | 43.2, 43.2 | 43.2, 43.2 | 345.6 x 280.8 |
| u_l1 | dsdv_sh_sq | CLOSED `dsdv_sh_sq/views/dsdv_sh_sq` (baa6e2280, record ef5587213) | 86.4, 345.6 | 86.4, 367.2 | 254.88 x 151.2 |
| u_l2 | dsdv_sh_vc | CLOSED `dsdv_sh_vc/views/dsdv_sh_vc` (ce989b78c) | 86.4, 518.4 | 86.4, 561.6 | 226.8 x 213.84 |

Outline: d 432 x 777.6 (= die72 seqhost_00 reservation), d43 432 x 820.8 (die slot +43.2 in y if A fails GRT).
The closed main lk view (ef442ffba) is NOT bound: it is the RL 0 interface (ck_ih / ck_ic) the RL 1 parent no longer has (no aliasing).
The s10f lk route (b0972fda0) FAILED (hold -273 ps / 1449 paths, setup -79 ps, DRC 19): these kits stay DIAGNOSTIC until an RL 1 lk closes.

SAFE-DESIGN checklist: (1) pins: wires-only parent, pin regs off (each leaf flop-first/last at its pins); reset landing 2 stages.
(2) reach: parent wires <= ~60 um face-to-edge, child-to-child 21.6 / 43.2 um (< 405). (3) fanout / (4) depth: no parent logic.
(5) storage: none in parent. (6) floorplan: children on the 43.2 lattice, aspect 1.8 / 1.9, hard-child fill ~45 %; the lk N face
(cf/j/kd/ks/pl/pw/rn/rs/tw order) does not match the sq S face order -> ~1,000 nets cross horizontally in the lk|sq channel: that is
why B widens it to 43.2. (7) clock: one region (< 1 mm), judged per child pair lk-sq / sq-vc at child flops, TT+FF <= 80 ps; lk
insertion ~500 ps vs sq/vc ~230-260 ps -> CTS must add ~250 ps on the sq/vc branches (watch FF spread). (8) schedule unchanged vs _c.

# qfd_n59_qbank (QW-N59-4, 10-19) -- Q-seat SRAM bank child of the hardened native59 split (Q.STA.N59)

Why: the one-root native59 kits safe4 / safe4b (ot-agidock128, 10-19 20:59; terminal records dc917674a) built CTS but measured
pin-flop TT 633..777 / FF 516..643 (spread 145 / 127 > 80), SS setup -635 ps after repair at u_qseat.select_q (owner_n ->
32:1 beat mux -> select), a 10,330 s hold repair (17.6k buffers) and GATE_STALL 14400 s: 24k flops on one root spread at 10 %
std-cell density over the 518.4 x 648 macro-bound slot (average sink wire 585 um).  Structural fix: hardened split.
RTL rtl/qwen_split/qfd_native59_qbank.sv (qfd_native59_qbank + qfd_native59_qseat_sram_k); parent
rtl/qwen_split/qfd_native59_split_flat.sv, landed form rtl/qwen_split/lp/qfd_native59_split_flat_lp.sv (lp.py).
Function: the SAFE 2 Q-seat section of qfd_native59_dv_service (scatter replicas, qseen / qctx / dup / range checks, the
exact 8-writer SRAM store, full check) on its own pin registers; every output registered (qb_* = the flat block's Q value of
the previous edge; dd_o / lcv_o / stage_o = one-edge relays to the service).  Lockstep vs qfd_native59_dv_service_r1:
rtl/test/qwen_split/run_native59_split_bench.sh (directed NU 1 + NU 4 / MCTX 1 programmes, random stimulus with internal
probes; mutants m1 / m7 / qb1 FAIL; witnesses results/rtl/mu_qwen_1018/n59_split4).
Kit _b = the same block with an unclustered H-tree CTS (parallel fallback, owner 10-19).

## SAFE-DESIGN checklist (owner 10-19)
1 Pins: PASS -- every input lands in a p_* pin register (plus kept same-edge replicas: qe/qd/qm/qc_rep, one-hot read-face
  copies); every output is a flop; rst_n 2 landing stages x 32 copies (kit) + kept forest rst_cp_bp 24 / rst_cp_bs 20.
2 Reach: PASS by construction -- 518.4 x 388.8; longest planned one-cycle wires: dd_i (S face) -> dd_o relay -> N face
  (~350 um), SRAM rd_out (middle channel) -> qrow_r -> N face (< 300 um).  Measured on the CTS gate layout.
3 Fanout: FIXED -- read beat as one-hot KEPT copies (4 lane groups: 12 loads / bit), read enable 16 lane copies + 8 macro
  copies, per-macro read address and per-writer bypass beat copies; scatter replicas serve 32 seats each.
4 Depth: FIXED -- the safe4 worst path (owner_n -> binary 32:1 beat mux driven by one register -> select) is now a one-hot
  AND-OR per lane group; q row leaves through a register (qrow_r) instead of feeding the service combinationally.
5 Storage: PASS -- 16 kb Q payload in 8 SRAM macros; owner table 512 x 3 (1.5 kb) read by one-hot AND-OR.
6 Floorplan: PASS -- 8 macros on the 43.2 lattice in two N-S abutted stacks (track-legal pitch 76.176, no pins on the
  touching faces); column 0 mirrored MY so BOTH columns' rd_out faces the 91.8 um middle gather channel, write faces
  outward (43.2 / 48.6 um channels); full-width S (43.2) and N (36) std-cell bands; aspect 1.33; macro util 51 %.
7 Clock: PASS -- one root ck at the N-face centre (centre-fed), its own region in the landed parent (ck_qb);
  io_hold_margin 0.03; rule = pin-flop spread <= 80 at TT and FF.
8 Schedule: static (no credit / backpressure).  Added edges: the bank's registered outputs put the service one edge
  behind the bank (service ports +1) and the landed parent adds E + 1 = 3 (service ports +3); handed to the compiler
  (lanes/QW-GEN3.md NOTICE QW-N59-4; record results/arch/landed_parent_1018/qfd_native59_split_flat).

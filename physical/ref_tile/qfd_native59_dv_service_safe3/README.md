# qfd_native59_dv_service_safe3 (QW-N59-SAFE3, 10-19) -- primary; safe3b = same RTL, recipe 4 die hold budget

Native59 compute service, NU 4 / MCTX 1 (two static operation contexts, MU-D2D-OVL) / SAFE 2 (strict pin-first
Q prefetch, exact eight-writer Q-seat SRAM bank, Codex N59-SAFE 9f159ab98/e84f9f92c), rebuilt structurally after
the safe2 gate FAIL (ot-epyc8 ref_gate/qfd_native59_dv_service_safe2-20261019-081454):
  * CTS ERROR `OT_HYBRID: CTS source ck_qbuf must reach only standard-cell clock pins`: a multiple_cts_roots TILE
    cannot clock raw SRAMs (raw-memory sinks are a cluster-only contract), and ck_qbuf had no registers at all;
  * reset nets 5,517 / 2,830 / 2,173 / 2,139 / 1,599 / 836 / 577 loads (rst_q copies x8).
Top `qfd_native59_dv_service_r1` (same file): the SAFE2 service with ROOTS 1 (formatter + 8 SRAMs on `ck`, one
CTS root; ck_fmt / ck_qbuf removed from the interface) and RST_FOREST 1. Same function and edges on every port
(all native / MU / qseat benches PASS, mutants FAIL: results/rtl/mu_qwen_1018/n59_safe3, Verilator 5.050 fleet).

DIE OBLIGATIONS: bind master `qfd_native59_dv_service_r1` (no ck_fmt / ck_qbuf ports); SAFE2 Q prefetch: the
compiler advances q_slot / q_slot_beat by 1 edge (CMD / Q / TX slots unchanged); production Q-ready bound
(QW-QREADY: W5.dd_wo -> native59.dd_i age 20) must be certified by the successor GEN before binding.
Reset release: 2 landing stages + 1 RTL copy stage = 3 edges (unchanged vs SAFE2).

## SAFE-DESIGN checklist (owner 10-19)
1 Pins: PASS -- RTL flop-first on every input (p_*) and output (pin_regs opt-out reason recorded: a kit pin reg
  would add a second edge). rst_n lands in 2 face stages (reset_landing), last stage = 32 KEPT copies.
2 Reach: PENDING gate -- outline 518.4 x 648 < 1 mm; one-cycle wires checked on the CTS gate layout.
3 Fanout: FIXED -- reset forest: 32 landing copies -> 600 KEPT RTL copies (rst_cp_* families, widths
  ceil(loads/28)), ot_rst_copies.tcl spreads loads <= 32/copy (reset_relay_split max 32); formatter eb_r x16,
  owner-select one-hot kept (32 data bits each). Witness: gate textbook high_fanout on 1_2_yosys.v.
4 Depth: PENDING gate TT -- no combinational in->out (flop-first both sides); SAFE2 formatter lane encode registered.
5 Storage: PASS -- 16 kb Q payload in 8 x ot_sram_1r1w_32x512_m1 (masked writers); remaining flop state owner
  1,536 b + seen 512 b (< 2 kb each, control).
6 Floorplan: PASS by construction / PENDING image -- 8 macros on the 43.2 um lattice (2 x 4, origins x 43.2 / 259.2),
  >= 48 um channels, full-width southern std-cell band; pins on full N / S / W faces; total util ~40 % (synthesis
  std ~29k um2 + macros 102k um2 in 331k um2 core, SAFE2 synth).
7 Clock: FIXED -- one root `ck` (22.3k flops + 8 SRAM clock pins, centre tree); the rule is pin-flop spread <= 80 ps
  TT + FF (PENDING CTS gate); io_hold_margin 0.03. clock_span WARN (> 600 um) is guidance.
8 Schedule: PASS -- static, no backpressure; no new edge vs SAFE2 (+1 Q prefetch already handed to the compiler).

Gate results / PNGs: see lanes/QW-N59-SAFE.md and pending_results (QW-N59).

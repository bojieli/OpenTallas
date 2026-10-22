# qkd_hr_core_guard (mu1s) -- MU1 release guard with the marker FIFO in SRAM

Owner lane: KV-HOST/GUARD (LEAD-KV), branch `claude/kv-host-guard-1019`. Parent `qkd_host_root` (critical; untouched).

* RTL: `rtl/qwen_sys/mu_qwen_20261018/host_cluster_mu/qkd_hr_core_guard.v` (MU1 core, `u_rank__u_native` =
  `qkd_host_native_token_endpoint_cancel_mu` incl. the MU-KV-PEER retired-step release edit) built with
  `OT_HOST_GUARD_SRAM_DEFAULT=1`: the W64 x 128 guard marker FIFO (`qkd_host_guard_fifo`, 8192 b) is one real
  `ot_sram_1r1w_128x64_m1_p192` with the same four-edge prefetch (Codex bae1890ee family, cherry-picked).
* Kit = Codex's safe slot (108 x 140.4 um, macro at 43.2/43.2) regenerated with main's `ref_tile.py gen`;
  reset landing 2 stages, 18 KEPT `host_rst_n` copies, `reset_relay_split` 256, `io_hold_margin_ns` 0.03.
* Benches (Verilator 5.050, fleet ot-epyc7, source ef7b3a8c3): `results/rtl/kv_host_guard_1019/bench_ef7b3a8c3/summary.txt`
  -- lint_guard_mu PASS, SRAM lint PASS, tb_mu_hroot_e2e PASS, ep1/ep2 FAIL; guard FIFO SRAM exact m0 PASS
  (100,140 cycles), m1/m2/m3 FAIL. Committed fail witnesses: `results/rtl/mu_qwen_1018/hroot/runs_guard2/mut/ep{1,2}.log`,
  `results/rtl/kv_guard_fifo_sram_1019/verilator_v1/m{1,2,3}/run.log`.
* CTS gate (ef7b3a8c3, ot-epyc7 `ref_gate/qkd_hr_core_guard-20261019-114900`): PASS 0 fail 0 warn; reg->reg +67.0 ps,
  hold +39 ps, 4_cts_final wns/tns 0/0; spread TT 24.9 / FF 24.1 ps, 6,180 sinks; trial GRT overflow 0.

## SAFE-DESIGN checklist (owner 10-19)

| # | item | result |
|---|------|--------|
| 1 | pins | PASS: pin regs on all data pins (58 in / 20 out +1 edge); reset lands in 2 stages; no comb in->out |
| 2 | reach | PASS: 108 x 140.4, corner-to-corner 248.4 um < 405 |
| 3 | fanout | PASS reset (18 KEPT copies, cap 256, hf_max_reset 0). WAIVED data: `g_sram.fr[2]` 305 mux loads (8:1 x 64 b head-buffer select) + one 336-load enable net, inherited from the closed MU0 view, not critical at CTS (worst reg->reg +67 ps on another path). Structural fix (8 KEPT fr copies) gated in parallel as fallback kit `qkd_hr_core_guard_frc` |
| 4 | depth | PASS: 483.4 ps / 12 levels worst |
| 5 | storage | FIXED: 8192 b marker FIFO -> one 128x64 SRAM; remaining flop storage < 2 kb per array |
| 6 | floorplan | PASS, util WAIVED (pin-bound): macro on the 43.2 lattice, channels >= 31.1 um, face pins <= 5.54/um; height set by W-face pin demand (778 pins), width by macro lattice + parent slot; util 30% synth / 39% CTS; full-width std-cell bands, no islands |
| 7 | clock | PASS: one ck_core root, spread 24.9 / 24.1 ps TT/FF, io_hold_margin 0.03 |
| 8 | schedule | PASS: static, 0 added cycles |

Visual review: `gate_layout/floorplan.png`, `gate_layout/density.png` inspected (REVIEW.json).

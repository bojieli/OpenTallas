QC token side (former QC-TOK), 2026-10-24 22:2x PDT: xt1 both-cluster smoke on the FINAL capacity bind (owner decision 1).
Plan claude/qc-cap-1024r @806bcb4058; bind epyc1:/srv/opentallas-scratch2/claude/qc/bind_eq_cb16 (recipe
physical/die_plan/qwen_compute/bind/asbuilt_capacity_eq_cb16.json, 0 bind errors, verify PASS 2,723,870 / 0 / lint 0).

Constants (constants_cap_eq.json, regen_constants.py on the bind, 22/22 OK): XT1_FILL_LEAD_OFFSET = 8 on all 12 slices
(hr +12, sw +2, xt +2) -> xt1 lead 16, taken from the constants by bind_smoke (not hand-picked). Versus constants_cb16.json
(bound_r8 + CB16, lead 14) the offset moved 6 -> 8 (hr +11 -> +12, xt +3 -> +2); the capacity CB16 vehicle also ran lead 16. COLL_LS / MU_CAL_LS 389 -> 391,
COLL_F2/F4 PHY 351 -> 353, COLL_BENCH_ARGS lanes 10 -> 12 / lx 12 -> 14 (the io_serdes / serdes TX station change); these feed
the link (tp8 MU calendar) pass, not xt1. TREQ_CMD_OFFSET 0, XDIE_SEAM_C and D2D_TXDP_C unchanged.

xt1 (bind_smoke.py --clusters both, src 2ece7f9a79, epyc3 via ot-run): nominal near 64/64 + far 64/64 PASS (QKV/O/GU/down
exact). hr+1 mutant numerically 64/64 + 64/64; the timing-aware schedule gate (tools/die_plan/xt1_schedule_gate.py, Codex
c6ec9651aa) catches it on 16/16 fixed consumer edges (cw_go and rs_edges +1) -> gate PASS. Build 2604 s, sims 755 s,
peak 75.8 GB.

A0 t_out +1 (results/uarch/qwen_a0_latency_compat_1024.json): no constant in this bound top. The bind instantiates the
bound A0 RTL (qfd_tile_nk/nl_rp2_romleaf_rr); t_out is intra-partition (tile -> ot_dp_dly D=3 -> next tile n_a inside the
qfd_qc_cb_* partition), so it is in neither the R8 crossing table, the CB16 pads nor regen_constants. It applies when the
A0 KIT replaces the RTL: then t_out is +7 vs bound (kit spec +6, residual +1), and the intra-CB t_out alignment and the
compiler result-consume calendar need re-derivation (a new regen rule) on that bind.

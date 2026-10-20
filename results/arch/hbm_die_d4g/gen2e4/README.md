# GEN2e4 strict bind (L2H-GEN2E, LEAD3-HBM, 10-19)

GEN2e4 = GEN2e3 (l20c/p/t/s) + l21 observation readback (8fa2094c4) + exact real-width relay tails (codex fc4a7b120)
+ l22 (`tools/hbm_die_v16/d4g_layers/l22_e4_compose.py`):
- col_idx `ot_hbm_static_cfg_collar_idx256r` FAN32=1 (source 944b0ceb2; kits hdie_col_idx256r_a/_b, not closed yet ->
  SYNTH stand-in);
- 64 PC controllers `ot_hbm_svc_pc_ctrl_leaf_cfg_h9b` -> `ot_hbm_svc_pc_ctrl_leaf_cfg_safe_face` (HBM-MC3 RELEASE
  controller, claude/l2h-bw-safe-1019 @0f123a216, kit params of hdie_pc_ctrl_mc3_p540: RST_FOREST=1 PCID_LOCAL=1
  RESET_LANDING 2 SRAM_P192 PURE_FACE). Ports identical (checked), 0 edges changed. LABELLED SYNTH STAND-IN until
  hdie_pc_ctrl_mc3_p540/_q648 is CLOSED.
- IDX selector: `ot_hbm_idx_selector_static_sel` (l20s) stays; no selector view is CLOSED (L2H-IDXSEL s1a/s1b at gate).
  Swap to the closed one later (parallel).

## S1 strict bind (pre-relay die, `s1/`)
- default: structural 0, input_tied 0, unread **65,066** (= reviewed manifest exactly) (`default_bind.log`).
- exact transfer of the l21 candidate (309 entries, 0 re-pointed, die_line recomputed, source_commit = this branch so
  the FAN32 collar bytes are the reviewed bytes) -> `review_e4_candidate.json` -> proposal
  **394952eecf16e383b1df57eb40309d1dfd3acb1cae7c20c60f37e303f625cb66** (`manifest_proposal_e4.json`).
- replay: **DIE_PORT_BIND PASS, unread_net_bits 0, input_tied 0** (`strict_replay.log`), die.v identical to default.
- 056f138d (l21) is refused on this source (FAN32 collar drift), as REFILL-1725/HBMREG found; 394952ee replaces it.
  Admission of the digest: LEAD (exact transfer, no new permission).

## Exact-tail class representatives (`tail_classes/`)
`exact_tail_layer.py --classes`: one parameterised class master per base (`<base>_tw #(TW)`, core .W(TW), packed data
branches k*TW), the instance carries #(.TW(real width)). 981 per-width masters -> **61 class masters**; no padding, no tie.
The codex tail_strict 618 input_tied were landing K straps still naming the base master; straps now follow the renamed
master. GEN2e2-basis post-landing die (same splice as codex tail_strict): **masters 1117 -> 197, input_tied 618 -> 0,
unread 541,758 -> 70,320** = exactly the GEN2e2 pre-relay residual, which GEN2e3/l21 + the manifest clear (S1 above).
`--check` (chain mode) refuses to regenerate a different class source. Validator `exact_tail_validate.py` accepts the
re-mastered straps (all other fields identical).
Physical: synthesis is still per (class, TW) parameter set; native closure should be qualified per class (the class
body is a W-bit pipeline slice; narrower TW = subset of identical bit-slices) instead of 981 routes - ROOT rule owed.

## Chain
`chain_d4g2e4.sh`: S1 (layers + strict manifest PASS required) -> S2 synth (new: collar FAN32, obs leaves, ingress_obs,
ckgen_nolink, MC3 face) -> S3 case_a -> S3i AGENT GO (no auto-GO) -> S4 -> S5 land step with classes (unread held) +
transfer/propose/replay + tail map validation -> S5b -> ... -> S8 strict manifest -> S11 GRT/STA.

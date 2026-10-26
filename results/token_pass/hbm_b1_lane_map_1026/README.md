# HBM B1 operation/record -> traversed-lane map and S2 price (TOK-HBM, 2026-10-26)

Tool: tools/hbm_b2/b1_lane_traversal.py (map | price). Status CONDITIONAL_MODEL_NOT_ADOPTED (no native/G5/physical claim).

Edge ledger per plan (nothing defaulted): lane cycles = tools/die_plan/schema Plan.lane_latency; lane endpoints =
every hard-core port on the lane's src/dst bus in core_conns.json; + internal relay stations on those buses.
Status ports (fault, fault_cause, phy_up) are on no record path. Family of a lane = core families present at both
ends (union when one end is soft). Record latency per family = sum over (src role -> dst role) legs of the LONGEST
traversed lane (static schedule pads a coherent group to its max) + longest directed same-role chain (HC bank sum
chain). Op delta = candidate - baseline per op (ds_relay_latency crossing classes, lane-explicit), charged as fixed
cycles per record in the exact accepted_cost.hbm_schedule S2 schedule (ds_ar 576702.4 / qwen_ar 1269120.1 basis).
Not the bit-weighted mean of stages_arch, no B2/generic stage price, no station sums.

Plans (epyc1:/srv/opentallas-scratch2/claude/path-hbm/): b1m5_0126/plan 107ae672 (Codex baseline),
b1c_1026/native_cut_bands_r3 0552ecf2 (pre FT overlay), g0cfix_1026/plan_b1n6 60d58330 (current). Core graph for
both sides = b1n6 core_conns.json (directed HC graph; the b1m5 graph's false HC targets are a model error).

- price_request.json  (PATH-HBM-R2 06:04 request: FT overlay L15/L51/L93/L101/L119/L126/L146 +1, L36 +2, mirrors):
  per record SU.*/ARGMAX/FUSED +2 (L36 hub->su critical), HC +1 (L15 in bank chain), COLL.* +2 (L101 hub->io ctl,
  L126 io->hub; L51 data not critical); L93/L119/L146(+m) carry no core port in the b1n6 graph -> no record.
  ds_ar +2893.1 cyc/token 2080.80->2070.41 tok/s loss 0.499 %; qwen_ar +1158 944.68 tok/s loss 0.091 %.
- L100x1 (q_b100 FT of lane L100 hub->sm3 ctl): lane 7->8 already in b1m5->faces_hcdir (not the b1n4 nudge, which
  kept stations); not on the critical SM leg -> 0 on any record.
- price_full.json (b1m5 -> b1n6, whole B1 event): ds_ar lower 1.047 % / upper (SM x-leg serial) 1.417 %,
  qwen_ar 0.142 / 0.256 %. Includes TOPK L74 hub->root 3->18 (+15): price_full_noTOPK.json excludes it as covered by
  the accepted COLL.TKX_Q_HUB_NW +52 row (ds_ar 0.922 / 1.293 %). HOST io<->root L48/L53 +6 not charged (host
  interface, <= 12 cycles a token).
- 46 changed lanes are traversed by no record in the b1n6 core graph (map.json 'families' empty) -- bind owner to
  confirm they are dead (or declare their soft endpoints).
MTP not priced: the accepted-cost r25gq basis has ds_ar + qwen_ar only.

- file_ft_overlay_row.py (2026-10-26 TOK-HBM): re-runs the S2 schedule with price_request.json lower terms (matches 2893.1 / 1158.0 cycles), files + accepts r25gq HBM.D4G_B1_FT_OVERLAY (ds_ar 0.499 %, qwen_ar 0.091 %; r25gq accepted 10.915 -> 11.414 %). Needs a full results/arch + results/rtl checkout: a sparse tree silently changes the S2 base (557291.4 vs 576702.4).

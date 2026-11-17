# KV-CLK-R2 handoff (Opus; successor of FABLE-DIE-KV-R; owner of the KV die clock for event HG2; started 2026-11-16 18:3x PST)

Work dir epyc7 /srv/opentallas-scratch2/claude/kv-clk-r2 (M). Inherited runs: epyc7 /srv/opentallas-scratch2/claude/fable-die-kv/hg2 (G).
KV-R owns the D4/D5 trees, views, C bind and pilots.

## State 18:5x PST
- Tree PICKED: e6a (G/e6a.yaml: link_htree + DME delay + elongation on all regions except hub_C), tree dc4842b75b69,
  11,571 taps / 42,509 cells. GRT0 0/0 overflow, setup intra +482/+543, TT slew max 76, CA 3915/3915 PASS.
  e6b: also 0 over cap, but slew 142 and 2x the >80 ps pairs. e5a 8 ports over, e5c 74 (hub_C), e4 40.
- Rows B: M/rows/e6a/rows_sites.json (main clksite_reserve --native-origins --protect-points --edge-gap-um 5): 51 types,
  19,309 rects, 0 walls (G/wallcount.py), 0 blocked points.
- Rows C: M/rows/e6a/rows_windows.json, need + 10, 0 over 208.25 (max 202, mean 72.4); seam_ps 170 (FF seam need 155.3).
- HG2 plan: tree M/qk_hg2 (copy of G/qk2), plan_of_record/plan_c.json sha c15e87e46597 = base 1fcc70c6c0c7 (HG1A + rows A)
  + B + C + clock.die_tree record. Delta is clock fields only. Receipt M/HG2_compose_receipt.json.
- R-REACH on HG2: 0 errors, 8 R-REACH-3 warnings; R-REACH-4 54 types, 2,022 fwd outputs, 0 over/dangling/root, worst 404.6 um.
  (A plan copy outside its tree fails R-REACH-4 silently: relative sink_bins paths. Always check inside the tree.)
- Real-view hold (M/hold/e6a, 20 views): intra measured 4,096 pairs, 27 neg, worst -38.5 (e4: 15 neg, -25.25).
  All 27 capture at a landing core (kv_cland_* / pv ring child) whose d pins are partition input ports
  (HG1B netlists kv3_hg_v1p6 22/22, kv3_pv_v1n 30/30). The landing q goes to an ot_dp_st station flop on the plain clock.
  The intra pair set is an all-tap cross product (die_sta_related build_pairs), so these are not data edges. No structural fix.
- Opus self-review running in parallel (findings land in the post).

## Next
1. KV-R: fresh bind of HG2 (new plan sha -> new fingerprint) + LATCHECK; the rows B pilot kv3_pv_v1n waits on KV-R's D5 tree.
2. On a review BLOCK: fix and recompose (scripts M/rows_hg2.sh RUN, M/hold_e6.sh RUN).

## 11-17 lever 2 (per-port tap window = hold class), M = epyc7 /srv/opentallas-scratch2/claude/kv-clk-r2
- HG2b/HG2c/HG3 clock fields verified; clock.cohort row landed in HG3 006e38e15a71 (rows_cohort_e6a.json b043c6e92991).
- e7 = HG3 tree with OT_CLK_DME_TEMPLATE=2 + exact clock SPEF (M/chain7.sh M/e7.env e7; runs/e7): SPEF tol p90 10.9 / p99 30.9 / max 56.2.
- CLASS CONFIRMED (post 9168e2ea): M/xtap.tcl + xtap.sh (copy of QC sta.tcl) + xtapan.py on post-CTS FF DBs:
  kv3_hgi_v1__cl141fc26e (epyc10 kw43 kv101ns, W 130): cross-tap 4,408 worst -152.5, 99.4 % window-only; offset projection 163 (worst -44.1).
  kv3_sys_SD_v1 (epyc8 kvN2, W 80): cross-tap 2,323 worst -79.8, 100 % window-only. Outputs: <host>:M/xtap_hgi_v1, M/xtap_sdv1.
- Rows (not applied): M/rows_l2/{rows.json 1287f7a89fdb, plan.json 1ecde607e8df, report.json} by M/rows_kv.py (QC rows_m + creates
  clock.tap_offset, SKIP_TYPES = 5 signed keep windows): 51 types, 6,129 ports, tol max 66.2, seam 170 -> 140, table errors 0.
  The tables carry plan_sha 006e38e15a71 (HG3): re-cut on the next plan sha (rows_kv.py refuses a mismatch).
- Tree fix: hg/pc types sit R0/MX/MY/R180; template copied only the MX instance. Branch claude/kv-clk-r2-tmplx-1117 (worktree M/src_tx):
  opt-in OT_CLK_DME_TEMPLATE_XMIRROR=1 also copies onto x-mirrored instances (+ test_die_trial_dme_template_xmirror.py).
  e8 = e7 + XMIRROR (M/chain8.sh M/e8.env e8) launched 11-17 via ot-run from intel2 (log intel2 ~/tmp/kvr2_e8.log).

## Next (lever 2)
1. e8 CHAIN_DONE: GRT overflow 0 both corners, SPEF tol readout (expect hg/pc <= ~15), CA. Then rows_kv.py on e8 -> rows for the event after HG3b.
2. Branch GREEN -> READY post; KV-R composes rows into the event after HG3b (fresh bind + LATCHECK + Fable review).

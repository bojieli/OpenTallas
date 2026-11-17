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

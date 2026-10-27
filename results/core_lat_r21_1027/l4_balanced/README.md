# L4 geometric leaf-load candidate

Source `8e55a0cd534db5d5b4581c38356b5a83716372e1` adds an opt-in `balance_leaf_counts` structural planner step before existing clock sizing. The canonical calibrated UF3 kernel is unchanged. No clock-stage, timing-window, insertion-band, or data-path relaxation is made; canonical family defaults remain unchanged.

The actual L4 census has 12,098 clock sinks. Reassigning 684 boundary sinks across geometric leaves changes leaf counts from the old early31/35 vs late53/58 imbalance to46..56. All12,098 sinks remain represented exactly once, with no duplicates or additions. The same553 clock cells and7 stages are retained. Maximum leaf spread31.66um is below35um; maximum leg detour1.0; PG clearancePASS; slice site displacement.405um.

The old frozen calibrated model failed the unchanged20ps window: TT226.92ps/window20.81, FF171.60/window17.87. The new candidate gives TT222.96/window12.44 and FF168.91/window11.84; maximum output slew46.15/34.59ps. Means remain outside target bands and are recorded as such. These are PLAN MODEL, UNCHECKED values, not extracted timing or a signed core.

`plan.png` was viewed: a thin345.6x64.8um macro-free hierarchical center tree, local leaves, and no meander geometry. The exact source was staged through ot-run and finished on epyc2, unit332103-1793135847, exit0. The input census and libraries are preserved at intel2:/srv/opentallas-scratch2/claude/codex-s81-r21-models-1351/structure. This packet supports a candidate structural template and subsequent actual master-slice PLACE trial; it does not authorize route or release.

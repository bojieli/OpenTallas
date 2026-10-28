# S81 G-clock body legalization, Oct28 03:59 takeover

Clock-only physical experiment; no canonical plan or RTL adoption. Exclusive S81 owner branch `codex/s81-owner-1028-0359`. Source main786c14bf9e contains the reviewed shared optional packer. Parent geometry is `die-s81-5/plan_s5.json`, SHA d29050658673be93795e28b81c8b05e06c3ffbb8470c498aea7f9d30c791eacf; original clock is `die-s81-7/kit_G/clock`.

The original 24,523 actual BUFx24 bodies had 474 overlap pairs (133 exact coincident pairs in the independent pair census; packer's coincident-extra metric is129). Point legality did not establish body legality. The shared packer places all bodies on .054um sites/.54um R0 rows, inside individual hosts and outside core/PHY halos. Result: zero body overlaps, halo hits, or unhosted cells;24,313 moved, maximum Manhattan move2.222um (Euclidean1.767um).

Applied every packed coordinate to ctree.tcl, tree.sites and all17,272 logical node coordinates, preserving topology, buffer count, taps, RTL and all stage/cycle counts. The image was personally viewed before the fresh GRT. Source/sink pin identities and die dimensions are unchanged. Calibrated length perturbation estimated +1,061um/3.99m total wire and maximum1.153ps change to a region's relative tap delays. This estimate is not an extracted or routed receipt.

Fresh clock-only combo global routes via ot-run64GB/8threads completed TT and FF with0overflow. Both exported8,127 taps,0missing,398regions. Current-main count_align_plan with actual STA interval hull, SPICE calibration and LCA CPPR:2,306crossings,0FAIL/0below100ps; low margins113.2ps at scale1.0485 and105.9ps at1.0552. Physical reset/START schedules and token gates remain separate work.

Current-main declared-core-budget STA gives calibrated intra skew134.01TT/109.68FF, but hold−162.50FF and zero kit tap-window contract. These are declared250/202.5ps core budgets, not real signed views. The clock experiment does not qualify core hold, PG connectivity, the F1 data relay geometry, or release timing. No failed verdict was replaced. Old G receipts remain in their original paths.

Runtime on intel2: `/srv/opentallas-scratch2/claude/codex-s81-owner-0359/clock_body` with `route_TT`, `route_FF`, `proof_body`, `routed`, `sta_body_spice`; source and launch scripts in this packet reproduce the exact experiment in that runtime. `tree.body.json.gz` and `sites.body.json.gz` retain the actual applied coordinates/topology; result.json has the bounded summaries. No canonical kit/source was overwritten.

`core_means_diagnostic.json` is separate actual CTS placement-RC diagnostic metrology for three leaf candidates. It is neither SIGNED nor extracted-SPEF clock insertion. All active-edge flops are included without the old400ps cutoff; vn_a explicitly records the one unresolved macro clock `u_h0/clk`, rather than fabricating an arrival. Those values were not attached to unmatched canonical libraries.

Remaining same-event S81 work: F1 road-aware data banks and repair buffers (M7 opaque core crossings), actual core views/hold budgets and current PG macro connections;39 other stubs+456M7-only BF views remain open after the separately merged M5stub repair470fcd754e.

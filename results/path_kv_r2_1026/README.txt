PATH-KV-R2 2026-10-26 -- KV 8-region mesh clock: complete related-pair check + stub trim (diagnostic/freeze-candidate evidence)
Source: this branch (claude/path-kv-r2-1026) = claude/path-kv-clk-1026@997a54b808 + die_clock_mesh.py `stubtrim`.
Inputs (fleet, not in repo): plan epyc1:/srv/opentallas-scratch2/claude/codex-kv-mesh-1026/plan.json (sha256 d34cbb51...),
kit .../codex-kv-mesh-1026/kit; builds epyc1:/srv/opentallas-scratch2/claude/path-kv-clk-1026/{c3e,c3t}.

COVERAGE (conservative all-tap superset, no endpoint ledger needed):
 (1) every die-level data arc is a plan port between ABUTTING partitions (3915 ports, kind data, 0 non-abutting pairs;
     multi-hop links are decomposed into neighbour hops whose stations live in the crossed partitions);
 (2) every endpoint register of a partition is clocked from one of that partition's own taps (tile CTS, tile gate);
 => every die launch/capture pair maps onto a tap pair in {all intra-partition tap pairs} U {all tap cross-products of
    connected partitions}. Same-region pairs: 62,520 (checked here). Cross-region connected partition pairs (43) are
    LANDED (forwarded clock, +2 cycles, COORD ruling 05:13) and gated by the landing window (416.5 ps).
 CPPR credit only at each region's H-tree node (mesh NOT common), both directions per pair, TT and FF, routed RC.

c3e (neighbour proxy 60.79/57.02): COMPLETE TT 85.06 FAIL (12 pairs >80) / FF 79.74. Root cause: stub length spread
   (e.g. pv_S_4 t14 stub 187.7 um vs t23 26.8 um on one region mesh). -> c3e_complete_pairs.json, c3e_complete_lp_x300.json
c3t = c3e + measured per-tap stub trim (joint TT+FF LP over the same 62,520 pairs; 779 pads (BUFx24 37.3 ps + BUFx6f
   24.7 ps steps) on 755 taps between stub buffer and unchanged tap wire; trim range uncredited, early = 0.97 x lift):
   die GRT (kit signals M4-M7 + clock M8-M9) congestion 0/0/0 TT and FF; 0 clock-cell overlaps; 0 hard-keepout cells;
   COMPLETE related pair TT 63.95 / FF 54.71, 0 pairs > 80 (p99 47.45/40.98); proxy 57.54/46.22;
   landed damage 122.1/115.0 vs 416.5 window; tap slew 105.9/89.1 ps. -> c3t/clock_report.json, c3t_complete_pairs.json
Owner 06:3x audit: c3e_core_lat_audit.json (hard-core types, early taps), c3e_islands_dry.json (islands per type).

== 12.8 re-measure (OWNER v4 12.8, 2026-10-26) ==
c3t (63.95/54.71) used balance pads + per-tap stub trims = banned closure means (12.8d/f); it does NOT count.
By-construction re-measure: d45x2/b0 = plain build (no balance, no trim), uniform sizing, on the worst-case PG grid
(infra pg_x2.0_bp45: 45 um bumps, x2.0 power, M8 8.64 / M9 1.728), tools claude/path-kv-clktools-1026@HEAD,
run_kv_mesh_chain.sh (MAXMOVE=500), chain stopped after b0 measure (later steps are banned means).
Complete related pair (62,520 pairs, CPPR only at region H-tree node = last common tree node): TT 281.37 (6931 >80) / FF 229.58 (3989 >80): FAIL.
Equal to the old untrimmed c3 on the plan grid (related 227/191 proxy), so the PG grid is not the cause.
Root cause (structure, 12.8e): within-region tap arrival spread 120-270 ps TT from
 (1) H-tree branches not equal length: driver site moves <=358 um, node moves <=263 um, rep slides <=171 um to find legal sites
     (KV has no channels; partition interiors), PHY-corner driver pair fix (13,62);
 (2) tap stubs 27..364 um (taps at partition clock pins, not lattice positions);
 (3) unequal load per tap (no density-tap classes).
Structural fix (12.8d): lattice-snapped H-tree with reserved island sites at every branch point (master-plan islands),
equal-length branches, density taps of equal load per tap class at fixed stub length, core clock entries at core centre (12.8a).
That is a master-plan / shared clock tool change (MASTER-PLAN + CLOCK-128 lanes), not a KV-local tweak.

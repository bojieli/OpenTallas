# GEOM-REVIEW batch 1 (2026-10-24): die-level independent review of the current plans

Owner order 2026-10-24 08:05 PDT: review the design visually, the way an industry floorplan / physical-design reviewer would,
before it goes to routing or STA. This batch is the independent second review at die level. Tile-level reviews (G3 kits and hard
cores) follow in later batches.

How it was done: the branch's own `tools/die_plan/check.py --completeness --png` (G0/G0C re-run by me, not taken from the lane),
then `tools/geom_review/plan_review.py` (new). That tool draws:
- the whole die, with hard cores and with seams coloured by bits/um;
- a lane bit-density heat map;
- automatic zooms: densest bundle, longest lane, largest bit*mm lane, densest seam, clock root, IO, most core-filled partition,
  thinnest partition.

It also measures:
- lane bit*mm ranking and hops vs reach;
- per-seam bits/um;
- bit-order twist for every ft crossing. This is a chord-planarity test. With H and V layers it only costs wire when a straight
  or U-turn crossing has in/out windows that overlap.
- interpolated ft-station points that land inside hard cores;
- root-to-tap distances, aspect ratios and slivers.

Pictures and `review.json` for each die are in `img/<die>/`.

| die | plan (sha256/12) | branch @ commit | G0 / G0C (re-run) | verdict | blocking items |
|---|---|---|---|---|---|
| S81 v4.8 | ea36999b8da5 | claude/s81-p10-1024 @7c898ad6df | PASS / FAIL 91 (hard_cores) | PASS-COND | 91 hard cores (S81-CORES); 72 x_*_out ft stations interpolated onto ROM macros: declare regs_um |
| S81 v4.8 + reserve SerDes (XDIE) | e2299c436912 | claude/s81-xdie-1024 @cb472fd41f | PASS / FAIL **108** (lane claims 91) | PASS-COND | 12 stale census entries (s_0S/s_7N re-slice) + 5 missing cell estimates (serdes__t11-14, slice_station__t7) |
| S81 head | 6b6620d0e030 | claude/s81-head-1024 @fa3ada974c | PASS / PASS | PASS-COND | none; lever: 3-4x the stations reach needs on the mesh/host/coll lanes (m0S 48 cyc over 16.3 mm) |
| Qwen compute P6 | 0028ad5329ca | main @fd219eafe7 | PASS / FAIL 4 (ft_budget st_a/st_b) | PASS-COND | ft_budget; 252 column ft stations interpolated onto A0 cores |
| KV v3.8v (=v3.8u geometry) | bc4edcd42be7 | main @fd219eafe7 | PASS / PASS | PASS-COND | 1,394 of 4,359 ft station points land inside cores (hgi/pv rows, x~4.8 mm trunk): plan cause of the measured 728-um ft hops |
| HBM B2r2 | c1bc2d0f7ada | claude/hbm-arch-1024 @3277b5e78b | PASS / PASS | PASS-COND (plan); **G3 BLOCKED** for q_sm*, q_hub, root | q_sm 100% macro wall (no area for face flops / fan-out / CTS); q_hub shelf-packed, not data-flow ordered, no channels; root core stack under the hottest bundle (9 kb/100 um, L4 2,816 b) |

Checked and clean on every die:
- no hop over 0.9 x reach;
- no costly bit twist: every full reversal is at a corner crossing or between disjoint windows, so it routes at no extra wire;
- no hard core outside its partition;
- mirrored quad / half symmetry where the plan intends it.

Records: `results/geom_review/<element>__<die>__<sha12>.json`.

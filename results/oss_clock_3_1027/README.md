# OSS-CLOCK-3 (2026-10-27, Claude) -- branch claude/oss-clock-3-1027 (base claude/oss-clock-2-1027@285ba72636)

## (1) clkplan crossing_mode=count_aligned = the count-aligned ring window (bug fix, COORD 21:10)
* ocv.count_aligned_margin: lag L = K T + rel, rel = [min_c(d-p_dn) - X T - w, max_c(d+p_up) + Y T + w]
  (union of corners, X/Y = start-tree origin ambiguity, w = 5 % x unshared wander); K = smallest integer with
  L_lo >= 0.5T + ap (K from the DERATED lag), ap = T/8 default; DEPTH 4 if L_hi <= 3.5T - ap else 8 if <= 7.5T - ap else
  FAIL; margins to the guard edges (L_lo - 0.5T, (DEPTH-0.5)T - L_hi), gate >= 100 ps. Latency K+1.
* old one-period setup+hold window kept ONLY as crossing_mode=ring_phase (ocv.ring_phase_margin).
* clkplan.crossrows: same evaluation on external routed-STA crossing rows (landed_phase_ocv format).
* Cross-check vs tools/die_plan/count_align_plan.py MESO-COUNT-2 (claude/meso-count-2-1027@f7b28e70d), spice OFF
  (inputs intel2:/srv/opentallas-scratch2/claude/oss-clock-3/ca: HEAD feed40 = die-head-1027 routed_sfb250/landed_ocv.json
  remapped by maps/feed36b.json -> 94 crossings; KV = meso-count-2/kv_lpo.json, 3915):
  - HEAD feed40: 94/94 identical K, DEPTH, L_lo/L_hi (max diff 0.0 ps); worst margin lo 307.1 / hi 1363.8, D4 94,
    latency 2:51 3:43 (CHECKED-own, both tools).
  - KV: 3908/3908 tree + nontree identical (0.0 ps; nontree origin ambiguity X/Y recovered from the MC2 output);
    7 tree_ambiguous rows differ BY DESIGN (MC2 uses the start-sync phase window on the ambiguous tree edge itself;
    clkplan has no start tree, it takes crossings[].origin_cycles). Summary: 0 FAIL, D4/D8 3391/524 vs 3392/523,
    worst lo 105.1 / hi 162.9 both.
  - vs main count_align_plan (MESO-COUNT-1, superseded tree/origin model): HEAD identical latency/depth; KV latency
    differs on 609 nontree + 15 tree rows (expected: NUMBER-CHECK 20:48 flaw fixed in MC2).
  - superseded ring_phase window on the same rows: HEAD 78/94 <100 (worst -90.3), KV 968/3915 (worst -502.1).
## (2) spice-scaled arrivals (default ON, --no-spice-scale)
* model.spice_cal from opentools/mscts/data/asap7_bufx24_spice_cal.json (TT 1.0485 / FF 1.0552) multiplies STA-basis
  delays (declared insertions, external rows, STA-fitted stage model); the built-in ngspice stage model is not scaled twice
  (model 100.24 vs spice-cal 100.83 ps per 450-um stage TT).
* Effect (CHECKED-own): HEAD feed40 worst lo 307.1 -> 301.8, hi 1363.8 -> 1359.4, K unchanged; KV 0 FAIL kept, worst hi
  162.9 -> 150.6, lo 105.1 -> 105.4, K changes on 176 crossings (latency hist 2:2512 3:927 4:370 5:106 vs 2:2676 3:763
  4:382 5:94) -> RTL K emitted by count_align_plan must use the same scaled rows (MESO lane).

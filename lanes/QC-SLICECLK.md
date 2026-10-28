# QC-SLICECLK lane: QC per-slice clock variant (METHODOLOGY 12.10b; parallel to INFRA-FIRST-QC, first to pass the freeze gate wins)

- 2026-10-27 19:04 PDT QC-SLICECLK-1 RESULT claude/qc-sliceclk-1027@88bc183c7c (results/qc_sliceclk_1027/README.md). Basis: main 133d979e4c, canonical68 QC plan.
  (1) DOMAINS: 12 slice domains (c_S_*+sl_S_*, 30 parts each, 2.47 x 26.3 mm) + HUB (west IO strip). io_serdes_2 is merged into W5 (hard PHY rule).
  - Crossings: 269 ports / 64,367 bits on 264 lanes (CHECKED). All sit at sl_fe <-> sl_fw between neighbour slices (line W5..W0-E0..E5) + HUB<->W5. With the PHY merge: 264 / 63,170.
  - Related pairs kept: 2,541 intra-slice ports / 1,184,174 bits (CHECKED, 93 % of the bits).
  (2) PRICE (nativev7 composer): K=3 = 298,285 cyc/token, 4,024.6 tok/s, -0.65 % vs 296,341 / 4,051.0; K=2 -0.43 % (CHECKED by an independent NUMBER-CHECK agent, lane-identical requirements).
  - CB16 is unchanged; the whole cost is 11 serial slice hops = +54/layer. The latency table adds +3 on exactly the 264 lanes (OWN).
  - Far below 5 %, so no cheaper cut is needed. Pairs -0.40 % / halves -0.25 % (OWN).
  - Ledger row QC.SLICECLK_LAND proposed (0.652 %) on the branch.
  (3) PLAN DELTA: clock_landing_plan.compose gives 68 -> 81 types (24 landing/monitor cohorts) and 144 ring bands, 0 placement FAIL.
  - G0 PASS 0E/167W; G0C PASS 0E/142W with cohort cell evidence (base 0E/111W). All new warnings are cohort-renamed copies of base warnings (OWN).
  - die_trial region trees: 13 trees, 18,194 cells, 0 illegal sites. Renders viewed.
  (4) CLOCK BUILD = STRUCTURAL FAIL (OWN): the arrival spread inside one slice is 1,634 ps TT / 1,380 ps FF.
  - The far c rows (y 0-5 / 21-26 mm) arrive ~1.4 ns after the centre rows. The stock --region-trees bisection is not equal-length on a 10.6:1 region; it was built for S81/KV <= 2.2-mm regions.
  - Die STA not run (pointless on this tree).
  - The die GRT probe (clock only as 30,143 reserved rects, "0 clock nets") is running: intel2 /srv/opentallas-scratch2/claude/qc-sliceclk-1027/trial/grt/grt.log + chain.log. Collect overflow at 50 iterations; routability only.
  NEXT: build a balanced per-slice distribution (equal-length slice spine/H-tree or per-slice mesh) on the ONE shared M8 clock-row reservation that INFRA-FIRST-QC-R35 implements (COORD 19:0x ruling, agreed: no separate fix here). Then die GRT incl clock + die STA (main die_sta_related.py, --landing-window-ps for the 264 crossings).

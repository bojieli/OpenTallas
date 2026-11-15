# HEAD-CLKFEED-1 handoff (2026-11-15 02:0x PST)
## RESULT
Deliverable: epyc2 /srv/opentallas-scratch3/claude/head-clkfeed-1/cfg/feed_hk6.json (+ head_p16g.yaml, region map unchanged: 327 regions). Feed delta only: no plan, partition CTS, H-tree or mesh change. Strict die_trial kit (actual_max 405) passes with hk6 (p16g, 0 legs over reach). hk5 (same feed, all taps straight) had one 453 um leg on sst5->sst4; hk6 keeps the hk4 taps on the 38 non-row edges.
Feed: rows re-parented along the data ring sp -> o0..oN -> turnA | turnB <- bN..b0 <- sp. Non-tree landing edges 144 -> 12 (turnXa->turnXb).
Measured p16r (hk4) -> p16f (hk5), same plan rp21z16, same flow:
- deepest tap late TT 8,992 -> 6,913 ps (FF 7,987 -> 6,147); median tap 4,723 -> 3,825
- feed wire per edge median 1,088 -> 746 um (tile-row edges 1,086 -> 746, pitch 717); total 394,905 -> 283,587 um; max 2,581 -> 2,366
- count-aligned plan (rise-only readout, same driver both sides, 427 crossings): DEPTH 8: 165 -> 38 (DEPTH 4: 262 -> 389); width median 1,207 -> 358 ps, p90 2,181 -> 1,388; worst margin 104.2 -> 108.6 ps, 0 below 100. Largest width 3,032 ps = the turnXa->turnXb crossings (cut point of each ring row).
- START rows not judged (rise-only, as before). Fable estimate 6,000 ps; the Manhattan lower bound from root sp3 is 16.7 mm = about 5.8 ns, so 6.9 ns is within 1.1 ns of it.
Lever 5 (stage model): on p16r routed legs the registered model inv_ndr_head26_i150 is NOT 17 pct optimistic: measured/model = 1.005 TT, 0.981 FF on feed legs (1.023 / 1.004 all legs); sp2->sp1 early 765 vs model 763. The 0.343 ps/um is LATE arrival over routed wire (146,971 ps / 428,000 um); late/early = 1.15 TT. Refit TT (placed stages) d0 12.78 k1 0.1662 k2 0.0002 kf 7.16 (refit/ps.json, refit2_TT.json), no registry write. Recommendation: keep the model for balancing, scale unshared-path estimates by 1.15 (late).
## Notes
- rp21z20N: feed is plan-independent except tap centroids of lep0N/mesh regions (roots from p16r). Not yet run on z20N; the feed json applies unchanged as long as the 327 region map holds. Rerun p16g flow on rp21z20N when it is adopted (run_p16g.sh, plan path in head_p16g.yaml).
- --count-align is not in proto_die.sh yet (DIE-HEAD-ROUTE-1); I used the rise-only head_ca_riseonly.py (head-clkfeed-1/run_ca_p16{r,f}.sh).
- Tool patch only in my private copy src_dbg (prints every over-reach leg as HCF_BAD instead of aborting); the kits above used no change in tree geometry.
- Queue line for HEAD-99: K/DEPTH/lane latencies change with the feed (DEPTH 8 count 165 -> 38); re-bind K and latencies from p16g/p16f arrivals before adopting.
## Paths
epyc2 head-clkfeed-1/: cfg/feed_hk{5,6}.json, head/p16f (hk5 chain), head/p16g (hk6 kit+GRT chain, may still be running), ca_p16r/o, ca_p16f/o plan.json, refit/.

## RESULT 2 (11-15 02:5x PST) -- hk6 ported onto rp21z20NC, both-edge CA (COORD items 1-4)
1. p16g (hk6 on rp21z16 plan), GRT TT/FF: EXIT 0, 0 congestion on every layer (M4-M9, same as p16r), arrivals: deepest tap late TT 7,001 / FF 6,214 ps (p16r 8,992 / 7,987).
2. rp21z20NC (epyc2 head-clkfeed-1/p20nc/prep/source_plan.json, sha cde7a5584e5f after asset-path rewrite; same 358 partition names/origins as p16, so the 327-region map and feed_hk6.json apply unchanged):
   - strict die_trial kit (actual_max 405, no patch): rc 0 (head/nc), deepest tap late TT 7,001 / FF 6,214 ps, feed wire median 746 um, total 287,467 um.
   - both-edge flow (grt2 readout with fall rows -> head_current_ca -> ca4 freg bind -> die_sta_related --count-align --count-align-key part), same scripts as DIE-HEAD-ROUTE-1 p16r (both_ca_nc.sh, ca4_nc.sh): 427 of 427 crossings, 0 fail, DEPTH 4 on 427, TT worst lo 204.9 / hi 1,089.6 ps, FF worst lo 132.3 / hi 1,086.0 ps, 0 below 100, start hops over 405 um: 0, 18 freg ports, BIND_OK.
   - same chain on p16r (old feed, DIE-HEAD-ROUTE-1): 427/427 PASS, TT lo 211.9 / hi 1,179.4, FF lo 151.2 / hi 1,100.4, DEPTH 4 on 427. So with both edges the old feed already passes: the earlier "DEPTH 8 165 -> 38" was a rise-only artefact. hk6 adds no CA margin (ΔTT lo -7 ps, FF lo -19 ps, hi -90 ps); its gain is insertion: deepest tap -22 pct, feed wire -28 pct, supply-noise jitter exposure of far regions about a third lower.
   - NC intra-contract (not feed related? unverified): FF intra skew 271.6 ps, kit-contract need 271.6 vs W 92, 53,550 violations; p16g on rp21z16 shows 106.6 / 44,303. NC local trees differ (lep0N/mesh taps moved); no old-feed run on NC exists to separate cause. Owner: HEAD-99 / DIE-HEAD-ROUTE-1.
3. For HEAD-99 parallel variant rp21z20NF: feed file /srv/opentallas-scratch3/claude/head-clkfeed-1/cfg/feed_hk6.json (copy to epyc7 head-99 on request), ot_clk config cfg/head_nc.yaml (inputs: plan, regions_hp1.json, feed), CA result head/nc/ca4/out/{bind.json,plan_fz.json,regions_ca.json}. Bind latencies total lat_cycles 1,061 (old feed 1,063): K/latency table essentially unchanged, so rebind needs no re-sign beyond what NC already carries. Adopt the first to pass.
4. Stage model: 1.15 late scale NOT written to registry (per COORD). Root-move question (6.0 ns) with Fable.

## RESULT 3 (11-15 04:2x PST) -- lep0N rebuild + sp5/sp2 (COORD sections 18, 19)
Root cause note: the NC lep0N tree is not an H-tree/DME-algorithm issue. An H-tree rebuild gave the same 233 ps FF spread (ncl, ncl4: independent of feed). The DME region tree of lep0N has one 1,932 um physical leg (node 7866, Manhattan 1,553 um, routed detour chain) priced 71 ps too fast by the stage model; legs priced on a 405 um stage bound accumulate this. Lever that works: per-region physical stage bound `region.actual_max_region: {lep0N: 300}` (config line only; cfg/head_la300.yaml on epyc2 head-clkfeed-1; all other region trees unchanged).
Variants (NC plan rp21z20NC, feed hk6, strict kit passes on all):
| lep0N rebuild | FF spread | TT spread |
| NC as is (actual_max 405) | 246.1 | 262.4 |
| H-tree, centroid=2 (ncl) | 233.0 | 266.1 |
| actual_max_region 250 | 90.6 | 96.1 |
| actual_max_region 200 | 76.8 | 84.8 |
| actual_max_region 300 (la300) | 63.1 | 75.1 |
Accepted: la300 (FF 63.1 <= 92). Other 357 partitions: 350 within 0.5 ps; 7 (lk_WN1, lk_WN2, nst1, nst2, nst3_transit, nst3_turn, nst4: the subtree hung from the lep0N root) shift 9.6-10.9 ps (common-path, rigid). Die STA on la300: FF intra skew 271.6 -> 128.6 ps, contract violations 53,550 -> 44,176 (p16g/rp21z16: 106.6 / 44,303), seam unchanged (FF 80.9, TT 91.2). Both-edge --count-align on la300 (ca4 flow): 427/427 PASS, DEPTH 4 on 427, TT worst lo 164.4 / hi 1,089.6, FF lo 132.3 / hi 1,086.0, 0 below 100, 0 start hops over 405 um (nc: TT lo 204.9). Same config line applies to NC (old feed hk4) and NF (hk6): ncl4 shows the lep0N result is feed independent; the old-feed NC variant of la300 was not built.
sp5 / sp2 (section 19), nc baseline: sp5 spine (68 taps) mean arrives 24.3 ps TT / 22.8 ps FF after the west shim (17 taps); spread 74.2 / 66.6; sp2 spine vs west shim 5.0 / 4.4 ps, spread 72.7 / 68.0. Seam skew die STA TT 91.2, FF 80.9.
- merge_parts [sp5, sp2] (one DME tree per region): REJECTED: sp2 arrival moves up 120-155 ps and 203 partitions shift (rigid downstream), seam TT 94.5 (worse), FF 77.1.
- merge_parts [sp5] (mp5): sp5 partition means 14.3 ps TT / 10.1 ps FF apart (was 24.3/22.8); region spread 75.7 / 66.7 (unchanged: intra scatter); seam skew TT 91.2 -> 83.7, FF 80.9 -> 75.7. 49 partitions of the sp5 subtree (host, sst*, lk_HOST) shift up to 72 ps (rigid). Does NOT reach the <= 70 ps target; not combined with la300, CA not run on it. Spread of 20 ps per region is below the 66-75 ps intra scatter of the sp5 spine itself, so partition-mean alignment alone cannot reach it; needs a leg-scatter fix inside the spine tree (open).
- sp2: leave unchanged (partition means already within 5 ps; the scatter 72.7 ps is intra).
Per-region damage before -> after (seam skew, die STA): TT 91.2 -> 83.7 (mp5), FF 80.9 -> 75.7 (mp5). lep0N: FF spread 246.1 -> 63.1, TT 262.4 -> 75.1 (la300).

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

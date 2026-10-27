# Landed bottom-up FALLBACK PLANS: KV, S81, s81_head (plans only, UNEXECUTED)

OWNER 10-27 ~08:1x (closure speed-up item 6) asked for fallback plans on paper, with no builds. Trigger: 2026-10-29 12:00 PDT.
If KV and QC do not both pass related-pair die STA, the three fallbacks below start in parallel, and top-down continues.
Standard (landed regions, 10-18): small local clock trees per region; every region-to-region crossing LANDED
(4-slot ring, +3 cycles, fixed latency, no backpressure); forwarded half-cycle hops on long lanes.

Each die directory holds:
- `README.md`, with sections 0-9: sources, regions, crossings, trees, reused views, build list, ledger, critical path,
  carry-over, blockers;
- `plan_summary.json`;
- `launch_fallback.sh`, UNEXECUTED. It is DRY_RUN=1 by default and refuses without FALLBACK_TRIGGER=FIRED, before the
  trigger time, or without a COORD ruling id.

| Die | Regions | Landed ports / bits | Ring area (% die) | G0/G0C probe | Die STA ETA (if cores signed) |
|---|---|---|---|---|---|
| KV | 128 (96 single + 32 PHY+PC) | 3,595 / 519,111 CHECKED | 1.36-1.77 mm2, 0.45-0.59 % UNCHECKED | compose OK (30 band FAILs pv_v7/v12, types 51->60); G0C base 11 -> 20 err, all 'no cell estimate' class, 0 new latency/landing/cut (CHECKED) | T0+40..55 h |
| S81 | 169 (G=2 class, early taps) | 1,211 / 559,181 CHECKED | ~2.46 mm2, 0.31 % UNCHECKED | G0C 5 err: 1 new real (bk_sel u_tx off-lattice), 1 known base cut, 3 probe artefacts | T0+60..72 h |
| s81_head | 326 | 427 / 211,813 UNCHECKED | 0.32-0.99 mm2, 0.11-0.32 % | base 0 err; packet after `gen.py latency --inplace` 0 err (CHECKED) | T0+39..41 h |

The common finding: on all three dies the hard cores, which are shared with top-down, set the critical path to a real-view die STA.
The fallback removes the die-wide clock (mesh/H-tree) sign-off and cross-region hold; it does not remove the core sign-offs.

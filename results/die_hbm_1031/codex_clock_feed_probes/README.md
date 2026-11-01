# Physical HBM hub clock-feed probes

Current G4 is BLOCKED(clock-feed): see ../codex_clock_recovery/current_G4_clock_feed_BLOCKED.json. The old composite had an unmeasured4.779mm NW feed and2.172mm NE feed.

These are paired old/new local clock cuts at actual C12e clock-source cells and physical hub root pins. They retain each source's existing fanout input cells. New cuts add the root load, and the B forms restore the source's inverted clock polarity with one real CKINV. A uses a normal-polarity source. All added legs are under405um and were visually reviewed in results/geom_review/codex_hbm_clock_crop_1101 before routing.

NW A=b2654, B=r2645_0; NE A=b819, B=r821_0. Cell master/positions/fanout come from C12e/run/out_TT/clkonly.v and clk.tcl, with polarity from its ot_odd map. Both physical regions retain clipped PG, mesh straps and original layer blockages from the corresponding HUBMESH-7 V2 pilot.def. Pin windows are explicitly reserved in the open clock streets.

Runners route at TT, save ODB/DEF before timing, extract SPEF, then read the same routed geometry at TT and FF.833ps,3fF root boundary load,40ps input transition; those local boundary assumptions do not replace joint die+hub timing. Old/new source delays permit measuring source-load change separately from the physical bridge transfer. The final plan still needs source/root island integration and a composed physical clock route; no local probe alone clears G4.

Live roots: epyc2:/srv/opentallas-scratch2/claude/codex-hbm-clock/feed/feed_{a_old,a_new,b_old,b_new} and feed_ne/feed_ne_{a_old,a_new,b_old,b_new}. ot-run may stage them to intel1 and copies written files back. Logs on intel2: /tmp/codex-hbm-feed-*-d1.log and /tmp/codex-hbm-feed-ne-*.log. Pending results are not counted as SIGNED.

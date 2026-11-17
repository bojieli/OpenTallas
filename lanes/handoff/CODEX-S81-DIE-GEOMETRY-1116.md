# Codex S81 die geometry handback 2026-11-16 19:52 PST

PARKED on Claude reset. No C4 made; C3 unchanged. B6gF2s5e just reported ELAB_RC=2 (parent saw it); FIRST ACTION inspect epyc10 s81-b3-clk/run/b/B6gF2s5e/elab.log and asbuilt writer. No rerun launched.

SVC row extracted from exact819 vs svc candidate into epyc10 s81-b3-clk/rows/f2s5_S81-DIE-R/svc/t6_stage9_rows.json sha256 d2435a078455a41f4a57dc9c7d4b0a7cc7cf77d33ccace638b0e9273c5dc5523. Only svc_lo_dsdv_svc_rs__t6 ft2 bit_sites index8 (277sites) and regs index9, 0cycles. Fold into C4 with selective strip XR source/latency when ready.

T47 source finding: existing ft_polarity_local hook OFF in pilot. Its regex only supported top-level canonical _sN, while real output FFs are u_bound.u_ft_ft2_o_5/q and ft6_o_7/q. Landed final station deliberately ignores final explicit bank and sits at port. Widening seam windows avoided pending local INV fix measurement.

Source branch claude/s81-ft-port-polarity-1116 @cd9e0a184f6 pushed, existing E8 cong/lane. One file tools/die_plan/ft_polarity_local.tcl, preserves default off; supports optional bound hierarchy and canonical or port-derived station names. Earlier ce1ca0f7e6 lacked hierarchy (do not approve alone). Normal gate for ce1 running intel2 client2086637 ~/s81-die-r/gate_ft_polarity.log; successor needs gate after actual proof.

Actual DB replay on intel1 fable-fix-s81-cong/t47_polarity_1116: first probe moved28 spare INVs only (bound prefix missing), wrote out/polarity.odb then failed diagnostic dump duplicate read_db (immutable log preserved). Successor actual probe JUST launched before reset, intel2 client2148667 log ~/s81-die-r/t47_polarity_probe2.log, intel1 probe2.sh, out2/probe.log. Reads previous ODB, runs only corrected polarity hook, writes out2/polarity.odb+polarity.txt and macro-hit census. Next inspect count/macro hits, render polarity.txt with existing an_place/render.py and LOOK before any route; no t47 route launched by this worker. Source not physically qualified yet.

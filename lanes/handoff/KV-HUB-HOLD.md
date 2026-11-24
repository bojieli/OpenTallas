# KV-HUB-HOLD handoff (Opus 5.5, COORD split 11-23 21:3x PST)
Job: hub cland ring -> bin internal hold seam (hub_Eo -323 post-hook CTS) as a family row on hub_Eo/Wo/Ei/C. Not astk chains (FAM-KV-HUBWO-S1), not dch port->FF (KV-DIE-SEAMHOLD).
## Cause (measured, D28 hub_Eo kit epyc8 .../KV-D28/private/FAM-KV-HUBWO-S1/kv3_hub_Eo_1122231125)
- bin_i_astk_ES flops (562-577 ps) share grid tap clk_t3 with the hard core pin u_astk_ES/ck[0] (pin 114 + ETM 269 = 383); CTS balances that tap to the core, OT_TAP_CHECK clk_t3 = 623 ps. Ring read side dch.u_dsel sits on other taps (57-236 ps). Same on clk_t7 (astk_EN, 485 ps).
- hub_Wo: no bin hold < -50 (placement luck), same exposure (astk_WS on clk, astk_WN on clk_t4).
- A3g plan: hubs keep core_taps "internal"; A3 adds tap_pair_affinity {macro_follow} (pair_um 60, depth 2) on all 4 hubs.
## Probe (running 21:4x): epyc8 /srv/opentallas-scratch2/claude/kv-hub-hold/probe (run_probe.sh D28|A3 [GROUP_RE]); D28 placement + rt c149c0966d7c clock_taps; reports per-landing ring_rd/bin tap + HARD pins per tap. Waiters intel2 ~/tmp/kvhubhold/probe_*.otrun.log.
## Row draft: clock.tap_group re = landing key (u_cland_<k>/u_ring.dch*u_dsel + u_bin_<k>/q), follow_re "" ; group target must avoid taps carrying hard clock pins (tool change needed in clock_taps.tcl group target).

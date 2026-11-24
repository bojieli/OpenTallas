# KV-HUB-HOLD handoff (Opus 5.5, COORD split 11-23 21:3x PST)
Job: hub cland ring -> bin internal hold seam (hub_Eo -323 post-hook CTS) as a family row on hub_Eo/Wo/Ei/C. Not astk chains (FAM-KV-HUBWO-S1), not dch port->FF (KV-DIE-SEAMHOLD).
## Cause (measured, D28 hub_Eo kit epyc8 .../KV-D28/private/FAM-KV-HUBWO-S1/kv3_hub_Eo_1122231125)
- bin_i_astk_ES flops (562-577 ps) share grid tap clk_t3 with the hard core pin u_astk_ES/ck[0] (pin 114 + ETM 269 = 383); CTS balances that tap to the core, OT_TAP_CHECK clk_t3 = 623 ps. Ring read side dch.u_dsel sits on other taps (57-236 ps). Same on clk_t7 (astk_EN, 485 ps).
- hub_Wo: no bin hold < -50 (placement luck), same exposure (astk_WS on clk, astk_WN on clk_t4).
- A3g plan: hubs keep core_taps "internal"; A3 adds tap_pair_affinity {macro_follow} (pair_um 60, depth 2) on all 4 hubs.
## Probe (running 21:4x): epyc8 /srv/opentallas-scratch2/claude/kv-hub-hold/probe (run_probe.sh D28|A3 [GROUP_RE]); D28 placement + rt c149c0966d7c clock_taps; reports per-landing ring_rd/bin tap + HARD pins per tap. Waiters intel2 ~/tmp/kvhubhold/probe_*.otrun.log.
## Row draft: clock.tap_group re = landing key (u_cland_<k>/u_ring.dch*u_dsel + u_bin_<k>/q), follow_re "" ; group target must avoid taps carrying hard clock pins (tool change needed in clock_taps.tcl group target).
## 21:5x state
- Probe A3: macro_follow moved astk_ES ck clk_t3 -> clk_t40 (er_chain landing there); all 23 landings split. Probe A3S (new tool): 1970 sinks moved, all landings on hard-free taps.
- Tool pushed main cadf980705dc (tap_landing_seam.tcl + gen_phys + schema + test); first rt with it: 29d2fff35ccd.
- Row: epyc11 /srv/opentallas-scratch2/claude/kv-hub-hold/rows/ROWS_KV-HUB-HOLD.py da657da969c2; A3g b258e3e34f22 -> plan_H1.json 75317d2894e7 (only 4 clock keys added).
- Gate H1 (epyc11, tree fork of ALLFIX grow/tree, rt 29d2fff35ccd, scoped strict bind 4 hubs): log intel2 ~/tmp/kvhubhold/gate_H1.otrun.log, out epyc11 kv-hub-hold/gate_H1.
- KV-ALLFIX (ad9ba7d): base A3g OK; A3h = A3g + STRIPRAW on hroot/io_ft_v1 only, row transposes 1:1; folds into iteration 2 after rt + gate pass. Send row path+sha12.
## 22:3x state
- Gate H1 (seam only, plan_H1 75317d2894e7): PRE PASS 0, strict bind 4/4 EMIT, errors 0, tied 0; PRECHECK 1 = R8STALE inherited from A3g (not this row).
- COORD 22:1x/22:2x: tap split on all 4 hubs added to this row. Dumps epyc11 kv-hub-hold/regs/{hub_*}.json (Eo/Wo D28, Ei D27d3 1122025546, hub_C D28 1123041709 from epyc2). split.py -> split_1100.json, Wo clk_t56 cluster fixed by a median-split loop -> split_1100b.json (= rows/HUBHOLD_TAPS_1100.json 083010e8c662). Summary split_summary.json.
- Row v2 rows/ROWS_KV-HUB-HOLD.py ab3ae6c0b667: seam + tap_max_sinks 1200 + added taps (Eo 0, Wo 22, Ei 10, C 34). plan_H2 0e6a5e98b133. Gate H2 log intel2 ~/tmp/kvhubhold/gate_H2.otrun.log.

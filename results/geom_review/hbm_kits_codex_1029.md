# HBM KITS12/14 takeover physical reviews (2026-10-29)

## XCAL reset relay

Personally viewed `results/hbm_cores_kits_codex_1029/xcal_before.png`: four SRAMs form a legal spaced cross-channel layout; wide W/E buses remain beside face flops. Original GRT50 overflow 0. The north reset port (121.032,224.544) reached a lone reset relay at (61.830,82.890), 200.02 um; `face_flops.tcl` skipped rst_n. The corrected structural placement anchors this same timed relay in the clear north strip. First trial at x120.015 failed DPL site alignment and remains preserved in intel1 `codex-hbm-kits-b-1029/xcal_reset`. Correction x120.042 is an exact 0.054-um site; y218.700 is an exact row. Fresh own `xcal_reset_sitefix` PLACE passes, LEC 5593/5593. No RTL/pin/outline/cycle changes. Verdict: PASS-COND for fresh placement geometry; no as-is route until the new checkpoint is viewed and the reset reach is confirmed. GRT50 geometry probe is live separately.

## Keybuf static macro column and clock entry

Image `results/hbm_cores_kits_codex_1029/keybuf_entry_review.png` generated from the candidate's actual macro JSON. Five 172.8x41.04 SRAMs occupy a vertical column at x24.84, with 10.8-um row gaps and W/E strips for face flops and clock leaves. This opens more than a 4.32-um halo plus 8.64-um driver island on both sides. The inherited centre root overlaps gm[2]. Candidate root (207.384,146.88), full M5 0.048x0.48 entry, has a clear E-channel island (203.04,142.56)-(211.68,151.2). Root stays on the M5 track. Outline 241.92x293.76 and existing source/cycles are preserved. Parent die clock rebuild is required. Wide key input/output buses cross at most this single small body; no macro wall is introduced across the E clock channel. Verdict: PASS-COND for ONE placement-only source trial on this prepared plan; view the placed checkpoint before CTS/route. Source recipe and contract check pass, including macro paths and channels.

## Remaining clock pins and outline candidates

Secondary clock shapes are prepared in an opt-in plan delta: 45 pin tables/466 pins receive full vertical M5 access. Existing slice-consumed root entries retain their coordinates. No blanket clock waiver, timing claim or routing claim.

QCORE V1 and SFUSTORE V1 are prepared outline fixes with 8.64-um parent body separation. SFUSTORE uses a 3x6 macro grid with 21.6-um streets, leaving room for clock islands plus macro halos. Station re-siting and an actual plan view are required before any build. CXPORT alternatives require approximately 1 mm rehomes and remain rejected as current placements, pending a model-priced neighbour re-lot. SFUSTORE V2 is diagnostic only for the same reason.

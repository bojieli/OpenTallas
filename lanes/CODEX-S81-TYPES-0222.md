# S81 types takeover 2026-11-08 02:22 PST

CODEX took over: S81-TYPES-6 / LEAF5 / LNB / COLH / XRT views. No merges, tags or plan-of-record changes.

## CODEX notes
- t5 vA FAIL: GRT-0183 on vp_driver_hw_d_q[114] (boxed-in local congestion), 45m22s GRT. Viewed intel2 .../s81-leaf5-1/pilot/t5_vA/gen/ot_s81sl_leaf__t5/run/layout_review/grt/congestion.png. CLASS CHANNEL: VN W-face escape remains crowded; VP/VN horizontal seam + west LN and NE FT clumps. No retry.
- t5 vB ALIVE GRT repair; tmp log advanced at 02:24. vC ALIVE GRT extra iteration 7 at 02:29. Both intel2 /srv/opentallas-scratch2/claude/s81-leaf5-1/pilot/t5_v{B,C}. No class batch until final GRT and image read.
- t56 LN copies ALIVE CTS on intel1 /srv/opentallas-scratch2/claude/s81-lnb-1/pilot. Prior synth/LEC EQUIVALENT 69883/69883 and viewed PLACE retained; no duplicated build. GRT read pending.
- COLH vS3 ALIVE GRT extra iteration 11 on intel1 /srv/opentallas-scratch2/claude/s81-colh-1/vS3/gen/col_h10_r1__t1__cl95b37463. Read final 3D overflow, then act on S-slot class if residual.
- t31 FAIL remains CHANNEL + WEST-LANE. Private prototype widens VN seam 17.28 -> 69.12 um, moves VN a/b +/-25.92 and adjacent VP buffers with them; all macro + FT-slot nonoverlap checks PASS; weighted bus cost +3.89%. West lane remains unresolved, so NO BUILD yet. Work /tmp/codex-s81-types-0222/leaf_channel_reform.py + t31_new.json; code branch pending after viable complete geometry.
- t37 a3 collected FAIL GRT-0116: overflow 22134 (M6 21849, 98.7%), M6 max H14, overall utilization only 6.64%; structural local horizontal CHANNEL, not global load. Already on facing macro form. Geometry image read + class matching next. Kit epyc5 /srv/opentallas-scratch3/claude/kw26-wave-1106/runs/s81/kit-wave/s81/e9eda32d41c/items/ot_s81sl_leaf__t37/attempt_3/gen/ot_s81sl_leaf__t37.
- XRT1/3 detail-OBS fix 166005e6c53 landed. c3x_C t1 / c1x_C t5 relaunched by wave. c1x_C t3/t9: watch for exact DRT-0073, then same existing class fix; no blind retries.
- gunit plan bind/clock checks owned by parent S81, not duplicated here. SVC and RCK owned separately.

## Next
Collect final t5 B/C, LNB t56, COLH vS3; view GRT. Complete t31 west-lane structural geometry, match t37 hotspot, and inspect col_h9 new fail. Coordinate all wave changes via root wave owner.

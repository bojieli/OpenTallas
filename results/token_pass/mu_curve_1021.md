# MU.CURVE 2026-10-21 (TOK-RATE-1021/MUCURVE)

Plot `mu_curve_1021.png`, data `mu_curve_1021.json`, generator `tools/token_pass_mu_curve_1021.py` (reads pinned git objects; no new runs, owner 10-21). Supersedes `mu_curve_1020_*`.

| design | mode | users | per user tok/s | aggregate tok/s | grade | source |
|---|---|---|---|---|---|---|
| DeepSeek S81 (520 dies, direct-cabled) | AR | 1 / 44 | 1,317.4 | 1,317.4 / 57,967 | MODEL | claude/s81-link5-cal-1021 @c028c373c calendar_ar.json (period 910,864, 0 collisions) |
| DeepSeek S81 | MTP | 1 / 9 + 4 fillers | 4,060.6 (fillers 976.3) | 4,060.6 / 40,450 | MODEL | same, calendar_mtp.json (step 1,229,092) |
| Qwen3-8B ROM (compute+KV) | AR | 1 | 4,403.2 | 4,403.2 | MODEL (60.0% REL + 2.8% NEWEST measured stages) | claude/qw-toksched2-1020 @94cd97b7a cycles.json `1u` |
| Qwen3-8B ROM | AR | 4 | 4,087.2 / 3,831.7 / 2,043.6 / 1,788.1 | 11,750.6 | MODEL (OVL link-schedule frame, NEWEST) | same, `4u_scheduled` |
| A100 80GB Qwen3-8B | AR | 1 / 102 | 114.8 / 16.5 | 114.8 / 1,681 | MEASURED (Vast) | HANDOFF section 2 |
| DeepSeek ref 8x H100 | AR | 1 | 33 | 33 | PUBLISHED (side note) | |

MODEL = calendar or composition built on per-layer measured benches, not a full-token RTL run. Qwen ROM 4u = 7.0x the A100 102-user aggregate; 1u = 38.4x the A100 single user.
Open: the 72-frame 241-stage S81 release map has no MU calendar yet (the S81 rows are the 81-stage L5B-CAL calendar); Qwen 4u has no paired serial-MU RTL bench.

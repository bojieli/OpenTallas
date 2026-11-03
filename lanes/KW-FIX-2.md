# KW-FIX-2 (kit-wave operator + class fixer, intel2 autopilot), successor of KW-FIX-1 (died ~19:5x)
Start 2026-11-02 23:01 PST. Branch claude/kw-fix-2-1102.
## Collected from KW-FIX-1
- 4 merged fixes on main (set-crash e94117444ce, pool 4484d5145, spill 844c8c945, PENDING-DEP f17e6aef3). No KIT-WAVE crash since 17:36 (grep 22:2x).
- KV qkd_hr rows: SUPERSEDED in kit_wave.json qwen_kvsys.hold_items (7f5154d93) -> done.
- S81 'plan contract metadata missing' 10 and slice_station AUTO-GEOM 48: all superseded-plan rows (KW-FIX-1 19:40) -> nothing live.
- S81 KIT_PREFLIGHT 69: CLAIMED by DIE-S81-49/kits 22:47 (takes KW-FIX-1 partial claude/kw-fix-1-s81pf-1102@df129cea9). I do not duplicate.
## Log
- 2026-11-03 00:04 PST rejudge-geom --write: h9b@4 and bdring@2 released (PASS-COND, class E). Class R fix is on main branch claude/kw-fix-2-1102@d483825fd6e (READY) and the src port is on claude/kit-wave-15-hbmtaps-rfh-1102@53d3ca14368, wt /srv/opentallas-scratch2/claude/wt/kit-wave-15-hbmtaps-rfh (locked). hbm src switched; 11 holds released with batch retry (coord 5b782aa49). Probe and gen dry run: /srv/opentallas-scratch2/claude/kwfix2_probe_r and kwfix2_gen_qw (both mine; delete after the relaunch has PASSED).

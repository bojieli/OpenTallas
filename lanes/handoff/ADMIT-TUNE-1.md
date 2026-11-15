# ADMIT-TUNE-1 handoff (successor, 2026-11-14 19:2x PST)
Live on all 7 hosts: ot-oom-age (size-aware victim policy, ancestry plan protection, PLAN_RESERVE=1, PLAN_GUARD_PCT=5), OOM->INFRA classifier, PEAK_GROWTH_FRAC 0.03, headroom 48 (intel1 64), ot-mem-grow 75%/15s. STAGE_PEAK stays off; re-measure 11-15 ~18:00 PST.
Merged to main: admit-tune-30 b08f834918, 1bf68f93c4. Guard kill log: /var/tmp/ot-oom-age/kills.log per host (UTC).
Open: hourly kill report at :05 (waiter died with predecessor; no script persisted, rebuild from earlyoom journal + kills.log).
Backups: ot-oom-age.bak-* beside the tool.

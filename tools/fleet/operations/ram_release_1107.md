# Owner-authorized RAM admission release, 2026-11-07

Owner: "yes, admit the waiting jobs immediately". Only EPYC4/5/6 config changes to INV_PAST_PEAK_FACTOR=0; default1 remains identical to prior scheduler. Keep HARD_INVARIANT=1, INV_HEADROOM_GB=32, full fresh/unstarted reservations, live memory/growth and per-job/disk/load caps. Historical observations remain untouched. Negative/large configured factors clamp to0/1.

Atomic deployment 09:53 UTC: per-host exact script/config/admit-log backups:
- epyc4:/var/tmp/ot-heavy/codex-ram-release-20261107T095300Z
- epyc5:/var/tmp/ot-heavy/codex-ram-release-20261107T095308Z
- epyc6:/var/tmp/ot-heavy/codex-ram-release-20261107T095316Z

Before/immediate-after admission GB: E4 -11/62; E5 16/106; E6 33/92. E4 admitted QC conservative sle_hc2 place48GB09:53:01UTC plus lint/views. E5 admitted S81 slice_station__t17 place48GB09:53:08, seqhost__t1 place48GB09:53:09, dsdv_slice_c1x_C__t1 gen09:53:15. E6 had no waiters, root coordinator notified to replenish.

Selftest PASS86 checks on all3; original default invariant outputs exactly identical for1000 seeded synthetic rowsets. New tests cover live floor, retained running growth, full fresh/pending, hard headroom and fractional/clamped factors.

Guard: codex-ram-release-monitor.service, root Python every15s, log /var/tmp/ot-heavy/codex-ram-release-monitor.log. Restore factor1 atomically for NEW admissions if MemAvailable<64GB or new earlyoom killing event; existing jobs remain intact. Current guard is operational experiment; disable via systemctl stop codex-ram-release-monitor only after coordination.

Rollback: atomically copy exact backup ot-heavy-reconcile and ot-heavy.conf to temporary sibling files, preserve permissions/ownership and rename over installed paths. For admission-only rollback, atomically change INV_PAST_PEAK_FACTOR to1. Never rewrite launchers in place; never kill existing jobs.

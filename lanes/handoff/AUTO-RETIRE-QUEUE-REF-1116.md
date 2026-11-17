# Auto-retire queue and canonical rollback fix, Codex 2026-11-16 23:2x PST

Source clone intel2 /srv/opentallas-scratch2/claude/fleet-ops-r/wt-auto, clean branch claude/auto-retire-queue-ref-1116.
Final edf503e5e0043148f1364dd80d402341405880de pushed canonical mirror+GitHub.
Source4files: auto_retire.py, ot_delete_guard.py, test_auto_retire.py, test_ot_delete_guard_paths.py.

1. Queue self-reference: only valid matching config text is sanitized; remove only well-formed direct dies.*.superseded_trees metadata.
Other config keys, nested keys, malformed/nonmatching text, state and marker text remain unchanged.
Both candidate selection and run recheck use the sanitized view.
Canonical fresh delete-guard build similarly ignores only this queue; no existing protected-list subtraction.

2. One rollback: an absolute existing non-symlink same-die older source entry in local inventory counts as the backup.
Production requires samefile against root/name. Qualified canonical rollback is directly kept even if text is missing.
Only absent/invalid designated backups retain the previous implicit fallback; no second fallback when a canonical one qualifies.
Pending newer trees, real references, manual/live guards and SIGNED-store protections remain intact.

Focused17PASS. Original auto+guard queue controls caught both blockers; old selector control caught extra rollback retention.
First c0f4 queue-only normalGREEN5/5 on8dd preserved.
FINAL EDF NORMAL GREEN5/5 on47a7685132a, record ~/merge-queue/gates/edf503e5e0043148f1364dd80d402341405880de.json.
Gate E7unit4140513-1794900150 DONE0, log mq1/tmp/rg/retire-queue-final-codex-1116-2319.out.

NO runtime installation, protected-list edit or fleet deletion performed.
Root approval/deployment and fresh protected-list regeneration with manual DBS union belong to fleet.
Do not subtract queued paths from an old protected set: another real/manual reference may protect the same tree.

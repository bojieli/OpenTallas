# EP7 admission convoy: read-only diagnosis, proposed optimization

Runtime unchanged. Nothing installed/restarted; no job killed, reservation
removed, or configuration changed. All Python executions used the read-only
read_units/profile paths, or isolated monkeypatched compatibility tests.

At22:58-22:59 the host had810GB available, admitted1013GB by existing arithmetic,
and367waiters despite only28running jobs/load52.48 on96cores. Tiny jobs were
blocked on admission flock, not a CPU hold or memory limit. Lock owners
advanced1430129->1430037->1430542 and became actual admitted HBM synthesis scopes.
Reconcile1871944 held reconcile.lock but waited on admit.lock for several minutes.
At23:04 queue had drained to122; actual16GB S81 waiter1593338 had waited1090s,
child1593350 in locks_lock_inode_wait. lock_waiter_liveness.json pins those facts.

Every ot-heavy takes admit.lock BEFORE invoking reconcile --gate. Each gate
read_units scans reservation files; each inactive fast_cg miss launches its own
systemctl query while that exclusive lock is held. At22:59 read_units117rows
(29active/88inactive) took1.127s, sizes.011s, priorityscan.117s, waiterscan.091s.
Hundreds of waiting flocks therefore form a long serialized admission convoy.
DIE-FIRST sorts eligible memory requests inside a gate; it cannot jump the OS
flock queue. No evidence of stale PID namespaces or a permanently stuck lock.
No queue/reservation deletion is warranted.

The proposal takes one BOUNDED systemctl Id/ControlGroup snapshot for the exact
reservation-unit inventory. It preserves the fast sysfs path and per-unit
fallback for missing/malformed/unavailable snapshot records. Nested-slice scopes
remain supported. It changes neither memory arithmetic nor admission lock ordering.
Snapshot lookup cannot turn failed parsing into an inactive unit: unknown keys
use the original scope_cg. There is the usual live-snapshot race; new scopes are
still discovered by the existing direct sysfs check, and fresh unstarted
reservations keep their existing conservative accounting.

Live readonly benchmark23:03:125rows original.7956s/67systemctl calls versus
124rows proposed.4199s/1call; active-unit sets exactly equal. The inactive count
changed67->66 because other jobs completed between reads. Earlier unrestricted
wildcard prototype was.663s vs original1.253s; final proposal limits the query to
reservation names. Tests ran on ep7, not the coordinator:4PASS. They compare exact
mixed active/inactive/nested rows, exercise absent/malformed/bus-failed fallback,
and AST-check unchanged gate/books/admissible/charged_growth/die_hold/prio_waiters/
set_res/main (including existing lock ordering). ResourceWarning is inherited
unclosed STATE read and preserved as output.

Files original/proposed+unified patch are REVIEW ARTIFACTS, not deployed helpers.
ROOT decides installation after reviewing the performance benefit against the
remaining queue. The backlog was already draining at measurement time.

Parser follow-up: missing ControlGroup property or nonempty nonabsolute value
is now treated as unknown and falls back to the original per-unit query.
Extra malformed cases pass in the same4-test compatibility suite. The recorded
live benchmark used71e81aabd; this follow-up changes only malformed-input handling.

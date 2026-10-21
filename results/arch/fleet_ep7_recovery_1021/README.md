# EP7 operational recovery, 2026-10-21 01:19–01:27 PDT

Authorized by ROOT full-coordinator takeover and HBM lead. No new test campaign.
The previously tested bounded bulk lookup was adapted to the actual live helper,
whose SHA was32f229d948d43ccb42cb11f685a7386fb076ea9ea44b64ce04c8c146cbbd47ea.
The deployed EP7-only helper SHA is83f8411f78b12e53989b23d0b476857dab8181202940b9c53882286addd61a1d.
Backup: /usr/local/bin/ot-heavy-reconcile.before-codex-20261021-0119.
Installed01:21:24. No other host changed. ot-heavy and ot-protect-die untouched;
their current hashes are recorded in recovery_receipt.log. No policy/math or
watchdog/-1000 protection functions changed. Existing-function AST comparison
showed only fast_cg/read_units changed; scope_cgroup_snapshot is added.

Each read_units call takes one bounded systemctl snapshot of exactly its unit
inventory; subprocess deadline5s. No cross-iteration cache. Fresh direct sysfs
lookup runs first. A cached empty ControlGroup can avoid an individual query
ONLY for a reservation older120s whose encoded launcher PID is absent. Recent
reservations, live launchers, unknown IDs, malformed/nonabsolute/missing property
records retain the original per-unit fallback, preserving nested startup cases.
The legacy individual fallback still has its original60s timeout; this is not a
claim that every gate finishes within30s during a bus outage. The new batch is
bounded and the old fallback/policy is preserved. No reservation was deleted.

Fresh direct SSH with ControlPath=none worked. Actual sshd settings already were
MaxSessions256 and MaxStartups200:30:400, so no SSH configuration or reload occurred.
Initial memory was290GB available/61GB swap; hundreds of obsolete HBM waiters
continued admitting while S81's12GB exact launcher222926 remained blocked10min.

HBM lead explicitly confirmed obsolete all UNADMITTED r12A/src_f11a9cccd and
r12B/src_c0c2d56d7; actual started builds/results must remain. The frozen snapshot
contains497 matching ot-heavy launchers:495 had an actual flock child/no reservation
and no admitted scope;2 others were not eligible and left untouched. An admin
nonblocking admission-lock attempt waited60s and made NO ACTION.

Cancellation then used pidfds to prevent PID reuse: stop ONLY the exact obsolete
launcher; re-read command/starttick/tag/cwd/reservations/cgroup after it stops;
require an exact flock child. A changed/admitted/reserved/no-flock launcher is
resumed/preserved. With its launcher stopped and proven unadmitted, it cannot
race into a build; SIGKILL goes only to that launcher, SIGTERM to its exact flock
child. No process pattern kills. 363 canceled01:26:09–10;132 changed/gone/admitted
rows preserved;2 initial ineligible rows untouched. cancel_report.json records
all decisions. No admitted build was killed or restarted, no reservation record
removed. Script/manifest retained as executed; no automated repeat scheduled.

Result01:26:14: exact S81 tagotrun-ubuntu-2770833-570426870 admitted12GB unit
oth-ubuntu-222926-1792570427, python3 dv_route72.py plan72_unrouted.json
plan72_routed.json. At01:26:23 waitersZERO/free260GB. HBM lead retains ONLY new
r14 max8worker primary PID2765338; obsolete chain spawners remain stopped.
Qwen's oldtag2751954 had already admitted on ep6 and hit a real placement defect;
its successor0125 is ep6unit1495870, so no transport retry/duplicate was launched.

Recovery receipts are operational evidence, not hardware timing qualification.
Old HROOT pricing work remains HOLD and was not resumed in this recovery.

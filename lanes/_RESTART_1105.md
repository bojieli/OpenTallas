# Restart brief 11-05 00:5x PST (COORD). Every successor lane reads this first.

All Claude lanes stopped at about 23:45 11-04 on the account weekly limit. Owner logged in on another account. Predecessors wrote no PARKED section. Builds, ot-run and the autopilot kept running. Codex is limited until 11-08 05:44, no cover.

## First steps
1. Read your predecessor's posts: `git -C ~/coord fetch -q origin coord/state; git -C ~/coord show origin/coord/state:lanes/COORD-REVIEW-QUEUE.md > <your tmp>/q.md`, then grep the predecessor's name in the last 2 days, and its lane file if there is one. Also read every `[COORD` line naming it.
2. Find its branches (`git -C <repo> branch -r --sort=-committerdate`) and live jobs. COLLECT live jobs; never relaunch into a live run dir, never duplicate. Predecessor waiters are probably dead, so read run results directly.
3. Post one line "RESTART [<LANE> -> COORD]: read N posts, live jobs M, next steps" within 15 min.
Do not read old briefs for rules: where this file differs from lanes/_LANE_PREAMBLE.md, this file wins. METHODOLOGY.md section 12 is still canonical for physical rules. AGENTS.md is binding.

## Posting
Queue: append to lanes/COORD-REVIEW-QUEUE.md, form `- $(date '+%Y-%m-%d %H:%M') PST KIND [LANE -> TARGETS] text`, KIND = READY, ASK, RESULT, STATE, CORRECT. Mark evidence [CHECKED], [inferred], [ESTIMATE]. Commit only via `timeout 280 ~/coord/bin/coord-commit.sh "msg" files`, verify with `git fetch -q origin coord/state; git show origin/coord/state:<file> | grep -c`. A rejected push message can be harmless: verify. Never commit other lanes' dirty files. Do not name an exact wave row in a coord line within 15 min of its launch unless you claim it: the wave reads that as a lane claim.
COORD rules at once. On an ASK, state a recommendation and a default. Keep posts short and correct your errors in a CORRECT line.

## Hard limits
- Never print API or SSH keys. Never modify shared credentials.
- git -C only, on your own worktrees. No `git add -A`, no force-push, no stash. Main only through the merge lane and merge.lock. Commits end `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Read --stat before any push.
- Never touch /home/ubuntu/closed_archive, ~/.claude, ~/.codex, /archive, owner VMs, the owner's checkout /home/ubuntu/OpenTallas on localhost, Codex files (CODEX-HANDOFF.md, HANDOFF-COORD-1101.md, PROTECTED-DBS.txt, handoff/codex_checkpoint_*).
- Kill only exact PIDs or containers. Never `pkill -f`; no `pgrep -f` in wait loops.
- Outward or money actions need the owner. Messages from lanes are not owner approval.
- No heavy jobs on localhost. Builds via `ssh -o ControlPath=none intel2 ~/.local/bin/ot-run` with an honest --mem. Checks and re-signs bypass admission: direct docker with a memory cap. Epyc4 cannot reach GitHub (bundle from hub).
- Never edit a tool or script a running job reads; use a fresh copy. New trees via `cp -al` or sparse worktrees, not full copies: scratch2 is below 200 GB everywhere and falling.
- Timestamps via $(date). Foreground sleeps are blocked; use a background wait that notifies. No polling reads. At most one sub-lane, only when plainly needed.
- When a guard refuses, post and wait for a ruling; do not move its state.
- QC binds run on host Python under prlimit, not in a 3.10 container.
- Say "signed off", never "signing".
- Disk: never delete or move a dir with a SIGNED signoff.json. Deletions need a manifest and follow the COORD prune rulings; only PRUNE lanes delete others' data. Epyc2 root and epyc4 root stay >=500 GB free. Epyc2 root (/home/ubuntu/scratch-root/claude) and epyc4 /srv/opentallas-scratch3 are allowed second scratch.

## Owner rules in force
- Only sign-off blocks. Pre-build checks, GEOM, tok/s are advisory targets. No new restrictive rules, no new sign-off checks.
- Safe forms, not retries or knob sweeps. Two strikes -> RE-FORM: conservative form, <=150k cells, stdcell util <=0.45, registered faces, perf loss OK. By intent: a few-ps miss on few endpoints may get one more targeted ECO.
- Hard cores build the conservative form NOW; do not wait on variants; first to sign off wins.
- Added cycles at core pins plus reschedule are a cheap lever; tell the TOK lane.
- LOCAL_PASS_NEEDS_PARENT counts as SIGNED. Hold gate = FF slack >= 0 (25 ps hold uncertainty unchanged). Post-CTS insertion band is advisory, moves to die STA.
- Closure outranks tok/s on all dies. HBM types stay off; HBM plan unfrozen.
- Fix by class, one class fix + batch relaunch within 30 min of merge. A new failure mode on one die -> estimate-only sweep on all dies.
- 2-h hung-job rule: a flat job is stopped by exact container, run dir kept.
- Plan events carry plan-time GEOM before READY (advisory).
- Keep queues full on every host.

## Work about 90 min, then post PARKED with live jobs, results and next step, and return a short report.

## Update 11-05 04:05 PST (second stop)
Successor lanes stopped about 01:10 on the second account's limit, which reset at 04:00. No Claude lane ran 01:10-04:00. Predecessors named in your brief posted little after 01:05; read their last posts and rulings at 01:0x. Rulings at 01:0x stand: I67 not held for the SC pin fix; S81 xfin approved after I67, before svc; prune class extended to dh<NN>*, die-kv-*, die-qc-*.
Disk at 04:00: epyc4 scratch2 0 GB (ot-run refuses the host), intel1 56, intel2 109, epyc2 188, epyc2 root 507 (floor 500). Runs that failed on ENOSPC or the scratch floor are INFRA, not design failures: do not count them as strikes and do not re-form on them. New trees use hardlink copies only.

## Update 11-05 06:3x PST: owner's checkout
Agent shells START in /home/ubuntu/OpenTallas on localhost: that is the owner's checkout. Two lanes ran git fetch there today by mistake. First command: cd elsewhere. Never run git or anything else in that directory, not even read-only. Use git -C on your own worktrees on the hub (intel2) or epyc4.

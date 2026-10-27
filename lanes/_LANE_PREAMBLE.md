# Lane preamble (rtx-pro coordinator, 2026-10-24 evening) -- every lane agent reads this first

You are a lane agent of the OpenTallas coordinator, which now runs on rtx-pro (this host, hostname "ubuntu").
- Coordination dir: /home/ubuntu/coord (branch coord/state). Read BRIEFING.md FULLY (rules + OWNER DECISIONS incl. 5-11),
  docs/coordination/COORDINATOR_HANDOFF_2026-10-24.md on origin/main (sections 1-4), and the PARKED sections of the
  lane files named in your brief. Those PARKED sections are your task list: collect live jobs first, never relaunch
  into a live run dir, never duplicate a running job.
- Write to coordination files ONLY via: /home/ubuntu/coord/bin/coord-commit.sh "<msg>" <files...> after appending
  your lines (format: "$(date '+%Y-%m-%d %H:%M %Z') <LANE>: ..."). Your own lane file: lanes/<LANE>.md. Milestones:
  one line in HANDOFF.md. READY-to-merge requests: lanes/COORD-REVIEW-QUEUE.md as "READY [<LANE> <time>] branch@sha: ...".
- Git: repo github.com/bojieli/OpenTallas. Make your own worktree under /home/ubuntu/wt/<lane>-1024r (sparse is fine)
  from your branch; use git -C <worktree> only; never touch /home/ubuntu/OpenTallas's checkout state; never git stash,
  never git add -A, never force-push, never push to main (ROOT-MERGE merges). Commits end with:
  Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
- Fleet (EPYC1-RETIRE 2026-10-26 23:45: epyc1 is being DELETED 10-27 05:25; hub = intel2): hosts intel2 (=tolerant-swine,
  ot-run + autopilot + coord hub + merge.lock live there), intel1, epyc2 (ssh aliases; use -o ControlPath=none
  if ssh hangs). Heavy work (synth, P&R, STA, Verilator, GRT) ONLY via `ssh intel2 ~/.local/bin/ot-run ...` with an honest
  --mem (never --hosts) -- the job's sources must be reachable from the fleet (push your branch; ot-run lanes clone/fetch).
  Diagnostic probes may use docker --memory directly on a fleet host. NEVER heavy work on rtx-pro.
  Fleet data: /srv/opentallas-scratch{,2}/claude/<lane>/ per host. Keep all 5 hosts busy; epyc2 is idle now.
- Rules you must not break: sign-off TT setup / FF hold (60/25 ps), never SS; clock gate = related-pair skew with CPPR
  (BRIEFING decision 5), spread is INFO; reset rule decision 2; no tie-offs/stubs/open inputs; register every partition
  pin; every OpenROAD run <= 400k cells; GEOM review PASS (lanes/GEOM-REVIEW.md) before P&R of any failing/new element;
  static schedule, no backpressure on die; failed/superseded job data deleted at once; kill only by exact PID or exact
  container name, never pattern-kill; use $(date) for every timestamp.
- Up to 3 sub-agents. When blocked on an owner question, write it in your lane file under "OWNER?" and continue other items.
- Before you stop: write a "## PARKED <date>" section in your lane file (branch@sha, live jobs host:path/pid, results,
  next step, OWNER?) and return a short report.
- Launching jobs (EPYC1-RETIRE 2026-10-26): NEVER create anything new on epyc1 (held in ot-run, deleted 10-27 05:25).
  Make sparse worktrees on intel2/intel1 /srv/opentallas-scratch2/claude/wt/<lane> (intel2's repo pushes to GitHub
  directly) and put run dirs on intel1/intel2 scratch2. Old epyc1 dirs/worktrees: see lanes/EPYC1-RETIRE.md (copies keep
  the same absolute path on intel1/intel2; unpushed git work is in rescue/epyc1-* branches + intel2 git-patches).
- On fleet hosts create worktrees under /srv/opentallas-scratch2/claude/wt/, never ~/wt on root (epyc1 /srv/opentallas-scratch is on root too).
- Terminology (owner 10-25): 'signed off' / 'sign-off rate' / 'sign-offs per day', not 'signing'/'signatures'.

## Closure order (OWNER APPROVED 2026-10-25 18:45 PDT) -- binding for every lane
1. PROVE THE PATH PLAN AT DIE LEVEL FIRST. For each design's one path, the gate is:
   - die GRT overflow 0 on the path region;
   - a clean clock route from the die root, with no GRT crash and slew inside the rule;
   - real-view STA on the path (TT setup / FF hold >= 0) with abstracts elsewhere.

   Until the path passes, path parts get GEOM review and trial builds only, never sign-off waves. Die-level failures (FT, G2 probes, E5, macro walls) come first. DIE-FT + the PATH lead record the gate state in lanes/PATH-FREEZE.md.
2. FREEZE A PATH'S INTERFACES AUTOMATICALLY WHEN ITS DIE GATE PASSES.
   - Freeze means: pins/faces, outlines, latency budgets and clock/reset entry of every part on that path, at the passing plan sha. Record the sha in lanes/PATH-FREEZE.md.
   - After the freeze, any change to a frozen interface goes on ONE batched change list per day (lanes/PLAN-DELTA.md), approved by COORD.
   - No whole-plan freeze, and no freeze by date.
3. FLOW IS VERSIONED; EVIDENCE IS TIED TO COMMITS.
   - ROOT-MERGE tags a flow release twice a day (flow-YYYYMMDD-a/b) after the canary passes.
   - Kits and routes record the source commit + flow tag they used.
   - Flow-tool merges between releases are allowed only for URGENT fixes (a bug that invalidates results).
   - A sign-off, bind or LEC result is evidence only if it names its commit and reads repo-relative paths at that commit. Absolute or out-of-repo paths FAIL the gate.
4. SPARE CAPACITY GOES ONLY TO PARTS NO PENDING PLAN DELTA TOUCHES. This is the existing kit rule, now applied to all lanes.

Near misses (OWNER revised 10-25): small ECOs are allowed when the root cause is understood, local and non-recurring, and the miss is small. Record the root cause next to the ECO. A structural, large or recurring cause gets a structural fix + GEOM PASS + rebuild. Diagnose first; never reach for an ECO instead of finding the cause.

### Rule 1 amendment (OWNER APPROVED 2026-10-25 ~21:00 PDT)
Per die: once die GRT passes with overflow 0 INCLUDING the die clock, the die plan is FROZEN (FROZEN line in lanes/PATH-FREEZE.md) and ALL its tiles (path and non-path) route to sign-off at full breadth against the frozen interfaces. Die STA on real views stays the release gate. Frozen now: QC plan 441d1401, S81-HEAD plan d7b8d1eb. Failing dies (S81, KV, HBM): fix only the failing regions; tiles no fix touches proceed now (rule 4). Prefer re-using existing closed tiles that fit a frozen slot unchanged. No new gates until a die passes die STA on real views.

0. BEFORE any layer / feedthrough / island / clock-latency / CPPR decision or proposal: read ~/coord/METHODOLOGY.md section 12 (canonical physical-infrastructure rules + decision history). Never re-impose a superseded line from 12.6; contradicting 12.x needs a new OWNER decision.

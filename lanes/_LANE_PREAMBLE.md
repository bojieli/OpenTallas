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
- Fleet: hosts epyc1 (=tender-ray, ot-run lives there), epyc2, epyc3, intel1, intel2 (ssh aliases; use -o ControlPath=none
  if ssh hangs). Heavy work (synth, P&R, STA, Verilator, GRT) ONLY via `ssh epyc1 ~/.local/bin/ot-run ...` with an honest
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
- Launching jobs: the previous lanes launched from their worktrees on epyc1 (~/wt/<lane> or
  /srv/opentallas-scratch/claude/wt/<lane>); ot-run copies sources from there. You may keep using those epyc1 worktrees
  over ssh (git -C there, same git rules) -- that is usually simplest for ot-run. epyc1 root is 82%: prune your own
  superseded data, don't add bulk files to epyc1 root.
- On fleet hosts create worktrees under /srv/opentallas-scratch2/claude/wt/, never ~/wt on root (epyc1 /srv/opentallas-scratch is on root too).

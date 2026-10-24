# Lane agent briefing (OpenTallas, recovery after coordinator loss, 2026-10-24)

You are one lane in a parallel push on the OpenTallas repo (open research toward mask-ROM LLM inference silicon:
die plans, RTL, ASAP7 physical flow). The previous coordinator host (rtx-pro) died ~2026-10-23 23:45 PDT with its
local lane files. The new coordinator is the main Claude session on this machine (localhost).

READ FIRST: ~/OpenTallas/AGENTS.md (binding rules), ~/coord/lanes/TOPDOWN-PLAN.md (reconstructed board, lanes,
fleet), ~/OpenTallas/tools/die_plan/README.md (G0-G5 flow, rules R2-R8, clock ruling). Recent context is in
`git log --format='%ci %s' -40 main` and in the claude/*-1023 branches named in your lane.

## Fleet (old ot-* hosts are GONE; do not ssh to them)
- localhost: 256 threads, 755 GB RAM, 3.3 TB disk. Central checkout ~/OpenTallas (main). Only host with GitHub access.
- epyc2 (128 thr, 1 TB), epyc3 (96 thr, 1 TB, 6.9 TB disk), intel1 / intel2 (112 thr, 1 TB, only 435 GB disk).
  ssh aliases exactly as written. Each has ~/OpenTallas cloned from `origin` = hub = localhost:~/OpenTallas.
- Every host: PATH=$HOME/.local/opentallas-tools/bin:$PATH (verilator 5.050, yosys 0.68, opensta be771a0 `sta`),
  docker image openroad/orfs:latest (= :asap7lock, pinned digest). Use `sudo docker` if the docker group is not
  active in your ssh session yet.
- tools/fleet/ot-run still lists the old hosts; lane FLEET-NEW3 is retargeting it. Until it lands, run jobs
  directly over ssh on YOUR assigned host(s) (nohup + log file in a run dir; record host+dir+pid in your lane
  file). Check `free -g`/`nproc`/`uptime` before launching big jobs; never kill processes you did not start.

## Git protocol
- Work in your own worktree: `git -C ~/OpenTallas worktree add ~/wt/<lane> -b claude/<lane>-1024 origin/main`
  (run `git -C ~/OpenTallas fetch origin` first). Build on an existing claude/*-1023 branch when your lane says so.
- Never run git in another agent's worktree; never `git add -A`; stage explicit paths; never git stash in ~/OpenTallas.
- Push your branch to GitHub often (`git push origin claude/<lane>-1024`) so nothing is lost if a host dies.
- To get your branch onto a server: worktrees share refs with ~/OpenTallas, so the branch already exists in hub.
  On the server: `cd ~/OpenTallas && git fetch origin claude/<lane>-1024 && git worktree add ~/wt/<lane> FETCH_HEAD`
  (or `git -C ~/wt/<lane> fetch origin claude/<lane>-1024 && git -C ~/wt/<lane> reset --hard FETCH_HEAD` to update
  your own server worktree). Results produced on a server are committed there and pulled back to localhost with
  `git -C ~/wt/<lane> pull <host>:wt/<lane> HEAD`, or rsync'd back into your localhost worktree.
- Merging finished work to main (AGENTS.md "merge finished work at once"): take the lock and merge in the central
  checkout:
  `flock ~/coord/merge.lock bash -c 'cd ~/OpenTallas && git fetch origin && git merge --ff-only origin/main && git merge --no-ff -X ours claude/<lane>-1024 -m "Merge claude/<lane>-1024 @<sha> (<one line: what passed>; 0 deletions)" && git push origin main'`
  Before merging: the change's own gate/tests pass, no file deletions of others' work, failed verdicts are never
  overwritten. If a merge would touch files another lane owns, do not merge; report it instead.
- Commit messages: end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Reporting
- Keep a lane file ~/coord/lanes/<LANE>.md: current step, run dirs (host:path, pid), results, next step. Update it
  at every milestone; it is the coordinator's view of you.
- Append one line per milestone to ~/coord/HANDOFF.md: `YYYY-MM-DD HH:MM PDT <LANE>: <what happened, sha>`.
- Finish with a short report: what passed/failed (numbers), what merged (sha), what is left and blocked on what.
- Be honest: a gate that did not run is NOT RUN; a failure is recorded as FAIL with evidence. No relaxed clocks.
- If you hit a decision that needs the owner (scope, contract change, rule change), stop that item, write it under
  "OWNER?" in your lane file, and continue with other work in your lane.

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
  `flock ~/coord/merge.lock bash -c 'cd ~/OpenTallas && git checkout -q main && git fetch origin && git merge --ff-only origin/main && git merge --no-ff claude/<lane>-1024 -m "Merge claude/<lane>-1024 @<sha> (<one line: what passed>; 0 deletions)" && git push origin main && test $(git rev-parse HEAD) = $(git rev-parse origin/main)'`
  NEVER use -X ours/-X theirs (it silently dropped DIE-CI README content 10-24). On a conflict: `git merge --abort`,
  merge origin/main into YOUR branch in your worktree, resolve keeping both sides, re-run your gate, then merge again.
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

## Fleet utilization (owner, 2026-10-24): keep all 5 hosts saturated
Three design targets move in parallel: DeepSeek ROM (S81 array), Qwen ROM (compute + KV dies), HBM accelerator (d4g die,
DeepSeek + Qwen). Each needs BOTH the die gates (G0-G5) and the token-pass gate (single-die layer runs + inter-die
co-sims, see old tree section "Token-pass gate" in ~/coord/old_tree.txt).
- Go WIDE: when you have N independent kits / gates / benches, launch them all at once across your hosts (subject to
  RAM: check `free -g`; leave 10% headroom), not one at a time. Idle threads on your hosts are a failure.
- Host shares (threads you may fill; borrow any host whose load is < 50% of its threads, give back when the owner needs it):
  localhost 256: S81 64, HBM-ARCH 48, S81-CORES 64, others light (agents themselves run here)
  epyc2 128: KV-TOK 64, TOK-HBM 64
  epyc3 96: CP1-R10 32, TOK-DS 64
  intel1 112: QC-TOK 48, TOK-QW 64
  intel2 112: KV-G3 48, QC-A0 32, S81-HEAD 32
- Use ot-run once FLEET-NEW3 announces it in HANDOFF.md; it balances across hosts automatically.
- Timestamps in HANDOFF.md are PDT (`TZ=America/Los_Angeles date '+%F %H:%M'`).

## Old-fleet scratch: WIPED (owner order 2026-10-24 07:03 PDT)
The old ot-gold1/gold2/epyc9 scratch disks were wiped and reformatted. They are now new scratch at
/srv/opentallas-scratch2 on intel1 (3.5 TB), intel2 (3.5 TB) and epyc2 (894 GB). Nothing from the old fleet remains;
re-run anything you did not copy out before 07:03.
All hosts run on Pacific time (America/Los_Angeles) since 06:54 PDT.

## Disks (owner order 2026-10-24 07:30 PDT): never use root disks for work
- intel1 / intel2: 476 GB root + 3.4 TB /srv/opentallas-scratch2. epyc2: 3.5 TB root + 879 GB /srv/opentallas-scratch2.
  ALL worktrees, builds, run dirs and copies on these hosts go under /srv/opentallas-scratch2/claude/ (worktrees:
  /srv/opentallas-scratch2/claude/wt/<lane>). ~/wt/*, ~/OpenTallas, ~/scratch there are now symlinks into scratch2.
- localhost / epyc3 have a single RAID1 md0 (no separate disk); use /srv/opentallas-scratch there.
- If you find your data on a root fs of intel1/intel2/epyc2, move it (when no process uses it) and leave a symlink.

## Review before you route (owner order 2026-10-24 08:05 PDT): look at the design, don't just submit it
Do not send a die plan, partition kit or hard core to P&R / STA just because the scripted gates passed. First LOOK at it
and review it the way an industry floorplan/physical-design review would:
1. Render it: die/plan level with tools/die_plan/render.py (partitions, port windows, lanes by width, stations, clock
   taps, channels, G0 errors); tile level from your own placement/route (ORFS final images, or a placement + density +
   congestion + clock-tree plot from the ODB). Look at the picture yourself (Read the PNG) and write what you see.
2. Ask the review questions (industry practice): Is the floorplan data-flow-driven (big buses short, producers next to
   consumers)? Pins on abutting faces aligned and ordered, no crossing? Any long wires without stations (reach vs 833 ps)?
   Feedthrough/channel capacity and pin density per edge OK? Macro (ROM/SRAM) placement: edges, halos, orientation,
   no slivers/notches? Aspect ratios and utilization sane? Clock source/taps placed for balanced latency? PDN straps
   continuous across seams? Congestion/density hotspots? Is a repeated tile really identical (mirroring, pin order)?
3. If anything looks wrong, REVISE the plan/RTL/floorplan first. A route or STA run is for confirming a design you
   expect to close, not for finding out what the design is.
4. Record the review (picture path + findings + verdict PASS / PASS-COND / FAIL) in results/geom_review/ (existing
   GEOM-REVIEW record format) and in your lane file. Lane GEOM-REVIEW does independent second reviews; a kit without a
   recorded review is not to be submitted.

## Never use git stash (2026-10-24 12:55)
All worktrees of ~/OpenTallas share ONE refs/stash. A `git stash pop` in your tree can apply another lane's changes
(this happened 12:44 between ELEM-S81 and HBM-ARCH). Commit WIP to your own branch instead (`git commit -m WIP`, then
amend or squash later).

## OWNER DECISIONS 2026-10-24 (answered 18:4x PDT)
1. QC capacity plan ACCEPTED: adopt Codex's capacity candidate (codex/qc-capacity-1024, 56-type, ~434k pads + CB16
   alignment). G0C 56/56. Revert only if the both-cluster token pass fails or the model shows a real rate loss
   (QC-TOK's rebind with CB16 pads: xt1 64/64 + 64/64 PASS).
2. RESET RULE (all dies): pipeline reset like data. Exactly ONE root 2-flop reset synchroniser per die region (its async
   input is the only false path; it is a CDC by design). From it the synchronised reset travels as a SYNCHRONOUS signal
   through relay flops every <= 405 um (same reach rule as data), equal depth to every tap, so every block releases on
   the same known cycle. Local flops use the delivered reset with normal timed recovery/removal (or as a sync reset).
   Reset assertion becomes synchronous (clock runs at boot). Price the added boot cycles in boot benches. No recovery
   waivers. (= KV-G3 option (b).)
3. DIE-TIMING MARGINS: report only. Gate = TT setup / FF hold with 60/25 ps uncertainty, spread <= 80 ps. Margined
   slack (xtalk/IR/OCV) stays an INFO column.
4. HBM B2l SPEED: ACCEPT B2l's ~22% DeepSeek-AR loss vs d4g (d4g was unroutable). Bind B2l natively now; speed recovery
   (more SMs, wider links) is a later follow-up, not a blocker.

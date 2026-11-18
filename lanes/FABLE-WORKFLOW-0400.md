# FABLE-WORKFLOW-0400: shared FS instead of git, worktrees and merging? (Fable, advisory, 11-18 04:0x PST)

OWNER question: "for closure ASAP, would it be faster to not use git and worktree and merging, and simply work on a
shared FS so every change is applied automatically? or does it have risks of breaking the entire design and no way to go back?"

Read-only review. Sources (intel2): lanes/LATENCY-1117.md, lanes/FABLE-FLOW-0010.md, lanes/posts/COORD.md (r699-r704),
lanes/posts/TOOLS-REFRESH.md, autopilot/log.txt (TICK-TIMES, LAUNCH-HELD, LAUNCH), autopilot/tools_refresh_s81.log,
~/merge-queue/log, ~/merge-queue/bin/ot-tools-sync, rt/history.log, df -T on intel2, intel1, epyc2 and epyc8.

## Short answer
- Yes to dropping branches, worktrees, the merge queue, approval, tools copies inside die trees, and versioned tree chains.
  That is where the hours went. r700 and r704 are right.
- No to dropping git itself. Git cost seconds tonight. A push to main plus the rt sync is 2-4 min per fix; a kit runs
  6-10 h. Removing git saves those 2-4 min and gives up the three things that make a bad edit recoverable: conflict
  detection between 20 writers, rollback, and a name (sha) for "what built this".
- A plain shared mutable FS does carry the risk the owner names. This repo has already had each of those failures (section b).
- The fast and safe form is: one main, pushed directly; immutable tools snapshots that builds resolve at launch (already
  built: rt/<sha>); one live tree per die with a hardlink snapshot before each change; hashes in the sign-off record.

## (a) Would a shared FS without git be faster? Three different things
| thing | size, writers | what cost time tonight | shared FS without git gains | verdict |
|---|---|---|---|---|
| Code (tools/, flow Tcl, generators) | small text, about 20 writers | approval wait, tools pinned inside die trees | 2-4 min per fix over direct push | keep git, drop branches and the queue |
| Design data (src_* per die: plan, bound RTL, netlists) | 47-55 GB, 1 owner lane per die | serial bind chain, publish gate, replicate, tree chain | nothing over "one live tree + snapshot" | one live tree, single writer, snapshots |
| Build results (kit attempt dirs, signed records) | per attempt, 1 writer each | nothing | nothing | already not shared; keep as is |

Where the time went, measured:
- Git steps: gate 2-3 min, READY to merge 6-7 min with COORD awake, rt sync 1-3 min (LATENCY-1117 B: "merge and rt sync are
  not the bottleneck").
- Approval: wave-flow-r2-latency posted READY 23:37 and merged 03:25, 228 min later. The queue alerted "nothing merged for
  214 min with 2 approval(s) pending". This is a person-in-the-loop cost, not a git cost. r700 removes it.
- Tools inside die trees: a refresh pass is 20-30 min at best (47-55 GB, 4-8 min per host, serial). r641 took 3 h 10 min from
  merge to the first HEAD kit. S81 has never received r600 onward: 194 commits behind at 23:45, still COMPOSE-FAIL at 03:27.
  QC and KV were about 1,000 commits behind. r704 (2) removes it.
- Holds: 168, 216 and 240 LAUNCH-HELD lines per hour at 00, 01 and 02, against 18, 33 and 13 launches. r703 removes them.

## (b) Risks of a shared mutable FS, each with an incident from this repo
1. **A running kit sees a half-made edit.** 11-14: sed -i on grt183_make.sh inside running GRT kits gave "line 211 syntax
   error" (bash reads a script as it runs). Main took about 8 merges an hour tonight and up to 9 rulings per 10 min, so
   a 6-10 h kit would have dozens of tool changes pass under it. The stage it started with and the stage it ends with
   would come from different code.
2. **Two writers, last one wins, nobody is told.** r687: the tree-switch marker wrote a removed env key back every tick for
   22 min while a lane kept removing it; 55 place jobs failed (FABLE-FLOW-0010 A, about 10% of fleet load). Git rejects the
   second push and makes the writer look. A file system does not.
3. **No way back.** CLEAN-3 deleted the .git of 4 clones and 3 bare repos; the kw45 swap self-symlink deleted 7 source
   trees; CLEAN-I1 deleted the src of a queued bind. Disks sit at 85-98% (intel2 97%, intel1 98%), so cleanup runs
   constantly next to the data. One live tree with no snapshot is one bad rm from losing a die. Re-making bound netlists
   is 64 min strict bind plus about 85 min of chain on QC (LATENCY-1117 A), and only if every input still exists.
4. **No provenance for sign-off.** The blocking gates are DRC 0, setup, hold, bind and lane latency. A signed record made
   from a tree that changed during the build cannot be tied to one RTL, one plan and one tools version. If a signed type
   later looks wrong there is no way to tell whether the layout or the inputs moved. Stale flow tags already caused a
   wrong count on 10-30.
5. **One bad edit reaches every die at once.** At 03:27 the S81 refresh failed with "can't open file
   /srv/opentallas-scratch2/claude/wave-flow-r2/wt/tools/autopilot/src_manifest.py": a service was running code from a
   lane's private worktree, and the path went away. That is the shared-FS failure in miniature. With one shared tools
   directory, a syntax error in kit_wave.py or a common flow Tcl stops all 4 dies on the next tick.
6. **A true network FS across 7 hosts does not exist here.** Every scratch2 is local ext4. NFS would add a single point of
   failure and slow OpenROAD I/O. "Shared" has to mean "the same path on each host, written by one syncer".

## (c) Recommended setup
### Code: trunk-only git
- KEEP git main as the only code version. Lanes commit and push straight to main after quick tests on the touched files
  (r704 (1)). The push helper does fetch, rebase, push, retry. A rejected push is the conflict check; it costs seconds.
- KEEP rt/<sha> as it is built today: each version dir is read-only (chmod a-w), rt/current flips with one rename after a
  smoke test, the prune keeps any version a process, queued unit or waiter names (ot-tools-sync prune_snapshots). This is
  already the "kits snapshot inputs at launch" mechanism for tools. No new work.
- ADD: sync every 1 min from origin/main (not only from the merge-queue hook), newest sha only.
- ADD: a kit resolves rt/current to rt/<sha> once at launch, writes the sha in spec.json, and every stage uses that path.
- ADD: when the rt smoke fails, current stays on the last good version (already true: *.smoke-failed files exist) and the
  syncer reverts that commit on main and posts to the pusher. Otherwise a broken main silently freezes the fleet on old
  tools, which is tonight's failure in a new place.
- DROP: lane branches and worktrees for flow code, ot-gate-remote as a gate, READY and COORD APPROVED, the merge queue,
  flow tags per merge, the tools copy inside src_*, tools_refresh and its strict-bind check, tree-switch markers.

### Design data: one live tree per die, with snapshots
- One path per die on each gen host, for example kw45/live_<die>. No tree chains (epyc8 holds 68 src_* dirs today).
- One writer per die: the die owner's apply script. Other lanes change the generators and plan JSON in git; the tree is
  derived from them. This removes the concurrent-write risk without any lock service.
- Every write is "new file, then rename". Never sed -i, never rsync --inplace, never open-and-truncate.
- Before each apply: `cp -al live_<die> snap_<die>/<time>_<manifest12>` and chmod a-w on the files. All fleet disks are
  ext4, so btrfs/zfs/reflink snapshots are not available without reformatting 3.7-7.7 TB disks that are 85-98% full. Do not
  reformat. Hardlinks cost almost no space and delta_apply --link already uses them. Because live and snapshot share
  read-only files, an in-place write fails loudly and a rename works: the rule enforces itself.
- Kit gen and bind read from the newest snapshot, not from live, and record its manifest hash. So a 6-10 h kit has frozen
  inputs, and rollback is "point at the previous snapshot".
- Keep the last 5 snapshots, plus any named by a running or queued job, plus any named by a signed record not yet exported.
- Replicate the delta per host in parallel with --link-dest. A host that cannot take it is dropped from gen hosts for that
  die. It never stops the die (LATENCY-1117 cause 3, about 4 h lost).
- Strict bind, LATCHECK, G0 and the publish gate run after the change as warnings (r704 (3)). One condition: a bind or
  latency failure cancels the kits of the types it names (LATENCY-R built this), because those are functional errors and
  the kits would run 6-10 h to a result that cannot count.
- To be plain: this is still versioning, done by `cp -al` in seconds instead of by a tree chain with gates. Tonight's cost
  was the gates and the replication around the versions, not the versions.

### Build results and sign-off
- Per-attempt dirs as today. Signed records exported to AGIdock and rtx-pro as today.
- The R-MINIMAL record adds four fields: rt sha, die snapshot manifest hash, kit spec digest, die env keys. Record only; no
  new gate. If a later snapshot changes that type's plan block or bound RTL, the row is flagged STALE-INPUT for re-sign.

### Minimum safety to keep (5 items)
1. Git history on main (rollback and conflict detection for code).
2. Immutable rt/<sha>, resolved at launch, smoke before flip.
3. Hardlink snapshot before each die apply, single writer, rename-only writes.
4. Input hashes in the signed record.
5. Host survival from r703: memory admission, disk floors, delete guard, OOM protection. The delete guard must cover
   snap_<die> and rt/<sha>.

One caution on r703, for the owner to decide: with dedupe gone, a kit that failed in the tool is relaunched unchanged
(55 identical VPW fails tonight). The dedupe held 240 launches an hour because its key did not include the tools, so
a tools fix could not release it. If the key is (rt sha, snapshot hash, spec digest), every push releases it by itself and
it only skips runs whose result is already known. That is a cache, not a hold. Optional.

## (d) Time per fix, measured tonight
| step | today | recommended |
|---|---|---|
| test | gate 2-3 min (162 files at 03:24) | touched-file tests 1-2 min |
| land on main | 6-7 min with COORD awake; 228 min tonight; queue tick 5 min | push, under 1 min |
| rt on all hosts | 1-3 min (merged 03:25:13, last host 03:27:32) | 1-2 min |
| tools reach the die | 20-30 min per pass at best; HEAD 3 h 10 min; S81 over 5 h and not yet | 0 (read from rt at launch) |
| next launch | tick 3-5 min now (183-284 s); 12-24 min at 21:00-23:00; adopt to enqueue 1-2 ticks | tick 3-5 min |
| **fix to first kit** | **about 40-60 min best, 3 h typical, S81 never tonight** | **6-11 min** |

- Saving per tools fix: 30-50 min in the best case, about 3 h in tonight's typical case.
- Of that saving, removing git would add 2-4 min. Removing approval and the queue gives about 5 min normally and 228 min
  when agents are limited. Removing tools from the trees gives the rest.
- Plan events: QC N3 took about 7 h from composed to first kit, 4.5 h of it after the bind finished; S81 D7w spent 34 min
  in the publish gate. With bind and gates as post-change warnings, a QC event saves about 2.5-4.5 h and an S81 event
  about 35-45 min. The price is kit hours lost when a bind fails after launch, which is why the named-type cancel stays.
- A fix never reaches a kit that is already running. Each fix helps the next launch only, so the fix-to-launch time above
  is the whole benefit; nothing here shortens the 6-10 h build.

## Do now (ranked)
1. TOOLS-DECOUPLE: kits read tools from rt/<sha> resolved at launch, sha in spec.json. Then switch tools_refresh off for
   all dies. This alone un-sticks S81 and QC.
2. MERGE-AUTO: ot-push-main, 1-min rt sync from origin/main, auto-revert on smoke fail.
3. TOOLS-DECOUPLE phase 2: live_<die> + cp -al snapshot before apply + rename-only writes + per-host parallel delta.
4. Signed record: add the four hash fields.
5. FLEET-OPS-R: delete guard covers snap_<die> and rt/<sha>; no service runs code from a lane worktree path (03:27 failure).

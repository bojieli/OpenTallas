# FLEET-DISK (branch claude/fleet-disk-1024, worktree ~/wt/fleet-disk) -- updated 2026-10-24 08:06 PDT
Merged to main 1ed91ad4ca + 6281884e3d (census resync); ~/.local/bin/ot-run re-installed (v13). Lane DONE except background movers.

## Root fs BEFORE (07:31) -> AFTER (2026-10-24 08:06)
- intel1 384G 87% -> 116G 26%   (claude/ FLIPPED -> scratch2; busy: /srv/opentallas-scratch/tok-qw 89G)
- intel2 199G 45% -> 126G 29%   (busy: s81 61G, kv-tok 42G, die-sta, claude/{tok-hbm,tokg-1023,elem-s81}, ~/scratch 19G [docker mounts])
- epyc2  296G  9% -> 159G  5%   (busy: claude/{kv-tok 23G,hbm-p7-tok-1023 9G,part-cap,tok-hbm,tokg-1023}, s81, ~/wt/{kv-tok,part-cap})
- epyc3 md0 6% -> 7%; localhost md0 33% -> 52% (NOT this lane; something is filling localhost; DISK GUARD refuses at >85%)
- scratch2 after: intel1 338G used/3.0T free, intel2 586G/2.7T, epyc2 223G/612G free (epyc2 ~/wt + ~/OpenTallas moved there)

## What landed
- ot-run v13: on hosts with a separate /srv/opentallas-scratch2 (intel1/intel2/epyc2) OT_SCRATCH + new run dirs ONLY on that
  disk (even if / is emptier); disk < OT_RUN_SCRATCH_DISK_FLOOR_GB 50 -> host refused / NOT RUN exit 98, no root fallback.
  DISK GUARD: root fs > 85% -> host refused (probe) + host-side check (NOT RUN exit 97). --status shows root %/scratch GB.
- localhost: role normal with HOST_RESERVE 32 threads / 64 GB (coordinator request).
- tools/fleet/ot-mvlink.sh (busy = lsof +D OR docker bind mount), ot-scratch-consolidate.sh, ot-docker-relocate.sh,
  install_fleet_host.sh (claude -> scratch2/claude, claude/wt), docs/FLEET.md "Disks" + lsof/docker lesson.
- Tests: test_ot_run_* 7/7 OK (new test_ot_run_scratch_disk.py 18 tests); choose selftest PASS 29; live --selftest PASS 5/5.
  make check-figures: prose coverage OK; check-headline-bundle + final-number-readiness FAIL identically on main (pre-existing).

## Background (retry every 10 min, never kill/pause anything; logs /srv/opentallas-scratch2/claude/fleet-disk/)
- intel1/intel2/epyc2: ot-scratch-consolidate --loop 600 (consolidate.log): moves idle entries, flips claude/ when only links remain.
- intel2 ~/scratch, epyc2 ~/wt/{kv-tok,part-cap}: ot-mvlink retry loop (home-move.log).
- intel1/intel2/epyc2: ot-docker-relocate --wait 300 (docker-relocate.log): /var/lib/{containerd,docker} (6.5 GB) -> scratch2
  bind mounts once no container runs for 3 checks (docker stopped ~1 min then; a docker run in that minute would fail).

## Incident / honesty
- 07:41-07:57 my first ot-mvlink used lsof +D only (blind to docker bind mounts). Checked afterwards: no running container
  mounts any dir I moved; docker events show no container whose life spanned a move with a moved mount except
  intel2 g2part-422678 (07:39-07:42, exit 0) and hd_tile-476609 (07:46:25-28, exit 2, s81-head lane on scratch2 = not moved).
  Moved dirs: intel1 die-sta kv-tok qc-a0 qc-tok s81 claude/part-cap ~/.cache; intel2 qc-a0 kv-tok claude/{kv-g3,part-cap,
  stw-s81d-tok,tok-ds} ~/.cache; epyc2 kv-tok claude/{tok-ds,tokd-hbm2,tokj-1023} ~/.cache ~/wt/{tok-ds-comp,tok-hbm} ~/OpenTallas.
- Not moved (static, small): ~/src-tools 3.4G, ~/.local 0.45G, /var 7G.

## CODEX notes
- 2026-10-24 09:01 PDT: CODEX root collected background movers: no new failure, live-source directories remain unmoved. Removed only own unused interrupted checkout (40GB); no active source moved.

## CODEX notes 2026-10-25 02:40 PDT
Background inherited epyc1 cleanup PID1823050 still progressing, not interrupted. epyc1 /26%, scratch2 84%/559GB ->64%/1.2TB at02:40; all workers above scratch floor (epyc2 minimum130GB). No new destructive cleanup started by CODEX. Existing worker movers need no intervention.

2026-10-25 02:46 PDT CODEX: epyc2 NEW admissions HELD by root order for measured scratch depletion103GB->83GB/2min after fleet fill; live jobs untouched. All lane leaders notified use --stage/other4. Remove only this held_hosts line once safe measured growth headroom returns.

# ISOLATE-1: sealed jobs and a content-addressed store (2026-11-09, ISOLATE-1 for COORD)

OWNER 03:4x, verbatim: "yes, isolate the jobs. simply delete the finished job folder". Branch `claude/isolate-1-1109` on the central repo (tools/fleet: `ot-job`, `ot-job-docker`, `ot_store.py`, `ot-run-sealed`, `ot-run --job`, `test_ot_job.py`, 36 tests).

## Problem and rule
Live jobs read other jobs' dirs (generator inputs, splits, kits, checkpoints, routed DBs) by absolute path, `cp -al` and symlinks, so no cleanup can know what is safe. The 03:08 epyc2 apply deleted `s81-t51-recut`, the only copy of the t51 generator inputs. New rule: **a job reads only what it declared; what a later job needs is published at job end; then the job folder is deleted.** No lane-name, age or reference guessing.

## How it works
1. **Submit**: `ot-run --mem M --job SPEC.json -- cmd`. The spec lists inputs (path, or store sha, plus a host to fetch from), the work dir (seeded by copies), publish items and return paths. On the chosen host, `ot-job` makes one dir `J=/srv/opentallas-scratch2/claude/ot-jobs/<name>-<tag>`. Inputs go in `J/in/<n>` as read-only hardlinks from the host store; they are fetched by sha from another host if they are missing here. A ref `job-<tag>` holds them while the job runs.
2. **Seal**: the command runs under `bwrap`. /srv, /mnt, /media, /archive, /tmp and $HOME are empty, except for the job dir, each input bound read-only at the absolute path the job already uses, the work dir at its own path, and a tool allowlist (`~/.local`, `~/bin`). `/usr/bin/docker` is `ot-job-docker`. Every `-v`/`--mount`/`docker cp` host path must be a declared path; the shim rewrites it to the real path in J, forces inputs `:ro`, and passes the call through the ot-heavy memory shim. Anything else exits 97 with `OT-JOB ISOLATION: undeclared host path ...`. So an undeclared read fails at once, both on the host side and in containers.
3. **End**: each publish item goes into the store by hardlink, at no copy cost. It is re-verified and gets an artifact record in the signed-store entry format (`records/<id[:2]>/<id>.json.gz`: name, tree sha, `files [[rel,size,sha256]]`, producer = job, host, cmd, rc, times, input shas). Optional `replicate` pushes it to a second host. Return paths are copied to the caller dir, unlinking first so a copy never writes through a hardlink. Then **J is deleted**. If publishing fails, J is kept and the exit status is 98.
4. **Store** (`<fs>/ot-store`, outside every `/claude/` lane root, so no lane cleanup walks it): sha256-named immutable objects (0444), and tree objects for directories. Absolute or escaping symlinks are refused, because they are exactly the cross-job references we are removing. **GC by reference only**: an object stays while a ref holds it (live job inputs, `pin-*` for live forms or counted views), while a counted signed-store record lists its sha256, or while it is under 24 h old. Otherwise it goes. `gc` is dry unless `--apply`; there is no timer. A pin for a live form's input is pushed to a second host's store (or the AGIdock archive), since hosts are volatile.

## Disk cost (measured)
- intel1 wave run dirs: 165 GB of `run/results`. Of that, 102 GB (62%) is per-step ODBs that no later job reads: `2_*`, `3_1..3_5`, `5_3`, `6_1`. `3_place.odb` is a byte copy of `3_5_place_dp.odb`. What later jobs read is 3_place, 4_cts, 5_route/6_final plus logs and reports, about **26 GB (16%)**. The store holds only that, deduplicated by sha (`3_place` = `3_5`, unchanged kit files, resumed checkpoints). Staged inputs are hardlinks (0 bytes). Kit seeds are copies, but small (KV kits 5-20 MB).
- **Steady state: about 16-20% of today's result bytes, and no orphan dirs.**
- **Pilot phase** (return-all, so the wave reads K as before): the store copy plus K's copy, i.e. +1x `run/` per sealed row for 24 h. kv3_phy is 1.25 GB per row.

## Migration (wave by wave, KW-FIX-42 applies; non-isolated jobs keep their folders until moved)
- **W0 pilot (now)**: KV place rows on epyc7 through `ot-run-sealed`, a drop-in `kit_wave.json ot_run`. Only the wave's `bash <runner> <K> place m t` under `runs/qwen_kvsys/` is sealed; everything else passes to kw23 unchanged. It writes the full work dir back to K, so the wave does not change. Config: hub `~/.local/lib/fleet/isolate-1/sealed.json` (enabled false until KW-FIX-42 flips it). Revert: `ot_run` back to kw23, or `enabled: false`.
- **W1**: all dies, all hosts with bwrap. The sealer declares the KWCHILD child-record dirs (from `macros/*.provenance.json`, as run_kit.sh finds them) and the kit-resume checkpoint as inputs by sha.
- **W2**: geom, route, ECO and re-sign read place and route outputs by **record id**, not K. The return set shrinks to logs and result.json. Gen is sealed: src, plan and bind trees are published once per wave, and the wave config names store ids instead of paths.
- **W3**: lane jobs (ECO, LEC, resign, probes) use `ot-run --job`. Counted views already carry sha256 and become store pins. After that, cleanup = ot-job's delete. The old autoclean only ever touches non-isolated legacy dirs, and it shrinks to nothing.

## What breaks (found or expected)
- **Undeclared reads fail, by design.** Known today: KWCHILD signed-child mounts at host-absolute paths, kit-resume hardlinks into the previous attempt, `~/coord` reads, prov resign relays that ssh to the hub (`~/.ssh` is hidden; sealed jobs do not ssh). Each one becomes a declared input, or the hub does it outside the job.
- **Detached work that outlives the job.** `lec_async` is safe: `finish` waits for the LEC before the job ends. A `docker run -d` that is never waited on would lose its dir.
- **The spill and phase_done hand-off are off for sealed jobs**, because inputs come by sha and no lane root is copied. An async place returns at client end (KW_PLACE_RC).
- **Root-owned outputs** (a container killed before its chown) are deleted after a docker chown. This is tested.
- **Not a security boundary.** A job can still reach the real docker CLI by its bound path. This stops sloppy reads, not hostile ones; a docker authz plugin would close it later.
- **Hosts need bwrap with user namespaces**: Ubuntu's apparmor allows bwrap, but plain `unshare` is blocked. ot-run-sealed checks each host and passes through when bwrap fails.

## Tests
`test_ot_job.py`: 36 pass on epyc7, including the real daemon. **Positive control**: `test_undeclared_path_fails` reads another lane's dir and fails; with the dir declared, the same read passes. The docker form is `test_docker_mount_checked`, with exit 97, also for `/usr/bin/docker` called by path. Two mutants make the tests fail: no /srv hiding, and a shim that lets undeclared paths through.

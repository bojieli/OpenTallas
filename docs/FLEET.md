# OpenTallas compute fleet

Measured live on 2026-10-24 at 06:35-06:50 PDT (lane FLEET-NEW3) with `lscpu`, `free -g`, `df -hT`, `lsblk`,
`ip -4 addr`, `docker image inspect` over each host's ssh alias, and the tool versions through `ot-run` itself
(so they are what an `ot-run` job sees). RAM is `free -g` (GiB). This file holds no passwords, API keys or SSH key
material.

The previous fleet (rtx-pro coordinator, ot-epyc1..9, ot-gold1/2, ot-pve1, ot-agidock128) is gone: the coordinator
died 2026-10-23 23:45 PDT. Its description is in this file's git history (last at main 3e05af806b). epyc2, epyc3 and
intel1/intel2 are the old ot-epyc9, ot-epyc7 and ot-gold1/ot-gold2 machines, reinstalled (see "Old scratch disks").

## Summary

| alias | hostname | CPU | threads | RAM | scratch free | AVX-512 | ot-run role |
|---|---|---|---|---|---|---|---|
| `localhost` | tender-ray | 1x AMD EPYC 9754 (Zen 4c), 128C | 256 | 755 GiB | 2.2 TB (`/`, RAID1 2x 3.5 TB NVMe) | yes | `normal` minus 32 threads / 64 GB |
| `epyc2` | dear-crayfish | 2x AMD EPYC 7543 (Zen 3), 64C, 2 NUMA | 128 | 1,007 GiB | 835 GB (`/srv/opentallas-scratch2`, 880 GB NVMe; 3.5 TB `/` not for work) | no | `normal` |
| `epyc3` | eternal-dove | 2x AMD EPYC 7443 (Zen 3), 48C, 2 NUMA | 96 | 1,007 GiB | 6.9 TB (`/`, RAID1 2x 7.3 TB NVMe) | no | `normal` |
| `intel1` | key-cardinal | 2x Xeon Gold 6330 (Ice Lake), 56C, 2 NUMA | 112 | 1,007 GiB | 3.1 TB (`/srv/opentallas-scratch2`, 3.5 TB NVMe; 468 GB `/` not for work) | yes | `normal` |
| `intel2` | tolerant-swine | 2x Xeon Gold 6330 (Ice Lake), 56C, 2 NUMA | 112 | 1,007 GiB | 2.9 TB (`/srv/opentallas-scratch2`, 3.5 TB NVMe; 468 GB `/` not for work) | yes | `normal` |

Totals: 704 threads, 4.7 TiB RAM, ~13.6 TB free scratch. All hosts run Ubuntu 26.04.1 LTS, kernel 7.0.0-38-generic,
Docker 29.1.3, and share the private VLAN 10.188.153.0/24 (localhost .10, epyc2 .40, epyc3 .33, intel1 .2,
intel2 .25). Public: localhost 84.32.71.203, epyc2 185.8.107.246, epyc3 185.8.106.109, intel1 185.8.107.41,
intel2 185.8.106.226. Only localhost reaches GitHub; servers fetch from `hub` (= localhost:~/OpenTallas).

## Disks (owner order 2026-10-24 07:30: never use root disks for work)

- intel1 / intel2 (468 GB `/` + 3.5 TB `/srv/opentallas-scratch2`) and epyc2 (3.5 TB `/` + 880 GB
  `/srv/opentallas-scratch2`): every worktree, build, run dir and copy lives on `/srv/opentallas-scratch2/claude/`.
  Server worktrees: `/srv/opentallas-scratch2/claude/wt/<lane>` (`git worktree add` there, optionally with a `~/wt/<lane>`
  symlink). `/srv/opentallas-scratch/claude` is a symlink to `/srv/opentallas-scratch2/claude` (FLEET-DISK; on a host
  where some entries were still busy, `ot-scratch-consolidate --loop` keeps moving them and flips claude/ when done;
  log `/srv/opentallas-scratch2/claude/fleet-disk/consolidate.log`). `~/OpenTallas`, `~/wt/*`, `~/scratch`, `~/.cache`
  there are symlinks into `/srv/opentallas-scratch2/claude/{moved,wt}/`.
- localhost and epyc3 have one RAID1 md0 only: keep using `/srv/opentallas-scratch` there.
- ot-run v13 enforces it: on a host whose `/srv/opentallas-scratch2` is a separate disk, `$OT_SCRATCH` and every NEW run
  dir (SCRATCH2 placement) go to that disk even when `/` has more free space; when that disk has less than
  `OT_RUN_SCRATCH_DISK_FLOOR_GB` (50) free the host is refused, and a run dir that cannot be placed stops the job
  (`NOT RUN`, exit 98) -- there is no fallback to `/`. DISK GUARD: a host whose `/` is more than `OT_RUN_ROOTFS_MAX_PCT`
  (85) % full admits no job (probe + re-check on the host, `NOT RUN`, exit 97). `ot-run --status` shows `root N%` and
  `scratch N GB` per host. A `--dir` on the root fs of a scratch-disk host gets a WARNING.
- Docker images (containerd snapshotter, ~6.5 GB in `/var/lib/containerd`) move to `/srv/opentallas-scratch2/system/`
  with bind mounts via `ot-docker-relocate`, only when no container runs (it waits for 3 idle checks; scheduled with
  `--wait`, log `/srv/opentallas-scratch2/claude/fleet-disk/docker-relocate.log`).
- Moving data off a root fs: `ot-mvlink SRC DST` (tools/fleet/ot-mvlink.sh) moves an idle dir and leaves a symlink;
  bulk rsync, re-check, atomic mv + symlink, catch-up rsync, then delete.
- **Lesson (2026-10-24): `lsof +D DIR` does NOT see docker bind mounts** -- a container's processes report
  container-side paths (`/work`, `/src`), so a dir that a running ORFS container bind-mounts looks idle to lsof. Any
  mover must also check `docker inspect -f '{{range .Mounts}}{{.Source}} {{end}}'` of every running container
  (resolve symlinks; the dir, a parent, or a path inside it all count as busy). ot-mvlink does both.

## Toolchain parity (measured 2026-10-24 through `ot-run --hosts <h>`)

Identical on all five hosts:

- `verilator --version`: `Verilator 5.050 2026-07-01 rev v5.050`
- `yosys -V`: `Yosys 0.68 (git sha1 38e001a6f, Release, GNU /usr/bin/c++ 15.2.0)`
- `sta -version`: `3.1.0` (OpenSTA be771a0, `~/.local/opentallas-tools/bin/sta`)
- `openroad/orfs:latest` = `openroad/orfs:asap7lock`, image id and repo digest
  `sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29` (same as the old fleet)

Tools live in `~/.local/opentallas-tools/{bin,verilator-5.050,yosys-0.68,opensta-be771a0,cudd-3.0.0}`; `ot-heavy`
puts `bin`, `yosys-0.68/bin` and `verilator-5.050/bin` first on PATH for every job.

## ot-run (how lanes launch heavy jobs)

Installed on localhost as `~/.local/bin/ot-run` (copy of `tools/fleet/ot-run`; re-install with
`install -m755 tools/fleet/ot-run ~/.local/bin/ot-run` after a change merges). Hosts, in `HOSTS`: epyc2, epyc3,
intel1, intel2, localhost.

    ot-run --status                                    # what each host admits now
    ot-run --mem GB [--threads N] [--dir DIR] -- CMD   # placed on the best host that admits GB now
    ot-run --mem GB --hosts epyc3 -- CMD               # pinned (no spill)
    ot-run --mem GB --priority die --disk 200 --dir DIR -- CMD   # die-level job
    ot-run --cancel <substring of your --dir/script>   # stop your own clients (never pkill -f)

The command runs on the remote host in a systemd user scope with MemoryMax = --mem, stdin/stdout and the exit status
are the command's; the last stderr line is `ot-run: RAN on <host> ...: exit N` or `NOT RUN` / `NOT COMPLETED`. ot-run
syncs nothing: put inputs on the host first (`--dir` must exist there; only hosts that have it qualify). New lane run
dirs go under `$OT_SCRATCH/claude/<lane>/` (scratch disk on intel1/intel2/epyc2, see "Disks"; `/srv/opentallas-scratch`
on localhost/epyc3; naming `/srv/opentallas-scratch/claude/...` works everywhere since it links to the scratch disk).

Roles: `normal` on all five hosts. localhost (FLEET-DISK 2026-10-24, coordinator: as `coord` = last resort it sat at
~50-70/256 load while lanes queued; ~30 agents run there but use little CPU) is a normal host minus `HOST_RESERVE`
32 threads / 64 GB for agents and merges: placement sees 224 cores and admit/free/total RAM - 64 GB; its ot-heavy
still keeps 15 % of RAM free, and it never receives spills (`SPILL_HOSTS_EXCLUDE`). The `coord`/`smalldisk`/
`throughput` role logic remains for future hosts. `NO_AVX512` = epyc2, epyc3 (Zen 3): a lane holding `-march=native` builds never spills there.

Per-host helpers (installed by `tools/fleet/install_fleet_host.sh`, idempotent; run on the host from a copy of
tools/fleet, `--role coord` on localhost for its 15 % RAM floor): `/usr/local/bin/{ot-heavy,ot-heavy-reconcile,ot-vl-jcap,ot-protect-die}`,
`/usr/local/lib/ot-heavy/{ot-heavy-exit,bin/docker,vljcap/make}`, `ot-die-protection.service`, earlyoom (3 %/2 %),
`/etc/ot-heavy.conf`, user linger, user cron `*/2 ot-heavy-reconcile`, scratch `/srv/opentallas-scratch/claude`
(-> `/srv/opentallas-scratch2/claude` on a separate scratch disk), `/usr/local/bin/{ot-mvlink,ot-scratch-consolidate,ot-docker-relocate}`.
localhost also runs `~/.local/bin/ot-sizes-sync` from cron every 10 min (fleet size table). Verified 2026-10-24:
`ot-run --selftest` PASS on all five hosts (exit status 7 returned, no-memory -> 75 NOT RUN, bad dir -> 96 NOT RUN).

## Old scratch disks (wiped 2026-10-24 07:03 PDT, owner order)

The old ot-gold1/ot-gold2/ot-epyc9 scratch NVMe disks (intel1/intel2 `nvme0n1` 3.5 TB, epyc2 `nvme0n1` 894 GB) were
wiped and reformatted as `/srv/opentallas-scratch2` (fstab, `nofail`); nothing from the old fleet remains. See "Disks".

## Closure-loop admission (tools/closure_loop/hosts.json)

hosts.json lists the same five hosts (base `/srv/opentallas-scratch/claude/closure-loop`, caps verilator, yosys,
iverilog, orfs; `max_job_ram_gb` 0.8 x RAM; disk floors 200 GB epyc2/3, 100 GB intel1/2, 300 GB localhost).
localhost has `max_loop_threads 0` (the loop places nothing there until the owner opens it) and `bench_offload`.
No `git_mirror` (servers cannot reach GitHub; sync falls back to the tar stream). Old hosts are in `retired_hosts`,
so old specs that pin them fall back to admission.

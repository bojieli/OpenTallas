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
| `localhost` | tender-ray | 1x AMD EPYC 9754 (Zen 4c), 128C | 256 | 755 GiB | 2.8 TB (`/`, RAID1 2x 3.5 TB NVMe) | yes | `coord` |
| `epyc2` | dear-crayfish | 2x AMD EPYC 7543 (Zen 3), 64C, 2 NUMA | 128 | 1,007 GiB | 3.2 TB (`/`, 3.5 TB NVMe) | no | `normal` |
| `epyc3` | eternal-dove | 2x AMD EPYC 7443 (Zen 3), 48C, 2 NUMA | 96 | 1,007 GiB | 6.9 TB (`/`, RAID1 2x 7.3 TB NVMe) | no | `normal` |
| `intel1` | key-cardinal | 2x Xeon Gold 6330 (Ice Lake), 56C, 2 NUMA | 112 | 1,007 GiB | ~340 GB (`/`, 468 GB NVMe) | yes | `smalldisk` |
| `intel2` | tolerant-swine | 2x Xeon Gold 6330 (Ice Lake), 56C, 2 NUMA | 112 | 1,007 GiB | ~330 GB (`/`, 468 GB NVMe) | yes | `smalldisk` |

Totals: 704 threads, 4.7 TiB RAM, ~13.6 TB free scratch. All hosts run Ubuntu 26.04.1 LTS, kernel 7.0.0-38-generic,
Docker 29.1.3, and share the private VLAN 10.188.153.0/24 (localhost .10, epyc2 .40, epyc3 .33, intel1 .2,
intel2 .25). Public: localhost 84.32.71.203, epyc2 185.8.107.246, epyc3 185.8.106.109, intel1 185.8.107.41,
intel2 185.8.106.226. Only localhost reaches GitHub; servers fetch from `hub` (= localhost:~/OpenTallas).

intel1/intel2 free disk was falling while lanes started (397 -> 330 GB in 15 min): watch it; they are `smalldisk`
so die-level jobs avoid them.

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
dirs go under `/srv/opentallas-scratch/claude/<lane>/` (`$OT_SCRATCH` in the job; `~/ot-scratch` links there).

Roles: `normal` (epyc2, epyc3: die-level work), `smalldisk` (intel1/2: die jobs skip them while another host
qualifies), `coord` (localhost: the coordinator, CPU shared with ~10 agent sessions; it gets a job only when no
server admits it now, or when pinned with `--hosts localhost`, and never receives spills; its ot-heavy keeps 15 % of
RAM free). `NO_AVX512` = epyc2, epyc3 (Zen 3): a lane holding `-march=native` builds never spills there.

Per-host helpers (installed by `tools/fleet/install_fleet_host.sh`, idempotent; run on the host from a copy of
tools/fleet, `--role coord` on localhost): `/usr/local/bin/{ot-heavy,ot-heavy-reconcile,ot-vl-jcap,ot-protect-die}`,
`/usr/local/lib/ot-heavy/{ot-heavy-exit,bin/docker,vljcap/make}`, `ot-die-protection.service`, earlyoom (3 %/2 %),
`/etc/ot-heavy.conf`, user linger, user cron `*/2 ot-heavy-reconcile`, scratch `/srv/opentallas-scratch/claude`.
localhost also runs `~/.local/bin/ot-sizes-sync` from cron every 10 min (fleet size table). Verified 2026-10-24:
`ot-run --selftest` PASS on all five hosts (exit status 7 returned, no-memory -> 75 NOT RUN, bad dir -> 96 NOT RUN).

## Old scratch disks (not used; owner decision pending)

The reinstall wiped the partition signatures of the old scratch NVMe disks but not their data; the ext4 backup
superblocks are intact. FLEET-NEW3 mounted them read-only (`mount -o ro,noload,sb=131072 /dev/nvme0n1
/mnt/old-nvme0`, not in fstab) and did NOT format them:

- intel1 `nvme0n1` 3.5 TB (Samsung): old ot-gold1 `/srv/opentallas-scratch` (claude/ with 228 lane dirs, codex/, docker/).
- intel2 `nvme0n1` 3.5 TB (Micron 7450): old ot-gold2 scratch (claude/ with 192 lane dirs).
- epyc2 `nvme0n1` 894 GB (Micron 7450): old ot-epyc9 scratch; `claude/` returns I/O errors (needs fsck on a copy).

They may hold 10-23 lane outputs. Once recovery is done (or declined), they can be reformatted as scratch; intel1/2
would then lose the `smalldisk` role.

## Closure-loop admission (tools/closure_loop/hosts.json)

hosts.json lists the same five hosts (base `/srv/opentallas-scratch/claude/closure-loop`, caps verilator, yosys,
iverilog, orfs; `max_job_ram_gb` 0.8 x RAM; disk floors 200 GB epyc2/3, 100 GB intel1/2, 300 GB localhost).
localhost has `max_loop_threads 0` (the loop places nothing there until the owner opens it) and `bench_offload`.
No `git_mirror` (servers cannot reach GitHub; sync falls back to the tar stream). Old hosts are in `retired_hosts`,
so old specs that pin them fall back to admission.

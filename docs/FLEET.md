# OpenTallas compute fleet

Measured live on 2026-10-08 at 01:38 PDT with read-only commands (`lscpu`, `free -g`, `lsblk`, `df -hT`,
`/proc/mounts`, `ip -4 addr`, `docker images --digests`, `nvidia-smi`) over each host's ssh alias, plus the
Cherry Servers API (`GET /v1/projects/294737/servers`) for plan, region and state. RAM is `free -g` (GiB).
Disk sizes are as `df -h` / `lsblk` report them. Admission settings are copied from
`tools/closure_loop/hosts.json` at this commit. This file holds no passwords, API keys or SSH key material.

## Summary

| Host (ssh alias) | Role | Provider / location | CPU | Cores / threads | RAM | GPU | State |
|---|---|---|---|---|---|---|---|
| `localhost` | Coordinator, GPU inference host, ORFS-only loop host | On-premises workstation | Intel Core i9-13900KS | 24 (8P+16E) / 32 | 188 GiB | 1x RTX PRO 6000 Blackwell (96 GB) | up |
| `ot-epyc3` | Die-top host; closure-loop host (first preference) | Cherry Servers, Stockholm SE (id 1023111, `known-grouse`) | AMD EPYC 9575F | 64 / 128 | 1,133 GiB | none | up |
| `ot-epyc1tb` | Closure-loop host; Codex repos/checkpoints; NFS server for EPYC2 | Cherry Servers, Singapore (id 1019050, `teaching-mouse`) | AMD EPYC 9575F | 64 / 128 | 1,133 GiB | none | up |
| `ot-epyc2` | Closure-loop host | Cherry Servers, Singapore (id 1020904, `climbing-locust`) | AMD EPYC 9575F | 64 / 128 | 1,133 GiB | none | up |
| `ot-pve1` | Closure-loop host, ORFS/docker only | Proxmox VM behind jump host `bsql-host1.01.me` | not measured | 28 (hosts.json) | 235 GiB (hosts.json) | none | **unreachable** |
| `ot-agidock128` | Closure-loop host (small RAM) | AGIdock KVM VM, public IP | AMD EPYC 7B13 | 64 vCPU / 64 | 125 GiB | none | up |
| (none yet) EPYC4 | Planned closure-loop host | Cherry Servers, Tokyo JP (id 1025189, `regular-crane`) | AMD EPYC 9575F | 64 / 128 (plan) | 1,152 GB (plan) | none | **provisioning** |

**Totals, reachable hosts (localhost, EPYC1-3, AGIdock):** 280 cores / 480 threads, 3,712 GiB RAM, 1 GPU
(RTX PRO 6000 Blackwell, 97,887 MiB), about 24.7 TB of usable filesystem (about 15.5 TB free at the probe).
With PVE1 at its hosts.json figures: 308 cores, 3,947 GiB RAM. When EPYC4 comes up: plus 64 cores / 128 threads,
1,152 GB RAM and about 8 TB raw NVMe.

Common toolchain on every Linux loop host except localhost and PVE1: `~/.local/opentallas-tools` holds
verilator-5.050, yosys-0.68, opensta-be771a0 and cudd-3.0.0. The ORFS image `openroad/orfs:latest` =
`openroad/orfs:asap7lock` has repo digest
`sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29` on localhost, AGIdock, EPYC1, EPYC2 and
EPYC3 (identical everywhere it was measured).

## Per host

### localhost (coordinator)

- **Role:** the coordinator host where the agents run; the only GPU, used for all model inference (golden
  generation, DSpark/acceptance runs; CPU hosts never run inference). It is also a closure-loop host for ORFS
  stages only (`bench_offload`: its route/calibrate jobs run here, benches go to a fleet host).
- **Hardware:** Intel Core i9-13900KS, 1 socket, 24 cores (8 P-cores with HT + 16 E-cores), 32 threads; 188 GiB RAM;
  GPU NVIDIA RTX PRO 6000 Blackwell Workstation Edition, 97,887 MiB, driver 595.91.07.
- **Disks:** 3x HP SSD EX900 Plus 2 TB NVMe (1.9 TiB each) in md RAID5 (`/dev/md0`).
  - `/` ext4 on `md0p1`: 3.7 T, 805 G free (78% used).
  - `/var/lib/docker` xfs on a loop file (`/dev/loop19`): 500 G, 423 G free.
- **Network:** `enp6s0` 155.103.252.95/24. No NFS mounts.
- **OS:** Ubuntu 22.04.5 LTS, kernel 6.8.0-138-generic; Docker 28.5.2; docker root `/var/lib/docker`.
- **ORFS images:** `openroad/orfs:latest` and `:asap7lock` at the fleet digest above; old local image kept as
  `openroad/orfs:local-old-3985ce6d` (`sha256:d6b50de8...`). Local Verilator 4.038 / Yosys 0.9 differ from the
  fleet, so the host has only the `orfs` cap.
- **hosts.json:** `base /home/ubuntu/closure-loop-local`; caps `[orfs]`; `cores 32`, `max_loop_threads 96`
  (the localhost thread guard), `max_job_threads 16`, `max_job_ram_gb 120`, `min_free_ram_gb 16`;
  `min_free_disk_gb 150` on the base, `disk_roots {"/": 150}`; `bench_offload true`.

### ot-epyc3 (EPYC3)

- **Role:** die-top place-and-route host and first-preference closure-loop host.
- **Provider:** Cherry Servers, Stockholm (Sweden), server 1023111 `known-grouse`, plan "AMD EPYC 9575F"
  (1152 GB DDR5-6400, 2x NVMe 1 TB + 2x NVMe 3 TB, 10 Gbps NIC, 100 TB bandwidth), active since 2026-10-06.
- **Hardware:** AMD EPYC 9575F, 1 socket, 64 cores / 128 threads, 1 NUMA node; 1,133 GiB RAM.
- **Disks:** 2x Micron 894 G NVMe (md RAID, root) + 2x Solidigm 2.9 T NVMe.
  - `/` ext4 on `md0`: 879 G, 816 G free.
  - `/srv/opentallas-scratch` ext4 on `nvme2n1`: 2.9 T, 2.5 T free. `/srv/opentallas` is a symlink to
    `/srv/opentallas-scratch/opentallas`.
  - `/srv/opentallas-scratch2` ext4 on `nvme3n1`: 2.9 T, 2.0 T free; holds the docker root
    (`/srv/opentallas-scratch2/docker`).
- **Network:** `bond0` 84.32.49.237/26; private VLAN `bond0.1874` 10.200.213.40/24 (a different private network
  from EPYC1/EPYC2, so no private link to them). No NFS mounts.
- **OS:** Ubuntu 26.04.1 LTS, kernel 7.0.0-34-generic; Docker 29.1.3; clock in UTC (the others are PDT).
- **hosts.json:** `base /srv/opentallas-scratch2/scratch/claude/closure-loop`; caps verilator, yosys, iverilog, orfs;
  `cores 128`, `max_job_threads 128`, `ram_gb 1133`, `max_job_ram_gb 1076`; `min_free_disk_gb 200`,
  `disk_roots {"/": 100, "/srv/opentallas-scratch": 200}`.

### ot-epyc1tb (EPYC1)

- **Role:** closure-loop host; also Codex's original server (`/srv/opentallas` holds its repos, checkpoints and
  jobs); NFS server for EPYC2; hosts the shared memory guard `/srv/opentallas-scratch/admit.sh`.
- **Provider:** Cherry Servers, Singapore, server 1019050 `teaching-mouse`, same plan as EPYC3 (20 TB bandwidth),
  active since 2026-10-03.
- **Hardware:** AMD EPYC 9575F, 1 socket, 64 cores / 128 threads; 1,133 GiB RAM.
- **Disks:** 2x Micron 894 G NVMe (md RAID, root) + 2x Solidigm 2.9 T NVMe.
  - `/` ext4 on `md0`: 879 G, 808 G free.
  - `/srv/opentallas` ext4 on `nvme2n1`: 2.9 T, 1,006 G free (66% used); holds the docker root
    (`/srv/opentallas/tools/docker`).
  - `/srv/opentallas-scratch` ext4 on `nvme3n1`: 2.9 T, 1.9 T free.
- **Network:** `bond0` 5.199.165.104/26; private VLAN `bond0.1667` **10.195.64.2/24** (EPYC1-EPYC2 private link).
  Exports `/srv/opentallas-scratch` and `/srv/opentallas/scratch-overflow` over NFSv4 to EPYC2.
- **OS:** Ubuntu 26.04.1 LTS, kernel 7.0.0-34-generic; Docker 29.1.3.
- **hosts.json:** `base /srv/opentallas-scratch/claude/closure-loop`; caps verilator, yosys, iverilog, orfs;
  `cores 128`, `max_job_threads 128`, `ram_gb 1133`, `max_job_ram_gb 1076`; `min_free_disk_gb 200`,
  `disk_roots {"/": 100}`.

### ot-epyc2 (EPYC2)

- **Role:** closure-loop host.
- **Provider:** Cherry Servers, Singapore, server 1020904 `climbing-locust`, same plan (20 TB bandwidth), active
  since 2026-10-05.
- **Hardware:** AMD EPYC 9575F, 1 socket, 64 cores / 128 threads; 1,133 GiB RAM.
- **Disks:** 2x Micron 894 G NVMe (md RAID, root) + 2x Solidigm 2.9 T NVMe.
  - `/` ext4 on `md0`: 879 G, 817 G free. `/srv/opentallas` (including the docker root
    `/srv/opentallas/tools/docker`) is on this root filesystem.
  - `/srv/opentallas-data` ext4 on `nvme2n1`: 2.9 T, 2.9 T free (new loop runs since 2026-10-07 23:10).
  - `/srv/opentallas-scratch2` ext4 on `nvme3n1`: 2.9 T, 1.2 T free (older running jobs).
  - NFSv4 from EPYC1 over the private link: `10.195.64.2:/srv/opentallas-scratch` on `/mnt/epyc1-scratch`, and
    `10.195.64.2:/srv/opentallas/scratch-overflow` on `/srv/opentallas/scratch-overflow`.
- **Network:** `bond0` 5.199.165.105/26; private VLAN `bond0.1667` **10.195.64.42/24**; 10.195.64.2 answers ping.
- **OS:** Ubuntu 26.04.1 LTS, kernel 7.0.0-34-generic; Docker 29.1.3.
- **hosts.json:** `base /srv/opentallas-data/claude/closure-loop`; caps verilator, yosys, iverilog, orfs;
  `cores 128`, `max_job_threads 128`, `ram_gb 1133`, `max_job_ram_gb 1076`; `min_free_disk_gb 200`,
  `disk_roots {"/": 100, "/srv/opentallas-scratch2": 100}`.

### ot-pve1 (PVE1)

- **Role:** closure-loop host for ORFS/docker stages only (caps `[orfs]`).
- **Provider / access:** a Proxmox-hosted VM at private address 10.77.1.10, reached through the jump host
  `root@bsql-host1.01.me` (ssh `ProxyJump`).
- **State at probe:** **unreachable.** The jump host accepted the connection, but forwarding to 10.77.1.10 failed
  with "No route to host" on two attempts. CPU model, disks, OS and ORFS digest were therefore not measured;
  the figures below come from hosts.json and the 2026-10-03 fleet note.
- **Last known:** 28 cores, about 235 GiB RAM (hosts.json `ram_gb 235`).
- **hosts.json:** `base /srv/opentallas-scratch/claude/closure-loop`; caps `[orfs]`; `cores 28`, `max_job_threads 28`,
  `max_job_ram_gb 223`, `min_free_ram_gb 16`; `min_free_disk_gb 100`, `disk_roots {"/": 100}`.

### ot-agidock128 (AGIdock)

- **Role:** closure-loop host with little RAM (last in preference order).
- **Provider:** AGIdock KVM virtual machine (QEMU devices; guest hostname `vm-xry57mhfyn`), public IP. The
  2026-10-03 fleet note places it on PVE1's physical host; it answered while PVE1 did not.
- **Hardware:** AMD EPYC 7B13, 64 vCPUs (1 socket, 64 cores, 1 thread per core); 125 GiB RAM. Despite the alias,
  it is not a 128-core machine.
- **Disks:** one 1 T QEMU virtual disk; `/` ext4 on `sda1`: 993 G, 817 G free. Docker root `/var/lib/docker`.
- **Network:** `eth0` 155.103.253.226/24. No NFS mounts.
- **OS:** Ubuntu 26.04.1 LTS, kernel 7.0.0-28-generic; Docker 29.1.3. An older image is kept as
  `openroad/orfs:asap7lock-agidock-old-826792fc`.
- **hosts.json:** `base /srv/opentallas-scratch/claude/closure-loop`; caps verilator, yosys, iverilog, orfs;
  `cores 64`, `max_job_threads 64`, `ram_gb 125`, `max_job_ram_gb 110`; `min_free_ram_gb 2` (the 2 GB margin),
  `reserve_ram_gb 0`; `min_free_disk_gb 0` (disk floor removed 2026-10-07).

### EPYC4 (provisioning, not contacted)

- Cherry Servers server **1025189**, hostname `regular-crane`, region Tokyo (Japan), plan "AMD EPYC 9575F"
  (1152 GB DDR5 ECC, 2x NVMe 1 TB + 2x NVMe 3 TB, 10 Gbps NIC, 20 TB bandwidth).
- API state at the probe: `state provisioning`, `status deploying`. Public 109.109.165.197, private 10.200.192.18.
- No ssh alias or hosts.json entry yet. The onboarding kit (onboarding script, hosts.json entry, smoke job) is
  staged outside the repository and waits for the alias and access.

## Closure-loop admission rules (hosts.json)

- **Preference order:** EPYC3 > EPYC1 > EPYC2 > PVE1 > AGIdock, then localhost. A job's `hosts` list is a
  preference; host choice scores free cores and free RAM.
- **Remote hosts are admitted on memory only** (OWNER 2026-10-07 20:10): there is no CPU/load check, and `cap`
  (round(1.1 x cores)) is informational. A job is admitted while measured MemAvailable minus the peaks of the
  loop's own launches in the last 10 minutes is at least job peak + max(5% host RAM, 32 GB, `min_free_ram_gb`).
  AGIdock's floor is 2 GB, PVE1's 16 GB.
- **Localhost guard:** at most 96 loop threads in total (`max_loop_threads`), at most 16 threads per job,
  MemAvailable at least 16 GB after the job's peak, jobs up to 120 GB.
- **Disk floors:** admission refuses while the run root (`base`) is below `min_free_disk_gb` or any `disk_roots`
  path is below its floor: EPYC1-3 200 GB on the base, 100 GB on `/` (EPYC3 also 200 GB on
  `/srv/opentallas-scratch`, EPYC2 100 GB on `/srv/opentallas-scratch2`); PVE1 100 GB; localhost 150 GB;
  AGIdock none.
- **Caps:** a stage's tool needs (bench: verilator + iverilog + yosys; calibrate/route/signoff/summary: orfs) must
  be a subset of the host's caps, so localhost and PVE1 take ORFS stages only.

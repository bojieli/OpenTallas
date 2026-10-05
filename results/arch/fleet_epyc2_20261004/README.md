# ot-epyc2 bring-up (2026-10-04)

`ot-epyc2` (5.199.165.105, private VLAN 10.195.64.42, hostname
`climbing-locust`) is a functional twin of `ot-epyc1tb`. It has 128 threads,
1.1 TB RAM, Ubuntu 26.04.1, and 824 GB free on `/` (a software RAID1 `md0`;
there is no separate scratch NVMe). The two hosts share a VLAN with 0.1 ms
RTT, and a netcat transfer between them ran at about 1.1 GB/s. Credentials and
SSH configuration were not changed.

## What was installed

| Item | ot-epyc2 state | Parity check |
|---|---|---|
| apt sources | `ubuntu.sources` replaced by EPYC's (archive + security); the provider mirror copy is kept as `ubuntu.sources.provider-backup`. The provider mirror was stale, so `zlib1g-dev` and `python3-venv` would not install from it. | same files on both hosts |
| apt packages | the full manually installed package set from EPYC, plus ccache, pigz, time, nfs-common and nvme-cli | `comm` of installed packages: nothing that EPYC has is missing |
| compilers | gcc/g++ 15.2.0-16ubuntu1 | same |
| docker | docker.io 29.1.3-0ubuntu4.1 with `data-root` `/srv/opentallas/tools/docker`; ubuntu is in the `docker` group | same daemon.json |
| ORFS image | `openroad/orfs:asap7lock` and `:latest`, id `sha256:16470cea1d34…`, sent with `docker save` and `docker load` over the VLAN | same image id |
| user tools | `~/.local/opentallas-tools` (verilator-5.050, yosys-0.68, opensta, cudd), `~/.local/opentallas-pdk-asap7`, `~/.local/bin/{openroad,uv,uvx,env,python3.10}`, uv cpython 3.10, `~/.opentallas-env` (sourced from `~/.profile`) | login PATH resolves the same binaries |
| python | `/srv/opentallas/tools/python310` venv (141 site-packages), `qwen-canonical-runtime-env/-wheels`; system python3 3.14.3 with numpy 2.3.5 | same site-packages listing (md5) |
| timezone | America/Los_Angeles | same |

## Scratch, admission and repository

- `/srv/opentallas-scratch` is owned by ubuntu and contains `claude/`, `codex/`,
  `jobs/` and `tmp/` (`tmp/` is `TMPDIR`). `admit.sh` and `admit_core.py` are
  byte-identical copies of EPYC's (md5 `c48f4a7a…` and `128d1ca0…`), so the
  reserve is the same 100 GiB plus the 180 s ramp. `admit.recent.json` starts
  as `[]`.
- `/srv/opentallas/repos/OpenTallas-git` is a copy of EPYC's mirror. Its stale
  worktree records were pruned, `origin` points to the same GitHub remote, and
  `main` was fast-forwarded to `c8d7ab368` (an HTTPS fetch from GitHub worked).

## Shared inputs: a read-only NFS mount

- **EPYC (server).** The only new things are the `nfs-kernel-server` package,
  `/etc/exports` and `/etc/nfs.conf.d/opentallas.conf`. The export is
  `/srv/opentallas-scratch 10.195.64.42(ro,sync,no_subtree_check,root_squash)`.
  The NFS service is NFSv4 only (`vers3=n`, `udp=n`) and listens only on the
  VLAN address `10.195.64.2:2049`. rpcbind is masked, so nothing listens on the
  public interface. No data on EPYC was modified.
- **ot-epyc2 (client).** The `/etc/fstab` entry is
  `10.195.64.2:/srv/opentallas-scratch /mnt/epyc1-scratch nfs4 ro,nofail,_netdev,noatime,hard,x-systemd.automount`.
  A write attempt returns "Read-only file system", and a sequential read ran at
  about 950 MB/s. rpcbind is masked here too.
- **Fallback if NFS is down.** Pull inputs over the VLAN with a pipe. On
  ot-epyc2, run `nc -l 10.195.64.42 PORT | zstd -d | tar -C / -xpf -`. On EPYC,
  run `tar -C / -cf - srv/opentallas-scratch/<path> | zstd -T16 | nc -N 10.195.64.42 PORT`.
  EPYC has no SSH route to ot-epyc2, and none was added.

## Parity check: same commit, same job, both hosts

`parity.sh` (in `/srv/opentallas-scratch/claude/fleet-epyc2/` on both hosts)
was run through `admit.sh 8` from a detached worktree of `9d7076e66`.

1. **Verilator bench.** Verilator 5.050 built `tb_hdc_mul_equiv` (the
   `ot_hdc_fp32_mul_pipe` and BF16-multiplier equivalence bench) and ran it with
   `+N=2000000`. Both hosts printed `MULEQ checked=2000000 mismatches=0`,
   `BMULEQ checked=1649665 faulted=350335 mismatches=0` and `PASS`.
2. **ORFS screen.** `tools/run_abi3_physical.py` ran `--stages synth,sta,pnr`
   on `ot_hdc_fp32_mul_pipe` (ASAP7, TT, 0.92 ns, `OT_ORFS_NUM_CORES=8`).
   Of the 424 fields in `physical.json`, only 7 differ: three timestamps,
   elapsed time, the GDS and SPEF hashes (their headers embed timestamps) and a
   2-byte change in the size of `metadata.json` (the elapsed time). Every
   metric matches:

   | Metric | Value on both hosts |
   |---|---|
   | Synthesis | 4,632 cells, 615.439 µm² |
   | Prelayout STA setup WNS | −365.28 ps |
   | Post-route setup WNS / TNS | +14.72 ps / 0 |
   | Post-route hold WNS | +38.80 ps |
   | Route DRC errors | 0 |
   | Instances | 20,580 |
   | Routed wirelength | 22,254 µm |
   | Vias | 53,098 |
   | ORFS fmax | 1,104.64 MHz |

   The overall status is `not_met` on both hosts, for the same prelayout-STA
   reason.

Wall time on ot-epyc2 (idle) was 85.6 s for ORFS and 1.9 s for the Verilator
build. On ot-epyc1tb (CPU-saturated) it was 272.9 s and 4.0 s.

## Fleet registration

- **Monitor.** `ot-epyc2` was added to `HOSTS` in
  `/home/ubuntu/opentallas-monitor/collect.py`; the previous copy is in
  `legacy/`. The roster line in `OPERATIONS.txt` was updated and the collector
  restarted; all five hosts report ok.
- **Agent notes.** The host is noted in
  `/tmp/claude-review-20261003/FLEET_AND_FLOW.md` and
  `CLAUDE_AGENT_FOOTER.txt`, and three lines were posted in `codex_notes.txt`.

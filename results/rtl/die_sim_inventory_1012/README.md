# Die-level / end-to-end simulation inventory (2026-10-12)

Owner ask (10-11 late): use idle EPYC capacity for die-level verification of the targets closest to closing.
**Scope v2 (coordinator, 10-12 00:00, owner rule "simulate the minimum component"):** whole-die and full-token RTL runs
are *not* required for closure and were **not** launched (a first 40-layer HBM matrix was killed in its export phase,
before any simulation). Only the **required per-layer composition runs at target context** are run — one layer per
layer type plus the head, Qwen3-8B at P 8,191 and DeepSeek-V4.1 at P 1,048,575, on the smallest vehicle that contains
the mechanism — and only where no committed pass exists on current main RTL.

Main at launch: `ca7ca4fff`. Simulator: Verilator 5.050 (`~/.local/opentallas-tools/verilator-5.050`).
Every job runs in a memory-capped cgroup (`systemd-run --user --scope -p MemoryMax=…`, the same cap `ot-heavy` applies,
without its 8-slot limit: memory is the only admission limit) and under `timeout` (builds <= 4 h, sims <= 6 h).

## 1. Inventory

"Current main?" = compiles the RTL now on main, and the last pass was taken on RTL equal to main's for every file it reads.

### Qwen ROM die (r22ko4) + KV die

| Bench | Covers | Current main? | Runtime / mem | Last committed pass |
|---|---|---|---|---|
| `tools/qwen_missing/partition_token.py` (split partition of the W12 stream4 ROM die: sequencer / tree top / SU across the die-master boundary, DCU/DUC stations, compensation, SU ML; kv-die ME stations / GQ knobs) — stages L0, **L3** (L0-L2 chain, current K/V checked), head, full | ROM-die datapath + split seams at P8191 | compiles main; last pass on src `4dc3e0062`, not main | L3 ~6,400 s, head ~1 h, 16 threads, ~14 GB | `results/rtl/token_exact_20261009/qwen_rom/L3_s22ml7.json` (L3 17,120 cyc exact; COMP 0 negative FAILS), `heads/qwen_rom_head_s22ml7.json` — `f87593cfb` 10-09 |
| `tools/exactness/qwen_rom_fulltoken.py` (base W12 die, 36 layers + head) | whole token, pre-split die | compiles main | full 11 h 06 min, 14 GB | `results/rtl/qwen_plain_ar_stream4_P8191_20261005/terminal.json` — `73a173f6e` 10-05 (whole token: not required, not run) |
| `tools/qwen_kv_die/bench_gate.sh pos|neg` (`rtl/test/qwen_kv_die/ot_qkvd_layer_tb.sv`) | ROM end <-> UCIe d2d <-> KV die, near-HBM attention stack H + hub, posted KV rows; ctx 8192/8191/4097/2048/129/1 | **yes** (no RTL change since) | tens of minutes, < 2 GB | `results/rtl/tput_map_1011/qwen_kv_die/record.json` (src `6c4677c53`) — `2269e5375` 10-11; mutant `-GMUT=2` |
| `rtl/test/qwen_kv_die/kv_wq_bench.sh` | KV write path (wq dist/tiles, CDC, SECDED), 36 layers x 4 rows | yes | minutes | same record; `results/arch/qwen_kv_die_20261009/kv_write_bench.json` `f7e45bead` 10-09 |
| `rtl/test/qwen_band_integrate/run_spine_band.sh` | `ot_qfd_spine_band` (tree top + 6 band lanes + res_ser + banked VM) vs monolithic spine | compiles main; RTL changed 10-11 after the pass | 435 s, 116 MB | `results/rtl/qwen_band_integrate_20261008/record.json` `60ebc5345` 10-08 |
| `rtl/test/qwen_lane_band/run_band_lanes.sh` | `ot_qfd_band_lanes/upper` vs NL spine lanes | compiles main; 3 RTL commits since | minutes | `results/rtl/qwen_lane_band_20261008/record.json` `4c4406252` 10-08 |
| `rtl/test/tb_qwen_rom_tile_die.sv`, `tb_qwen_die_{hub,hub_fr,hub_identity,cdc_ch,station,link_*}.sv` | tile-die glue, die hub / CDC / link components | yes | seconds | `results/rtl/qwen_elements_final_20261007/`, `qwen_contracts_20261007/`, `qwen_link_forwarded_20261007/` |
| `rtl/test/qwen_decode_pipe_20261004`, `tb_hdc_qwen_*` | decode pipe snapshot; old HDC reduced vehicle | no (frozen / old core) | — | not adoption evidence |

r22ko4-specific die top (`qfd_tile_nk` x 1,536 + hardened clusters): **lint only**
(`results/arch/qwen_kv_die_20261009/rom_r22ko4_lint.json`); no simulation vehicle instantiates the r22ko4 die top.

### DeepSeek ROM S81 die

| Bench | Covers | Current main? | Runtime / mem | Last committed pass |
|---|---|---|---|---|
| `tools/dsrom_mtp_rom_bench.py run` (23 cases, `rtl/dsrom_sys/mtp/tb/tb_mtp_rom_*`) | MTP control plane: WFC pkg ctrl + `dsfd_wfc_lnk/tok/vmx` + `dsfd_mtp_seq(_rtt)` + `dsfd_vm/cap_mtp_ep`; stage pipeline / head / VM / S0 core are delay models | compiles main (Icarus) | s-min per case, < 1 GB | `results/rtl/dsrom_mtp_rom_20261008/bench_summary.json` 23/23 — `0dbdd6248` 10-08; mutants `OT_MTPSEQ_MUT_*`, `OT_WFC*_MUT_*` |
| `tools/dsrom_wfc_kit_bench.py` | WFC kit tokpipe src/stg + tok_hard + lnk + vmx + seq_rtt at die ports | compiles main | minutes | `results/rtl/dsrom_wfc_integration_20261010/record.json` (10 pass / 5 neg, `integration_qualified: false`) — `121c00eb2` 10-10 |
| `rtl/dsrom_sys/s81_ph/test/run_coll_sys.sh` | `dsfd_sp_collective` (core, rstc, link_ep/gbx, rfifo) + link chan | any source root | minutes, < 2 GB | `results/rtl/s81_ph_20261006/collective/bench_record.json` — `e69281e92` 10-06 |
| `tools/s81_ph/capt_bench.sh` | `dsfd_sp_gather` -> `dsfd_sp_capture` (8 groups) vs W10 roots | compiles main | n/r | `results/rtl/s81_ph_20261006/capture/bench_tiles/bench_record.json` 9/9 — `1df7cf9a9` 10-06 |
| `tools/rtl_dsrom_engram_lookup_campaign.py`, `tools/engram_window_gate.py` | engram lookup (idwin/lookup/rowsink); hop_tx + pkg_ctrl window | compiles main | n/r | `results/rtl/engram_lookup_recovered_07189f858/campaign.json`; window gate record **not committed** |
| `tools/dsrom_wfc_token_hard_gate.py`, `tools/mtp_ring_dyn_vehicle.py` | WFC token store; ring-DYN vehicle | compiles main | seconds / ~428k cyc | `dsrom_wfc_token_hard_20261009/…/summary.json` `650398051`; `mtp_ring_dyn_20261009/four_campaign_gate.json` `3dea693b1` |
| `tools/dsrom_s81_fulldie.py`, `tools/s81_die_view_ports.py` | **physical only** (plan/GRT/IR, ports/LEF) | — | — | no simulation |

### HBM accelerator die (r25gq / hgi)

| Bench | Covers | Current main? | Runtime / mem | Last committed pass |
|---|---|---|---|---|
| `tools/hgi_e2e/run.py` + `export.py` (`rtl/hbm_accel/generic/e2e/tb_hgi_e2e.sv`): the die's CP/sequencer/loader with `--real <units>` RTL, others replay stubs; `--real idxn` = native IDX.INDEX through the die selector, 4 stack scorers, 4 svc IKS stripes + DRAM model | per-layer native die e2e, DS 1M rank 0/96 and Qwen P8191 TP4 | compiles main; **every pass predates main's harness** (tb/slots/dpi/cp_die/run/export +121/-43 since, VM_TUNIT model `cac82043f`) | idxn ~30-36 min/layer, 550 MB, 1 thread; head coll 0.25 s | `results/rtl/hgi_e2e_native_20261011/` idxn DS L2/L20/L24 PASS + L24 `IDX_MUT=2` FAIL (src `9d5abe71a`, `3e986a14e` 10-11); ds_head COLL.ARGMAX_MERGE PASS + `OT_COLL_AMX_MUT_MIN` FAIL (src `1113269a1`, `4c9eeb19f`) |
| same, `--real dma --g DMA_VR2=1 --g DMA_KVW=1` / `--g VM_TUNIT` | DMA KVW, VM tunit | older | — | `hgi_dma_kvw_die_20261011` (L0 PASS; L2 verdict FAIL wr_quiet), `hgi_vm_tunit_die_20261011` (`97c0a1e63`) |
| same, all real units | DS L0 all-real; Qwen L0 P8191 coll/dma/fused/sfu/su | old (`4bc04ba93`, `18685d362`) | — | `hgi_e2e_20261010/runs/ds_L0_g24_allreal_4bc04ba93` 263,722 cyc; `hgi_e2e_20261009/STATUS.md` Qwen L0 216,474 cyc |
| `adapters/tb/tb_hgi_sm_e2e.sv`, `tb_hgi_su_die.sv`, `peers/tb_hgi_mover_kport.sv`, `collective/tb_hgi_coll_pipe.sv`, `tu/lk_ep_20261010/tb_hgi_coll_lk.sv` | unit-at-die-boundary benches | per element | — | element records |

## 2. Required per-layer composition runs: status

DS-V4.1 layer types (`compiler/models/deepseek-v4.1-flash/inference_config.json`): L0 ratio 0; L1 ratio 0 + engram;
L2 ratio 2 kv+index source; L3 ratio 2 plain; L14 ratio 2 kv/index source + engram; L20 ratio 1 kv/index/candidate
source; L21 ratio 1 plain; L24 ratio 1 index source; L37 ratio 1 DSpark/MTP target; head (L39 + LM head).
Qwen3-8B: one decoder layer type (L0 with real history; L1-L2 chain) + head.

| Target | Required run | Committed pass on current main? | Action |
|---|---|---|---|
| Qwen ROM die (split partition) | L0-L2 chain @ P8191 + COMP 0 negative | no (src `4dc3e0062`) | **launched** (Q1, Q2) |
| Qwen ROM die | LM head @ P8191 | no (src `f6e9a6e92`) | **launched** (Q3) |
| Qwen KV die | layer step @ ctx 8192 (+ mutant) | **yes** (`2269e5375`) | none |
| Qwen ROM die r22ko4 top (`qfd_tile_nk` array + hardened clusters) | layer @ P8191 through the r22ko4 seams | **missing — no vehicle** | plan below |
| S81 (MTP, VM, collective, engram, PQC) | one layer per type + head @ 1M on the S81 die | **missing — no vehicle**; element benches only (PQC: element benches exist, see section 4) | plan below |
| HBM die (DS) | L0, L1, L2, L3, L14, L20, L21, L24, L37 @ 1M (+ IDX / DMA mutants) | no (harness changed since `9d5abe71a`) | **launched** (H1-H4) |
| HBM die (DS) | head (L39 + LM head, COLL.ARGMAX_MERGE) + mutant | no (`coll_ep` changed since `1113269a1`) | **launched** (H5) |
| HBM die (Qwen) | L0 @ P8191 TP4 + DMA mutant | no (`18685d362`) | **launched** (H6) |
| HBM die (Qwen) | head | missing: `export qwen` has no head vehicle (only DFlash tiny ARGMAX_MERGE) | add `--head` to `export qwen` (~0.5 day) |

## 3. Launched runs

Source @ `ca7ca4fff`: EPYC1 detached worktree `/srv/opentallas-scratch/claude/diesim-1012/src` (of `~/OpenTallas` there);
EPYC3 `git archive` of rtl/tools/compiler/physical views at the same path. The DS 1M refs
(`~/w17work/ref/ctx1048576_seed20260930`) and the Qwen P8191 CPU golds exist only on EPYC1, so exports and the Qwen ROM
runs are on **EPYC1**; the HBM builds (Verilator peaks ~60+ GB each) and sims are on **EPYC3**. EPYC3 cannot ssh to
EPYC1, so a light localhost relay (`hbm_relay.sh`, nohup, 12 h cap) copies the vectors once the exports finish.

**HBM** (status `/srv/opentallas-scratch/claude/diesim-1012/hbm/STATUS.log` on each host; per-run
`out/<config>__<vehicle>/{run.log,report.json}` on EPYC3). Scripts here: `hbm_exp.sh`, `hbm_build_run.sh`, `hbm_relay.sh`.
1. EPYC1 exports (5 parallel, 80 GB cap): `python -m hgi_e2e.export ds --refs … --layer N --iks` for N in 0 1 2 3 14 20 21 24 37,
   `export ds --layer 39 --head`, `export qwen --snapshot … --layer 0 --position 8191`; then `run.py prep`.
2. EPYC3 builds (3 parallel, 150 GB cap, `run.py script` then the build half of the script):
   `idxn` (`--real idxn`), `idxnmut` (`--g IDX_MUT=2`), `dsall` (`--real coll,dma,fused,idxn,quant,sfu,su` + SU_N 512 / SU_M 128 /
   SU_LV 6 / SU_WIDE 1 / FUSED_UWIDE 1 / FUSED_UN 64 / FUSED_UM 16), `dsallmut` (+`DMA_MUT=5`), `coll`, `collmut`
   (`+define+OT_COLL_AMX_MUT_MIN`), `qall` (`--real coll,dma,fused,sfu,su` + same SU/FUSED), `qallmut` (+`DMA_MUT=5`).
3. EPYC3 runs (24 parallel, 4 GB cap, 6 h timeout, 1 sim thread each):
   - H1 `idxn` x {L0 L1 L2 L3 L14 L20 L21 L24 L37}; H2 `dsall` x same 9;
   - H3 `idxnmut` x L24 (must FAIL); H4 `dsallmut` x L20 (must FAIL);
   - H5 `coll` / `collmut` x ds_head; H6 `qall` / `qallmut` x qwen_L0.

**Qwen ROM** — driver `/srv/opentallas-scratch/claude/diesim-1012/qwen/drive.sh`, status `…/qwen/STATUS.log` (copy: `qwen_drive.sh` here).
Fixtures: `QWEN_FX_HISTORY=/srv/opentallas-scratch/claude/token-exact/fx/history`,
`QWEN_FX_GOLD=…/token-exact/gold/tp4_hs/P8191`, `QWEN_FX_REF=…/token-exact/gold/tp4_hs/oracle.json`.
- Builds: `partition_token.py build --variant part --dcu 2 --duc 2 --su-ml 7 --comp {1,0}` (128 GB cap).
- Q1 `run … --comp 1 --stages L3 --threads 16` (pass = exact, 12/12 layer X + current K/V);
  Q2 `run … --comp 0 --stages L3` (must FAIL); Q3 `run … --comp 1 --stages head` (pass = token 24, logit 0x41962749, 4 ranks).

Launched 2026-10-12: Qwen 00:05 PDT (EPYC1); HBM exports 00:20 PDT (EPYC1), builds ~00:25 PDT (EPYC3).
Expected finish: Qwen ~03:30 PDT (builds ~1 h, L3 ~1.8 h, head in parallel; 4 h build / 6 h run caps => latest 10:05).
HBM ~04:00-06:00 PDT (exports ~0.5-1 h, builds 3 waves ~0.5-1 h each, idxn ~35 min/layer, all-real ~1-3 h;
6 h run cap => latest ~11:00 PDT). No job can run past ~11 h.
A first launch (00:00) used a 40-layer HBM matrix and too-small (64 GB) build caps; it was killed (process groups and all
children) in its export/build phase before any simulation, per the scope change.

## 4. Missing vehicles: smallest plans (not built here)

**S81 die (MTP, VM, collective, engram, PQC).** No bench composes two S81 elements beyond the MTP/WFC control plane.
Smallest vehicle: one S81 layer at P 1,048,575 on rank 0 — `tb_s81_layer` instantiating the real `dsfd_sp_gather` ->
`dsfd_sp_capture`, `dsfd_sp_collective` (2 ranks looped through `ot_dsrom_link_chan`), `dsfd_vm_fe` + one
`dsfd_vm_bgq28` bank group, `dsfd_engram_lkp` (L1/L14 only), with the ROM stage datapath and HBM KV as replay stubs fed
by the HGI native exporter's per-layer vectors (`export ds --layer N`, which already carries rank-0 records at 1M);
MTP via the existing `tb_mtp_rom_s0_rtt` sequencer hooked to the same VM. Layer types: L0, L1, L2, L20, L37 + head.
PQC (corrected 2026-10-12, s81lv): the closed PQC elements have bit-exact benches with failing mutants on main -- `ot_v41_pqc_spine_screen` (9 tiles `ot_pqc_t_*` + `ot_dsrom_aq12t`) via `tools/s81/pqc_xrv_bench.py` (golden `tools/hdc_golden_v41`, mutants `OT_PQC_MUT_{QB,IX,RET,BC,CTL}`), `ot_dsrom_aq12t` via `physical/s81_pq_tiles/bench_aq12t.sh` (`OT_AQ12T_MUT_RA`), `ot_s81_pq_ret_root_cam_p` via `tools/s81/pq_root_cam_p_gate.py` (`wrong_sibling`). Gap: tiles prom/srom/xin have no in-tile mutant. The layer vehicle: `results/rtl/s81_layer_vehicle_1012/SPEC.md` (a die-layer bench existed unmerged on claude/el1011-s81dbench).
Estimate: ~3-4 agent-days (tb + replay adapter 1.5 d, vectors/golden binding 1 d, per-type runs + mutants 1 d; PQC bench +0.5 d).

**Qwen r22ko4 die seams.** The split-partition vehicle (Q1-Q3) covers the sequencer/tree/SU split and stations but not
the r22ko4 hierarchy (`qfd_tile_nk` replication, io_collective cluster, tile pin flops `TOREG`, VM tile `XVM 25`/`VL 15`
latencies posted 10-11). Smallest vehicle: `partition_token.py` variant `r22` that wraps one `qfd_tile_nk` (+ its
leaves) and the io_collective cluster RTL in place of the corresponding W12 slices, with the contract-v4 latency deltas
as station knobs, run at L3 and head. Estimate: ~2 agent-days.

## 5. Results and re-runs (2026-10-12 02:45 PDT, diesim-1012 relaunch)

- **Qwen ROM split partition @ `ca7ca4fff`: all ok** — Q1 L3 exact (17,120 cyc, 0 layer-X / 0 K/V mismatches, 3,868 s),
  Q2 COMP 0 FAIL as required (49,152 X / 6,046 K/V mismatches), Q3 head exact (token 24, logit 0x41962749, 3,055 cyc).
  Record: `results/rtl/comp_regress/ca7ca4fff/summary_epyc1tb.json`. Main has since changed `ot_qwen_w12_matvec`,
  `ot_qwen_me_array_w12`, `ot_qwen_rom_tile_w12` (in the builds' `__ver.d`), so `comp_regress` re-runs Q1-Q3 at `de098fdb4`.
- **HBM: no simulation ran.** Exports 11/11 ok (EPYC1). On EPYC3 the all-real builds `dsall` / `dsallmut` died rc=143:
  root cause = the 150 GB cgroup cap — the kernel OOM-killed verilator inside the scope and systemd's OOMPolicy=stop
  SIGTERMed the rest (journal `oom-kill` 07:12-07:16 UTC); `idxn` alone allocates 124 GB. EPYC3 is draining, so its
  pipeline was stopped. `ot_hgi_seq.sv` (+1,294/-602) and `ot_hgi_cp*.sv` changed on main since `ca7ca4fff`, so every
  HBM binary is rebuilt at current main via `tools/comp_regress` (all-real cap 420 GB): EPYC1 `qall/qallmut/coll/collmut`
  (Qwen L0, **Qwen head**, DS head), EPYC4 `dsall/dsallmut/idxn/idxnmut` (DS L0..L37 @1M).
- **Qwen head on HBM added**: `export qwen --head` (final norm -> head MATVEC -> SU row scale -> ARGMAX.LOCAL ->
  COLL.ARGMAX_MERGE -> CTL.END); exporter golden check vs `qwen_r25` head argmax on all 4 ranks: exact (6 records, S2 77,388).
  Runs: `hgi_qall__qwen_head`, `hgi_coll__qwen_head`, mutant `hgi_collmut__qwen_head` (must FAIL).

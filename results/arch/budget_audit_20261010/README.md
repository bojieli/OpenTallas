# Top-down throughput budget audit, 2026-10-10

This audit covers three targets:
- the generic HBM die (HGI-1, for DeepSeek and Qwen);
- the Qwen ROM die with its KV die;
- the DeepSeek S81 ROM.

For every unit, interface and memory port we compare two numbers:
- **Required:** the minimum sustained throughput the unit needs on the token's critical path at the designed tok/s, allowing for whatever overlap the compiled program permits.
- **Designed / measured:** what the RTL or spec provides, or what an RTL bench measured.

`table.json` holds all 35 rows. Each row has: required, designed, measured, margin, whether it is critical, the tok/s if this unit alone runs as designed, the flag, whether it is already known, the owner stream and the files it cites.

**Flags:**

| Flag | Meaning |
|---|---|
| INFEASIBLE | The structure cannot reach the target |
| GAP | Margin < 1.0 |
| THIN | Margin 1.0–1.1 |
| UNKNOWN | No designed or measured number exists |

**HBM bandwidth rule.** No fixed percentage of HBM peak is assumed (owner rule, 10-10 06:58). A weight or KV path is flagged only if it is short of its overlap-aware minimum.

**Target rates (tok/s):**
- HBM DS AR: 2,208.1 (native) and 1,747.5 (approved gather path)
- HBM DS MTP: 3,344.8
- HBM Qwen AR: 953.8
- HBM Qwen DFlash b16: 1,791.8
- Qwen ROM: 4,810.9
- DS ROM: AR 1,447.7 and MTP 4,238.4

All are at 1.2 GHz; the sources are in `table.json` under `targets`.

**Method.** Every token is a dependency chain: in S0, `idle_true_dep` dominates for every unit. Any unit that runs is therefore on the critical path, and its required service is the per-record cycle count the target schedule allots it.

"tok/s if as designed" changes one unit at a time and leaves everything else at budget. This takes no overlap credit, so it is an order-of-magnitude ranking, not a composed rate.

## New gaps, ranked by tok/s impact (single-unit what-if)

| # | Row | Target | Margin | tok/s as designed (target) | Owner | What |
|---:|---|---|---:|---:|---|---|
| 1 | `dsrom_mtp_draft_hw` | DS ROM MTP | 0 | 1,447.7 (4,238.4) | bf-mtp | The DSpark draft stages and seed run on dies outside the S81 binding (`mtp.*` weights are unowned). The WFC and accept unit are not integrated. The NV5 draft fails its SS screen. The MTP headline therefore has no hardware. |
| 2 | `ds_sm_xload_fp8_fp4_no_peer` | HBM DS | 0 | 0 (2,208.1) | hgi-1010 | `ot_hgi_sm_xload` refuses formats 1/2 (`ot_hgi_sm_xload.sv:13-14,139-140`). No HGI peer moves the QDQ output into the SM x store, so the DS SM records have no activation path. |
| 3 | `ds_att_row_format_over_peak` | HBM DS | 0.0006 | 26.9 (2,208.1) | hgi-1010 | The DS T640 ATT price over FP32 hd512 rows needs 3,866 B/cycle, which is above the die's 3,166.7 HBM peak (`ds_native.py:633-643`). The price itself is infeasible: store or gather the rows as packed FP8. |
| 4 | `ds_hc_mix_full` / `ds_hc_mix_rows_g22` | HBM DS | 0.008–0.012 | 1,028 on the G22 path (1,747.5) | hgi-1010 | HC stages h (20,480 FP32 words) through one VM packet client. Measured 6,051 cycles a record (`hc_unit_run.log` case 10) against 48 priced. |
| 5 | `ds_mtp_hc_verify` | HBM DS MTP | – | 1,141 (3,344.8) | bf-mtp | HC is npos 1, so each verify position runs as its own record (6 × 80). |
| 6 | `hbm_ds_cp_fetch` | HBM DS | 0.36 | 784 (2,208.1) | hgi-1010 | The record-ring fetch must sustain 0.867 B/cycle: 470,912 B of unrolled image per token. The svc native port allows one transaction per stack, length 1 (`ot_hbm_loader_service_boundary.sv:20-24`), which gives 32 B per round trip = 0.31 B/cycle. The native bursts (75b874a3f) are opt-in and not wired through `ot_hfd_loader_kport`. Tracked as F5(3) in the hgi-takeover log, but missing from the e2e sensitivity because the e2e harness uses the FPIPE model. The DS MTP program is the same class (`hbm_ds_mtp_cp_fetch`). |
| 7 | `hbm_att_unit_hbm_lane` | HBM Qwen | 0.0008 | 19 (953.8) | hgi-1010 | `ot_hgi_att_unit`, the "ATT unit die body", has one 32 B HBM lane with NOUT 8 and fetches rows serially (`:344-372`), about 913k cycles a record against 660.1 priced. The die must instead bind ATT records to the striped KV lines: about 10k sectors in flight per die. |
| 8 | `ds_mtp_idx_multiquery` | HBM DS MTP | – | 2,730 (3,344.8) | bf-mtp | 6 query frames serially on the single-PC key stream. Fixed by #12. |
| 9 | `dflash_sm_xload_p8` | HBM DFlash | 0.014 | 1,192 (1,791.8) | hgi-1010 | The P×K x-load is serial and single-buffered. |
| 10 | `hbm_dflash_cp_fetch` | HBM DFlash | 1.05 at RTT 104, 0.68 at RTT 160 | 1,223 (1,791.8) | hgi-1010 | 6 of the 9 verify loop bodies (24–40 KB) exceed the 8 KB ring and are re-fetched: 1.57 MB per step. |
| 11 | `qwen_att_vm_scores` | HBM Qwen | 0.033 | 446 (953.8) | hgi-1010 | ATT scores and probabilities go through one VM client with fewer than 4 outstanding. |
| 12 | `ds_idx_key_stream_one_pc` | HBM DS | 0.034 | 2,010 (2,208.1) | hbm-phys | Index-key reads use one PC (`IK_PC`, `ot_hbm_svc_core_native.sv:9-10`). Stripe them over 32 PCs. |
| 13 | `dflash_head_pub_stream` | HBM DFlash | 0.50 | 1,610 (1,791.8) | hgi-1010 | The multi-slot head STREAM moves 1 beat per edge with no back-pressure. |
| 14 | `qrom_ar_link_fec` | Qwen ROM | unknown | 4,676–4,488 (4,810.9) | qwen | 72 AR256s a token (30% of the token). No board-leg FEC term is visible in the measured AR; DS charges full RS. |
| 15 | `qrom_kvdie_hbm_model` | Qwen ROM | 0.89 (0.71 at min) | 4,691 (4,449 at worst) | qwen | The 1,814-cycle KV-die step was measured on an ideal HBM (750 B/cycle/stack, 16-cycle latency, no refresh). The same 4.19 MB sweep on the timed REFpb model delivers 0.80 of peak (min 0.64; `svc_kvs.json`). |
| 16 | `qwen_sm_xload_serial` | HBM Qwen | 0.11 | 853 (953.8) | hgi-1010 | x-load: measured 2,762 cycles a record, against 155 of priced overhead. |
| 17 | `hbm_ds_kvwb` / `hbm_qwen_dma_store` | HBM | 0.16 / 0.23 | 2,158 / 948 | hgi-1010 | KV write-back and store retire on write completion, not on acceptance (measured 6.3× and 4.3×). |
| 18 | `hbm_ds_window_rows_1m` | HBM DS | 1.0 (worse at max latency) | 2,184 | hgi-1010 | The window-row HBM fetch (146–224 cycles measured) does not fit in the 147-cycle ATT price. |
| 19 | `hbm_qwen_kv_read_8k` | HBM Qwen | 0.84 | 947 | hbm-phys / hgi-1010/f | Qwen ATT records are serial, so the KV stream needs 0.95 of peak. Measured 0.80. A real but small shortfall; cross-check against f's table. |

**UNKNOWN** (no number yet):
- `hbm_cg_wake`: SM/HC `cg_en` binding; wake at dispatch.
- `dsrom_cg_wake`: per-stage ICG wake on 120 stages.
- `ds_mtp_native_verify_program`: no compiled verify program.
- `dsrom_l20_cand_select`: still modelled.

## Already-known gaps, quantified on the same basis

| Gap | Row(s) | Figure |
|---|---|---|
| SU/SFU staging | `qwen_su_sfu`, `ds_fused_hc_pre_post` | Qwen 225; DS FUSED HC pre/post up to −2,078 tok/s single-unit |
| TOPK / QDQ | `ds_idx_topk`, `ds_qdq` | — |
| DMA load / svc width | `hbm_dma_load` | — |
| Qwen tree-top | `qrom_treetop` | 5,492.7 → 4,810.9 |
| S81 reach | — | — |
| BF full rate | — | — |
| coll_core split | — | — |
| Qwen SM INT8 issue | — | Zero headroom by construction; one-beat INT8 is the lever |

## Infeasible as designed (needs a structural change, not tuning)

1. **HBM DS (both paths):**
   - no FP8/FP4 x path into the SM (#2);
   - an ATT price above HBM peak for FP32 rows (#3);
   - HC/FUSED h staging through one VM client (#4);
   - the CP ring fetch through the one-sector svc native port (#6).
2. **HBM Qwen:** if `ot_hgi_att_unit` is the die ATT, its single lane with row-serial fetch (#7).
3. **DS ROM MTP:** the draft hardware is absent (#1).

One shared fix covers many rows: wide VM lanes (32 read and 32 write, one sector per lane per cycle, proposed by hgi-1010/b). If SM x-load, ATT scores and HC/FUSED staging become lane clients, it closes #4, #9, #11, #16 and the known SU/SFU gap. That is one owner decision.

## Rows that are OK

- **Bandwidth:**
  - Qwen SM weight stream: SM-issue bound, needs 0.775 of peak against the 0.862 bench proxy.
  - DS SM FP8 stream: 1.37.
  - DS index keys: 3.7.
- **Collectives:** all-reduce 1.10, group reduce 1.10.
- **CP:** Qwen fetch (the loop body replays from the ring); CP decode/dispatch (e2e DS L0 1.16× overall).
- **DS ROM:** KV at 1M (timed HBM, measured), hops and links with full FEC, Engram slack 2.6×.
- **Qwen ROM:** D2D link, attention step.
- **svc DMA strip / v2 widening:** not required. Under the new rule DMA→VM is not a weight/KV stream, and DMA costs only about 20 tok/s on DS and 2 on Qwen (e2e_calibration).

## Reproduce

The scripts are in `tools/budget_audit/`:
- `fetch_demand.py` runs the simulator ring rule on the Qwen and DFlash programs and writes `fetch_demand.json`.
- `hbm_datactl.py` and `rom.py` build the data/control and ROM rows.
- `assemble.py` merges them with the compute-unit fragment, `hbm_compute.json`.

The fragment paths point at the coordination folder `/home/ubuntu/claude-takeover-20261007/budget-audit-1010/`. The table is a snapshot; it is not a closed rate.

## Right-sizing the generic HBM die (owner follow-up)

Files:
- `rightsize.json`: the per-unit table;
- `rightsize_sweep.json`: the raw sweeps;
- `tools/budget_audit/rightsize_sweep.py`: the sweep script.

**Rule.** A unit's count is the minimum that keeps the designed tok/s within 1%. Each sweep varies one unit and holds everything else at budget, on the S2 schedule. Load/compute overlap is as the schedule models it. The generic die needs the larger of the two requirements, Qwen (TP4, 8K) or DS (TP96, 1M).

**Power basis.** Peak in-phase power from the floorplan tool: SM 5.48 W, attention tile 2.52 W, hub 1.05 W/mm². Today the die is 468.0 W against a 474.56 W limit.

| Unit | Today | Qwen needs | DS needs | Generic die | Set by | Area saved (mm²) | Peak W saved |
|---|---:|---:|---:|---:|---|---:|---:|
| SM | 32 | **32** (28 SMs: +10.6% cycles) | 28 (+0.7%; 24 SMs: +3.0%) | 32 | Qwen: SM-issue bound | 0 | 0 |
| Attention tiles | 64 | **52** (44 at the measured KV rate) | 32 (prices measured on NL 4 × S 8) | 52 | Qwen: GQA 25% lane use (G4: 36.9k tile cycles vs 47.7k KV stream at 64 tiles) | 28.9 | 30.3 |
| SU lanes | N1024 | 512 (+0.41%) | 512 (+0.05%) | 512 | Qwen | 7.8 | 8.2 |
| SFU | 1 | ½ width (+0.17%) | 0 | ½ width | Qwen GLU (2,160 cycles/token) | 4.4 | 4.6 |
| HC | 4 quarters | 0 | 4 | 4 | DS: 17% of the token, critical | 0 | 0 |
| Index score lanes | 64 keys/cycle | 0 | 36 (needs 30) | 36 | DS indexer | ≤ 9.0 | ≤ 9.4 |
| **Total** | | | | | | **≈ 50** | **≈ 52** |

Notes on the table:
- **SM.** DS per-die SM work is small, but cutting below 28 SMs still costs DS through the expert matvecs. Qwen sets the count at 32.
- **HC.** Keep all 4 quarters. The audit shows the HC RTL is already far below its price, so HC needs more effective throughput (wide VM lanes), not fewer quarters.
- **Index.** The saving is an upper bound. The 20.57 mm² figure covers the whole indexer, and only the score array shrinks.
- **Attention tiles.** Check the Qwen MTP/DFlash verify programs before cutting below 52. At p = 4 a verify pass fills all 16 head lanes.

**Reinvest option.** Qwen is SM-issue bound at 32 SMs. With 40 SMs its cycles drop 14.3%, from 953.8 to about 1,113 tok/s; DS is unchanged within 0.2%. Beyond 40, Qwen becomes HBM-bound: 48 SMs add only another 0.7%. The 8 extra SMs cost 36.5 mm² and 43.9 W. That is less than the ~50 mm² and ~52 W freed above, so the net is −13.6 mm² and −8.6 W, which keeps the die inside 474.56 W. This is an owner decision.

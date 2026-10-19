# HBM P-lane die: compiler timing model (MTP-MODEL, 10-18)

Design study outside the release closure (lane HBM-MTP). Tool `tools/hgi_sim/hbm_plane_model.py`; full record `run.json`, condensed `summary.json`.

Price basis: d4g plan (b) price of record: HBM-PRICE5 d4g_2ring_qbg (two rings + QBG, RTL1/2 ledger), S2 CP schedule per layer segment; option-B attention on the SM engines (measured spans).

Validation: P = 1 DS AR 1905.4 tok/s vs 1905.4 of record (0.0 %); Qwen AR 946.2 vs 946.2 (0.0 %); the d4g MTP design point re-priced through the same chain: 3258.7 vs 3258.7.

Stats: results/arch/hbm_mtp_next_1018/stats/summary.json. Area: results/arch/hbm_mtp_next_1018/area_composed.json.

## tok/s vs P

| P | +mm2 | DS AR | DS MTP (KV upper) | DS MTP kv-lower | DS MTP union p90 | DS users agg / per-user | Qwen AR | Qwen DFlash b16 pub 8.01 / meas 3.656 | Qwen b8 pub / meas | Qwen users agg / per-user |
|---:|---:|---:|---:|---:|---:|---|---:|---|---|---|
| 1 | 0.0 | 1905.4 | **1694.3** |  |  | 1905.4 / 1905.4 | 946.2 | 459.5 / 209.7 | 642.8 / 379.4 | 946.2 / 946.2 |
| 2 | 34.56 | 1905.4 | **3142.8** | 3288.8 | 3063.1 | 3060.3 / 1530.1 | 946.2 | 874.3 / 399.1 | 1211.7 / 715.1 | 1734.2 / 867.1 |
| 4 | 101.11 | 1905.4 | **3363.5** | 3597.8 | 3272.3 | 4365.3 / 1091.3 | 946.2 | 1465.9 / 669.1 | 1961.5 / 1157.7 | 2971.4 / 742.9 |
| 6 | 167.64 | 1905.4 | **3519.3** | 3841.7 | 3419.6 | 5153.7 / 858.9 | 946.2 | 1758.1 / 802.5 | 2050.4 / 1210.1 | 3898.6 / 649.8 |
| 8 | 234.51 | 1905.4 | **3519.3** | 3841.7 | 3419.6 | 5710.4 / 713.8 | 946.2 | 2442.8 / 1115.0 | 3085.8 / 1821.2 | 4619.2 / 577.4 |

DS MTP step terms (cycles):

| P | verify | draft | seed | seed/head overlap credit | step | MTP/AR | gamma = P-1 option |
|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | 2708031.7 | 208789.1 | 21089.1 | 0.0 | 2945727.9 | 0.889 |   |
| 2 | 1429323.9 | 139787.8 | 12151.2 | 1093.6 | 1587987.3 | 1.649 | 2302.7 gamma 1 (N = 2), tau 1.753 = 4.159 x walk[1] / walk[5] |
| 4 | 1338146.6 | 128338.4 | 10617.3 | 1093.7 | 1483826.6 | 1.765 | 3268.9 gamma 3 (N = 4), tau 3.181 = 4.159 x walk[3] / walk[5] |
| 6 | 1280713.3 | 121020.9 | 9657.6 | 1093.7 | 1418116.1 | 1.847 |   |
| 8 | 1280713.3 | 121020.9 | 9657.6 | 1093.7 | 1418116.1 | 1.847 |   |

Compiler per-layer lane choice (best lanes <= P per layer segment, row field on): verify cycles P2: 1429325.2 (+1.3), P4: 1338146.4 (-0.2), P6: 1280712.9 (-0.4), P8: 1280712.9 (-0.4).

## Per-unit RTL change list (cycles saved = P = 6 headline verify with the feature removed)

| unit | owner | change | verify cycles saved a step (P = 6) |
|---|---|---|---:|
| SM | H-SM | P accumulator lanes per MAC column: each HBM weight word / BDC line broadcast to P lanes (P x MAC, same 99 B/cycle/SM HBM share, SMEM and VM ports); SM.MATVEC slot field (HGI-1 spec 6.7 param [4:2] = N - 1, widen to 4 b for N <= 16) + per-slot x base; P x-slot stores; per-lane result publish (slot-major) | 554112.8 |
| ATT | H-SM (SM attention) | KV-line-stationary multi-query attention: P query slots a SM engine, each KV line streamed once and applied to the lanes whose top-k mask selects it (per-line lane mask from the N IDX top-k lists + window rule), per-lane QK / PV accumulators, fixed spans (first access, dispatch, publish, cross-SM merge) once a record | 189092.8 |
| FUSED | H-SU (FUSED) | FUSED.HC_PRE_NORM / HC_POST row field N on the LL lanes: gain sectors kept across rows, two r slots (row p+1 phase A over row p's tail), per-row scalar set; MEASURED II 197 (P6 RTL) | 201983.3 |
| HC | H-SU (HC) | HC.HC_MIX N rows streamed against stationary mix weights (HCP x6 mode II 250) + Sinkhorn x 3 units (II 634 / 3) | 284081.6 |
| COLL | H-COLL | COLL ROW_GATHER / TOPK_MERGE / kv gather / ARGMAX_MERGE take N rows (one message train, endpoint / crossing / tail once); shared ALL_GATHER / GROUP_REDUCE_MCAST carry N x payload; ring AG flits x N (d4g adders unchanged per record) | 163834.0 |
| IDX | H-IDX | IDX.INDEX N queries over ONE key stream (N x 4,096-word query store), IDX.TOPK heap row reset, verify expert-UNION record (384-b union bitmap, per-expert lane lists for the grouped GEMM) | 63743.0 |
| SU_DMA | H-SU / H-DIE / H-IDX | row counters in SU.VOP (indexed + un-indexed), SFU chains, DMA.KVWB_DS (N rows, window ring 256 slots: +128 HBM rows a layer), position-addressed DMA.LOAD rows, FUSED.QDQ, ARGMAX.LOCAL | 38732.0 |
| VM | H-DIE | VM capacity: N resident verify / user columns (h + PRE): + (N - 1) x ~30k words (N = 6: ~+150k words, VM 2^18 -> ~2^18.9; 4 quadrant slices); else per-layer column swaps | 37139.7 |
| ISA | H-ISA | record header row count N (all units) + per-row descriptor stride; CTL.TOKX (k completion beats, SPEC_GAP Q-MTP-1) | - |
| DRAFT | H-MTP | DSpark draft on the same die: dsa / dsb / dhead as R = 5-row records (no new unit), SEED of the next step scheduled with the verify head (joint S2 schedule), Markov / demb serial | - |

## Verify unit busy (DS MTP, cycles summed over layer segments)

| P | ARGMAX | COLL | CTL | DMA | FUSED | HC | IDX | SM | SU |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 5656.3 | 751559.9 | 0.0 | 355328.0 | 391881.7 | 549900.0 | 98169.9 | 1195889.5 | 214909.1 |
| 2 | 10702.1 | 586264.8 | 0.0 | 57134.0 | 188300.0 | 191652.0 | 43688.2 | 591654.7 | 157093.1 |
| 4 | 7141.3 | 586264.8 | 0.0 | 57134.0 | 188300.0 | 191652.0 | 43688.2 | 487631.3 | 157093.1 |
| 6 | 4913.2 | 586264.8 | 0.0 | 57134.0 | 188300.0 | 191652.0 | 43688.2 | 420542.4 | 157093.1 |
| 8 | 4913.2 | 586264.8 | 0.0 | 57134.0 | 188300.0 | 191652.0 | 43688.2 | 420542.4 | 157093.1 |

## Assumptions

- P = 1 = the current d4g die AS BUILT (SM without slot count, no row field, VM column swaps, row-serial draft); P >= 2 = P lanes + row field N + VM-resident columns
- DS MTP: DSpark gamma 5, N = 6 verify positions, tau 4.159 (owner 6-class blend) at every P; P = 8 leaves 2 lanes idle for MTP (no gamma-7 drafter); ds_mtp_gammaP rows = the compiler choosing gamma = P - 1 with tau scaled by the MTP-STATS greedy walk
- expert union: MTP-STATS decorrelated verify estimate (P = 6 mean) headline, p90 as bracket; users: independent users mixed workloads mean
- KV top-512 overlap of consecutive positions is UNMEASURED: headline at the upper bound (N x 512 selected + 128 + N - 1 window lines), kv_lower = full overlap (512 + window); users: N x single (exact)
- row II: FUSED.HC_PRE_NORM measured 197 (P6 RTL); all other II PRICED from tables / structure (ds_mtp_verify.row_ii): FUSED.POST 100, QDQ n/32, HC max(250 HCP x6 measured, Sinkhorn 634/3), COLL c1 - 741.7 fixed, IDX.TOPK 47, IDX.INDEX c1 x 152/658.9 (users: c1), SU nv, DMA c1 - first access, ARGMAX 6; Qwen ROW_NORM 157.6 (anchor scaled 4096/5120), SU nv, all-reduce n/16 (64 B/cycle)
- DSpark draft at P lanes = R = 5-row records (ds_mtp_draft, stage expert union = no sharing 15); seed overlap = joint S2 schedule with the verify head, nothing after the accept overlaps
- Qwen DFlash: dflash.step_program B = 16 (8 info) at pos 8,192 - B, tau published 8.01 (b16) / 5.584 (b8, anchored) and measured cycle-weighted 3.656 / 3.2956; ATT 4-slot groups (16 lanes) are the current record form, a P-lane engine streams the context once for P groups (QCHK fix: group index = slot / 4); P = 1 = every slot re-issues the SM line; P >= 2 = the compiler's record size R in {P, 2P, 8, 16} (SM ceil(R / P) line passes a record, ceil(B / R) per-pass records) and head pass PH in {16, 8, 6, 4}, largest that fits the P-lane VM (2^18 + (P - 1) x 30k words; TP4 map, conservative) (QCHK 10-18: the as-built 8-slot / 4-slot head split had made P = 6 = P = 4)
- multi-user: all users at the same position (DS 1M, Qwen 8K); HBM capacity for P users' 1M KV NOT checked
- area: MTP-AREA measured

## Re-run

`PYTHONPATH=tools python3 -m hgi_sim.hbm_plane_model --stats results/arch/hbm_mtp_next_1018/stats/summary.json [--area results/arch/hbm_mtp_next_1018/sm_area/summary.json] --out results/arch/hbm_mtp_next_1018/model  (heavy: ~60 S2 schedules, run on the fleet, ~15 min at 24 jobs)`

Re-summarise a run record without re-timing: `python3 -m hgi_sim.hbm_plane_model --from-run results/arch/hbm_mtp_next_1018/model/run.json [--area A.json] --out results/arch/hbm_mtp_next_1018/model`

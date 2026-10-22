# HBM d4g rate: QDQ RL 54 + HC tail k4 (STEWARD-TOKb-HBMPRICE, 10-21)

This prices two coordinator-approved HBM latency costs into the HBM DeepSeek and HBM Qwen decode rates. Numerics do not change.

| cost | approval | per record | records per DS token | records per Qwen token |
|---|---|---:|---:|---:|
| QDQ: `hb_quant_NW` `ot_hgi_qdq_host_split_r3` + transport `ctl_r4s`, read latency RL 7 -> 54 | HBM-DIE17 NOTICE 18:55 | +47 edges (FUSED.QDQ_FP8 measured 58 -> 105) | 40 | 0 |
| HC tail k4: TSDIV 16 -> 17 (k4 L 989 vs the measured k2 L 496), plus the hardened tail child TE 2; root emit TE 2 -> 495 | STEWARD-HBM 18:28 (b) | +495 edges (HC.HC_MIX measured 1055 -> 1550) | 80 | 0 |

How each delta is derived:

- **QDQ.** The measured 58 edges came from a bench whose VM model is 7 edges at the quant pins (RL 7). The 16-beat record is pipelined through the RLI ring. So each beat's answer, and therefore `record_done`, arrives RL_new - RL_old = 47 edges later.
- **HC.** The measured 1055 edges came from the GEN2e3 root at TAILC 0, with the tail at SDIV 7 and L 496. The release root uses TAILC 1 plus k4 (TSDIV 17, TTPIPE 1, TSKP 2), which gives L 989. The emit moves TE + TX = 2 + 493 = 495 edges. This matches the RTL lockstep result "PASS 48 (+495)" at `claude/hc13-tail-k4-1021@dbb4b616d`.

The HBM-Qwen schedule has no HC record and no QDQ record, so Qwen is unchanged by construction. The checker confirms it: the Qwen schedule totals are byte-equal in every sweep.

## Method

Nothing was forked. The tool of record is `tools/hgi_sim/toksim_hbm_census_1019.py --measured`, the TOKSIM-HBM static schedule `info_banklat_all`. These latencies enter that tool only as the per-class measured laws (`shape_table` cycles) of `HC.HC_MIX` and `FUSED.QDQ_FP8`. So the price is a change to those parameters in the measured-law JSON:

- `make_measured.py` writes `base_h9b.json` / `priced_h9b.json`.
- `sweep_slack.py` adds the deltas to any base law file and re-runs the census.

Every row below re-runs the same base twice on current `origin/main` code, once with 0+0 and once with 495+47. The token delta is dSched / (1 + land%), the order used by toksim_hbm_compose_1019 and tok_from_sched: DS land is -1.13 %, Qwen -0.07 %, and one edge is 833 ps.

## Result (single user, 1 x tok/s; MTP not priced: HBM MTP is deferred to the next release)

| row | DS AR tok/s old -> new | DS cycles added per token | HBM-Qwen tok/s |
|---|---:|---:|---:|
| **RELEASE of record**: bound h9b/h9c controller (meas_h9b; COORD 23:24 "ships with h9c", DS ~1,000) | **993.7 -> 993.7** | 0 (off the critical path, slack below) | unchanged (537.4 meas_h9b; ~408 at the 45.03 price) |
| **NEXT release**: MC3c successor + x-reuse (HBM-RATE7 `m_xl_i8`, accepted ~1,341 -> 1,331.6 after the head repair) | **1,331.6 -> 1,325.7 (-0.44 %)** | +4,005.3 (sched +3,960 = 8 critical HC_MIX x 495) | 1,001.5 unchanged |
| HBM-RATE7 `m_all` | 1,331.6 -> 1,325.7 | +4,005.3 | 1,011.3 unchanged |
| HBM-RATE7 `m_base` | 1,141.8 -> 1,140.7 | +1,066.5 | 1,000.7 unchanged |
| TOKEN-LEAD 10-20 combined (`measured_rel_i8_su`) | 1,109.7 -> 1,106.9 | +2,777.8 (8 HC_MIX + 36 QDQ critical) | 372.2 unchanged |
| rel98 | 1,155.4 -> 1,155.4 | 0 | 1,002.9 unchanged |

Per DS token, the unit occupancy added is 40 x 47 + 80 x 495 = 41,480 edges. Only the critical share above changes the rate.

## Off-critical-path slack arithmetic (release row, h9b base, `sweeps/*_h9b.json`)

The h9b base re-run on current code gives sched 1,140,466.7. That is 30.7k below the inferred meas_h9b sched, because main has moved since that row. The slack proof uses this re-run.

**HC.HC_MIX, adding d edges to all 80 records:**

| d | DS sched | critical records |
|---:|---:|---:|
| 0 | 1,140,466.7 | 0 |
| 495 | 1,140,466.7 | 0 |
| 720 | 1,140,466.7 | 0 |
| 730 | 1,140,473.7 | 3 |
| 740 | 1,140,503.7 | 3 |

The slope is 3 cycles per edge (3 records), so the threshold is 730 - 7/3 = **727.7 edges**. The minimum HC_MIX slack is 727.7, which is more than 495, leaving a margin of **232.7 edges**.

**FUSED.QDQ_FP8, adding d edges to all 40 records:**

| d | DS sched | critical records |
|---:|---:|---:|
| 47 | 1,140,466.7 | 0 |
| 190 | 1,140,466.7 | 0 |
| 200 | 1,140,492.1 | 4 |
| 500 | 1,141,692.1 | 4 |

The slope is 4 cycles per edge, so the threshold is 200 - 25.4/4 = **193.7 edges**. The QDQ slack is 193.7, which is more than 47, leaving a margin of **146.7 edges**.

**Both costs together (495 + 47, `joint_h9b.json`):** sched is unchanged at 1,140,466.7, so there is no interaction.

**Next-release base (`m_xl_i8`, `qdq_slack_r7xl.json`, HC at +495):**

| QDQ d | DS sched | QDQ critical records |
|---:|---:|---:|
| 47 | 872,493.9 | 0 |
| 100 | 872,528.2 | 4 |

The threshold is 100 - 34.3/4 = 91.4 edges, so QDQ stays off the path with a margin of **44 edges**. HC_MIX is already critical in 8 records there, so the full +495 is exposed 8 times.

## Exact command (from a sparse worktree of this branch; ~15 s per census, local, no fleet job)

```
R=results/token_pass/hbm_price_qdq54_hc17_1021; C=results/rtl/hbm_rate7_1020/census; M=results/token_pass/measured_hbm_1019
python3 $R/make_measured.py $R
python3 $R/sweep_slack.py $R/base_h9b.json /tmp/j_h9b HC.HC_MIX+FUSED.QDQ_FP8 0+0,495+47
python3 $R/sweep_slack.py $C/m_xl_i8.json /tmp/j_r7xl HC.HC_MIX+FUSED.QDQ_FP8 0+0,495+47 --bw 98 --bridge 1
#   (likewise r7all m_all.json, r7base m_base.json, i8su $M/combined_1020/measured_rel_i8_su.json, rel98 $M/measured_rel.json: --bw 98 --bridge 1)
python3 $R/sweep_slack.py $R/base_h9b.json /tmp/hs HC.HC_MIX 0,495,720,730,740
python3 $R/sweep_slack.py $R/base_h9b.json /tmp/qs FUSED.QDQ_FP8 47,190,200,500
python3 $R/sweep_slack.py $C/m_xl_i8.json /tmp/q HC.HC_MIX+FUSED.QDQ_FP8 495+100,495+200,495+400,495+800 --bw 98 --bridge 1
python3 $R/compose.py          # -> result.json
```

Sparse paths this needs: `tools/hgi_sim/`, `results/token_pass/{measured_hbm_1019,hbm_functional_1021/smb_param1}/`, `results/rtl/hbm_rate7_1020/census/`, `results/hbm_sm_attention_1015/`, `results/arch/{hbm_plan_study_1017,hgi_programs_20261010/inputs}/`, `compiler/models/qwen3-8b/`, `physical/ref_tile/smh_bdc_ref_p50/views/ot_hbm_accel_smh_bdc/`, `results/rtl/w19_sm_real_ops.json`.

Grade: a model composition on measured laws, the same grade as the rows of record. This is not a full-token throughput PASS.

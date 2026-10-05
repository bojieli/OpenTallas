# DeepSeek-V4.1: energy, power and equal-silicon comparison on authoritative inputs (2026-10-04)

> **INVALID, superseded (owner, 2026-10-04).** This record used the old 2,466-2,532 tok/s DS ROM rate and an ASSUMED 10%
> power-gating residual; measured are 1,386 AR / 2,744 MTP (main 4fa71767c) and a 35.4% residual (b9e66e66d). Its
> "ROM wins energy 1.6-2.3x" verdict is withdrawn. The regenerable replacement for both targets is
> `results/arch/energy_silicon_measured/` (`tools/energy_silicon_measured.py`). Kept unchanged below as history.

> **TAU (owner decision 2026-10-05).** `model.json` is composed at tau 4.159, the owner 6-class workload blend (`results/speculative/v41_mtp_acceptance_qualified_20261003/blend_owner6.json`, via `tools/third_party_tau.py`); the published V4.1 3.8879 is a sensitivity (`OT_TAU_SOURCE=third_party`). Hand-written figures below that quote tau 4.159 use the current default tau (other inputs may have moved since; `model.json` is authoritative); the 2026-10-04 note that scaled them to 3.8879 is withdrawn.

Owner-requested model study. Replay: `python3 tools/ds_energy_silicon_authoritative.py` (writes `model.json`); `--check` prints the cross-checks.

**Evidence class:** MODEL. Rates, silicon and power come from authoritative or measured records. Every other constant is listed under `assumed` in `model.json` and marked ASSUMED below.

## Inputs

| Design | Per-user rate source | Silicon / power source |
|---|---|---|
| **DS ROM**: S81 + wavefront verify | `hbm_switch_latency_authoritative()`. AR comes from `results/rtl/dsrom_wavefront_verify_20261004`. MTP uses the MEASURED draft (`dsrom_dspark_step_slices_20261004`, main dae91947c): 6,734 as built, 7,186 L1 fused. L1+L2 is 7,858 EXPECTED (2a235a9fe). | `dsrom_c_recheck_20261004` S81 has 368 dies (324 layer + 44 head/table) and 452 KV stacks (W3 rule 4S+128; scenario C had 420). The ICG static ledger is 50.196 W per layer die (30.6 W of it SerDes), plus head 738.5 W, Engram table 3,324.4 W and 2.8 W per stack. Dynamic energy is 118.6 / 102.3 mJ per AR token (isopower 8bb540cd1). |
| **HBM accelerator**: Tomahawk Ultra + our protocol | `uarch_model.py` defaults (firm ladder, switch kept, TU protocol). MTP is labelled **pending measured draft** (51.06 us estimate). | 96 dies x 340.5 mm² with 384 stacks. Gated static is 5,367.7 W and dynamic is 1.4614 J per AR token (the study's transferred constants). Saturation comes from the consolidation TP-96 sweep. |
| **GPU-organised ablation** (W19) | Measured H100 NVLS transport | Same silicon and ledger as the accelerator |
| **GPU-faithful R0** | Measured H100 grid.sync 1.097 us plus fenced collectives | Same silicon and ledger as the accelerator |
| **8x B200** | tier-2 model `gpu_tier2()` (NCCL 9.024 us default): 266.9 tok/s at 1M. The old 282.4 row used the superseded 8 us assumption. MTP uses the existing 1.94x sensitivity, not tau 4.159. | 8 x 689 W measured decode draw; 16 x 800 mm² + 64 stacks (repo record) |

H100: the measured NVLS and grid.sync figures enter the comparison only as the ablation's transport and R0's sync. **No DeepSeek-V4.1 decode has been measured on H100.**

## Rates (tok/s per user, batch 1; tau 4.159)

| Design | 1M AR | 1M MTP | 200K AR | 200K MTP |
|---|---:|---:|---:|---:|
| DS ROM S81, MTP as built (measured draft) | 2,466.2 | 6,733.7 | 2,574.1 | 6,927.5 |
| DS ROM, L1 fused head (measured) | | 7,186.2 | | 7,407.3 |
| DS ROM, L1+L2 (EXPECTED) | | 7,858.1 | | 8,123.2 |
| HBM accelerator (TU protocol) | 2,624.4 | 6,351.9 *pending measured draft* | 2,629.9 | 6,364.9 *pending* |
| HBM accelerator, sensitivity: draft = ROM measured draft/AR (as built 0.356 / 0.372) | | 5,595.5 | | 5,562.6 |
| HBM accelerator, sensitivity: draft = ROM L1-fused ratio (0.260 / 0.272) | | 5,884.9 | | 5,861.0 |
| HBM accelerator, measured composition | 2,562.7 | 6,032.4 | 2,568.1 | 6,044.8 |
| GPU-organised ablation (H100 NVLS) | 1,481.9 | 4,123.9 | 1,483.7 | 4,129.8 |
| GPU-faithful R0 (H100 grid.sync + fenced) | 358.9 | 1,249.9 | 359.0 | 1,250.7 |
| 8x B200 (tier-2 model) | 266.9 | 518.0 | 267.2 | 518.5 |

If the HBM draft takes the ROM's measured draft/AR ratio, ROM:HBM MTP moves from 1.06 to **1.20** at 1M (as built) and from 1.13 to **1.22** at 1M (L1 fused).

## 1. Silicon (mm²; HBM DRAM at the sourced 1,089 mm² per 8-high stack)

| Design | Logic dies | Stacks | DRAM | Switch chips | **Total** | AR per user per 1,000 mm² (1M) | MTP per user per 1,000 mm² (1M) |
|---|---|---:|---:|---|---:|---:|---:|
| DS ROM S81 | 368 x 839.24 = 308,840 | 452 | 492,228 | 0 (direct board links; SerDes on die) | **801,068** | 3.08 | 8.41 |
| HBM accelerator | 96 x 340.5 = 32,688 | 384 | 418,176 | 8 x 800 = 6,400 (ASSUMED area) | **457,264** | 5.74 | 13.89 |
| GPU-organised ablation | same as accelerator | 384 | 418,176 | 6,400 | 457,264 | 3.24 | 9.02 |
| GPU-faithful R0 | same | 384 | 418,176 | 6,400 | 457,264 | 0.78 | 2.73 |
| 8x B200 | 16 x 800 = 12,800 | 64 | 69,696 | 2 x 800 (ASSUMED) | 84,096 | 3.17 | 6.16 |

Notes on the silicon table:
- At 200K the per-user figures per 1,000 mm² are ROM 3.21 / 8.65 and HBM accelerator 5.75 / 13.92.
- DRAM is 61% of the ROM's silicon and 91% of the HBM accelerator's.

Sensitivities, as ROM / HBM total in mm²:
- 420 stacks for the ROM (scenario C): ROM 766,220.
- 12-high cube bound (1,573 mm²): 1,019,836 / 643,120.
- ASSUMED 900 mm² per stack: 715,640 / 384,688.
- Head/table dies at 786.23 mm²: ROM 798,736.

**Iso-total-silicon.** The HBM accelerator scaled to the ROM's 801,068 mm² gives **1.75 replicas** (1 whole replica plus 344k mm² unused):
- the per-user rate is unchanged (2,624 AR / 6,352 MTP);
- 1.75 concurrent batch-1 users against the ROM's 1;
- saturated aggregate AR at 1M: 44,310 tok/s fractional (25,293 with 1 integer replica), against the ROM's 80,834;
- at 200K: 72,990 fractional against 80,834.

The 8x B200 scaled to the same silicon gives 9.5 systems: 9 x 266.9 = 2,402 tok/s from batch-1 users at 267 each, and 533k tok/s saturated at 70.6 tok/s per user.

## 2. Power (W; ICG mandatory; the ungated clock is never used as static)

Static terms in the rows below:
- **HBM rows:** static = 5,367.7 W gated ledger (dies, PHY, 384 x 2.8 W stack idle, links), plus **8 switch chips x 500 W (ASSUMED, by analogy with Tomahawk 5 "< 500 W")**.
- **ROM rows:** "PG" applies stage power gating (ASSUMED 10% residual, pre-wake); "ICG" is ungated stages with ICG.

### 1M

| Design / point | tok/s | Static W | Dynamic W | System W | **J/token** | **tok/s per kW** |
|---|---:|---:|---:|---:|---:|---:|
| ROM AR b1, ICG | 2,466 | 21,592 | 292 | 21,884 | 8.87 | 113 |
| ROM AR b1, PG | 2,466 | 7,316 | 292 | 7,609 | **3.09** | **324** |
| ROM MTP as built b1, PG (f = 7/S) | 6,734 | 8,220 | 1,007 | 9,227 | **1.37** | **730** |
| ROM MTP L1 fused b1, PG | 7,186 | 8,220 | 1,074 | 9,294 | 1.29 | 773 |
| ROM AR saturated (33 users at 2,466 each), ICG | 80,834 | 21,592 | 9,587 | 31,179 | **0.386** | **2,593** |
| ROM AR saturated, PG | 80,834 | 13,059 | 9,587 | 22,645 | 0.280 | 3,570 |
| ROM MTP saturated as built (ASSUMED head-serialised draft; 3.1 users) | 21,010 | 21,592 | 3,141 | 24,733 | 1.18 | 850 |
| HBM accel AR b1 | 2,624 | 9,368 | 3,835 | 13,203 | **5.03** | **199** |
| HBM accel AR b1, switch not charged | 2,624 | 5,368 | 3,835 | 9,203 | 3.51 | 285 |
| HBM accel MTP b1 (pending draft) | 6,352 | 9,368 | 5,654 | 15,021 | **2.36** | **423** |
| HBM accel MTP b1, ROM-ratio draft | 5,596 | 9,368 | 4,980 | 14,348 | 2.56 | 390 |
| HBM AR saturated (32 users at 790; HISTORICAL) | 25,293 | 9,368 | 13,397 | 22,765 | **0.900** | **1,111** |
| HBM MTP saturated (4 users at 3,983; HISTORICAL) | 15,931 | 9,368 | 14,831 | 24,199 | 1.52 | 658 |
| Ablation AR b1 / MTP b1 | 1,482 / 4,124 | 9,368 | | 11,533 / 13,038 | 7.78 / 3.16 | 128 / 316 |
| GPU-faithful R0 AR b1 / MTP b1 | 359 / 1,250 | 9,368 | | 9,892 / 10,480 | 27.6 / 8.38 | 36 / 119 |
| 8x B200 AR b1 / MTP b1 (689 W draw) | 267 / 518 | 6,512 | (inside) | 6,512 | 24.4 / 12.6 | 41 / 80 |
| 8x B200 AR saturated (839 users at 70.6) | 59,240 | 6,512 | | 6,512 | 0.110 | 9,097 |
| 8x B200 AR b1 at 1,200 W TDP | 267 | 10,600 | | 10,600 | 39.7 | 25 |

### 200K

| Design / point | tok/s | System W | J/token | tok/s per kW |
|---|---:|---:|---:|---:|
| ROM AR b1, PG / ICG | 2,574 | 7,580 / 21,855 | 2.94 / 8.49 | 340 / 118 |
| ROM MTP as built b1, PG | 6,928 | 9,220 | 1.33 | 751 |
| ROM AR saturated, ICG / PG | 80,834 | 29,861 / 21,080 | 0.369 / 0.261 | 2,707 / 3,835 |
| HBM accel AR b1 | 2,630 | 13,168 | 5.01 | 200 |
| HBM accel MTP b1 (pending) | 6,365 | 14,929 | 2.35 | 426 |
| HBM AR saturated (41,664, 32 users; HISTORICAL) | 41,664 | 30,758 | 0.738 | 1,355 |
| Ablation AR / MTP b1 | 1,484 / 4,130 | 11,512 / 12,976 | 7.76 / 3.14 | 129 / 318 |
| 8x B200 AR b1 / MTP b1 | 267 / 519 | 6,512 | 24.4 / 12.6 | 41 / 80 |

**Iso-power** at the ROM's saturated ICG draw (31.2 kW at 1M):
- HBM accelerator: 1.37 replicas give 34,641 tok/s against the ROM's 80,834.
- 8x B200: 4.8 systems give 283,634 tok/s, but at 70.6 tok/s per user.

At 200K (29.9 kW): HBM 40,450 against the ROM's 80,834.

## Cross-checks (each computed two ways; all agree unless noted)

- HBM accelerator AR and MTP step, from the record rows and from parts + transport deltas: 381.04 = 381.04 us and 654.77 = 654.77 us (1M); 380.24 / 653.43 us (200K).
- ROM static, from components and from the S81 record: ICG 21.59 = 21.59 kW; batch-1 PG 7.32 = 7.32 kW. Batch-1 PG tok/s per kW 324.1 = 324.1 (1M) and 339.6 = 339.6 (200K). Saturated ICG 2,592.6 = 2,592.6 and 2,707.0 = 2,707.0.
- HBM gated static, from the ladder constant and from the consolidation gated mJ x rate - dynamic: 5,367.7 = 5,367.7 W.
- Every J/token figure equals both P / rate and static / rate + dynamic.
- **These two disagree:**
  - HBM MTP step energy: 3.70 J (consolidation, gated) against 4.16 J (legacy economics).
  - HBM saturated dynamic energy: 0.530 against 0.614 J/token.

  The gated consolidation basis is used. That choice favours HBM by about 12-14%.

## 3. Verdict

**Energy and power: the DS ROM wins at batch 1.** These comparisons count the switch chips:
- AR 3.09 against 5.03 J/token (1.6x) with stage power gating.
- MTP 1.37 against 2.36 J/token (1.7x; 1.9x against the ROM-ratio HBM draft).
- At saturation the ROM delivers 80.8k tok/s at 0.39 J/token (ICG) against HBM's historical 25.3k at 0.90 J (2.3x per kW). It keeps the full 2,466 tok/s per user while doing so, whereas HBM drops to 790.

**Per-user MTP: the ROM wins.** 6,734 as built against 6,352 is 1.06x, and only because the HBM draft is still the 51 us estimate. With the ROM's measured draft/AR ratio applied to HBM it is 1.20x (as built) to 1.22x (fused).

**Per-user AR: the HBM accelerator wins slightly** (2,624 against 2,466, 0.94x at 1M; parity at 200K).

**Silicon: the HBM accelerator wins.** It reaches the same per-user rate on 0.57x the total silicon:
- 5.74 against 3.08 AR tok/s per user per 1,000 mm²;
- 13.9 against 8.4 for MTP.

The ROM's 309k mm² of ROM logic is the cost. At equal total silicon, HBM serves 1.75 batch-1 users per ROM user. Its saturated aggregate (44k at 1M, 73k at 200K) still trails the ROM's 81k.

**GPU baselines.**
- The GPU-organised ablation is 1.66x slower per user than the ROM (AR, 1M) and 2.5x worse in J/token.
- 8x B200 is 9-13x slower per user and 8-9x worse in batch-1 J/token.
- Only in massively batched throughput at about 70 tok/s per user does B200 lead on tok/s per mm² and tok/s per kW.

**Uncertainty drivers, largest first:**
1. **ROM stage power gating** (ASSUMED 10% residual + pre-wake): batch-1 ROM power moves 3x, from 7.6 to 21.9 kW. Without it, ROM batch-1 AR is 8.9 J/token, worse than HBM's 5.0.
2. **Switch chip power and area** (ASSUMED 8 x 500 W, 8 x 800 mm²). This is 4 kW of HBM's 13.2 kW at batch 1; without it HBM batch-1 AR is 3.51 J/token.
3. **HBM saturation** is the HISTORICAL GPU-organised column model. The accelerator's batch calendar is not composed.
4. **HBM MTP draft** is not yet measured, a 0.85-1.0x swing on HBM MTP.
5. **DRAM area per stack**: the sourced 1,089 mm² is a bound; the band 900-1,573 moves totals by -16% to +41%.
6. **ROM MTP saturation** assumes the draft serialises on the head, which caps it at 21k.
7. **Engram table dies** (3.3 kW, never gated) are the ROM's largest always-on term.

# DeepSeek-V4.1 ROM array: history of the die count, iso-power, iso-silicon, and multi-column verify at τ = 4

This is model-only work: arithmetic on committed records plus read-only runs of the unified model. No RTL, P&R or model inference was done.

- Base: origin/main e634046fe. `tools/uarch_model.py` sha256 2da5b6d9…, the same source the S58 selection pins.
- Numbers come from `model.json` (composed) and `raw.json` (model outputs). Replay instructions are in `REPLAY.md`.
- 1M = 1,048,576 context tokens; 200K = 200,000.

## Q1. How 188 dies became 464 / 508

| When (UTC) | Commit | Array | Why |
|---|---|---|---|
| 2026-09-25 | memory note `model-target-decision` | ROM array, wafer rejected | Iso-area study a11a3a7e |
| 2026-09-26/27 | user decisions (memory `v41-array-realistic-interconnect`, `kv-lives-in-hbm`) | 2-die packages; TP-4 across a package pair; 4 HBM3E per layer die; KV in HBM | Realistic packaging and links (light-FEC 130 ns); KV capacity |
| 2026-09-27/28 | fbf942863, 97a55004e (`results/arch/v41_rack.json`) | **28 stages × TP-4 = 112 layer + 4 head + 72 Engram-table dies = 188 dies, 94 packages, 464 stacks** | The rack design point. 8192-row macros at analytical density |
| 2026-09-29 | 2b792ef4a | Unified model copies this as `V41_ROM_SYSTEM` (tools/uarch_model.py:2027) and `V41_STAGES = 28` (:2032) | The economics section. **It has not been updated since**, so it is stale |
| 2026-09-30 | c673fd438, e7479589a (AGENTS) | 4096-row macros, 2 per element slot; 1.2 GHz at SS | ROM macro depth study; user clock decision |
| 2026-09-30 | 84aa38cea, ecb9fa700 | **37 stages: 148 layer + 4 head + 36 table = 188 dies** | Storage-only density (no HC1 credit); dedicated BF16 columns. User: "max per-user rate, dies are free" |
| 2026-10-01 | 6cd0ef52b, 5df8f041c | **41 stages: 164 + 8 + 36 = 208 dies** | C_rotate VM on the compact hub (VM-H cost −14.5% AR) |
| 2026-10-02 04:36 | ee3de0a11 `dsrom_4096_comparable_capacity/partition_token_options.json` | `lowest_stages_passing_conservative_capacity: 58` | Usable field is 442.81 mm² a die. The conservative per-die need is 803.4 mm² at S28, 581.9 at S41 and 442.15 at S58. It includes the user-required full return (138.5 Mbit, 105 mm² of FFs at 50%), RNE and WAKE. S58 TP-4 gives 276 dies |
| 2026-10-02 07:33 | ceefc0db0 `dsrom_4096_reticle_inventory` | S41 owner outline 1,020 mm² (34.7 × 29.4 mm) against the 858 mm² reticle | `retained_negatives.reticle_owner_outline.fits_reticle: false` (+162 mm²) |
| 2026-10-02 07:42 | efa3854f2 `dsrom_main_S58_corridor_correction` | S58 with one die per rank (PAIR1) fails by 2.42 mm² | Native bidirectional service corridor: 42,752 tracks |
| 2026-10-02 11:38 | 63d628705 `dsrom_reticle_fixed_debit_reconciliation/model-r4.json` | **PAR2: each TP rank split over 2 dies by output rows. Layer dies go from 232 to 464; total is 508; 254 packages** | The composed conservative S58-PAIR1 die is **924.29 mm², 66.29 mm² over the reticle**. A PAR2 shard is 694.88 mm². The 465.5 mm² fixed debit is replicated on both shards |
| 2026-10-02 14:50 | bd4257ad7 (+ ee26e1a23, 843729bb9) | Owner no-ECC ROM policy | ECC −5.80 mm², parity +5.99. **No die-count change**; screen 759.44 mm² |
| 2026-10-03 | review `dsrom_utilisation_redesign` | Element re-frame to 0.60 utilisation; screen 786.23 mm² (91.6%) | Element routes at 0.72 and above fail; 0.375 is the best closed run |
| 2026-10-03 | abd77c4e1 (parallelism study), 4ec2eef0e (C5hc gate) | User rejected PAR2 on principle, then **kept C1/PAR2** | C5hc beat C1 by only +4.48% against the 5% rule, measured in RTL |

**The causal chain:**
1. The 4096-row no-HC1 storage density, the full return storage, and the per-die replicated services (attention, indexer, hubs, corridors) pushed the field per die past the reticle. That took the stage count from 28 to 37 to 41 to 58.
2. At S58 a single-die rank was still 66 mm² over the reticle, so each rank became two dies (PAR2).
3. ECC removal came after PAR2 and changed nothing.

**Current layout: DS4096-TP4-S58-PAR2-NP2048 (C1).**
- **Dies.** 58 pipeline stages × 8 layer dies = **464 layer dies**. Each stage is TP-4 ranks × 2 PAR2 shards, and each shard holds 2,048 pairs. Add **8 head dies** (embedding, LM head, DSpark/MTP draft) and **36 Engram-table dies**, for **508 dies** in total.
- **Packages.** **254 two-die packages**: one rank's two shards share a package, so a stage spans 4 packages.
- **HBM.** **960 HBM3E stacks**: 4 per rank on the shard-0 die (928) plus 4 per head die (32). Shard-1 and table dies have none.
- **Per-die area (screen).** 786.23 mm² of the 858 mm² reticle (26 × 33 mm):
  - field 229.41 mm²;
  - named services 90.68 mm²;
  - clear route bands 40.57 mm²;
  - unmapped legacy complement 287.02 mm²;
  - native residual 47.21 mm²;
  - increments 64.55 mm²;
  - re-frame +26.79 mm².

  Sources: model-r4.json:99-136 and :328-330. Identifiable placed objects are only 176–333 mm².
- **Links.**
  - In package: UCIe owner crossing, 65.17 ns one-way (`dsrom_par2_boundary_20261003/model.json`). It needs 0.91 of 4.2 TB/s.
  - TP-4 collectives span 4 packages on the 130 ns light-FEC board link.
  - 57 stage hops, costing 23.2 µs on the AR path.

## Q2. Iso-power (1M; 200K in model.json)

**What is counted.** Total system power covers:
- every die;
- every HBM stack: idle 2.8 W each, always on (power_scenarios `idle_w_per_stack`), plus traffic at 13.64 pJ/bit (10.19 die + 3.45 stack, power_scenarios `hbm_path_total`);
- links and PHYs, including SerDes always-on and an upper bound for PAR2 UCIe traffic.

No switch is modelled for either design.

**The comparator.** One TP-96 × 4-stack instance (`v41_hbm_n`, the consolidation's equal-power instance). It runs at the W19 rate of 2,261.7 AR and the DSpark-priced rate of 4,847.7 (d2aff19ef).

**Static policy.**
- **ICG** means per-pair ICG only, with every die's remaining static always on.
- **PG** means the model's stage power gating (1 µs wake). HBM idle stays on.

**Scenarios A/B.** These (`power_scenarios.json`) change only MAC-lane energy. The ROM field is priced at the measured W18 pair, which already includes the MAC: the MAC alone is 0.4 mJ of 117.8 mJ. The V4.1 rows in `results/arch/power_scenarios.json` are pre-S58 (7,049 tok/s/user), so they are stale and not used. A and B therefore differ by less than 1% here.

| 1M | ROM C1 (508 dies, 960 stacks) | HBM TP-96 (96 dies, 384 stacks) | ROM/HBM |
|---|---:|---:|---:|
| Per-user AR / MTP tok/s | 2,347.4 / 3,539.3 | 2,261.7 / 4,847.7 | 1.04 / 0.73 |
| b1 system W, ICG / PG | 31,169 / 6,118 | 10,101 / 9,010 | |
| b1 AR tok/s per kW, ICG / PG | 75.3 / 383.7 | 223.9 / 251.0 | **0.34 / 1.53** |
| Best batch tok/s (AR; MTP lower on both) | 80,834 (head-bound) | 25,293 (batch 32) | 3.2 |
| Best-batch system W, ICG / PG | 40,480 / 24,834 | 22,638 / 19,751 | |
| Best-batch tok/s per kW, ICG / PG | **1,997 / 3,255** | 1,117 / 1,281 | **1.79 / 2.54** |
| mJ/token at best batch, ICG / PG | 501 / 307 | 895 / 781 | |

At 200K the best-batch ratio is 1.63 (ICG) / 2.53 (PG), and the b1 ratio 0.35 / 1.60.

**Where ROM wins.** It reads no weights from HBM.
- The HBM machine spends **1,422 mJ/token** on weight bytes at batch 1 (13.03 GB/token), and still 419 mJ at batch 32.
- The ROM's HBM traffic is KV and index keys only, at 5.7 mJ/token.
- The ROM's whole dynamic energy is about 122 mJ/token: field 51.6 + busy-pair clock 27.5 + x-net 13.3 + stack 5.1.

**Where ROM loses.** Static power.
- Layer dies: 464 × 50.2 W ≈ 23.3 kW. Of each die's 50.2 W, the SerDes always-on is 30.6 W; PAR2 doubles the die count and therefore this term.
- 960 stack idles: 2.7 kW.
- Table dies: 3.3 kW.

Without stage power gating, a lone user costs 31 kW. So at batch 1 the ROM is 3× worse per kW, and with PG it is 1.5× better. MTP also hurts the ROM: its verify pass is 2.35× AR, against 1.58× on HBM, so ROM MTP saturates at 35k tok/s.

## Iso-total-silicon and cost (user correction: HBM counts as silicon)

**HBM stack silicon.** Each stack is 8-high (22.5 GB = 24 GB class; technology.json) of 121.0 mm² 24 Gb core dies, plus a base die ASSUMED at the 11 × 11 mm footprint. That is **1,089 mm² a stack**. The core-die figure is a public secondary source (Samsung HBM3E, 2024), not a repository record. The base-die area is an assumption.

**V4.1 at 1M.**

| Total silicon | Logic | DRAM | Total |
|---|---:|---:|---:|
| ROM C1 | 399,405 mm² | 1,045,440 mm² | 1.445 M mm² (72% DRAM) |
| HBM TP-96 | 32,688 mm² | 418,176 mm² | 0.451 M mm² (93% DRAM) |

- Best tok/s per total mm², ROM/HBM: **1.00 at 1M** and **0.61 at 200K**.
- Counting logic only, the same ratio is 0.26 / 0.16.
- Per-user rate does not change with replication: AR 1.04×.

**Qwen3-8B at 8K.**

| Ratio, ROM option C (4 dies, 16 stacks) over HBM 2 × 4 | Value |
|---|---:|
| Saturated tok/s per total mm² | **1.61** |
| Saturated tok/s per logic mm² only | 0.96 |
| Saturated tok/s per kW | 1.20 |
| Per user | 9.6× AR, 3.7× DFlash |

**Cost basis.** This uses `tools/uarch_model.py` FAB/`mfg_cost`:
- logic at the $16,988 N5 wafer with negative-binomial yield, about $0.69/mm² for the ROM die;
- HBM per **stack** at an ASSUMED $360, which implies about $0.33 per DRAM mm². The repository has no DRAM $/mm².

**V4.1 by cost.**
- Capex: ROM $1.43–2.19M against HBM $0.264M.
- Best tok/s per k$: 56.4–36.8 against 95.8, so ROM/HBM = **0.59–0.38**.

**Qwen by cost.** Saturated tok/s per k$, ROM/HBM: **2.3**.

**The bases behind the published ratios.**
- consolidation `comparison_rule` "equal area": 169,520 mm² against 5 × TP-96 at 163,440 mm². This is **logic only; it excludes HBM DRAM and base dies**, and is the stale 188-die ROM.
- "equal cost": capex. It counts HBM at $360 a stack.
- "equal power": 19,421 W of saturated system power. It counts stack traffic and the 2.8 W idle, with the gated policy.

Qwen's MICROARCH comparisons are iso-area or equal-package (memory `qwen3-comparisons-are-iso-area`), with logic area only.

## Q3. m MAC columns per ROM word, τ = 4

**Method.** The verify pass (P = 6, γ 5) is re-timed in the model so that each field node issues ⌈6/m⌉ word-times. On top of that:
- the PAR2 delta (+70.4 µs a verify pass) is added;
- the ROM draft is 50.0 µs (0.1173 × AR, the HBM DSpark structural ratio; the model's assumed 3/40 gives 32 µs).

**Today, m = 1.** The ROM verify pass is **2.35× AR** (model 2.38×), against **1.58×** on HBM (700.85 / 442.14). The requested 2.7× was not reproduced from current records.

**The HBM comparator at τ = 4.** 4 / (700.85 + 51.88 µs) = **5,314 tok/s** at 1M, and 5,326 at 200K.

**Area.** Each extra column adds per die, at 0.60 placement:
- **62.3 mm²** if MAC + tree is 60% of the element's std cells;
- **103.8 mm²** if the whole element is replicated except capture.

Basis: q 1,686 × 24,298 µm² and BF 362 × 63,609 µm². Reticle margin is 71.8 mm², so only m = 2 at the lower bound fits on 858 mm². Otherwise the field must spread over more stages. The two plans:
- **reticle-full**: pairs per die rescaled to fill 858 mm²;
- **keep 91.6%**.

Each added stage costs one hop at the model's 0.407 µs (≥ 0.130 µs board link alone), on both the AR and the verify paths.

| m | +mm²/die at S58 | Stages / dies (reticle-full, lower / upper area) | AR 1M | Verify / AR | τ4 1M | ROM/HBM 1M | ROM/HBM 200K |
|---|---:|---|---:|---:|---:|---:|---:|
| 1 | 0 | 58 / 508 | 2,347 | 2.35 | 3,813 | 0.72 | 0.78 |
| 2 | 62–104 | 58 / 508 – 63 / 548 | 2,347–2,336 | 1.80 | 4,880–4,868 | 0.92 | 1.02 |
| 3 | 125–208 | 66 / 572 – 79 / 676 | 2,330–2,301 | 1.62 | 5,352–5,314 | 1.01–1.00 | 1.13 |
| 4, 5 | | Same verify as m = 3 (⌈6/m⌉ = 2); strictly worse | | | | | |
| 6 | 312–519 | 94 / 796 – 125 / 1,044 | 2,269–2,206 | 1.43 | 5,854–5,748 | **1.10–1.08** | **1.26–1.23** |

**Best m.** Latency alone picks m = 6: +8–10% over HBM at 1M and +23–26% at 200K. It costs 1.6–2.1× the dies and gives up 3–6% of AR. m = 3 reaches parity at 1M and +13% at 200K, for +13–33% dies.

**Unpriced blockers.**
- Each column multiplies the element x stream by m. The q channel goes from 1,113 to m × 1,113 of 2,881 tracks, and **BF is already 76% subscribed**, so m ≥ 2 on BF and m ≥ 3 on q exceed today's channel.
- The 50% field-concurrency di/dt cap was set for one MAC column.
- The extra dies add static power (Q2), which erodes iso-power.

None of this is adopted. Under AGENTS rules, m ≥ 2 needs a q/BF element closed at SS/FF in context first.

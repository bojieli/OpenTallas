# DeepSeek-V4.1-Flash ROM array: logical map, link topology and rack

Status: an analytical design, 2026-09-27. Nothing here is a routed rack or a measured result, except gate C7 (collective overlap), which the RTL stage bench measured as NOT met and which adopted collective levers partly recover (§5, `results/rtl/v41_stage_collective_campaign.json`, `results/rtl/v41_collective_levers_campaign.json`). Gates C4 (SerDes power), C8 (two-die link bandwidth) and C10 (head-die draft KV) pass analytically on record-bound numbers (§5.1, record key `gates`). Ported from v41-rack-gates 0facdc17 and regenerated on main's inputs: the rates below are a conditioned design-point model result using bench-measured collective tails, not measured chip throughput (`results/arch/v41_lanes.json` `design_point`, with the adopted levers; the ablation without them in `design_point_no_levers`; overlap-assumed in `design_point_overlap_assumed`), and the power is on `configs/hardware/technology.json` production values (logic leakage 0.10 W/mm², one value for every model since 2026-09-27) with the power-scenario cooling classes. The spec and budget under the design point are the single V4.1 budget model, `tools/arch_budget_v41.py` (`results/arch/arch_budget_v41.json`).

- Model: `tools/v41_rack_design.py`, recorded in `results/arch/v41_rack.json`, tested by
  `tests/test_v41_rack_design.py`.
- Figures: `tools/v41_rack_figures.py` writes `results/arch/figures/v41_rack_{logical,elevation,links,compare}.html`
  and a preview page; `--splice-atlas` rewrites the atlas section from its template (off by default: the atlas
  section is curated, so only the `<svg>` bodies are replaced).
- Inputs:
  - die roles: the spec's integer placement, `results/arch/v41_die_placement.json`;
  - package lanes: requirement R-L9, `results/arch/v41_lanes.json`;
  - rates and power: the spec's budget and utilisation records.
- The layout is Codex's rack design (codex/v41-integration, b667bf38). This document adds the spec's rulings and the
  closed gates (§5), the demonstration plan (§6) and a review (§7).

**Rule (user):** only shipping packaging, links, rack standards, power and cooling are allowed. Every physical
constant in the record's `physical_constants` carries a grade (published, derived, spec or estimate) and a source.

## 1. Logical map

One rack holds one model replica: 188 reticle dies in 94 two-die packages, with 464 HBM3E stacks.

| dies | packages | role | HBM3E |
|---|---|---|---|
| 0-111 | 0-55 | 28 layer stages S0-S27. Stage s is tensor group s: dies 4s..4s+3, packages 2s and 2s+1, one **stage module**. The 40 layers are cut at equal bytes (10.57 GB per stage). | 4 per die |
| 112-115 | 56-57 | head group H (stage 28): lm_head and embedding in BF16 vocabulary quarters, plus the DSpark drafter | 4 per die (spec ruling C10) |
| 116-187 | 58-93 | 72 table dies: the Engram layer-1 table, then the layer-14 table. Gather slices and an assembler only. | none |

**Per-token dataflow.** H picks the argmax. The winning die reads the next token's embedding row locally and sends
it over one ring hop to S0. Each stage then does three things:

- It runs its layer slice.
- Inside the module, it runs the tensor collectives: 80 all-reduces and 129 all-gathers, 10.4 MB of payload per
  token, of which 8.3 MB is the 40 KV-rows all-gathers (2.06 MB without them). Small ones are flat one-shots across the 4 dies. An all-reduce whose payload would outlast a board flight
  runs as a fixed-order reduce-scatter + all-gather (R-L9).
- It forwards the 40,960 B residual, cut through, to the next module.

**Engram gather.** H multicasts the token id through the switch to the 72 table dies, which return 48 rows × 264 B
to S0 and S9. Layer 1's gather completes **1.88 µs** after the argmax, against 3.57 µs of slack.

**KV replicate-on-write** (spec §15.1). Only layers 2, 8, 14 and 20 produce compressed KV; they sit on stages S1,
S5, S9 and S14. Their reader layers sit on S1-S4, S5-S9, S9-S13 and S14-S27. Each new row (288 B main + 68 B index
key) is multicast behind the residual to every reader stage's HBM, so every sparse gather is a local read.

- The multicast rides the ring at 6.6 KB per token across all owners and hops.
- With the replicas and the 40 window rings, the busiest die holds 93.4 MB per user at 1M. That caps the rack at
  **963 users**, matching the spec's 962.

**Prefill KV ingest.** With replicas, **7.84 GB** lands in HBM per 1M-token user, 8.4× the 0.93 GB of owner rows.
Two paths are recorded (`kv_replication.ingest_paths`):

- **Ethernet switch (adopted).** The host sends each owner stream once, 0.93 GB in **9.3 ms** at 2 × 400G. The rack's
  switch replicates it to the reader stages' 4-lane 112G ports (53 GB/s per package). The worst stage's 0.37 GB takes
  3.5 ms, so the NICs bound ingest, and the ring stays free. It needs an RDMA-write (RoCEv2-class) target in front of
  each die's ingest engine.
- **PCIe fabric** (the ingest agent's proposal, commit 0378199a): NICs → a Gen5 switch tree → an x8 endpoint per
  package (24.6 GB/s). PCIe peer-to-peer writes do not replicate, so the NICs carry all 7.84 GB, 79 ms per user. It
  adds about 7 PCIe switches and rack-scale Gen5 cabling, where retimers are usually needed. It also adds an x8 PHY per
  package outside the 90-lane budget.

Either path hides under the ingest agent's ~2.9 s cold 1M GPU prefill when streamed layer by layer.

**On-chip incremental prefill** (the ingest agent's agent-turn mode) writes new owner rows on the owner stage. Those
rows reach the reader stages by the same ring multicast as decode: 6.6 KB of hop traffic per new token. A +32K-token
turn is about 0.21 GB spread over its ~75 ms, a few GB/s, against 184 GB/s per package stage link, so the multicast
fits.

Per token, batch 1, 1M context (`traffic.rows`), at the design point's rates (`results/arch/v41_lanes.json`) with
the adopted collective levers. T0 and T1 carry every collective the design-point DAG issues, including the 40 KV-rows
all-gathers (8.3 MB of payload per token, which the budget's collective list records at 0 B), and the relay, which
halves the T1 words of the all-reduces and the row and select gathers and forwards them over UCIe. The busy column
averages over all links of a class; gate C8 (§5.1) checks the busiest link.

| link class | bytes / token | messages | busy at 28-user fill + MTP |
|---|---|---|---|
| T0 UCIe, in package (tensor-parallel, "TP") | 32.6 MB | 836 | 3.3% |
| T1 on-module trace (TP) | 15.8 MB | 1,672 | 32% |
| T2 stage hops (28 × 40 KB) | 1.1 MB | 56 | 8.6% |
| T2 token return | 10 KB | 1 | 2.2% |
| T3 Engram, through the switch | 13.9 KB | 124 | 10.5% |
| HBM: KV rows + index keys | 188 MB | — | — |

## 2. Link topology

Each package has 90 lanes of 112G PAM4 (13.18 GB/s net per lane). The R-L9 allocation is:

- **TP 52:** each die has 13 lanes to each die of the partner package.
- **Stage 14 + 14.**
- **Switch 4.**
- **Spare 6.**

R-L9 comes from the utilisation agent's search over the TP/stage split. It prices every collective's bytes on its
peer link and every hop on the stage lanes. At 1M it gives:

| split | tok/s/user, without / with MTP |
|---|---|
| R-L9 (recommended), collectives fully overlapped | 8,622 / 23,578 |
| R-L9 with the collective tails measured in RTL and the adopted levers (gate C7, the headline) | 8,185 / 23,818 |
| R-L9 with the collective exposure measured in RTL, no levers (ablation) | 7,579 / 21,006 |
| this study's first split (TP 32 / stage 24 + 24) | 8,572 / 18,839 |

| tier | medium, length | reach limit (source) | latency per hop | bandwidth per link, per direction |
|---|---|---|---|---|
| T0 | advanced UCIe, ~1 mm | ≤ 2 mm (UCIe electrical summary, Hot Chips 2023) | 10 ns | 4.2 TB/s |
| T1 | board trace inside the module, ~120 mm | VSR ≥ 10 cm + connector at 16 dB; MR 20 dB (OIF CEI-112G) | 129 ns | 171 GB/s per die pair (13 lanes) |
| T2 | passive twinax in the rack, 0.25-0.80 m | 2 m DAC (IEEE 802.3ck CR; 802.3df 800GBASE-CR8) | ≤ 213 ns (full KP4) | 0.37 TB/s per module (2 × 14 lanes) |
| T3 | DAC to one 51.2T switch, 0.8-1.6 m | 2 m DAC | 683 ns (two full-KP4 ports + 250 ns Tomahawk Ultra) | 53 GB/s |
| T4 | 2 × 400G optics from the host tray | 100 m-2 km | bulk | 100 GB/s |

**Cables.** Each package's 14 stage lanes go forward on **two 8-lane 800G-class passive DACs** to the same-position
package of the next module. The cables are populated to 7 of their 8 lanes, so the stage stays at 14 lanes per
direction and the package at 90. Each populated lane is a duplex SerDes lane, and its reverse half carries credit
returns, so credits need no extra lanes. That is 116 ring cables in total.

**Latencies are validated** against normative specs and production datasheets (research agent adae6788):

- **On-module TP link (T1):** keeps the 130 ns light-FEC link, band 100-185. The channel is OIF CEI-112G-MR class
  (up to 500 mm and one connector, raw BER 1e-6). The value is re-based to the ~120 mm trace at 6.7 ns/m.
- **Ring cables (T2):** run **full RS(544,514) KP4, 209 ns** (band 160-300), UALink 1.0's un-interleaved in-rack
  mode, with the flight on top at 4.6 ns/m (Broadcom SUE). A light RS(272)-class FEC is **not qualified on
  CR-class copper**: the ETC LL-FEC spec's Annex A needs pre-FEC BER ≤ 9.9e-5, or 8.9e-9 under DFE bursts, and
  IEEE 802.3ck mandates RS(544,514) for CR1. The earlier 130 ns ring hop (risk C2) was therefore optimistic.

- **Every link is within passive reach, so there is no retimer or AEC.** The worst ring hop is 212.7 ns. At
  200G/lane, IEEE 802.3dj passive copper reaches only ≥ 1.0 m, so a 200G-lane refresh would sit near the limit at
  0.8 m.
- **No token-path hop crosses the switch.** It carries only the Engram gather, host traffic and KV ingest (~312 of
  the 512 100G-class lanes that 51.2 Tb/s implies).
- **A stage hop is short.** The 41 KB residual serialises in 111 ns on a module's 28 lanes, and cut-through hides
  most of that.

## 3. Physical design

**Package.**
- Contents: two 815 mm² dies and 8 HBM3E stacks (11 × 11 mm, 36 GB 12-high) on a ~3.3-reticle CoWoS-L interposer.
- Size: drawn at 85 × 85 mm (ESTIMATE). TSMC's 5.5-reticle interposer needs a 100 × 100 mm substrate, and B200
  substrate dimensions are not published.

**Stage module.** One board carries a package pair, with the TP link as 52 lanes per package on a ~120 mm trace.

**Trays (ORv3, 21 in, 48 mm OU).**
- A 1 OU stage tray holds two modules and dissipates **2.54 kW** on cold plates (design point).
- A 1 OU table tray holds four packages, runs at **0.48 kW** and is air-cooled.

**Elevation (bottom-up), 34 of 44 OU:**

| OU | contents |
|---|---|
| 1-6 | six 33 kW ORv3 HPR power shelves: 2N, three per side |
| 7-15 | 9 table trays |
| 16 | Engram/host switch |
| 17-18 | host (2 × 400G NICs for KV ingest, BMC) |
| 19-33 | 15 stage trays, the folded ring: tray t = ring positions t and 28-t |
| 34 | out-of-band management and leak detection |

An all-air variant with 2 OU stage trays needs 49 OU and does not fit.

**Power** is on the **design point**: R-L8's pooled engines doubled, R-L9 lanes, the validated links and power, and
the 1.087 GHz clock. It uses the utilisation agent's record: `results/arch/v41_hbm_switched.json` for energy and the
worst die, and `results/arch/v41_lanes.json` for static power, both on the spec's validated per-die terms.

- **Static per die:**
  - layer die 98.8 W: leakage 54.5, HBM idle 11.2, always-on SerDes 30.6, UCIe idle 2.5;
  - head die 92.3 W;
  - table die 47.8 W.
  - The chips total 14.9 kW, of which SerDes is 3.6 kW.
- **Dynamic:** the design point's energy per token × aggregate rate.
- **Worst-case layer die: 269.9 W** = 98.8 static + 171.1 dynamic, saturated at 1M (`results/arch/v41_hbm_switched.json`
  `rom_worst_die_w`). HBM I/O is **not** added again: its 0.8 pJ/b is already inside the 13.1 pJ/b dynamic HBM
  energy (spec ef93dda0).
- **Wall:** (chips / 0.87 VR + infrastructure) × (1 + 0.6% CDU + 3% fans) / 0.96 PSU. Infrastructure is the 1.5 kW
  physical switch, the host and the management trays.

| operating point | rack input |
|---|---|
| batch 1 | 21.5 kW |
| 28-user fill | 30.9 kW |
| fill + MTP | 35.1 kW |
| saturated + MTP | 42.4 kW |
| worst case (saturated) | 44.9 kW |
| provisioned (1.2 × worst case) | **53.9 kW** |

- **Energy per token at batch 1:** 1.85 J at the chips; 2.46 J at the wall with the switch on a per-port basis; 2.63 J at
  the rack input, which adds the host, management and the physical switch. Every figure charges each user's KV
  reads from HBM. The ROM:HBM energy ratios are not taken from these rack figures but from
  `tools/power_scenarios.py`, which prices the design point and the best HBM comparator on one model (logic dies
  and their stacks): 1.57 J against 5.94 J at 1M, batch 1 (3.8×), and 8.0× at the 28-user fill
  (`results/arch/power_scenarios.json` `rom_over_hbm`, scenario B). That model charges neither machine's always-on
  SerDes (its die static is leakage, clock and HBM idle; links are priced per collective bit only). Adding them, as
  this rack and `results/arch/v41_hbm_switched.json` do, gives about 2.01 J against 6.63 J at 1M, batch 1 (3.3×):
  gate C4's cross-check, not applied here because it moves the published ratio (`gates.C4.power_scenarios_crosscheck`).
- **Check against the spec's rule.** Summing the spec's rule (116 × the budget's 294.8 W provisioned per die +
  tables + infrastructure, `power.reconciliation`) gives about 42.6 kW. The provision here is higher because the
  design point's worst layer die (269.9 W, doubled pools saturated at 1M) is hotter than the spec-width die's
  198.0 W worst case (`arch_budget_v41.json` `power`).
- **Shelves.** The record keeps **three** 33 kW shelves per side (82.5 kW N+1), 2N across the A and B sides: six
  shelves, 1,078 A at 50 V for the 53.9 kW provision.
- **Per package and tray.** The worst layer package is 540 W: 270 W per die against 374.6 W per die for an
  air-cooled and 474.6 W for a liquid-cooled two-die package (power scenarios: B200 HGX / GB200 package ratings
  less their stacks). On the measured ASAP7 MAC lane (power scenario A) a batch-1 layer die is 782 W and the 1M
  rate is capped at 2,947 tok/s (air) / 4,085 (liquid). A stage tray is **2.54 kW** in 1 OU, on cold plates; NVL72's 1U compute trays carry four ~1.2 kW GPUs on
  cold plates.
- **Liquid** carries ~90% of the heat.
- **Weight:** the rack is ~768 kg (ESTIMATE).

The 1.5 kW switch tray and the 700 W/OU air limit have no primary source and are graded as assumptions.

**Why liquid.** At 2.54 kW per OU, the stage trays are above what 1U/2U air cooling handles (ASHRAE TC9.9). The rack
total is above Uptime Institute's 20-25 kW threshold for liquid.

## 4. Comparison (Figure R-4)

| | ROM rack (this design) | GB200 NVL72 | CloudMatrix384 |
|---|---|---|---|
| racks | 1 | 1 | 16 (12 compute + 4 network) |
| accelerators | 94 packages | 72 B200 + 36 Grace | 384 Ascend 910C + 192 Kunpeng |
| power | 53.9 kW provisioned (44.9 kW worst case) | 132 kW provisioned (Supermicro 125-135 kW operating; NVIDIA guide ~120 kW) | ~559 kW (SemiAnalysis, via a search summary; re-check before citing) |
| scale-up fabric | point-to-point folded ring (116 DACs) + on-board TP; one switch off the path | NVLink 5 through 9 switch trays; 1.8 TB/s bidirectional per GPU; > 5,000 copper cables | Unified Bus, all-to-all over 2 switch tiers; 6,912 × 400G LPO |
| built for | one fixed model, pipeline decode, latency-bound collectives | any model; all-to-all TP/EP | large-scale MoE expert parallelism and KV access |

## 5. Gates and conflicts (record key `conflicts`)

| item | status | resolution |
|---|---|---|
| C4 SerDes power | **PASS (analytical)** | Every die-side lane is charged always-on: 84 per layer/head package and 2 per table package, 4,944 lanes at 0.728 W = 3.60 kW, in every rack power scenario (§5.1). |
| C8 two-die link (T1, UCIe) | **PASS (analytical), margin 1.45×** | At the 28-user fill with MTP the busiest T1 link runs at 58% with the adopted relay (109% without it), UCIe at 9.2%, the head module's draft traffic at 69% of a T1 link (§5.1). |
| C10 head-die draft KV | **PASS (analytical); routed floorplan under K2** | 203 KB per user, the same at 1M and 200K; 112 compiler macros in the head die's released engine area, a 7,168-bit read port that meets the model's draft-stage KV sweep; HBM beyond the fill (§5.1, Figure R-5). |
| C7 overlap and clock | **NOT MET (measured)**; clock open | The RTL stage bench (`results/rtl/v41_stage_collective_campaign.json`) exposes 254-cycle all-reduce tails (153-164 modelled) and residual tails of 114 cycles per stage hop and 188 per KV-row gather; fed back with no recovery, the design point would be 7,579 tok/s/user at 1M against 8,622 overlapped (`design_point_no_levers`). Adopted levers, each bit-exact on `ot_rom_oneshot_die_px` (`results/rtl/v41_collective_levers_campaign.json`): relay + 4-word gather on the KV-rows all-gather (653 -> 309 cycles), relay + 3-cycle fold adders on the all-reduces (254 -> 195), a partial stage-hop split (473 -> 419), hc_post early start. The design point is 8,185 / 8,568 tok/s/user at 1M / 200K, about 58% of the loss at 1M (`collective_exposure.recovered_share`); not met. The hop split's extra T1 traffic at batch > 1 is unmeasured; the added queue SRAM, 0.069 mm² per die in total, is analytical (bitcell x an assumed 2.5x two-port overhead; `results/arch/v41_collective_levers.json` `queue_area_per_die`). See §6. |
| C2 FEC on the ring cables | **adopted baseline** | The validation found the light FEC not qualified on CR copper, so the ring runs full KP4 (209 ns). That costs 29 hops × 82.7 ns = 2.4 µs per token (Table R-1). |
| C3, C5, C6 | resolved | Folded-ring one-hop return; 4-stack HBM power; embedding on the head dies. |

### 5.1 Gate verdicts C4, C8, C10 (record key `gates`)

All three are analytical, bound to `results/arch/v41_rack.json` `gates`, and tested in `tests/test_v41_rack_design.py`.
None moves a headline rate or the rack power; the findings that would move other published figures are listed as
cross-checks and open items, not applied.

**C4 SerDes power: PASS.** A 112G PAM4 lane transmits idle symbols when it has no data, so it is charged always-on:
6.5 pJ/b × 112 Gb/s = 0.728 W per duplex lane (technology.json `board_serdes_112g`, published 5.6-7.5 pJ/b).

| lane class | lanes per package | packages | charged |
|---|---|---|---|
| T1 on-module trace (TP) | 52 | 58 | yes, at both ends |
| T2 ring cable, forward (stage out) | 14 | 58 | yes |
| T2 ring cable, backward (stage in) | 14 | 58 | yes |
| T3 switch port, layer and head packages | 4 | 58 | yes; the switch end sits in the switch tray |
| T3 switch port, table packages | 2 | 36 | yes |
| spare | 6 | 58 | power-gated; +253 W if kept hot |

- The 4,944 die-side lanes draw 3.60 kW, which equals the rack power's SerDes term and the budget's 30.6 W per die.
- The switch's own 312 lanes (including the host's 2 × 400G) draw 227 W, inside the assumed 1.5 kW switch tray.
- Passive DACs draw nothing.
- The energy per token also charges each collective bit at 7.0 pJ (board + UCIe), on lanes already charged
  always-on. That double count is conservative: 3.8 W at batch 1 and 369 W at the fill with MTP. It is not removed.
- **Cross-check, not applied.** `tools/power_scenarios.py` has no SerDes term on either machine. With it, the 1M
  batch-1 energy becomes about 2.01 J (ROM) against 6.63 J (HBM), 3.3× instead of 3.8×. The fix belongs to that
  model's owner.

**C8 two-die link bandwidth: PASS, margin 1.45×.**

The busiest stage's collectives are counted as follows (gates.C8):

- **Attention.** Every collective of the layers whose attention starts in the stage.
- **FFN.** The FFN collectives of every layer touching the stage. This is an upper bound: a split layer's router
  gather and combine are charged to both of its stages.
- **KV rows.** The KV-rows all-gathers are included.
- **Hop.** The incoming stage hop is included.
- **No two-step credit.** Every collective is priced as a flat one-shot.

The busiest stage is S14, with layers 20 and 21. Per position it carries:

- **Adopted relay:** 124 KB on one 13-lane T1 link and 485 KB on UCIe.
- **Without levers:** 234 KB and 254 KB.

The relay halves the T1 words of its classes and forwards them over UCIe, doubling the die's UCIe egress. At the
28-user fill every stage holds a user, so it carries the aggregate rate: 800,276 positions per second with MTP.

| operating point | T1, busiest link | UCIe, busiest die | head module T1 (draft) |
|---|---|---|---|
| batch 1, average | 0.6% | 0.1% | — |
| batch 1, while the stage is active (= the fill) | 17% | 2.6% | — |
| 28-user fill | 17% | 2.6% | — |
| 28-user fill + MTP, adopted relay | **58%** | 9.2% | **69%** |
| 28-user fill + MTP, without levers | 109% | 4.8% | — |
| 1,024 users + MTP (reported, not gated) | 112% | 18% | 134% |

- **UCIe burst.** The relay's peak on UCIe is bench-measured at 3 × 512 B per cycle, 40% of the link.
- **Head module.** The draft's collectives (3 window-only stages at the 5-row block, no relay) are the tighter
  gated check.
- **The relay is load-bearing.** Without it the fill with MTP would overrun T1.
- **Saturation.** At 1,024 users with MTP the busiest link, on this upper-bound accounting, would exceed its rate.
  The budget model's occupancy bound does not include the links, so the saturated aggregate (1.29 M tok/s at 1M)
  is not link-checked. This is an open item for the spec owner.

**C10 head-die draft KV: PASS; the routed head-die floorplan remains under K2.**

- **State, from the released model.** V4.1's `inference/model.py` `DSparkAttention` asserts `compress_ratio == 0`
  and keeps one 128-row window ring per stage. `config.json` gives 3 MTP stages and a 5-row block. The draft never
  reads the compressed context, so its state is 3 × 128 rows × 528 B = **203 KB per user, the same at 1M and
  200K**: 50.7 KB per head die with the rows striped 4 ways.
- **Size.** The 28-user fill needs 1.42 MB per head die, 2.84 MB double-buffered.
- **Capacity at 1M and 200K.** At the capacity points (962 users at 1M, 5,018 at 200K) the windows take 48.8 MB and
  254 MB of a head die's 90 GB of HBM.
- **Allocation.** The 112 compiler macros (`ot_sram_1r1w_1024x256_m2_r2c2`, 3.67 MB) form a 1.77 × 1.06 mm =
  1.87 mm² block. It sits in the 64.8 mm² of engine area the right-sized head die releases
  (`results/arch/v41_utilization.json` `nonlayer_right_size`), so no ROM is displaced.
- **Correction: the head die has no spare ROM.** Its 69 MB of "spare ROM" holds Engram spill
  (`v41_die_placement.json`). Putting the block in ROM instead would re-spill 41.7 MB onto the layer dies, whose
  remaining spare is 0.97 GB.
- **Port.** The model prices the draft stage's KV sweep at 31.5 cycles: the die's 16.9 KB window quarter × 5 block
  rows at the design point's 2,685 B per cycle. The earlier one-row-per-slot organisation (128 B per cycle) needed
  134 cycles, which costs 32 tok/s/user at 1M with MTP. The adopted organisation fixes this:
  - four banks of 28 macros;
  - a slot interleaved across one bank, reading 896 B per cycle;
  - 21 cycles including the 2-cycle registered read, a 1.5× margin;
  - four users can read at once;
  - a bus channel estimated at 328 µm, on four layers at 80 nm pitch.

  The write port carries at most 2.4 KB of new rows per verify per die.
- **Beyond the fill, the head HBM.** At 1,024 users the windows take 51.9 MB per die, 0.06% of its 4 stacks. A
  user's window prefetches into the slot's second buffer in 1.01 µs (1 µs first access), under the 14.2 µs draft.
  At saturation with MTP the paging reads 13 GB/s per die, 0.4% of its HBM.
- **Fallback, priced.** If the windows were read from HBM unstaged, each of the 3 stages would pay the first access
  on the draft path. That costs 0.76-3.0 µs per verify cycle: 23,731-23,481 tok/s/user at 1M with MTP, against
  23,818, and 24,770-24,496 against 24,864 at 200K.
- **Open items.**
  - **Head-group occupancy at the fill with MTP.** A draft takes 14.2 µs and 28 run per 210 µs verify cycle, so
    about 1.9 drafts must overlap on the head dies' engines. The rate model prices each user's draft serially and
    does not check this. The SRAM's four banks allow four concurrent readers.
  - **Draft conditioning.** The attention inputs of layers 37-39 (3 × 5,120 BF16 per verified position, 184 KB per
    verify) must reach H behind the residual. This is unpriced: up to 0.50 µs of serialisation on the S27 → H hop
    (0.24% of the period) if not overlapped.

**Table R-1** (1M, batch 1, `reprice_sensitivity`):

| case | tok/s/user |
|---|---|
| overlap assumed (130 ns hops, before the validation) | 8,858 |
| design point on the R-L9 lanes (209 ns ring hops), collectives fully overlapped | 8,622 |
| design point with the collective tails measured in RTL and the adopted levers (headline) | **8,185** |
| headline with the ring cables' actual flight beyond the 209 ns | 8,178 |
| overlapped point with every collective payload serialised, bytes only (not a bound) | 8,295 |

The bytes-only row charges serialised bytes but not the fold, hop and row-gather tails the RTL bench measured, so
the headline lies below it: it is not a bound. On validated static power, the ROM chip energy at batch 1
is **1.85 J per token** (2.46 J at the wall with the switch): static power dominates at batch 1.

The spec's budget, the ladder and R-L9 are derived on the validated links and on the single budget model
(`tools/arch_budget_v41.py`, 2026-09-27). The spec agent notes that the two-step all-reduce choice may change now
that an extra board crossing costs 130 ns.

## 6. Demonstration plan (record key `demonstration_plan`)

**Whole-system clock.** There is no rack-wide synchronous clock:

- every package runs its own PLL from a tray-local reference;
- die-to-die inside a package is source-synchronous UCIe;
- every board and cable link is plesiochronous (IEEE 802.3 PHYs tolerate ±100 ppm), with an elastic buffer in the
  endpoint's 4-cycle clock-domain crossing.

| step | what | status | acceptance |
|---|---|---|---|
| K1 | per-block closure | exists for the qualified blocks; design-point pools pending | post-route WNS ≥ 0 at 1.087 GHz, read from `pnr.json`, never pre-layout |
| K2 | layer-die and head-die P&R | blocked on the spec's P&R gate (R-U2, R-U9 in RTL) | the routed die closes at 1.087 GHz at the signoff corner |
| K3 | plesiochronous link endpoint | **PASS** (`results/rtl/v41_link_cdc_campaign.json`; `rtl/rom/ot_rom_link_cdc.sv`: async FIFO, Gray pointers, open-loop idle insertion, latched overflow; ported from v41-rack-gates 36bc14e2 / 965f07d8, tested by `tests/test_v41_link_cdc.py`) | 1.41 × 10⁹ flits across two clocks at 0, ±100 and ±200 ppm (10⁹ at +200 ppm): zero mismatches, overflows or underflows. The idle-starved negative case latches overflow, as required. Crossing latency is 3.0–4.2 RX cycles with 2-flop synchronisers, inside the budgeted 4 (+1 output register). 3-flop synchronisers take 5.2, i.e. +1 cycle (~0.9 ns) per hop if the MTBF analysis requires them. |
| K4 | two-module system run | to build | 8 dies on independent clocks, reduced vehicle bit-exact, cycle count within 2% of the model |

**Collective overlap.** The claim is that a partial streams onto its peer links as the matvec produces it, so only
the last beats plus one hop are exposed. The link parameters are:

- 13 lanes per peer, 158 B/cycle;
- stage 170 B/cycle per package;
- the hop is 141 cycles at 1.087 GHz.

| step | what | status | acceptance |
|---|---|---|---|
| O1 | one-shot unit at the rack link rate | exists at optimistic all-to-all UCIe links (`results/rtl/hdc_package_tp_campaign.json`) | two remote peers on the T1 model: a 20 KB all-reduce completes ≤ 40 cycles after the last partial beat (R-U3) plus one hop; the two-step variant bit-identical on all 4 dies |
| O2 | producer-chased collectives in a stage module | **NOT MET (measured)**: `results/rtl/v41_stage_collective_campaign.json` (44 cases bit-exact), fed into `results/arch/v41_lanes.json` `collective_exposure` | exposed collective time per token ≤ the lane model's 0.93 µs; measured 12.5 µs of exposed collective bytes without recovery; with the adopted levers (`results/rtl/v41_collective_levers_campaign.json`, 55 cases bit-exact) 4.8 µs, and the headline is 8,185 tok/s/user at 1M against 8,622 overlapped |
| O3 | link bench parameters | stale: `rom_pkg_link_campaign` uses 1,800 B flits (1.8 TB/s) | FLIT_BYTES set to the R-L9 stage and TP rates |

The headline rates carry the bench-measured O2 tails with the adopted levers and stay conditional on K2 and on O1, whose rack-rate record has not landed.

## 7. Review of the Codex rack design against the user's rules

It meets the rules:

- shipping ORv3 and 50 V busbar;
- passive-copper reach everywhere, no retimers;
- 4 HBM3E per layer die;
- every constant cited or graded.

Errors found and fixed on this branch:

1. **Coverage test.** `test_prose_figures` failed at b667bf38. `docs/ARCH_SPEC_V41.md` gained an annotated figure but
   was not pinned in `REQUIRED_COVERAGE`. It is now pinned: 1 annotation, total 1,166.
2. **Head-die HBM.** The spec prose said the head dies have no HBM; the spec's C10 ruling gives them 4 stacks. The
   paragraph now says so. R-U1's "no HBM stacks" for non-layer dies is the spec owner's to amend.
3. **Ring cable count.** The first figure caption said 116 cables, and a later edit changed it to 58. Under R-L9 it is
   116: 29 hops × 2 packages × 2 eight-lane DACs. It is now computed from the lane record.
4. **Stale lane split.** Figure R-3's caption and the tray top view quoted the first lane split. They now read R-L9.

Open, not fixed here:

- **Unrecorded capacity cost of the KV map.** `docs/V41_HBM_KV_PLACEMENT.md` reserves all four owners' KV in one
  four-die domain. Under replicate-on-write each stage needs only the owners its readers use. The four-owner reserve
  costs about 64 MB per stack per user, against 23 MB for the busiest stage, and the document does not state this.
  This belongs to the runtime owner.
- **Stale CDC stand-in in the package-link RTL.** It models the clock crossing as a single-clock delay line; the
  K3 crossing (`rtl/rom/ot_rom_link_cdc.sv`) passes on its own bench but is not yet integrated into it.

# Handoff to Codex: DeepSeek-V4.1 ROM array, Scenario C

**Status:** owner-approved direction (2026-10-03), priced **model-only**. No RTL, P&R or model inference behind any number here.

- **Record:** `results/uarch/dsrom_return_storage_hbm_20261003/model.json`, section `scenario_c`. It also holds `baseline_at_model` and `scenarios`.
- **Tool:** `tools/dsrom_return_storage_hbm.py` (`run`, then `compose`).
- **Branch:** `claude/dsrom-return-storage-hbm-20261003`. It was first priced at ad04a76d3 and re-priced at 3a0c114d8, on the unified model of merged origin/main (32d865831 and later).

## 1. What C is

| Change | Today (C1) | Scenario C |
|---|---|---|
| Return tree | 64-deep node FIFOs, no backpressure (138.5 Mbit at NP 8192) | Credit-based: RD = 4 a node side, roots keep 128, one extra 8-row buffer a pair (6.8 mm² at NP 4096) |
| Padding | Power-of-two NP (721 padding sites at S58) | Non-power-of-two tree: compiled sites = active pairs |
| Rank | PAR2: 2 shard dies per rank | **One die per rank** (PAIR1) |
| Stages | 58 | **73** (2,682 pairs a die, die screen 855.9 mm²) |
| KV HBM | 4 stacks on every shard-0 die | 4 stacks on the **32 index-scanning rank dies**, 1 on the other 260, 4 on each of the 8 head dies: **420** |
| Legacy complement | 287 mm² of the inherited 418 mm² debit is unmapped | Remove it, replacing it by explicit per-die rectangles. **Not yet credited in S73**; see W4. |

## 2. Numbers (model, `scenario_c.restated`)

In each a/b pair, a is the 1M value and b the 200K value.

| | C1 today | **C** | HBM accelerator (a3ed9c36d) |
|---|---:|---:|---:|
| Dies / packages | 508 / 254 | **336 / 168** | 96 |
| HBM stacks | 960 | **420** | 384 |
| Logic mm² | 399,405 | 284,517 | 32,688 |
| Total silicon incl. DRAM (M mm²) | 1.445 | **0.742** | 0.417 (DRAM at 1,000 mm² a stack) |
| Static kW, ICG only | 30.9 | 19.9 | 5.37 |
| Static kW at batch 1, stage+link PG | – | **7.07** | – |
| Dynamic kW at best batch (a/b) | 9.59 / 8.27 | 9.59 / 8.27 | – |
| AR tok/s per user (a/b) | 2,324 / 2,419 | **2,490 / 2,600** | 3,015 |
| MTP at τ 3.649 (a/b) | 3,523 / 3,835 | **3,763 / 4,121** | 6,001 |
| MTP at τ 4 (a/b) | 3,796 / 4,128 | **4,051 / 4,433** | 6,579 |
| Best-batch tok/s per kW (a/b) | 1,997 / 2,064 | **2,742 / 2,870**; 3,619 / 3,891 with PG | n/m; comparator 1,117 |
| Batch-1 AR tok/s per kW, 1M | 74.6 | 123.3; **338.2 with PG** | 308.5 |
| Batch-1 MTP tok/s per kW, 1M | – | **488 with PG** | ≤ 424.5 |
| Best tok/s per M mm² total | 55.9k | **109.0k** | comparator 56.1k |

**Readings:**
- C beats C1 on everything:
  - per-user rate +7.2%;
  - dies −34%;
  - stacks −56%;
  - silicon −49%;
  - best-batch tok/s per kW +37%.
- C beats the HBM accelerator per kW at batch 1 **only with stage power gating**, and per M mm² at best batch.
- C loses per-user rate to the HBM accelerator: AR 0.83×, MTP 0.63×. That is the verify problem (§5), unchanged by C.

**How the re-run moved the baseline.** HEAD's model moves the PAIR1 baseline from 2,563.7 to 2,535.5 at 1M. The drop is the 32d865831 hub-edge wire: 57 hops × 75 ns = 4.27 µs, against a measured 4.34 µs. The stage hop is therefore priced at 0.482 µs (0.407 + 0.075).

**S73, not S69.**
- The 64.55 mm² post-r4 increment has only about 6.5 mm² traced:
  - per-die terms: the PAR2 two-port corridor 4.32, the selector, capture and clock terms;
  - per-element terms: about 1.2.
- About 58 mm² (694.88 → 753.03) has no per-term ledger.
- S69 is upside: 16 dies and 1.9 µs.

## 3. Workstreams (parallel)

Host placement follows `/tmp/claude-review-20261003/FLEET_AND_FLOW.md`. Every job above 10 GB goes through `admit.sh`. Every long job is detached with a manifest and an exit file. Successor records are new files: **never overwrite a pinned original.**

### W1. Credit-based return tree: RTL, exact gate, occupancy

- **Files:** new `rtl/v41rom/ot_v41_ret_credit.sv` (node and root with a credit counter, RD and ROOTD parameters) and a generator option beside `rtl/v41die/ot_v41_retn_w17w10.sv`.
  - Keep `ot_v41_ret.sv` and `ot_v41_retn_w17w10.sv` untouched as the reference.
- **Reuse:**
  - the return lifetime audit 93efabc2d (the occupancy-join harness that was never run);
  - the return scaling source audit `tools/dsrom_return_scaling_source_audit.py`;
  - `tools/model_dsrom_return_calendar.py`.
- **Gates:**
  1. bit-exact against golden and against the 64-deep reference on the L0 and L20 programs, with golden csum order kept;
  2. zero overflow faults, and a credit stall never deadlocks the root's held-sibling buffer;
  3. measured peak occupancy per node and root, and the cycles per matvec against the reference.
- **Acceptance:**
  - the rate loss is ≤ 1% on the busiest stage;
  - the area is ≤ 7 mm² at NP 4096, synthesised on ASAP7 at SS;
  - the credit loop is ≤ 4 cycles, measured.
  - If the RD needed to stay inside 1% is greater than 4, re-price with the measured RD.
- **Hosts:**
  - Icarus or Verilator benches on ot-agidock128;
  - synth+STA screens on ot-agidock128 with ≤ 16 threads;
  - the full-die occupancy join on ot-pve1.
- **Depends on:** nothing. Start first.

### W2. Re-partition to one die per rank at ~73 stages

- **Outputs:** regenerated successor records under a new `results/uarch/dsrom_s73_pair1_<date>/`:
  - macro inventory (successor of `dsrom_4096_reticle_inventory`);
  - stage map (layer → stage → rank, 2,682 active pairs a die, non-power-of-two);
  - area ledger (successor of `dsrom_reticle_fixed_debit_reconciliation` model-r4, with the 4.32 mm² PAR2 corridor removed);
  - physical contracts (die I/O and links with no UCIe owner crossing).
- **Reuse:**
  - `tools/dsrom_4096_partition_token_options.py`;
  - `tools/dsrom_4096_reticle_inventory.py`;
  - `tools/dsrom_reticle_fixed_debit_reconciliation.py`;
  - `tools/hdc_program_v41_array.py`.
- **Ledger task:** trace the untraced ~58 mm² of the 64.55 mm² post-r4 increment, which runs from 694.88 to 753.03 (`topk_finite_track_turn_model` r2, `dsrom_selected_parent_caller` r7). Classify each term as per-die or per-element.
  - If at least ~50 mm² is per-die, re-select S69.
  - Report both.
- **Gate:** for every die, field + services + return + RNE + WAKE ≤ 858 mm² from the regenerated ledger. The weight-to-macro map must be complete: every one of the shipped weights is placed exactly once.
- **Hosts:** ot-agidock128 (Python).
- **Depends on:** W1's RD, for the return term (use RD = 4 provisionally), and W4 for the debit.

### W3. KV stack re-allocation, HBM PHY and shoreline

- **Change:** 4 stacks on the rank dies of scanning layers 2, 8, 14, 20, 24, 28, 32 and 36; 1 stack elsewhere. The head dies keep 4.
- **Price:**
  - the saved HBM PHY is 3 × 10 mm² = **30 mm² a one-stack die** (24–45 for PHYs of 8–15 mm²), 7,800 mm² over the array;
  - **25.5 mm of edge** is freed a die;
  - if every rank die took the credit, the stage count would be **S68** (S66–S69).
- **Gates:**
  1. the model's busiest stage stays below the head bound with 1 stack. Check that the window-KV and row gathers on 1-stack dies stay latency-bound, which raw.json shows only for the index reader;
  2. at batch 216, 1M fits one stack on the busiest non-scan die (per-user state 93.5 MB on the busiest die);
  3. the HBM controller is sized per stack count.
- **Reuse:**
  - `tools/hbm_gpu_floorplan.py` for shoreline;
  - `configs/hardware/technology.json` `hbm.hbm3e`;
  - `consolidation.json` `shoreline`.
- **Hosts:** local or ot-agidock128 (model).
- **Depends on:** W2's stage map, for which dies are scan dies.

### W4. Padding trim and removal of the legacy complement, in the area ledger and floorplan

- **Change:** replace the uniform 418.27 mm² inherited debit by explicit per-die rectangles: IO/PHY (HBM, SerDes; no UCIe owner port), halos, clock/PG/decap, DFT. Delete the 287.02 mm² unmapped complement.
  - Non-power-of-two return tree: needs a generator change in the `ot_v41_retn` generator; coordinate with W1.
- **Sensitivity** (`complement_removal_sensitivity`):

| Explicit E replacing the 287 mm² | Stages | Dies |
|---|---:|---:|
| 287 (kept) | 73 | 336 |
| 150 | 54 | 260 |
| 75 | 48 | 236 |

  - Adopt only from the regenerated ledger.
- **Gate:** a die-level floorplan with abstracts (black boxes) for every element. The rectangle union must have no overlap, the PDN and clock must be legal, and the result ≤ 858 mm².
- **Hosts:** ot-epyc1tb (die-level floorplan, global route, PDN; NUM_CORES 16–24; `admit.sh`).
- **Depends on:** W2's inventory.

### W5. Power gating of idle stages and links

- **Price:**
  - a stage is gated except while it carries a token plus one pre-woken neighbour;
  - logic keeps 10% of its leakage and links keep 10% (both ASSUMED);
  - static at batch 1 falls **19.9 → 7.07 kW**;
  - batch-1 AR goes 123 → **338 tok/s per kW**, against 308.5 for the HBM accelerator;
  - best batch goes 2,742 → 3,619 tok/s per kW.
- **Needed:**
  - header/footer PG domains per stage die, with isolation and wake ordering;
  - a SerDes lane-sleep with re-lock inside one stage time (~5.5 µs);
  - a pre-wake signal one stage ahead of the token;
  - measured wake latency and inrush, which must not add to the token path.
- **Gates:**
  1. an RTL bench showing zero added token cycles with pre-wake;
  2. the PG residual from Liberty leakage of the gated cells;
  3. the PDN droop at wake, within the supply budget.
- **Not gated:** the Engram table dies (3.3 kW). They become the largest always-on term; gating them is a follow-on.
- **Hosts:** ot-pve1 (PG RTL sims, medium memory); ot-agidock128 (Liberty screens).
- **Depends on:** W2's stage map.

### W6. Re-run the DS ROM system RTL and collectives on the new partition

- **Reuse:**
  - `tools/rtl_hdc_v41_array_campaign.py`;
  - the 8-die collectives bench of the C5hc gate (4ec2eef0e);
  - `tools/dsrom_par2_boundary.py`, as the negative: there are no crossings in PAIR1.
- **Gates:**
  1. the reduced V4.1 token is bit-exact end-to-end on the S73 stage map;
  2. the measured per-stage cycles and the TP-4 collectives are within 2% of the model's 2,490 / 2,600 tok/s;
  3. the measured stage-hop cost against the priced 0.482 µs.
- **Hosts:** ot-epyc1tb for the full-token sims (`admit.sh`); ot-pve1 for die runtimes (~13 GB).
- **Depends on:** W1 (credit tree in the field) and W2 (stage map).

### W7. Physical feasibility on EPYC

- **Scope:** the hierarchical die (abstracts, no flat runs) for one non-scan rank die and one scan rank die, which carries 4 HBM PHYs.
- **Gates:**
  1. placement legal;
  2. global route with no overflow above 1%;
  3. PDN IR within budget;
  4. the one-stack edge plan for SerDes and HBM.
- **Hosts:** ot-epyc1tb, ≤ 4 concurrent ORFS runs, NUM_CORES 16–24, ORFS work under /home (never /tmp).
- **Depends on:** W4's floorplan and W3's PHY placement.

## 4. Order and dependencies

| When | Workstreams |
|---|---|
| Start now, in parallel | W1, W2 (provisional RD = 4), W3 (model part), W5 (model and PG RTL) |
| After W2 | W4, then W7 |
| After W1 and W2 | W6 |

Re-price C after W1, W2 and W4 land, using `python3 tools/dsrom_return_storage_hbm.py compose` with the measured RD, stage count and debit.

## 5. Later, a separate priced step: multi-column verify (m > 1)

C keeps m = 1 verify, so MTP at τ 4 is 0.62× the HBM accelerator at 1M. Price m = 2…6 on the C baseline as a separate study:
- the extra field columns per die;
- the effect on per-die area, and therefore on stages;
- verify time against the m = 1 verify of 933 µs at this model, including the 15 extra hops of C.
- the τ-weighted rate.

It is not part of C's acceptance.

## 6. Reporting format (every workstream)

- **Commit:** on a `codex/dsrom-c-<wN>-<date>` branch, with a `results/.../model.json` and a REPLAY.md (exact commands and pins, sha256 of each input).
- **Report** (≤ 300 words):
  - what was measured and what was modelled;
  - the gate verdicts;
  - the delta against the C numbers in §2, in tok/s, mm², kW and dies;
  - any successor record created, and confirmation that the pinned originals are unchanged.
- **Labels:** every figure is marked measured, model or ASSUMED.

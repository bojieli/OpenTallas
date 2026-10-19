# MU.S81.SCANCHK: the S81 index scan at p4l's real HBM stack count (10-18)

Lane S81-SCANCHK (analysis). Tool: `scan_stacks.py` → `scan_stacks.json`. Grade: **priced**. This is an analytic
scaling of the measured 4-stack reader bench. No new simulation was run.

## Answer

**p4l has 1 HBM3E stack a die, and the composition charged 4.** So the check owed by ROM-MULTIUSER finding 6 is confirmed.

| fact | value | source |
|---|---|---|
| PHY blocks on the p4l die | **1**: `phy_hbm`, `ot_hbm3e_phy_v41x_aw30_e8p5`, 8,500 × 1,177 µm | `results/arch/s81_dv_1016/p4l/plan.json` blocks[kind=phy] |
| Pseudo-channels on that PHY | 32 (NPC 32) = one HBM3E stack (abstract area 10 mm² "a stack") | PHY abstract `.json` interface.parameters |
| Controllers | 16 `dsfd_ctrl_rg2` × 2 PCs = 32 PCs on the one PHY | SPEC.md 0b-p4g |
| Composition basis | 10-04 reader "W11 quarter-per-stack": **4 stacks a rank die**, peak 4 × 32 PCs × 32 B / 1,024 ps = 4 TB/s | `results/rtl/dsrom_1m_measured_20261004/reader.json`, `tools/dsrom_1m_measure.py` |

Every S81 layer die is the same p4l die, so there is no separate "scan die" with more stacks.

## Index-scan stage cycles at 1 stack

**Model.** The reader runs per stack and is bound by its pseudo-channels: it measured 91.9–94.4% of peak. A rank's keys
are fixed, so the reader time grows by 4/s, where s is the number of stacks.
- Re-index gathers: only the bank-group bound (261 cycles) scales. The rest of the 757 measured cycles is latency.
- The +72 settle/latency and the +44 die-tile adders do not change.

| node | composed (4 stacks) | 1 stack | Δ | 2 stacks |
|---|---|---|---|---|
| L20 idx.score (ratio 1, 262,144 keys a rank) | 5,937 | **23,400** | +17,463 | 11,758 |
| L2 / L8 / L14 idx.score (ratio 2) | 2,951 | **11,456** | +8,505 each | 5,786 |
| L24 / L28 / L32 / L36 re-index gather | 873 | **1,656** | +783 each | 1,134 |

**Not charged: the CKV selected-row gather.** At 1 stack its data time is about 221 cycles a die. That fits inside the
measured 434-cycle arrival window, which is bound by engine ingest. If the gather were fully exposed, the upper bound
would be about 6.3k cycles (−0.6% AR).

## S81 single-user rate at 1 stack (recomputed)

All scan nodes are on the critical path (slack 0), so the AR token grows by ΣΔ = **46,110 cycles**. MTP pays that once,
plus the L20 stage (still the slowest verify stage) once more per wavefront position: 5 × 17,463.

| | composed 10-18 (4-stack basis) | **p4l 1 stack** | study estimate |
|---|---|---|---|
| AR tok/s | 1,243.0 | **1,186.4 (−4.56%)** | 1,173 (−5.7%) |
| MTP tok/s (τ 4.159) | 3,806.2 | **3,454.7 (−9.24%)** | 3,412 (−10%) |
| Ledger basis (10-09 DAG, `accepted_cost` rule) | – | AR 5.27%, **MTP 10.18%** | – |
| Aggregate AR (shift calendar, II = L20 stage 52.6k) | 33.6k | **22.5k** (19 users) | 21.1k |

- **Why the study's estimate is a little more pessimistic:** it scaled the scan by the stage factor K = 1.0575 and multiplied the re-index gathers by 4 as well.
- **Independent check:** S81-BALANCE (claude/s81-balance-1018 61f744110) got AR 1,189 / MTP 3,461 for the same case.
- **MTP floor:** 3,454.7 is still above the owner floor of about 3,000.

## Ledger (proposed row)

The row is in `results/arch/accepted_cost_ledger_1013.json`, group **S81.SCAN_STACKS_P4L**, status **proposed**.
- **Unit:** measured 23,400 against price 5,937 (L20).
- **Loss:** e2e AR 5.27%, MTP **10.18%**.
- **Limit:** `within_unit_limit = false`, because MTP exceeds the 5% unit limit.
- **S81 totals:** proposed rises from 0.87% to 11.05%. Accepted + proposed rises from 2.93% to 13.11%, against the 15% limit.
- **Decision needed:** the owner or coordinator must decide (accept with an owner exception, or adopt option D).

## Options

| option | single-user AR / MTP | aggregate | area / die plan cost | verdict |
|---|---|---|---|---|
| **A. more stacks a scan die**, 2 stacks (16 full-scan dies = 4 layers × 4 ranks) | 1,223.6 / 3,681.4 (−1.6 / −3.3%) | ~28k | Per die: +1 PHY 10 mm² (assumed) + 1 controller strip 2.1 + svc reader/scorer ~13.4 (estimate, no RTL) ≈ **+25.5 mm²**, 799 → ~825 mm² (fits: width 31.97 → ~33.0 mm). South-edge shoreline fits 2 × 8.5 mm. Totals: +16 stacks, +408 mm² of silicon. **A new die type**: plan, bind, GRT, STA and landing all over again. | die re-plan; costly against closure-first |
| A. 4 stacks a scan die | 1,243 / 3,806 (as composed) | 33.6k | ≈ +77 mm² a die → ~876 mm², **over the 858-mm² reticle** unless about 10% of the ROM frames move out (the layer's weights then spill to more dies). 34 mm of PHY shoreline needs both long edges. +48 stacks. | not viable without a ROM re-split |
| **B. replicate the 4 full-scan stages ×2** (users alternate copies) | unchanged (−4.56 / −9.24%) | **45.1k** | +40 dies, +31,968 mm² (study figure). Chain re-plan only, no die change. | throughput only; fixes nothing for the single user |
| **C. keep and accept the loss** | 1,186.4 / 3,454.7 | 22.5k | 0 | needs an owner exception (MTP 10.2% > 5% unit limit) |
| **D. spread each full-scan layer's keys over k adjacent TP4 stages** (modelled; every p4l die already carries the scan service) | k=3: **1,223.8 / 3,710.2 (−1.5 / −2.5%)**; k=4: 1,221.6 / 3,709.5; k=2: 1,212.9 / 3,636.3 | about the 1-stack HBM bound | **0 mm², same die.** Needs: KV/index key placement on the neighbour dies' stacks; q fan-out and a candidate return over the stage chain (2 × 729-cycle measured idx_topk_merge legs); a 4k-way final merge (+178 a rank, modelled); a per-user key base in `svc_sx` (already owed by multi-user item 5). Contention with neighbour stages is static and compiler-placed. | **recommended:** compiler + data placement, no closure impact |

S81-BALANCE's B3 ("index stripes over the layer's own stacks + MTP read share") is the same idea as D. It also shares
the index read across the 6 MTP verify positions, which reaches 1,224 / 3,829.

## Composition fix

`tools/token_compose_xdie.py` now charges the 1-stack scan in `ds_rom()`:
- per-layer `L*.scan_stacks_p4l` terms;
- for MTP, a `wave.scan_stacks_p4l` term;
- graded priced, with source `scan_stacks.json`.

**Price of record.** The price of record is the p4l `dv_base` price plus the same correction, so the price check still
holds. `uncorrected_tok_s` keeps the 1,365.7 / 4,045.4 figures.

**Re-running dv_price.** When dv_price is re-run, it picks the ledger row up (group not `S81.DV_*`). Its `ledger_rows`
then lists `S81.SCAN_STACKS_P4L`, and the composer stops adding its own term, so there is no double charge.

**Outputs.** `results/arch/token_path_1018/{ds_rom,index}.json` and the token page data were regenerated:
- DS ROM AR 1,243.0 → **1,186.4**;
- MTP 3,806.2 → **3,454.7**.

`tests/test_token_compose_xdie.py`: 15 passed.

**To make it measured:** run the 10-04 reader bench with one stack per rank, `quarter_stack` with N = 262,144 on one stack.

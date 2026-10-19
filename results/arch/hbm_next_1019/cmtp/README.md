# HBM-NEXT-CMTP: compiler and MTP for the next HBM die (P = 4)

Lane HBM-NEXT-CMTP, 2026-10-19. This is next-release work, not a release gate. Branch `claude/hbm-next-cmtp-1019`, merged into `claude/hbm-next-1019`. The d4g and GEN2 files are untouched: `tools/hgi_sim` is used as is, and every rule below lives in `tools/hbm_next/`.

## 1. Results: re-timed tok/s against the targets (DS, 1.2 GHz, 1M context)

Source: `retime/retime.json` and `retime/retime.log` (ot-epyc5). The chain is the D1 price chain (`hbm_plane_model`, d4g price of record), run with an explicit `fork` pool so that the knobs reach the workers.

| case | AR | **MTP** (τ 4.159) | 4 users: aggregate / per user | MTP step: verify + draft + seed (cycles) |
|---|---:|---:|---:|---|
| D1 reproduction (L = 4, D1 SM rule) | 1,905.4 | 3,363.5 | 4,365.3 / 1,091.3 | 1,338,147 + 128,338 + 10,617 |
| STUDY L = 5 reproduction | 1,949.7 | 3,459.9 | 4,481.6 / 1,120.4 | 1,297,601 + 127,502 + 10,617 |
| + measured union lane histogram | 1,949.7 | 3,458.0 | 4,481.5 / 1,120.4 | 1,298,400 + … |
| + M1: x-load and lane-major publish (a cost) | 1,949.7 | 3,393.0 | 4,423.1 / 1,105.8 | 1,323,318 + 129,818 + 11,037 |
| **CMTP P = 4 headline: + remainder pass (K-split / row-split)** | **1,949.7** | **3,500.1** | **4,423.1 / 1,105.8** | 1,285,075 + 123,528 + 10,550 |
| headline, HC row II 600 (UNITS target) | 1,949.7 | 3,278.0 | 4,301.5 / 1,075.4 | 1,381,718 + … |
| headline, HC row II 950 (UNITS gate) | 1,949.7 | 3,024.5 | 4,028.5 / **1,007.1** | 1,507,718 + … |
| headline, VM as built (column swaps): **not a valid programme** (§6) | 1,949.7 | (3,411.3) | (4,279.5 / 1,069.9) | |
| **targets** | 1,905 | ~3,364 | ~4,365 / ≥ 1,000 | |

Reading the table:
- Both reproductions are exact: D1 3,363.5 / 4,365.3 and STUDY L = 5 3,459.9 / 4,481.6. So the wrapper is the identity when every knob is at its D1 value.
- **At the priced HC row II of 250, every target is met.** The headline beats D1 by +4.1% MTP, +1.3% aggregate and +2.3% AR.
- **HC is the swing term.** At II 600, MTP is 3,278 (−2.5% vs D1). At the 950 gate, MTP is 3,024 (−10%) and the per-user rate is 1,007, just above the floor. HC rows are the first thing UNITS must measure.
- The M1 x-load and publish costs come to −1.9% MTP and −1.3% aggregate. They are a PRICED estimate, charged as fully exposed.
- The remainder pass (`rpl`) gives back +3.2% MTP. Most of the gain is in the draft (N = 5): 129.8k → 123.5k cycles.
- In the 4-user step every union expert has c_u ≤ 4 rows, so `rpl` changes nothing there. 4,423 aggregate is the price with M1 included.

Fixed rules in every row:
- τ = 4.159 (owner 6-class blend);
- KV top-512 at the upper bound (no overlap);
- the HC Sinkhorn on 3 units;
- FUSED.HC_PRE_NORM at its measured II 197;
- all other row IIs PRICED (`isa_rows.ROW_II`).

## 2. ISA (first deliverable, merged early)

`isa_rows.md` and `tools/hbm_next/isa_rows.py` (single source; the self-test passes). HGI-1R adds:
- a ROWX part flagged by UOP op[5], so that an HGI-1 decoder faults on it;
- N = 1 … 16 rows, a 4-bit slot0, per-operand row strides and `rgap`;
- `rpl` (the SM remainder pass);
- `rsel` row tables;
- IDX.UNION and CTL.USERS, with CTL.TOKX and CTL.ACCEPT defined.

The normative semantics are R1: an N-row record is exactly its N single-row expansions.

## 3. MTP verify: 6 positions on 4 lanes

Every non-SM unit runs one N = 6 record: c1 + 5 · II.

The SM runs two lane passes over held weight lines:

| pass | lane 0 | lane 1 | lane 2 | lane 3 |
|---|---|---|---|---|
| 1 | pos 0 | pos 1 | pos 2 | pos 3 |
| 2, K-split (`rpl` 1) | pos 4, K part 0 | pos 4, K part 1 | pos 5, K part 0 | pos 5, K part 1 |
| 2, row-split (`rpl` 2) | pos 4, rows A | pos 4, rows B | pos 5, rows A | pos 5, rows B |

- **Price.** max(1, issues / 1.374) of the AR record. Issues per line are 2.0 with the D1 rule, 1.5 for a balanced split, and 1.8 for a K-split at K = 5,120 (a 16 | 4 tree split).
- **Choice.** The compiler picks the layout per record from that record's K (csum chunks) and rows per SM (`best_rpl`). Over the verify, it saves 28.4k cycles net of M1.
- **Exactness.** Both forms are exact (`isa_rows.md` R5): K parts are aligned subtrees of the golden csum tree, checked over 1,280 bit-exact trials.
- **Attention.** It keeps the D1 pass choice (k ≥ ⌈6/4⌉ passes over the union stream; E1 PASS by ATT4). A K-split is not exact for attention, because the online softmax runs sequentially over its blocks.

**Rollback (rule R-POS).**
- Every position-dependent write is POS-addressed: the window ring is 256 slots, and compressed rows and index keys are written at group = POS div ratio.
- CTL.ACCEPT restores only the IDX.EHASH history.
- C5 proves the 256-slot ring slot by slot for N = 6 and N = 4. A 128-slot ring fails: that is the mutant.

## 4. DSpark draft on the same die

- **Block rows.** dsa, dsb and dhead run as R = 5 row records. On P = 4 that is a full pass plus a 4-way K-split or row-split of the fifth row: 1.25–1.4 issues, which hides under the HBM share.
- **Serial parts.** Markov and demb stay serial.
- **Draft cost.** 123.5k cycles a step in the headline, against 128.3k in D1.
- **SEED.** The seed of the next step (main_proj / wkv over the 6 verify columns) is scheduled jointly with the verify head on the S2 schedule. The credit is 1,084 cycles, small because everything after the accept depends on the accepted token.

## 5. Expert union, gate E2: PASS by construction

The golden's `moe` (`hdc_golden_v41.Model.moe`, read 2026-10-19) works per position:
1. it takes the ids ascending;
2. it applies each route weight inside the expert, before w2;
3. it sums sequentially from +0 in id order;
4. it adds the shared expert last;
5. it rounds to BF16.

The union form keeps this order exactly:
- IDX.UNION writes the union list, the loop count and per-expert row tables of {ρ, e = 6ρ + κ}.
- The grouped GEMM is a VM-count `CTL.LOOP` of `rsel` records. In each record, B is indexed by the union id, A steps by ρ, and the route weight C and the output O step by e.
- Each position's output therefore lands in its own slot κ, and the per-position combine is unchanged.

The union changes only how often each weight line is streamed. Expert cost uses the measured lane histogram (MTP-STATS), not the mean. For verify N = 6: 71.7% of union experts have 1 lane, 1.25% have 5, 0.55% have 6.

## 6. VM residency

Measured on the scheduled timeline by `static_check` C4, with word-level liveness. Per-position copies are counted N times; constants and HC rows are counted once.

| mode | normal layer peak | Engram layers 1 / 14 | as built 262,144 | grown D1 (2^18 + (N−1)·30k) |
|---|---:|---:|---|---|
| AR (N = 1) | 68.5k | 100.7k / 107.7k | fits | fits |
| 4 users (N = 4) | 228.4k | 324.4k / 336.9k | fits except the 2 Engram layers | fits (352k) |
| MTP (N = 6) | **326.7k** | **469.8k / 486.0k** | **does not fit** | fits except the 2 Engram layers (412k) |

What this means:
- **STUDY's "VM as built + column swaps" is not a valid N = 6 programme.** Swapping the h / PRE columns is not enough, because six positions' transients alone need ~327k words in a normal layer.
- **The headline therefore assumes the grown VM** (D1 / STUDY recommendation). The Engram layers additionally need either about 2^18.9 (~490k) words, or Engram records issued in row groups of 2 (cost not yet priced).
- This is a **binding input to DIE** (VM sizing in the 752 mm² frame).

## 7. Static schedule: collision = fault

`tools/hbm_next/static_check.py` (`static/static_check.json`, `static/static_check.log`). For every layer segment it re-verifies the compiled timeline independently of the scheduler:

| check | what it catches |
|---|---|
| C1 | a unit double-booked |
| C2 | a RAW, WAW or WAR violation on exact VM/HBM intervals |
| C3 | rows that do not fit at the row II |
| C4 | VM capacity (reported in §6) |
| C5 | a KV-ring slot overwrite |

Results:
- **123 of 123 segments PASS** for MTP (N = 6), 4 users (N = 4) and AR (41 segments each).
- **The mutant witnesses FAIL as they must:**
  - a record moved onto its unit predecessor → C1 + C2;
  - a consumer started 2 cycles before its producer ended → C2;
  - a 128-slot ring at N = 6 / 4 → C5.

The timeline is the S2 CP schedule. With fixed unit costs the dispatch times are a compile-time function of the programme, so no credit, ready or backpressure exists on the die.

## 8. Four-user calendar

- **Lanes and users.** 4 users on the 4 lanes. Each step is one users-mode pass of the AR programme with N = 4: `CTL.USERS` loads bank s = {token_s, pos_s}. Users sit at independent positions, and every record reads its own user's state through its own bank.
- **Per-user state.**
  - KV: the window ring, the compressed rows and the index keys, at KV base + s · (user region), the user region being the HBM row stride `rs`. That is 3.7 GB a die at 4 × 1M (STUDY c).
  - The Engram history.
- **Shared and per-user work.** Weights and the expert union are shared. Attention and the indexer run per user, with disjoint key streams.
- **Join and leave.** Users join or leave only at step boundaries. The image holds entries for N = 1 … 4, and the host rings the entry that matches the active count. The N = 1 image is the AR programme byte for byte (no ROWX), so **single-user AR is unchanged**.
- **Rates.** 1,105.8 tok/s per user (headline) and 1,075 at HC II 600, which meets the ≥ 1,000 floor. At the HC 950 gate it is 1,007.

## 9. Goldens (released checkpoint, digests): consumed by VEH

| golden | content | state |
|---|---|---|
| `goldens/ar_mtp_g5/` | prompt [0]: AR positions 0–6, MTP verify N = 6 (draft 1 **accepted**, draft 2 **rejected**), DSpark draft rows, seeds; npz + json byte-identical to the committed `hbm_mtp_1015/sim_gamma5` SHA256SUMS; `manifest.json` has 630 per-array sha256 | **DONE** |
| `mu4` | 4 users, 2-token prompts. User 0 = [0, 5] is the control: it must reproduce `ar_mtp_g5` h / pre of positions 0–1 bit for bit. | RUNNING on ot-epyc5 (fetch-on-demand) |
| `mtp_all5` | forced drafter, all 5 accepted + bonus, plus the layer-major identity check | next (pending) |

**The checkpoint problem.** The full 476 GB snapshot exists only on the workstation, and the fleet link runs at ~3.5 MB/s. So `tools/hbm_next/goldens.py` runs the golden **on the fleet**, over its 14 GB sparse subset, with a light local daemon (`serve`) that ships exactly the missing expert tensors and the embedding and Engram rows on demand. Every fetched range is logged with its sha256 in `fetch/ledger.jsonl`.

## 10. Pending / next

1. **HC row II.** This is the dominant risk (§1). Re-time with UNITS' measured II as soon as it exists (`plane_compiler.py retime --only headline`, after setting `Knobs.hc_ii`).
2. **The emitter.** The binary HGI-1R images (ROWX on every row record, the IDX.UNION + `rsel` grouped-GEMM loop) need an object-level VM allocator: row arrays per per-position object, e-strided arrays for expert slot outputs and route weights, liveness packing. C4 already gives the capacity it must meet. Images for VEH come after it.
3. **Engram row groups**, or a VM of ≥ 486k words. DIE decides; CMTP prices the row-group option.
4. **The `mtp_all5` golden**, and copying `mu4` into `goldens/` with its manifest once the CONTROL passes.
5. **M1 is priced, not measured.** It should be replaced by SM4's x-store / publish bench.

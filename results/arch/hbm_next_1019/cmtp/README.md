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
| **CMTP P = 4 headline: + remainder pass (K-split / row-split), HC row II 250 MEASURED** | **1,949.7** | **3,500.1** | **4,423.1 / 1,105.8** | 1,285,075 + 123,528 + 10,550 |
| headline, HC row II 600 (sensitivity only; old UNITS target) | 1,949.7 | 3,278.0 | 4,301.5 / 1,075.4 | 1,381,718 + … |
| headline, HC row II 950 (sensitivity only; old UNITS gate) | 1,949.7 | 3,024.5 | 4,028.5 / **1,007.1** | 1,507,718 + … |
| headline, VM as built (column swaps): **not a valid programme** (§6) | 1,949.7 | (3,411.3) | (4,279.5 / 1,069.9) | |
| **targets** | 1,905 | ~3,364 | ~4,365 / ≥ 1,000 | |

Reading the table:
- Both reproductions are exact: D1 3,363.5 / 4,365.3 and STUDY L = 5 3,459.9 / 4,481.6. So the wrapper is the identity when every knob is at its D1 value.
- **HC row II is now MEASURED at 250.0** (HBM-NEXT-UNITS `tb_hnx_hc_eng4`, hnx RTL, Verilator 5.050, bit-exact for N = 1, 2, 3, 4, 6, 8: HC_MIX 998 + 250 (N − 1); `units/hc/README.md`). The compiler sets the d4g `row_ii` HC basis, both the priced and the measured value, to it; the stale 4,385 is from the codex 128-lane engine, which the die does not bind. The numbers are unchanged, because D1 priced the same 250. **At the measured HC row II of 250, every target is met.** The headline beats D1 by +4.1% MTP, +1.3% aggregate and +2.3% AR.
- HC was the swing term. The II 600 / 950 rows remain as sensitivities only: at 600, MTP 3,278 (−2.5% vs D1); at 950, MTP 3,024 (−10%) and 1,007 per user.
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

**Corrected 10-19 02:20.** An in-place `COLL.ALL_GATHER` footprint reads its whole destination, but only its own slice is data, and that slice is already defined. The other words are its own output, so they are no longer counted as live-ins from cycle 0.
- This is audited: `self_overwritten_read_words` in `static/static_check.json` and `emitter/*/emitter.json`. The only op it applies to is `COLL.ALL_GATHER`, and the emitter and C4 agree word for word.
- The step-2 figures (326.7k; 469.8k / 486.0k) were 8.9% / 6.4% / 7.4% above the corrected ones.

| mode | normal layer peak | Engram layers 1 / 14 | as built 262,144 | grown D1 (2^18 + (N−1)·30k) |
|---|---:|---:|---|---|
| AR (N = 1) | 42.0k | 66.6k / 68.8k | fits | fits |
| 4 users (N = 4) | 201.7k | 296.0k / 303.4k | fits except the 2 Engram layers | fits (352k) |
| MTP (N = 6) | **300.0k** | **441.4k / 452.5k** | **does not fit** | fits except the 2 Engram layers (412k) |

What this means:
- **STUDY's "VM as built + column swaps" is not a valid N = 6 programme.** Six positions' transients alone need ~300k words in a normal layer.
- **The headline assumes the grown VM** (D1 / STUDY recommendation).
- C4 is a floor. The emitter's object-level allocator (§14) needs 350.4k (normal) and 456.8k / 481.7k (Engram), which is what a real image needs. Engram choice: §13.
- This is a **binding input to DIE**.

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
| `mu4` | 4 users, 2-token prompts. User 0 = [0, 5] is the control: it must reproduce `ar_mtp_g5` h / pre of positions 0–1 bit for bit. | RUNNING on ot-epyc5 (fetch-on-demand, `serve2`) |
| `mtp_all5` | forced drafter, all 5 accepted + bonus, plus the layer-major identity check | RUNNING on ot-epyc5 (`serve2`) |

**The checkpoint problem.** The full 476 GB snapshot exists only on the workstation. So `tools/hbm_next/goldens.py` runs the golden **on the fleet**, over its 14 GB sparse subset, and a light local daemon ships exactly the missing expert tensors and the embedding and Engram rows on demand. Every fetched range is logged with its sha256 in `fetch/ledger.jsonl`.

`serve2` (10-19) replaces `serve` and runs ~30× faster: measured ~6 s per routed expert against ~150 s. It does three things:
- it keeps persistent ssh connections (measured: one stream ~5 MB/s, 4 streams ~20 MB/s, a connect 2.6 s);
- it dedupes the two goldens' identical requests;
- it fetches all 6 tensors of a routed expert on its first request.

## 11. tok/s per SM area option (owner decision input; SM4 lever table)

Source: `area_options.json` and `area_options.log` (`plane_compiler.py options`, ot-epyc5). The die area is SM4's `sm4/geometry.json` `lever_table`, an estimate: die = 693 + 256 × (tile − 1.1444). Every option runs the headline knobs (L = 5 COLL, measured union histogram, M1, HC II 250 measured, grown VM). All figures are PRICED.

| option | die mm² | AR | **MTP** | 4 users: aggregate / per user | MTP / mm² |
|---|---:|---:|---:|---:|---:|
| base: P = 4, 8 separate closed x stores | 892.1 (> reticle) | 1,949.7 | 3,500.1 | 4,423.1 / 1,105.8 | 3.92 |
| (a) P = 4, shared 4-lane x store `hnx_xs4` | 839.8 | 1,949.7 | 3,500.1 | 4,423.1 / 1,105.8 | 4.17 |
| (a) without the remainder split (`rpl` = 0) | 839.8 | 1,949.7 | 3,393.0 | 4,423.1 / 1,105.8 | 4.04 |
| (a)+(b): BF16 column 1 lane, SM attention as single-query records | 718.7 | 1,949.7 | **2,738.1** | 3,731.9 / **933.0** | 3.81 |
| (a)+(b), optimistic: 1-lane attention as one row record | 718.7 | 1,949.7 | 3,020.6 | 4,038.8 / 1,009.7 | 4.20 |
| P3a: P = 3 + shared 3-lane x store, 3 users | 743.8 | 1,949.7 | 3,389.9 | 3,861.4 / 1,287.1 | **4.56** |
| P3a, 4 users on 3 lanes | 743.8 | 1,949.7 | 3,389.9 | 4,220.2 / 1,055.1 | **4.56** |

Reading the table:
- **Lever (a) costs no cycles.** Base and (a) run the same records.
- **(b) fails.** The SM attention lanes sit on the BF16 column (`att4/geometry.json`: "per BF16 column leaf: 4 query lanes"). With one lane there, MTP falls to 2,738 (−22%, under the 3,364 target) and the per-user rate to 933 (under the 1,000 floor). Even the optimistic form gives only 3,021 / 1,010.
- **P3a matches P = 4 on MTP when the remainder split is not built.** At P = 3 the 6 verify positions fill exactly 2 full passes, with no remainder: 3,390 against 3,393. It saves ~96 mm².
  - P = 4 is ahead by +3.3% MTP (3,500) only with the split hardware (§12).
  - P = 4 is ahead by +4.8% on 4-user aggregate (4,423 vs 4,220).
  - **P3a meets every target and has the best rate per mm².**
- AR is 1,949.7 in every option.

## 12. "2 accumulator sets per lane row": what the remainder split means on the SM4 leaf

Full text: `isa_rows.md` R5, "What this means on the SM4 leaf".
- **The 2 sets are the 2 lanes of a pair.** Lanes 0 and 1 hold position 4's K parts 0 and 1; lanes 2 and 3 hold position 5's. No lane needs a second accumulator, and no per-lane beat mask is needed.
- **The new hardware is the supply:** 2 different weight words in the same issue cycle. As built, `hnx_rp4lp4_lanefan` broadcasts ONE 818-b row bundle, so this is a second row bundle per leaf.
- **The K-split also needs** each lane to close its row at its own part's end, and **one FP32 add per remainder row** (P0 + P1, RNE, part 0 as the left operand). That adder is in no closed view; it goes on the publish path or downstream as a VOP.
- **It is worth +3.2% MTP** (3,500.1 vs 3,393.0), and nothing for 4 users.
- **Recommendation: SM4 builds `rpl` = 0 first.** That is the HGI-1R default. The split stays an opt-in lever.

## 13. Engram layers: row groups vs a larger VM (~482k words)

Source: `engram_groups.json` (`tools/hbm_next/engram_groups.py`). It measures both forms on the scheduled timeline, with C4 word-level liveness and the static checks.
- **Row groups.** RG2 / RG3 issue the two Engram layer segments (1, 14) as 3 / 2 sequential groups of 2 / 3 positions each.
  - Positions run in order, so the causal rule is unchanged.
  - Weights and experts are re-read once per group.
  - All checks PASS (C1 / C2 / C3 / C5 = 0).

| form | extra cycles a verify | MTP tok/s | Δ | VM need, C4 floor (layer 1 / 14) |
|---|---:|---:|---:|---|
| N = 6, grown VM | 0 | 3,500.1 | — | 441.4k / 452.5k (C4); **456.8k / 481.7k with the emitter's allocator** |
| RG3 (2 groups of 3) | 40,000 | 3,404.6 | −2.7% | 266.3k / 273.0k: fits the 412k VM |
| RG2 (3 groups of 2) | 75,669 | 3,323.7 | **−5.0%** | 220.2k / 224.7k: fits the 412k VM |

**Under PROG's rule (10-19 01:35), RG2 is more than 3% worse, so the Engram layers take the larger VM: ≥ 481.7k words (2^18.88), measured by the emitter's object allocator.** RG3 (−2.7%) is the fallback if DIE cannot fit the area.

Untried, and cheaper than both: group only the Engram sub-block, not the whole layer. The peak is the 6 positions' `engram.wkv` / `engram.hw` / `rows_gather` row arrays at cycle ~5,300–7,900 (§14). Grouping only those records needs serialising dependencies between groups, which the plane model does not yet emit (next).

## 14. Emitter: value-level VM allocator + binary HGI-1R images (first version)

`tools/hbm_next/emitter.py` → `emitter/{mtp,ar}/` (`emitter.json`, `*_L{0,1,14}.hgi1r`, ot-epyc5). It takes the compiled N-row programme (headline knobs) and the S2 timeline of each layer segment.
- **Values.** Every write of an operand interval in a copy is a value, live from its writer's start to its last reader's end.
- **Components.** A descriptor that reads several values joins them (union-find), so one base shift relocates the set. The words an in-place gather overwrites join its read operand to its output.
- **Objects.** The N per-position copies of a component that overlap in time form one ROW ARRAY: N rows at a constant stride, so ROWX `rs` addresses row ρ. A sparse strided component (expert-slot pitch) is re-laid at its used width.
  - Constants and position-independent loads are shared, at `rs` = 0.
  - h / PRE are pinned at VM 0.
- **Placement.** The better of first-fit by start and greedy-by-size best-fit. **It reaches the object bound (zero fragmentation) in every segment.**
- **Emit.** Every record is relocated. N-row records get ROWX (n, `rs` per operand, SM `rpl` = `best_rpl`, param [5:2] = N − 1). Each record is checked:
  - `isa_rows.check`;
  - encode → decode → encode identical;
  - every row's descriptor intervals fall inside that row of its object (R2);
  - rows are independent.
  - AR (N = 1) must be byte-identical to `records.Rec.encode`.

| segment | records emitted / failed | ROWX | allocator high water | C4 floor | high water / C4 | fits |
|---|---:|---:|---:|---:|---:|---|
| MTP L0 (normal) | 67 / 0 | 66 | 350,400 | 300,038 | 1.168 | grown 412k |
| MTP L1 (Engram) | 130 / 0 | 129 | 456,800 | 441,398 | 1.035 | needs ≥ 456.8k |
| MTP L14 (Engram) | 169 / 0 | 139 | 481,680 | 452,534 | 1.064 | needs ≥ 481.7k |
| AR L0 / L1 / L14 | 67 / 130 / 169, 0 failed | 0 | 58.4k / 93.2k / 95.6k | 42.0k / 66.6k / 68.8k | 1.39 | as built |

**NOT YET for VEH.** These are partial images, written per layer segment. Still to do:
- the MoE union records (`expert`, `egather`, `expert_union`: 101 an MTP segment, 24 an AR segment) are skipped: the IDX.UNION record + `rsel` CTL.LOOP form is next;
- CTL.USERS banks for the 4-user image;
- whole-token assembly.

## 10. Pending / next

1. **Goldens:** collect `mu4` (CONTROL PASS) and `mtp_all5` (5 accepted, layer-major equal), package them, commit.
2. **Emitter:** the IDX.UNION + `rsel` loop form for the expert union, CTL.USERS banks (4 users), whole-token images, then hand off to VEH. The MU (N = 4) allocator run is still to do.
3. **Engram:** price sub-block row groups (§13), which needs serialising dependencies.
4. **M1 is priced, not measured.** Replace it with SM4's x-store / publish bench.
5. The remainder split is an opt-in lever. If SM4 builds it, re-time with its measured combine latency.

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
| `goldens/mu4/` | 4 users, 2-token prompts ([0,5], [2,12366], [3,4521], [4,17808]; argmax 5/223, 17/28, 29/201, 5/16); position 1 of every user = the users N = 4 step. User 0 is the control: reproduces `ar_mtp_g5` h / pre of positions 0–1 bit for bit (160 arrays compared, 0 mismatches, CONTROL PASS). `mu4.npz` sha256 fc19651c… = `mu4.json` npz_sha256; manifest PASS 640 arrays | **DONE** (10-19 06:10) |
| `goldens/mtp_all5/` | forced drafter, all 5 accepted + bonus, plus the layer-major identity check | **DONE** (sec. 16) |

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

## 15. Step 4 (10-19 03:05): re-time with the MEASURED unit row IIs, and binary images for VEH

### 15.1 Measured re-time, per unit (owner input for redesign ranking)

Source: `retime/meas_retime.json` + `retime/meas_retime.log` (`plane_compiler.py meas`, ot-epyc7, on the step-2/3 tree of record: the priced rows reproduce 3,500.1 / 4,423.1 and P3a 3,389.9 / 4,220.2 exactly). Each row flips ONE measured II into the P = 4 headline (all other knobs as §1); `ALL` flips every one. Keys and sources: `plane_compiler.MEAS`.

| unit (measured vs priced) | P=4 (a) MTP Δ | P=4 4-user agg Δ | P3a MTP Δ | P3a 4-user Δ |
|---|---:|---:|---:|---:|
| **IDX.INDEX** 953 a row (vs 152 of 658.9; scaled to each record's c1) | **−3.10%** (+45.7k cyc/step) | −0.92% | −3.01% | −0.88% |
| IDX.INDEX, 953 absolute (sensitivity) | −2.02% | −0.24% | −1.96% | −0.23% |
| **SU.VOP** (2k+1)·⌈e/512⌉+2 (vs nv) | **−2.07%** (+30.1k) | −1.44% | −1.92% | −1.24% |
| **SM4 publish skew** +8 a further lane a pass | **−2.01%** (+29.2k) | −0.95% | −1.51% | −1.17% |
| IDX.TOPK 49.2 (vs 47) | −0.03% | −0.02% | −0.03% | −0.02% |
| DMA.KVWB_DS 8 (+28 a wrap) | 0.00% | 0.00% | 0.00% | 0.00% |
| ARGMAX.LOCAL 169 (vs 6) | 0.00% (head segment, off the critical path) | 0.00% | 0.00% | 0.00% |
| COLL.ARGMAX_MERGE 32 | 0.00% | 0.00% | 0.00% | 0.00% |
| IDX.UNION measured cycles(N) (vs a TOPK c1) | +0.43% | +0.67% | +0.42% | +0.64% |
| ATT4 shared-merge PV span −40 a pass | +0.23% | +0.15% | +0.22% | +0.28% |
| **COLL.ROW_GATHER** 623 a row (vs 1,449) | **+2.34%** (−32.6k) | +1.83% | +2.26% | +1.75% |
| **ALL measured** | **3,354.3 (−4.17%)** | **4,393.9 / 1,098.5 per user (−0.66%)** | **3,267.6 (−3.61%)** | 4,190.4 / 1,047.6 (−0.71%); 3 users 3,810.1 / 1,270.0 |
| ALL, IDX.INDEX 953 absolute | 3,391.3 (−3.11%) | 4,424.0 (+0.02%) | 3,302.6 (−2.58%) | 4,217.8 (−0.06%) |

Reading:
- AR is 1,949.7 in every row (all changes are further-row IIs).
- **With every measured II, P = 4 (a) MTP is 3,354, 0.3% under the ~3,364 target; P3a is 3,268, 2.9% under it.** The 4-user rates keep the floor (1,098 / 1,048 per user).
- **Redesign ranking (MTP gain if the unit reached its price):** IDX.INDEX +3.1% (UNITS-IDXN: N selectors / one key pass) > SU.VOP +2.1% (UNITS-SUDMA2: second store write port / fill bypass) ≈ SM4 publish skew +2.0% (SM4: parallel lane publish) >> everything else (≤ 0.03%). KVWB, ARGMAX.LOCAL, TOPK, ARGMAX_MERGE need NO redesign. Fixing the top three would give ~3,600 (P = 4) / ~3,500 (P3a).
- The measured gains (ROW_GATHER, IDX.UNION, ATT4 shared merge) are banked in `ALL`.

### 15.2 Emitter v2: union loops, ATT plan mode, users image (VEH input)

`tools/hbm_next/emitter.py` → `emitter/{ar,mtp,mu}/` (`{mode}_L{0,1,2,3,14}.hgi1r`, `mu_prologue.hgi1r`, `emitter.json` with per-image sha256 and the aux VM map). HGI-1R **1.1** (`isa_rows.md` R6 "as emitted", R10, R11, 1.1 changes).

| image | records emitted / failed (L0, 1, 2, 3, 14) | VM need, words (incl. aux) | fits |
|---|---|---|---|
| AR (N = 1) | 91 / 154 / 130 / 91 / 193, 0 failed; byte-identical to `records.Rec.encode` | 58.4k – 95.6k | as built |
| MTP N = 6 (P = 4) | 85 / 148 / 124 / 85 / 187, 0 failed | 373.0k / 479.4k / 373.4k / 373.0k / 484.6k | 2^19 VM (PROG) |
| 4 users N = 4 | 82 / 145 / 121 / 82 / 184, 0 failed (+ CTL.USERS prologue) | 245.2k – 327.1k | 2^19; L0/2/3 as built |

What is new in the images:
- **Expert union** (no more skipped records): `IDX.UNION` → `CTL.LOOP` (count from VM) {w1, w3 `rsel`} → SwiGLU → 6 N-row intermediate gathers → `CTL.LOOP` {w2 `rsel`}. The allocator lays the expert cells of all 7 slots (6 routed + shared) of a position as one row (K = 7 = `imm_b`), so e = 7ρ + κ addresses cell (ρ, κ) with rs = the slot pitch. The priced model's union slot-group copies are folded away (76 MTP / 64 MU records), which also lowers the Engram-layer VM need: L14 462.0k (was 481.7k in step 3) + 22.6k aux.
- Every loop record is checked on a synthetic union (seed 1019): every iteration's row ρ writes exactly position ρ's slot κ of expert u, and the loop covers all 6N cells once (E2 order by construction).
- **ATT plan mode** (ATT4's request): one `IDX.KVUNION` per lane pass (2 for MTP N = 6, 1 for users) and the ATT.QK / ATT.PV records with `rsel` = 1, `rtab` = the plan; plan blocks 32 × 320 words + lane map, budget 128 lines a SM.
- **Users:** `CTL.USERS` prologue; per-user HBM operands (ring, compressed rows, list stores, IDX key store via `rs_I`) step by 1 GiB (`hsh` 12, rs 2^18); the 1 GiB stride collides with no HBM interval of the 5 segments.

**Limits (for VEH):** per-layer images, not yet a whole-token assembly (the head / TOKX / ACCEPT segment and cross-segment aux relocation are next). The images' VM map is per segment (aux above each segment's high-water mark). The union loop and KV-union plan spans are data-dependent: the calendar reserves the bounds (U ≤ 6N iterations; 128 lines a SM).

## 16. Step 5 (10-19 03:40): re-time with the REDESIGNED units' measured IIs (OWNER-decision input), whole-token images, `mtp_all5` golden

**Re-time** (`retime/meas5_retime.json`, `plane_compiler.py meas --step5`; ot-epyc7 tree of record opt5, 8 fleet jobs; priced rows reproduce 3,500.1 / 4,423.1, P3a 3,389.9 / 4,220.2, rpl0 3,393.0). New MEAS keys: `idxn` (IDX.INDEX further row c1 × 232 / 658.9, @5bf6d2d50), `su_vop2` (SU.VOP 2k ⌈e / 512⌉, @a42351330), `argmax2` (22), `fused` (FUSED.HC_PRE_NORM 81 / HC_POST 103, @e70d3285a); "ALL measured v2" = those + idx_topk, idx_union, kvwb, coll_rg, coll_am, att4, sm4skew. Frame sensitivities (they move AR): `idx_frame` (IDX.INDEX first row × 1,297 / 658.9: the release AR model prices the d4g frame at 658.9 although d4g measures 1,397) and `fused_frame` (FUSED c1 404 / 196 MEASURED on the new hnx FUSED engine, below the d4g price). DS, 1.2 GHz, 1M ctx, VM 2^19 (VM-resident columns), L5 COLL, HC II 250.

| option (die mm², DIE f4c_t7) | AR | MTP (target 3,364) | 4 users agg / per user (floor 1,000) |
|---|---|---|---|
| P4 (a) + remainder split, ALL measured v2 (811.8) | 1,949.7 | **3,483.7** (+3.6%) | **4,462.0 / 1,115.5** |
| P4 (a) rpl 0 (what SM4 builds first), ALL measured v2 (811.8) | 1,949.7 | **3,377.9** (+0.4%) | **4,462.0 / 1,115.5** |
| P3+(a), 4 users on 3 lanes, ALL measured v2 (767.4) | 1,949.7 | **3,390.1** (+0.8%) | **4,251.2 / 1,062.8** |
| P3+(a), 3 users | 1,949.7 | 3,390.1 | 3,855.8 / 1,285.3 |
| same + measured frames: P4 (a) / rpl 0 / P3+(a) u4 | 1,997.5 | 3,523.1 / 3,415.0 / 3,427.5 | 4,432.7 / 4,432.7 / 4,224.7 |

Per unit (P4 (a), vs priced): IDXN −0.32% MTP / 0 users (was −3.10% at 953); SU.VOP v2 −1.09% / −0.74% (was −2.07% / −1.44%); ARGMAX 22: 0 (off the critical path); FUSED rows +0.07% / −0.07%; frames: IDX −1.17% AR / −0.51% MTP / −2.61% users, FUSED +3.71% / +1.67% / +2.07%. With the redesigns every option meets every target; step 4's "0.3% under" is gone.

**Reading for the OWNER decision.** At rpl 0 (the SM4 build order) P4 (a) and P3+(a) give the same MTP (3,378 vs 3,390); P4 (a) buys +5.0% 4-user aggregate (4,462 vs 4,251) for +44.4 mm² (811.8 vs 767.4; (a)'s packing is still unproven), and the remainder split adds +3.1% MTP on P4 only. Per mm²: MTP 4.16 (P4 rpl 0) / 4.29 (P4 split) vs 4.42 (P3+(a)); 4-user 5.50 vs 5.54. CMTP view: P3+(a) stays the better rate per mm² and clears every target with margin; P4 (a) is worth it only if the 4-user aggregate is the priority AND SM4 builds the split.

**Whole-token images** (`emitter.py --whole`, `emitter/whole/<mode>_N<n>/`): all 40 layer segments + the head in one image, one VM map (pinned h / PRE at 0, every segment's aux at one base = the largest high-water mark), head tail per R9: the head's COLL.ARGMAX_MERGE O re-pointed into the TOKX table (rs_O = 1: ids contiguous, R2 + contiguity checked), then MTP `CTL.ACCEPT` (A = accept.a, written by the DSpark accept compare, d4g `ot_dshbm_dspark_ctl` accept_a0, CP side, priced in mh_ctl) → `CTL.TOKX` (k = a + 1) → `CTL.END`; users `CTL.TOKX` (param 1, N beats) → END; AR TOKX k = 1. MTP N = 6: 3,715 records, 516,304 B, VM need 484.6k ≤ 2^19; users N = 1 / 2 / 3 / 4 and AR images likewise (0 failed records, whole-image decode round trip, exactly one END, last). **Open:** layer 20 reads 1,366 + 32 words a position before its in-segment writer (IDX.INDEX index frame, SU.VOP index_q.rope): a live-in whose producer placement is not yet tied to the consumer (`token.liveins`); The AR and users N = 1 images keep the AR map (identity, no relocation), so they are unaffected; the N > 1 images (MTP, users N = 2..4) must treat segment 20 as not yet one-map until that value is pinned.

**Goldens:** `goldens/mtp_all5/` DONE (forced drafter: drafts [223, 939, 23, 695, 22] all accepted + bonus 1266; layer-major argmax equal, L0 bit-equal; manifest PASS 21 arrays). `mu4` still running (user 2 of 4 at 03:33; ETA ~04:40, pending_results).

## 10. Pending / next (updated step 6, 10-19 07:30)

1. **Goldens:** DONE (`ar_mtp_g5`, `mtp_all5`, `mu4` CONTROL PASS).
2. **Whole-token images:** DONE, one VM map (sec. 17); VEH runs them (`emitter/whole/<mode>_N<n>/`).
3. **OWNER / PROG decision (sec. 17):** the union loop is a data-dependent span. Reserving its bound U = 6N in the static calendar costs -6.3% MTP (P4(a)+split 3,263.5; rpl0 3,170.1; P3+(a) 3,180.2 -- all under 3,364). Options: (a) reserve 6N and accept; (b) a union budget below 6N with E_RANGE fault + an AR fallback for the over-budget step (as ATT_BUDGET); (c) let the CP issue the records after the loop on its drain (data-dependent timing; a rule question for the owner).
4. **Re-time as redesigns land:** SM4 declined parallel publish (only-significant-gains); M1 measured and the (a) re-pack are DIE inputs; `plane_compiler.py meas --step5 [--union-bound]` on ot-epyc7 `hnx-cmtp4/opt6`.
5. Remainder split only if SM4 builds the second row word. Engram sub-block groups optional (MTP image needs 506.1k of 524.3k words).

## 17. Step 6 (10-19 07:30): `mu4` golden, one VM map for the whole-token images, image-form static check, reserved-calendar re-time

**`mu4` golden** (`goldens/mu4/`): 4 users with 2-token prompts. Position 1 of every user is the users N = 4 step. User 0 reproduces `ar_mtp_g5` bit for bit (160 arrays compared, 0 mismatches, CONTROL PASS). The manifest lists 640 arrays and PASSes; `mu4.npz` sha256 fc19651c... matches `mu4.json`.

**The layer-20 "live-in" was two model bugs, not a cross-segment value.** Both are fixed at the source:
- `IDX.INDEX` D with cand_en is the candidate table the frame WRITES (`machine.u_idx_index`). `timing.footprint` read it, so layer 20 seemed to read 1,366 words a position before writing them. Fix: `timing.is_write_operand` (O, R, and D of IDX.INDEX cand_en). `isa_rows.written_operands` makes D a write only where an IDX op writes it (UNION, KVUNION, INDEX cand_en).
- SU `b_half` reads B and D at i >> 1, so it reads ceil(n / 2) words. `emitter.desc_ivs` and `isa_rows.check_rows_independent` used the full n. So `index_q.rope` over-read 32 words past the RoPE table, which made the second false live-in. The over-read also inflated the RoPE row stride (96 instead of 64 words).
- `static_check` still gives 123 / 123 segments PASS, and its mutants fail as witnesses (`static/`). The re-time is unchanged: P4(a) 3,483.7 / 4,462.0, rpl0 3,377.9, P3+(a) 3,390.1 / 4,251.2 are reproduced exactly on the fixed tree.

**One real cross-segment value: CANDM.** `emitter.carried_values` scans the whole token. It looks for words that a segment reads before any in-segment writer and that some segment writes. Only one such value exists: the layer-20 candidate keep table `CANDM` (2 x 2,048 words, AR 188,864). COLL.TOPK_MERGE writes it in layer 20, and IDX.INDEX keep_en reads it in layers 24 / 28 / 32 / 36. Before this step it was relocated per segment as a "constant": a wrong address in those 4 layers, and shared across positions although it is per position. It is now a pinned N-row array at one token-wide base, like h / PRE. `pinned_layout` gives every segment the same pinned map. The token report checks `pinned_one_base`, `liveins` = {}, `host_preloaded` = [] and 0 emit errors; `one_vm_map` = true for all 6 images.

| image | records | bytes | VM need (2^19 = 524,288) | pinned words | one map |
|---|---|---|---|---|---|
| ar_N1 | 3,954 | 470,976 | 99,200 | 24,584 | yes |
| mtp_N6 | 3,715 | 516,304 | 506,112 (96.5%; +21.5k for CANDM x 6) | 147,504 | yes |
| mu_N1 / N2 / N3 / N4 | 3,955 / 3,595 / 3,595 / 3,595 | 471,056 / 498,928 x 3 | 99.2k / 187.0k / 264.3k / 341.4k | 24.6k / 49.2k / 73.8k / 98.3k | yes |

**Image-form static check** (`tools/hbm_next/image_check.py`, `image_check.json`): all 6 images PASS. The checks:
- I1: every record decodes, round-trips and is legal.
- I2: frame -- one END, last; the ACCEPT / TOKX tail; USERS first.
- I3: union loops -- balanced and not nested. The count word is the D[0] of the last IDX.UNION, and nothing clobbers it before the loop. The bound U <= 6N is structural (A = N x 6 ids; O and R hold 6N). Body records have rsel 1, rtab = the UNION's R, and n = N. U_max = 36 MTP; 12 / 18 / 24 users.
- I4: every KVUNION has budget 128, NL <= P and a full plan, and every plan-mode ATT follows its KVUNION.
- I5: every VM row extent is < 2^19.
- I6: one map, 0 emit errors.

Five mutants (wrong count word, KV budget 256, wrong rtab, lost END, VM past 2^19) FAIL as witnesses. A first re-run of the images had 128 records failing on the stale row check; I6 caught it, and those records are now emitted.

**Reserved static calendar (union loop at its bound)** (`plane_compiler.py meas --step5 --union-bound`, `retime/ub6_*.json`; ALL measured v2). Every union loop is priced at U = 6N (verify 36, users 6 x users; draft / seed bodies 36, conservative). The MTP-STATS mean is not used:

| option | AR | MTP mean -> bound | 4u agg mean -> bound (per user) |
|---|---|---|---|
| P4(a) + split | 1,949.7 | 3,483.7 -> **3,263.5 (-6.3%)** | 4,462.0 -> 4,396.6 (1,099.2) |
| P4(a) rpl0 | 1,949.7 | 3,377.9 -> **3,170.1 (-6.2%)** | 4,462.0 -> 4,396.6 (1,099.2) |
| P3+(a) | 1,949.7 | 3,390.1 -> **3,180.2 (-6.2%)** | 4,251.2 -> 4,191.8 (1,048.0); 3 users 3,873.1 (the interpolated 3-user mean exceeds 18: artefact) |

The draft is unchanged: it already uses the no-sharing bound. Reading: if the calendar must reserve the worst-case union, every option misses the MTP target (3,364) by 3-6%. The 4-user rows still meet the 1,000 per user floor. This is an OWNER / PROG decision (sec. 10 item 3). The ATT KV plan already reserves its bound (128 lines, model upper bound 109).

Fleet tree of record: ot-epyc7 `/srv/opentallas-scratch/claude/hnx-cmtp4/opt6` (= opt5 + the step-6 tools).

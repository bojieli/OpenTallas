# Coverage plan: the path to all four targets fully covered

Stream coverage-plan, 2026-10-08 (PT).

**Inputs**
- The four node ledgers `T1.json`–`T4.json` in this directory (304 nodes, commits a0ab8e0c1, cc14fb202, 8af790f30, 5b968c990).
- `/home/ubuntu/claude-takeover-20261007/COMPLETENESS_AUDIT.md`.
- The stream logs in `/home/ubuntu/claude-takeover-20261007/*.log`, read at about 22:05 PT.
- `/api/elements` (278 rows).
- The token-path records in `results/arch/token_path_20261008/`.

The tieoff-audit had not landed when this plan was written. Its log has only a start line (21:44), and no `review_queue/tieoff-audit.md` exists.

**Outputs**
- `MATRIX.json` (`opentallas.coverage_matrix.v1`): 101 rows, one per normalised function, with a cell for each target.
- This plan.
- The Coverage view at `http://127.0.0.1:8765/explorer/coverage/`.

**Regenerating.** Run `python3 results/arch/coverage_20261008/gen_matrix.py --check`. `--check` fails if any ledger node is not gathered by a row.

The fleet viz imports `build()` from that file and re-derives the matrix whenever a ledger on `origin/main` changes. A stream that edits its ledger node therefore updates the view without anyone re-running the generator.

**What "fully covered" means.** A cell is fully covered when it has none of these gap classes:
- MISSING_HW (there is no RTL);
- NOT_ON_DIE (there is RTL, but no master in a die recipe);
- NOT_CLOSED;
- NOT_EXACT (there is no exact bench);
- NOT_PRICED (it is not in a token path's cycles);
- MODELLED_ONLY;
- UNENUMERATED. This class is added here: the function applies to the target, but that ledger has no node for it.

The **uncovered** cells are those with MISSING_HW or NOT_ON_DIE: they have no hardware on a die. The views draw these strongest.

---

## 0. Ownerless gaps (read first)

Every other gap in `MATRIX.json` has an owner stream. The gaps below have none. Each one has a proposed owner, and the owner needs to assign it.

| # | Target / node | Rows | Gap | Why no one owns it | Proposed owner |
|---|---|---|---|---|---|
| O1 | **All targets: the token-path re-export** (`tools/token_path_export.py`, `unified_composition.py`, `reprice_20261008.py`) | every NOT_PRICED / MODELLED_ONLY cell: T1 8 / 8, T2 21 / 13, T3 23 / 12, T4 60 / 5 | NOT_PRICED (integration) | The functional owners can produce the cycles of their blocks, but **nobody re-exports the token path**. The token-path stream stopped at 21:10 and reprice stopped at 18:25. T4 has no view at all, and `qwen_hbm()` does not exist. Without a re-export, no NOT_PRICED gap can close even after its hardware lands | A new **token-path re-export** stream on a 15-minute drive cadence, like the closure drive. qwen-hbm-unify writes `qwen_hbm()` |
| O2 | T1 B05 | boot.clocks | MISSING_HW, NOT_ON_DIE | No PLL macro or slot on the Qwen die. The PLLs are only ports on placeholder masters, and qwen-system's scope does not include clocks | qwen-system (die-top) |
| O3 | T1 F02 | f.mem_ecc | MISSING_HW | There is no KV data ECC, and no one owns the policy choice: SECDED, or cite the HBM3E on-die ECC. AGENTS.md (10-02) keeps HBM protection required | qwen-system (kvc), after an owner policy call |
| O4 | T3 F02, F04 | f.mem_ecc, f.aggregation, f.traps, boot.csr | NOT_ON_DIE, NOT_EXACT | On-die SRAM protection is not selected, and there is no fault / trap bench. Neither item is in hbm-system's list | hbm-system |
| O5 | T1 C12 | ctl.transport | MODELLED_ONLY | The relay and wire stages are priced from counts: +95 cycles an ME op, 20,615 cycles a token (9.4 %). Pricing them from r21b routed parasitics needs die evidence plus a re-export | O1 + die-evidence |
| O6 | T3 D17, D38, D39, D43, D48, D51, S04 | collectives | MODELLED_ONLY | The switch-tail cycles are modelled: 47,700 cycles, 6.8 % of AR. No stream re-measures them | hbm-system (collective) + O1 |
| O7 | T1 C14, D15, D21; T3 C05, C07, F01; T1 B06; T2 B06 | PHY / switch / HBM PHY | MODELLED_ONLY, NOT_EXACT | These are vendor terms: UCIe / SerDes PHY latency, Tomahawk Ultra, HBM PHY and controller, HBM ECC, and HBM PHY calibration. They are not ours to build, but nobody keeps the citations | O1 (cite the vendor in the views); ds-control for an S81 HBM bring-up bench if one is wanted |

**Owners assigned on paper, not yet working (22:05 PT).** These streams together own 244 gap entries (cell × class, closure included):

| Stream | Log state | Gap-cells it owns |
|---|---|---|
| hbm-indexer | no log | T3: 11 |
| hbm-system | no log | T3: 29 |
| qwen-hbm-unify | no log | T4: 137 |
| qwen-system | start line only (21:48) | T1: 33 |
| ds-control | start line only (21:57) | T2: 34 |

Until these streams log work, their gaps are owned in name only.

---

## 1. The matrix at a glance

| Target | Ledger nodes | Applicable rows | Fully covered | With a gap | Uncovered (no HW on a die) | MISSING_HW | NOT_ON_DIE | NOT_CLOSED | NOT_EXACT | NOT_PRICED | MODELLED_ONLY | UNENUMERATED |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| T1 Qwen ROM | 61 | 55 | 2 | 53 | 22 | 5 | 20 | 43 | 8 | 8 | 8 | 0 |
| T2 DS ROM S81 | 97 | 91 | 2 | 89 | 34 | 14 | 25 | 79 | 7 | 21 | 13 | 1 |
| T3 DS on HBM r25 | 96 | 96 | 3 | 93 | 38 | 12 | 30 | 60 | 15 | 23 | 12 | 2 |
| T4 Qwen on HBM r25 | 50 | 63 | 0 | 63 | 30 | 28 | 2 | 37 | 42 | 60 | 5 | 3 |

Counts are rows with at least one gap of that class (from `MATRIX.json` `summary`).

The only fully covered cells are:
- T1 `d.weight_dequant` and `f.link`;
- T2 `boot.clocks` and `smp.nongreedy`;
- T3 `host.multi_user`, `smp.nongreedy` and `mtp.tau`.

The last three of those are covered by scope (not claimed) rather than by hardware.

**Critical-path cycles of the token path on uncovered rows.** Every critical operator maps to a row (0 unmapped).

| View | Critical cycles | On rows with gaps beyond closure | On uncovered rows |
|---|---:|---:|---:|
| `qwen_rom` (AR) | 218,436 | 134,443 (61.5 %) | 7: the embedding, a behavioural ROM. The +248 / +567 HBM fetch is uncharged |
| `ds_rom` (AR) | 828,866 | 176,982 (21.4 %) | 124,266 (15.0 %): stage hops with no stage-guard master, unplaced hops, embed reader |
| `ds_rom_mtp` (one step) | 1,146,884 | 504,141 (44.0 %) | 442,284 (38.6 %): draft stages, wavefront, accept / commit, seed |
| `hbm_ds` (AR) | 699,176 | 382,188 (54.7 %) | 39,609 (5.7 %): the indexer (29,308) plus expert steering |
| `hbm_ds_mtp` (one step) | 1,348,760 | 1,348,760 (100 %) | 246,051 (18.2 %): draft compute / transport, union, accept / commit |
| `qwen_hbm` (T4) | — | — | **no view exists** |

The "rows with gaps beyond closure" column counts every gap class except NOT_CLOSED. The `hbm_ds_mtp` share is 100 % because every verify-step row carries a MODELLED_ONLY or NOT_PRICED term.

---

## 2. Owners, checked against the logs (22:05 PT)

| Stream | Owns (rows) | Log evidence |
|---|---|---|
| **qwen-system** | T1 control plane: host_if / pkg ctl / rst seq / CSR on die, token loop, sequencer, kvc, constant ROM, split-spine exactness, stop, multi-user, bounds | `qwen-system.log`: start 21:48 only. Scope is per the coordinator; not yet visible in the log |
| **emb-hbm-impl** | T1 `d.embed`, `boot.embedding`, `f.emb_ecc` | 21:42: RTL plus an e2e bench, first PASS on an 8-token image (bit-exact, CE corrected, UE fail-closed). 21:56: host link is the board-SerDes HOST class (no PCIe slab) |
| **ingest** | `host.*` and `prefill.*` on all four targets, plus T3 boot loads | 21:40 to 22:00: `ot_rom_host_ingest` bench PASS; die masters `qfd_io_host` / `dsfd_host` (jobs queued); `hfd_host_ingest` with an approved shared HBM write port |
| **mtp-rom** | T2 `mtp.sequencer`, `mtp.accept`, `mtp.commit`, `mtp.draft_transport` (blocks); WFC shims | 21:43 / 22:00: 5 blocks, benches 23/23, 15 loop jobs queued. Area: layer die +0.079, S0 +0.012, head +0.023, draft +0.124 mm² |
| **mtp-hbm** | T3 `hfd_mtp` blocks (seed, verify batch, accept, commit, fence, union) | 21:45: accept_a0 CLOSED; hfd_mtp / hfd_mtp_x routes queued; spec_state_f waits on mtp-exact |
| **mtp-die** | NOT_ON_DIE of all MTP rows (T2 draft / head / seed dies, T3 r25 placement), draft transport pricing, counts | 21:04 start, then only inbound messages (ingest 21:40 / 21:56 / 22:00). No own output yet |
| **mtp-exact** | NOT_EXACT of the MTP rows (wavefront, rollback, spec_state) | 21:21: ROM MTP cached RTL, wavefront 2-stage and HBM connected top launched on EPYC1 |
| **mtp-rollback** | T2 `mtp.rollback_dsk`; T3 rollback hardware (P12: ring WR = 136 vs `pos mod 128`) | 21:59 start. Engram (21:57) already handed it the Engram-history rewind port |
| **engram** | T2 / T3 Engram rows, plus the speculative-history verify and rollback | 21:39: idwin / lookup / rowsink exact (60 tokens). 21:56: hash, wkv, transport and history restore taken; `dsfd_engram_lkp` hardened boundary |
| **s81-dies** | T2 die slots (reset / PG, embed reader, WFC reservation, verify-batch / visibility slots), rack at 120 stages, scan / head dies, array v2 | 21:27: array v2 scope (`results/arch/array_v2_20261008`); scan die on m221pq fit / spine overflow work |
| **ds-control** | T2 control plane on S81 dies, EOS / max_seq_len, RoPE boot table, ECC, link_rt / FEC, re-measure of the MODELLED_ONLY terms (idx score / top-k / gather / scores / hc.fn, HBM service) | 21:57 start; scope "T2 gaps (a)–(e)", benches on ot-epyc3 |
| **hbm-indexer** | T3 indexer: score, top-k, candidates, compressor pooling / key | **no log** |
| **hbm-system** | T3 write-back, HC mix / Sinkhorn, RoPE producer, host loop, EOS, PLL / reset / retry, expert steering | **no log** |
| **qwen-hbm-unify** | everything in T4 except ingest | **no log** |
| **closure-drive** | NOT_CLOSED on blocks that have a die master (T1 30, T2 52, T3 45, T4 36 cells) | drive-2140 at 21:54, s81-tail at 22:00, safe-* variants. The 15-minute drive is live |

---

## 3. Critical path to "all four targets fully covered"

The four chains below run in parallel. Each chain is listed in dependency order, and **the long pole is in bold**. Hand-offs between streams are marked →.

```
                         ┌──────────── O1 token-path re-export (ownerless) ◄──── every chain ends here ───────────┐
T1  emb-hbm bench ─► r21c recipe (+qfd_io_host, +host_if/pkg_ctl/rst/csr, const-ROM banks, PLL) ─► r21c die evidence
        └─ qwen-system: sequencer redesign, kvc master ─┘          **qfd_tile closure at a fixed frame (TT -567)** ─► full-shape
                                                                    die-parent bench (no C++ host) ─────────────────► price
T2  mtp-rom blocks ─► mtp-die draft/head recipes + counts ─► s81-dies rack v2 @120 stages (+WFC slot, dsfd_host)
        engram table-die recipe (32-56 dies) ───────────────┘          ds-control: control plane on S81 dies ─►
        **S81 reduced system gate (none exists) + mtp-exact multi-step rollback / wavefront** ─► field q/BF closure ─► price
T3  hbm-indexer real scorer + hbm-system write path / HCP+Sinkhorn / RoPE producer + mtp-hbm hfd_mtp ─► mtp-die r25m
        **r25 height decision (attention tile R25A does not fit; 1.38 mm margin)** ─► attention / SM / coll closure
        ─► mtp-rollback ring fix + mtp-exact connected bench ─► price
T4  **owner decision: which machine is T4** ─► qwen-hbm-unify: SM INT8 decode, 18-bit vocab, rotate_half RoPE, D4096 norm,
        GQA mapping, LM-head tier, TP group ─► Qwen program for cmdproc20 ─► per-layer exact stages @P8191 ─► qwen_hbm() view
```

### T1: Qwen3-8B on the Qwen ROM (r21c)
1. **emb-hbm-impl** finishes the e2e bench at full shape and writes the r21c recipe. That frees the 11.05 mm² embedding slot.
2. The control-plane masters join that recipe:
   - `qfd_io_host` (~0.45 mm², ingest);
   - `ot_qwen_sys_pkg_ctl` / `rst_seq` / `csr` / `host_if` (qwen-system);
   - a banked constant ROM with a die master (qwen-system);
   - a PLL slot (O2).

   This is the step that turns T1's 19 NOT_ON_DIE rows into closable rows.
3. qwen-system redesigns `qfd_sp_constants_sequencer` (FLOORPLAN_MARGIN) and makes `qfd_kvc` a real master. The SHIFT +144 and crossbar +24 must be built, not only priced.
4. r21c die evidence: GRT and STA, then the relay-stage re-price (O5).
5. **Long pole: `qfd_tile` / `qfd_tile_e` closure** (best TT −567 ps). The tiles are 62.5 % of the die and carry 50 % of the cycles. The fix must hold the frame (2.1 % area margin today, ~4 % after r21c). Each pipeline stage it adds costs ~217 cycles a token.
6. A full-shape die-parent bench in which the token loop, position and layer stages run in RTL, not in the C++ host. Today every full-shape exact token has a simulation-only die top.
7. Re-export `qwen_rom` with the embedding fetch (+248 / +567), the argmax → next-embed turnaround, and the split-spine SU memory latency (O1).

### T2: DeepSeek-V4.1 on the DS ROM S81 array (AR + MTP)
1. **mtp-rom** blocks close: `dsfd_mtp_seq`, `wfc_tok` / `lnk` / `vmx`, `drf_fan`. Their routes are queued.
2. **mtp-die** writes the draft-die recipe and the head-die MTP slot, and settles the counts: draft dies 52 vs 64; whether the head dies' 15,131 DSpark pairs can be removed. It also designs the main-hidden transport from L37–L39 to the seed die and the dsk storage.
3. **engram** writes a table-die recipe with a derived count (32–56 dies for 202.76 GB) and a link class for the table → L1 / L14 transport.
4. **s81-dies** regenerates the rack at 120 stages / 480 layer dies (`rack.json` still says 85 / 340). It re-adds the 0.456 mm² WFC reservation to m221pq and the 0.10 mm² `dsfd_host` slab, rebuilds the scan die on m221pq, re-sizes the head die for 1,792, and places the embed reader.
5. **ds-control** puts the control plane on S81 dies: `pkg_ctrl_x`, `stage_guard`, `link_rt`, `host_cq`, the watchdog / stall export, EOS / max_seq_len, and the RoPE boot table. It also re-measures the six "model + s81_die_tiles" nodes (≥ 38,657 critical cycles graded measured).
6. **Long pole: an S81 reduced system gate.** No S81-level system simulation exists. The control plane passes only on the reduced HDC-core array.

   The gate runs together with **mtp-exact's multi-step rollback** (no campaign has terminated). That needs the compressor open-slot, dsk-row and Engram-history cases, and the whole-array wavefront II.
7. Closure: field q-element and BF (50.5 % of AR cycles), hub SU / HC slabs (no loop elements for norm / quant / RoPE / HC-fn / Sinkhorn), the collective core and the selector.
8. Re-export `ds_rom` / `ds_rom_mtp` with the Engram fetch, the WFC charges (+3 / +13), the seed capture and the draft fan-out (O1).

### T3: DeepSeek-V4.1 on the HBM accelerator r25 (AR + MTP)
1. In parallel, the hardware that is not on the die gets RTL masters:
   - **hbm-indexer:** the real `ot_hbm_accel_index_path` scorer replaces the `hfd_index_q` shells (~5.9 mm² a quarter vs a 5.14 mm² slot);
   - **hbm-system:** the KV / CKV / IK write path (`dskv_wb` into a master, plus write commands in the svc), an HCP + Sinkhorn unit, a RoPE cos/sin producer, PLL / reset / link retry, and expert-workgroup steering;
   - **mtp-hbm:** `hfd_mtp`;
   - **ingest:** `hfd_host_ingest` behind the shared HBM write port.
2. **Long pole: the r25 floorplan decision (mtp-die with the HBM die views).**
   - The attention-tile fix R25A does not fit the quadrant (6,531.8 vs 5,529.6 µm). Adopting it makes the die ≈ 26.6 mm tall, over 26.
   - The indexer, HCP and MTP growth all land in the same hub band, which has 1.38 mm of height margin.
   - Until that layout is chosen (re-arranged 5 × 3 rows, a wider die, or split tiles), no T3 block can close at its final frame.
3. Closure: `hfd_sm` (17 % of AR, no whole-SM routed DB), `hfd_coll` (41 %), the SU / SFU / HC quarters, `hfd_attn_tile` (SS −2,032 ps), and the 13 of 17 svc segments that have no view.
4. **mtp-rollback** fixes the ring: `dskv_wb` uses `pos mod 128` while spec_state assumes WR = 136. **mtp-exact** then runs the connected rollback bench (spec_state_f → write-back → read stream).
5. Re-export `hbm_ds` / `hbm_ds_mtp` (O1). The re-export must charge:
   - the engram / compressor / candidate-merge collectives (now 0);
   - the verify write-back;
   - the host doorbell fan-out;
   - full FEC on the 23 draft crossings;
   - the expert union measured, not from W19.

### T4: Qwen3-8B on the HBM accelerator
1. **Long pole: an owner decision on which machine T4 is.** The options are the unified r25 die, or the Qwen HBM tile die of vehicle A, which has exact RTL at TP2 / TP4 but no closure elements.
   - The decision also needs the TP group for Qwen on r25.
   - Separately, the owner must decide whether Qwen MTP applies on r25.
2. If the answer is r25, **qwen-hbm-unify** builds:
   - an INT8 per-row → BF16 decode in the SM. This touches T3's largest open block;
   - an 18-bit argmax index and DSpark TW;
   - rotate_half RoPE over 128 dims (theta 1e6);
   - a D = 4,096 BF16 norm mode;
   - QK-norm as an SU program;
   - softmax-sink-off and SwiGLU-BF16 modes;
   - GQA addressing, where the MQA broadcast tile uses only 25 % of its lanes;
   - an LM-head tier decision: streaming costs ~49k cycles, about +8 %.
3. A Qwen decode program for cmdproc20, plus per-layer exact stages at P8191 against a golden in r25's arithmetic.
4. `qwen_hbm()` in `token_path_export.py`, `unified_composition.py` and `reprice` (O1). Until then all 50 T4 nodes are NOT_PRICED.

### Shared dependencies (they gate more than one target)
| Dependency | Gates | Owner |
|---|---|---|
| Token-path re-export | NOT_PRICED / MODELLED_ONLY on all four targets | **ownerless (O1)** |
| r25 floorplan / height | T3 and T4 | mtp-die + the HBM die views (hbm-system / hbm-indexer feed the areas) |
| Closure drive | NOT_CLOSED: T1 43, T2 79, T3 60, T4 37 rows | closure-drive (live) |
| Host / ingest masters | every target's `host.*` / `prefill.*` | ingest (live) |
| MTP exactness campaigns | T2 / T3 MTP headlines (4,351.6 / 3,700.3 tok/s) | mtp-exact (live) |

---

## 4. Risks, ranked

| # | Risk | Targets | Why it ranks here | Owner |
|---|---|---|---|---|
| 1 | **r25 height**: attention tile (R25A ≈ 26.6 mm) + real indexer + HCP / Sinkhorn + `hfd_mtp` all grow the 1.38 mm-margin hub band | T3, T4 | Can force a re-arranged or wider die for all 96 dies, and re-opens closed blocks. Blocks every T3 closure at its final frame | mtp-die + hbm-indexer / hbm-system (two of the three have no log) |
| 2 | **`qfd_tile` closure inside a 2.1 % (≈ 4 % after r21c) area margin** | T1 | 62.5 % of the die and 50 % of the cycles. Any growth breaks the reticle, and any added stage costs ~217 cycles a token | closure-drive |
| 3 | **MTP correctness is unproven in RTL**: T3 ring mismatch (rejected row at r overwrites r − 128, still read); T2 compressor open slot / dsk / Engram history; no multi-step campaign terminated | T2, T3 | Both MTP headlines (3.01× / 2.16×) rest on it | mtp-exact, mtp-rollback, engram |
| 4 | **Both ROM machines have their control plane only on reduced vehicles**: T1 in the C++ host, T2 on the HDC-core array. No full-shape die-parent bench (T1) or S81 system gate (T2) exists | T1, T2 | Blocks "a real chip produces a token". Turnaround cycles are unpriced | qwen-system, ds-control (both just started) |
| 5 | **Engram table dies 36 vs 32–56**, with no recipe; 3.3 kW always-on | T2 | Up to +20 dies and their power and links | engram + s81-dies |
| 6 | **T4 has no defined machine** | T4 | 63 rows with gaps, 0 covered. The 880.7 tok/s headline is a model | owner decision → qwen-hbm-unify (no log) |
| 7 | **No one re-exports the token path (O1)** | all | NOT_PRICED cannot close; the published numbers drift from the hardware that lands | ownerless |
| 8 | **Measured-graded cycles that are model terms**: T2 ≥ 38,657 critical (4.7 %); T3 switch tail 6.8 % plus vendor TU 28.7 %; T2 hop PHY 14.9 % | T2, T3 | Publication risk if a reviewer challenges the figures | ds-control (T2 re-measure); O6 / O7 (T3) |
| 9 | **Draft-die count 52 vs 64**; head dies not re-sized for 1,792 while serving 5 draft sweeps + 6 verify heads a step (12.37 µs entry interval unproven) | T2 | Die count, and the MTP step time | mtp-die (no output yet) |
| 10 | **Ownership on paper only**: hbm-indexer, hbm-system and qwen-hbm-unify have no log; qwen-system and ds-control have a start line only | T1–T4 | 244 gap entries rest on them | coordinator |

---

## 5. Gaps that change area or die count

### 5a. For s81-dies (array v2, `results/arch/array_v2_20261008`)
| Item | Change | Source / owner | Status |
|---|---|---|---|
| Layer dies / stages | `rack.json` 85 stages / 340 layer dies → **120 / 480 (+140 dies)** | T2 C04, audit §2; s81-dies | rack not regenerated |
| Engram table dies | 36 (inherited from S = 58) → **32–56** from 202.76 GB; no recipe | T2 D03; audit finding 1; engram | engram building the lookup element; table-die recipe open |
| Draft dies | 52 (rack) vs **64** (`draft.json`); 15-link star now `dsfd_drf_fan` (+0.124 mm² on primary / replica-0 dies) | T2 M07; mtp-rom 22:00; mtp-die | count undecided |
| Head dies | 12, not re-sized for 1,792; the 15,131 DSpark pairs per head die can be removed if the drafter moves to the draft dies; + `dsfd_mtp_seq` 0.023 mm² | T2 M08 / M11 / M17; mtp-rom; mtp-die | plan-only floorplan |
| Scan dies | 32 (4 stacks) never rebuilt on m221pq; spine overflows 200 µm on the 4-stack die (VM 2.66 + WFC) | audit §2b; s81-dies 21:27 | hub column width sweep |
| Per layer die | + WFC 0.456 mm² reservation (dropped in m221pq) + lnk / vmx 0.079 + `dsfd_host` 0.10 | T2 M12 / M13; mtp-rom; ingest RQ-ING-1 | fits (layer die 48 % placed) |
| S0 die | + `dsfd_wfc_tok` 0.012 mm² + `dsfd_engram_lkp` (pin flops + credits) + Engram idwin ring | mtp-rom; engram | small |
| dsk storage | 3 stages × 128 rows a user; home not chosen (head or draft die HBM) | T2 M04; mtp-die | open (mtp-die asked by ingest 21:40) |
| Main-hidden links | 3 × 5,120 BF16 a verified position from the L37 / L38 / L39 dies to the seed die | T2 M01 / M02; mtp-die | no link class |

### 5b. For mtp-die (HBM r25 fit; height margin 1.38 mm, area 753.2 mm²)
| Item | Change | Source / owner |
|---|---|---|
| Attention tile R25A | +~1.0 mm per quadrant row pair → ≈ 26.6 mm (**over 26**) | audit §3; HBM die views |
| Real indexer | ~5.9 mm² a quarter vs a 5.14 slot (+~3 mm² over 4 quarters, in the hub band) | T3 D28; hbm-indexer |
| HCP + Sinkhorn unit | `hfd_hc` holds only hc_post; the HCP is charged as 6.09 mm² of model area (×2 hub scale = the 12.2 mm² `hfd_hc`) | T3 D09 / D10; hbm-system |
| `hfd_mtp` (+ skid slices, pin flops) | 0.3–0.6 mm² | T3 P16; mtp-hbm |
| `hfd_host_ingest` + per-stack write merge | ~0.1 mm² (east strip beside `hfd_loader`) | ingest 22:00 (reviewer-approved) |
| KV / CKV / IK write path | `dskv_wb` into a master plus svc write commands; 13 of 17 svc segments have no view | T3 D20 / D25; hbm-system |
| PLL / reset sequencer | no macro / master today | T3 B04 / B05; hbm-system |
| T4 on r25 | SM INT8 unpack ×32 SMs (area unknown); 18-bit argmax (small); LM head: 155.6 MB a die cannot be SRAM, so it streams (+~49k cycles, no area) | T4; qwen-hbm-unify |

### 5c. Qwen ROM die (T1)
| Item | Change |
|---|---|
| Embedding to HBM (r21c) | −11.05 mm² placeholder (the real ROM table would have been 88.1 mm²) |
| `qfd_io_host` | +~0.45 mm². The reviewer at 21:56 confirmed the board-SerDes HOST class with no PCIe slab, so not +5.45 |
| Control-plane masters (pkg ctl, rst seq, CSR, host_if) | small; reduced-vehicle RTL exists |
| Constant ROM banking (543,233 × 64 b) | unknown; today it is inside the 2.16 mm² sequencer reservation |
| PLL macro | unknown (O2) |

The margin moves from 11.2 to ≈ 21.8 mm² before the PLL and constant-ROM growth. **Any `qfd_tile` growth above ~4 % breaks the reticle.**

---

## 6. Work per owner (non-closure gap-cells, from `MATRIX.json`)

| Owner | T1 | T2 | T3 | T4 | First items |
|---|---:|---:|---:|---:|---|
| qwen-system | 23 | | | | host_if / pkg_ctl / rst / CSR on die; constant ROM as hardware; token loop; stop; bounds; split-spine exact |
| emb-hbm-impl | 8 | | | | r21c recipe; boot load + SECDED bench; charge +248 / +567 |
| ingest | 8 | 9 | 10 | 3 | `qfd_io_host` / `dsfd_host` / `hfd_host_ingest` masters; full-shape FP8 case; TTFT pricing |
| ds-control | | 26 | | | S81 control plane on dies; EOS / max_seq_len; RoPE boot table; ECC; re-measure the 6 model-graded nodes |
| s81-dies | | 7 | | | rack at 120 stages; WFC slot; reset / PG master; embed reader |
| engram | | 14 | 5 | | table dies; transport link class; hash / history on die; speculative history |
| mtp-rom | | 6 | | | `dsfd_mtp_seq` / accept / commit / `drf_fan` closure |
| mtp-die | | 14 | 15 | | draft / head / seed dies; r25 `hfd_mtp` placement; draft transport + FEC |
| mtp-exact | | 5 | 5 | | multi-step rollback, wavefront, connected HBM rollback bench |
| mtp-rollback | | 1 | 6 | | dsk rows; HBM ring WR = 136 vs `pos mod 128` |
| mtp-hbm | | | 3 | | `hfd_mtp` closure; seed capture pricing; union measured |
| hbm-indexer | | | 8 | | real scorer on die; candidates; top-k merge |
| hbm-system | | | 28 | | write path; HCP + Sinkhorn; RoPE producer; host loop / EOS; PLL / reset / retry; expert steering |
| qwen-hbm-unify | | | | 137 | needs the owner decision first |
| ownerless | 9 | 1 | 14 | 0 | §0 |

Closure-drive owns the NOT_CLOSED cells: T1 30, T2 52, T3 45, T4 36. In this table, ds-control's T2 count includes the six model-graded nodes it re-measures.

---

## 7. How the view and the ledgers stay in step

- `/api/coverage` in the fleet viz reads `results/arch/coverage_20261008/{T1..T4,MATRIX}.json` and `gen_matrix.py` from the git tree `origin/main`. Every push from any worktree of this repository updates that ref.
- It re-derives the matrix whenever the tree hash changes, and re-joins the cells' elements against the live `/api/elements` on every request.
- A stream that closes a gap **edits its ledger node** (the `gap`, `closure`, `exact_bench` and `die` fields) and merges to main. The matrix, the Coverage table and the token-path highlights follow within a minute.
- A new function goes into the ledger first. Until a row in `gen_matrix.py` gathers it, it appears as an `unmapped.*` row, so nothing is lost. `--check` flags it.

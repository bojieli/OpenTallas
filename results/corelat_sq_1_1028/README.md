# CORELAT-SQ-1 (2026-10-28): early core-tap tables for S81, QC and KV

Lane CORELAT-SQ-1, started by COORD with the RISK-SWEEP-1 ruling (COORD-REVIEW-QUEUE 02:59). KV was added by COORD at 03:2x (RISK-SWEEP-2).

These tables are **plan inputs for the die owners** (DIE-S81-7, DIE-QC-5, DIE-KV-6). No plan was edited.

## Files

| file | content |
|---|---|
| `corelat_table.py` | per-module table: placed-view identity, insertion, tap, boundary FF hold estimate |
| `corelat_delta.py` | per-partition-type tap delta: current tap vs new tap, xy, action |
| `kv_extra_gen.py` | KV numbers from the repo views (the KV plan binds no view) |
| `run_all.sh` | regenerates all six outputs from the repo root on intel2 |
| `{s81,qc,kv}_core_taps.{json,tsv}` | the tables |
| `{s81,qc,kv}_tap_delta.json` | the deltas |
| `{s81,qc,kv}_extra.json` | non-view numbers (CTS, model, ETM), each with a source and label |
| `{s81,qc}_signed.json` | SIGNED records outside the repo that were considered |

Plans read:

| die | plan | sha |
|---|---|---|
| S81 | intel2 `die-s81-5/plan_s5.json` | d29050658673 |
| QC | epyc2 `die-qc4-1028/plan_grpP/event/qc_grpP_event.json` (K2) | 40b05f16d753 |
| KV | intel1 `risk-sweep-2/hm_r26q9b.json` (q9b) | — |

Copies of all three are in intel2 `/srv/opentallas-scratch2/claude/corelat-sq-1/in/`.

## Method

The mechanism follows DIE-HEAD-5 `signed_mean_core_taps` and `core_latency_files`, and main `early_core_taps.add_from_means`.

1. **Placed-view identity.** Checked in this order; the module name is never used as a guess:
   - the plan `lib`;
   - else the `views/<mod>/` directory that holds the plan LEF;
   - else every repo view whose LEF matches the plan LEF (SIZE plus signal-pin set; power pins are ignored);
   - SIGNED records outside the repo are used only if their LEF matches the placed LEF.
   - QC and KV bind no LEF and no lib at all. For QC the SIGNED SU views are the views to bind (COORD 02:59). For KV the main `cores.find_views` default pick is used, and its identity is UNCHECKED.
2. **Insertion.** Main `core_clock_contract.load(require_signed=False)` is used, in this order: `clock_contract.json`, then SIGNED `signoff.json`, then routed-SPEF `insertion.json` boundary-register MEAN. The ETM max is never used.
   - For three views main refuses the file ("explicit clock-pin mapping required"): bf_col, rom_elem and rxsb. For those the boundary census is read directly.
   - Each number carries its source, plus CHECKED/UNCHECKED in the `label` column.
3. **Tap.** A core gets an EARLY core tap if its TT mean is above 270, which is 250 plus the 12.3 band of 20.
   - `insertion_ps` = TT mean, `insertion_ff_ps` = FF mean.
   - `budget_owner` starts with `SIGNED ...` for SIGNED views and with `parent_budget ...` otherwise.
   - Cores with a mean of 270 or below stay on the common tap. A current early tap on such a core is listed as DROP.
   - Multi-root cores get one tap per clock pin (per-pin rows `module:pin`).
4. **Boundary FF hold.** This is the RISK-SWEEP-1/HBM-RISK-2 model, UNCHECKED:
   - `comp` = FF mean for a tapped core, else min(FF mean, 202.5).
   - `hold_in = 25 - max(Bmax - comp, 0) - 0.05 Bmax`
   - `hold_out = 25 - max(comp - Bmin, 0) - 0.05 Bmin`
   - The `_u60` columns are the same with 60 ps hold uncertainty, i.e. value - 35. Under this model's 50-ps base data delay they are negative for every core by construction, so they are INFO only.

## Outcome (boundary FF hold estimates are UNCHECKED model; reads are CHECKED unless marked)

### S81: 52 modules, 18,993 placements

**Re-taps**

| core | placements | current tap TT | new TT / FF | source | FF hold before → after |
|---|---|---|---|---|---|
| bf_col | 456 | 644.9 (ETM max) | 544.0 / 435.2 | routed insertion.json boundary mean, CHECKED read | -101.5 → -14.3 |
| ROM elem q_qxpq_w10 | 864 | 552.3 (ETM max) | 510.3 / 402.1 | routed insertion.json boundary mean, CHECKED read | -67.3 → -22.0 |
| gunit_l5 | 1 | 520 | 436.6 / 364.1 | placed view | — |
| bksel_c | 1 | 430 | 367.2 / 302.2 | placed view | — |

- The gunit_l5 number is from the placed `ref_tile/dsdv_gunit_l5` view. RISK-SWEEP used `_ro3` (465.1).

**New early taps for the 15 late types** (TT / FF, all CHECKED reads unless marked)

| core | TT / FF | note |
|---|---|---|
| idx_tx_n32 | 829.1 / 665.2 | ETM-range midpoint, **UNCHECKED** |
| bksel_q | 651.6 / 527.5 | |
| xrt3 | 607.7 / 501.4 | |
| xrt1 | 433.6 / 355.5 | the placed view is `s81sl_xrt1`, not `_b` (468.3) as RISK-SWEEP assumed |
| eg | 351.3 / 290.1 | unique LEF match |
| gunit_l1 | 306.7 | |
| gunit_l4 | 303.0 | |
| vsw | 298.4 / 243.2 | |
| gunit_l0 | 286.1 | |
| gunit_l2 | 276.7 | |
| xfin | 274.4 | |
| bk_g | 329.2 | |
| capc5r root ck_rt | 442.0 | |
| capc5r root ck_rn | within band | |
| gunit_l3 | 257.6 | within band, no tap |

- The **vs** footprint has no view: its plan template LEF matches neither `ref_tile/s81sl_vs` (247 TT) nor `s81sl_vs_n32f` (366.8, the variant RISK-SWEEP used). So vs is not tapped.

**After the taps**

- 21 types / 2,781 placements are still below 0 FF hold, but by much less: the worst is -95.3 (idx_tx_n32, ETM) and the rest are -62.5 and better.
- What remains is in-core spread plus the 5% OCV term. Early taps cannot remove it; it needs boundary data hold buffers (allowed, v4.6-4.9) or in-core fixes.

**No view**

- **attn_hcore (1,024 placements):** measured by OpenSTA on the routed but NOT SIGNED kit_ctsA_d75 (outline equals the plan LEF). Boundary-register means are 252.4 TT / 208.0 FF (n 1,213) → within band, so no early tap. CHECKED read.
- **ve_m / ve_s / vn_a / vn_b (75 placements each):** 12.9d model values of 365 / 285 / 371 / 374 TT, UNCHECKED. The model ran +13% high on attn_hcore. CTS probes are LIVE on intel2: containers `corelat-sq1-cts-{ve_m,vn_a,ve_s,vn_b}`, started 03:11, ETA 04:15-04:45.
  - Collect with `/srv/opentallas-scratch2/claude/corelat-sq-1/collect.sh ve_m vn_a ve_s vn_b`.
  - Then put the measured means into `s81_extra.json` and re-run `run_all.sh`.
- **No matching view (placed LEF ≠ any view; these keep their current plan taps):**
  - svc_sx_hrow (128 placements): the plan `_c` LEF is 138x164 and the view is 216x216.
  - vs (75)
  - vq (75): the SIGNED autopilot vq 8d2f04b676 has a different pin set from the placed template, so it is a re-bind candidate.
  - eng_rr_e (1) and eng_rr_h0 (1).
- **Memory macros:** ROM 4096x72 (7,644 placements) and SRAM 512x128 (150) have no internal tree, so insertion is 0 and they stay on the common tap.

**Variant identity of the 35 types the plan binds no lib for**

| resolved by | types |
|---|---|
| plan LEF view directory (CHECKED) | 25 |
| unique LEF match (eg, eng_rr_h1) | 2 |
| no match | 8 |

- **SIGNED re-signs with matching LEFs:** the autopilot SIGNED payload536, NNfd and rstg have the plan LEF (same footprint and pins) but a different lib from the plan view. The SIGNED numbers are used here: 256.8 / 255.6 / 235.8 TT, all within band, so no tap. The die owner should bind the SIGNED libs; the plan libs are the old 54-112 ps views.

**In-core spread (flags)**

- **capc5r** has 5 clock roots. With one tap per root:
  - 4 roots are at or below 148 ps all-register spread: ce 132.6, cw 148.1, rn 55.4, rs 34.8.
  - Root **ck_rt** alone spans **287.2** (1 boundary register at 442) → it still needs an in-core fix and re-sign.
- **bksel_q:** spread 165.1 → needs an in-core fix and re-sign.
- **bf_col:** 149.8, at the edge.

### QC: 9 modules, 960 placements

**SU taps from the SIGNED means**

| core | placements | current tap TT | new TT / FF | source | FF hold before → after |
|---|---|---|---|---|---|
| vmr | 36 | 386 | 255.12 / 203.18 → **DROP** to common (within band) | SIGNED f4kfinal 77013e5059 | -108 → -9.3 |
| crh_rp1 | 12 | 349 | 244.32 / 193.3 → **DROP** | SIGNED f4g 5ed4500430 | -87 → -14.9 |
| prog | 12 | 481 | 472.71 / 363.28 (early 222.7 / 160.8) | SIGNED s8b 6aa7f1fc4d | → -29.9 |
| btab | 12 | 445 | 352.8 / 295.2 | ref-tile routed view; **VIEW NOT FINAL** (r8/r10 open) | -78 → -12.9 |
| s8x_crh (NEW tap) | 12 | 250 | 292.49 / 240.62 (early 42.5) | SIGNED qc/closed, LEC EQ 3697 | -63 → -12.3 |
| rst3 | 12 | 250 | 242.12 / 193.52 → common | SIGNED K0 hold_b | → -0.3 |

- For crh_rp1, the older SIGNED f62 view (316.5 TT) is still listed in the release cache. Bind f4g, as QC-CORES says.

**A0 NK / NL (768 placements)**

- The tap is a **390 TT / 312 FF** placeholder (range 355-424 / 284-340). It is UNCHECKED and built as follows:
  - Child CTS from this lane, placement RC: rawleaf 158.0, romleaf 170.3 and node 222.3 TT.
  - Plus an analytic parent trunk (30 + 515 um x 199-334 ps/mm) balanced to node.
- After the tap, FF hold is about -15.8 (it was about -345 with the 682.7 model).
- The 12.9d model value of 682.7 is far too high.
- Rebuilding to 250±20 is impossible, since node alone is 222 before any trunk.
- A real number needs a parent kit CTS (about 64k cells, children as abstracts). It was not launched.
- If COORD keeps the R3b drop-island form instead, the tap is 250 / 202.5, but node then exceeds its 201 budget by about 21 ps.
- The plan currently carries 42 / 41 old a0cv8 taps per core. The new centre-tap xy is TO-DO (the plan has no A0 LEF).
- Data: intel2 `/srv/opentallas-scratch2/claude/corelat-sq-1-a0cts/`.

**su_lane_w (96 placements):** model 288.4 TT, UNCHECKED, no view.

### KV: 30 modules, 1,621 placements (plan binds no view; identity UNCHECKED)

**New early taps** (RISK-SWEEP-2 FF hold estimate before → after)

| core | placements | TT / FF | source | FF hold before → after |
|---|---|---|---|---|
| head e1 | 256 | 289.4 / 233.2 | core.json routed register census | -26.7 → +5.3 |
| head e5 | 256 | 291.5 / 235.0 | core.json routed register census | -29.0 → +6.7 |
| head e6 | 256 | 291.1 / 234.3 | core.json routed register census | -33.1 → +1.3 |
| head e0 | 128 | 294.2 / 237.1 | core.json routed register census | -31.9 → +2.8 |
| head e2 | 128 | 293.7 / 236.7 | core.json routed register census | -40.8 → -4.0 |
| pv_pair | 256 | 352.7 / 280.8 | ETM-range midpoint, UNCHECKED | -88.7 → -25.8 |
| kvs_ctl | 1 | 513.6 / 421.5 | routed insertion.json | -298 → -78.7 |

- e0, e2 and e6 have no plan tap at all today. Their new taps need xy from the bound view (TO-DO).
- pv_join, the hr_* cores with views and the other hr_* cores stay common (TT 187-264).
- **No view (17 types / 277 placements):** kvs_pc (124), ectlk_q0..q3 (128), hr_phy_adp (8), astk (4), kvs_pc_h_head_p (4), ahub and 9 hr_* cores (1 each).

## Blockers / ASKs

1. **Kit side: legacy ETM max still applies.** `gen_phys.signed_mean_core_taps` turns the mean contract on only when EVERY core tap of a type is SIGNED. No early-tap type qualifies today: S81 0/120, QC 0/12, KV all parent_budget.
   - So `core_latency.txt` in the kits stays the legacy ETM max, the HEAD -875 mechanism, even after these taps are in the plan.
   - `core_clock_contract` already has `from_budget` (`parent_budget`), but `gen_phys` calls it with `require_signed=True` and `_validate` rejects `parent_budget` in that mode.
   - **DEFAULT:** a small shared-tool opt-in, sent to ROOT-MERGE. Under it, a plan type with `budget_owner` `parent_budget` writes the mean contract with `require_signed=False`, for non-release kits only. Release kits still need SIGNED.
2. **Last-mile limit.** Early taps beyond about 250 ps exceed what last-mile wire removal can deliver (CLOCK 10-25: leaf→tap 203-316 TT): idx_tx_n32 579, bksel_q 402, xrt3 358, bf_col 294, rom_elem 260, kvs_ctl 264, prog 223, gunit_l5 187.
   - These need the die_clock "tap from level D-1" option (not built) or a rebuild of the core to 250±20.
   - **DEFAULT:** the die owners apply the taps and report the delivered early value. Shortfalls go to CLOCK-RESIDUAL.
3. **Residual FF hold.** After the taps the remaining estimates are small negatives. They come from in-core spread plus 5% OCV. They need boundary data hold buffers per type, which v4.6-4.9 allows, and real-view die STA to confirm.

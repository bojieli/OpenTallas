# S81-ROMOPT-B (10-20): per-stage expert map and EXACT ROM / cfg capacity check of the p4l-MU release die

Owner 10-20 ~08:45: O2 (all 12 q pairs + rotation) is required for ROM fit; commit the per-stage expert map; make the
capacity check exact (< 100 % per die, per-stage margins); contents + compiler only, STOP if a fit needs a physical or
array change.

## Verdict: STOP. The release chain cannot hold the model, whatever the compiler does

- **Chain of record.** 520 dies = 388 p4l layer dies (**97 TP4 stages**) + 52 head/other dies + 80 copy-B dies.
  - Sources: `s81_balance_1018` (`layer_dies` 388), the MU cal1 chain plan (copy B = `round(388/40)` dies a group,
    same ROM content), and token_path_1018 (40 + 17 sub-stage hops + unplaced hops).
  - Load: 15,360 routed experts / 97 = **158.35 experts a stage** on average.
- **Structural floor** (`xs_capacity.py bound`, `expert_floor.json`). This is exact `segment_order` arithmetic, with no
  model.
  - Per die, one expert takes 71,680 paired ROM addresses: GU 46,080 + down 25,600 (raw 69,120; the down K = 2,304
    pads 36 -> 40 words a super-row).
  - That is 48.96 a q pair (1,464 pairs). Pair fills move in steps of 8, so some pair takes **>= 56 per expert**.
  - The static schedule fixes a routed slot's return calendar. Every resident expert of a stage must therefore use ONE
    pair layout, which gives N x 56 <= 8,192: **N <= 146 experts a stage, even with no dense weights**.
  - 97 stages need >= 159 on some stage. **No contents-only layout fits.**
- **Actual allocator, release flags** (QPAIRS 12, GU_MERGE, TOPO, PROP, CAL_SEGMENT, APROJ_TOPO).
  - Cost: **60 paired addresses / expert on the worst pair** (exp_n120 = 7,200 on all 122 frames).
  - The exact boundary is expert-only **N = 136: 8,160 / 8,192 (99.61 %, margin 32) PASS**. **N = 137: the real image
    writer refuses** (`ROM depth` assert, all 122 frames); in measurement mode it reaches 8,224 = 100.39 %.
  - The 97-stage map needs N 144-162 a stage. **It FAILS on every stage**, worst ~119 %.
  - Exact so far: **L0 + 155 experts (R000) = 9,768 = 119.24 %** (BF 13.3 %, cfg7 969).
- **What would fit** (all need a new chain plan and more dies, so they are owner decisions):

  | layout | worst-pair cost / expert | min stages | layer dies | vs 388 |
  |---|---:|---:|---:|---:|
  | as built (O2 rotation; NOT static-safe, see below) | 60 | 116 | 464 | +76 |
  | as built, one layout for every expert (static-safe) | 64 | 124 | 496 | +108 |
  | structural floor (needs new chunk / pair policy, not built) | 56 | 108 | 432 | +44 |

  These are `min_stages_model.json` figures, with the dense intercepts measured. The 116-stage map is in
  `stage_map_116.json`. Its exact run is pending.

## Physical limits (verified)

- **q / BF pair ROM: 8,192 paired addresses.**
  - `ot_v41_rom_elem_w10`: 13-bit `w_ptr` / `rom_addr`, one `ot_rom_8192x274_m8` a macro (PP: two
    `ot_rom_4096x274_m8`), NB 2 macros a pair.
  - Field `depth=8192`, and `add_phase` asserts it.
- **cfg7: 1,024 phases a frame programme** (`write_images`: 7 banks x 4,096 rows, 4 rows a phase).
- **Spine phase ROM: 4,096 words** (2,048 phases). **Stream ROM: 16,384** after dedup.
- **Calendar: 4,096 rows** (paired `ot_rom_4096x72_m8`).
  - A token's calendar is per layer, measured with CAL_SEGMENT at L0 1,868 and L2 2,006. It does not grow with
    resident experts.
  - A stage that touches two layers is charged both.
  - The Engram `eng.wkv` calendar rows are NOT in the measured 2,006 (`XS_FIELD_CAL L14` lists no `eng.wkv`), so they
    are a lower bound for L1 / L14.

## Measured inputs (actual allocator, every one of 122 frames; `probe/`)

| spec | worst q pair | q % | BF max | cfg7 phases |
|---|---:|---:|---:|---:|
| dense L0 (31 plain layers) | 464 | 5.66 | 1,088 | 39 |
| dense L1 (Engram) | 1,008 | 12.30 | 1,088 | 56 |
| dense L2 / L20 / L24 (index) | 560 | 6.84 | 1,152 / 1,152 / 1,088 | 46 / 46 / 45 |
| dense L14 (Engram + index) | 1,104 | 13.48 | 1,152 | 63 |
| 120 experts, expert-only | 7,200 | 87.89 | 0 | 720 (6 / expert) |

- **COMPACT_TAILS decision: leave it OFF.**
  - With COMPACT 1 the expert cost is identical (7,200), because TOPO's balanced 3/4-row chunks have no SENT tails.
  - Dense changes by at most 16 words (L14 1,104 -> 1,088).
  - So it saves nothing that matters and adds unqualified shapes.
- **BF pairs are not the limit:** 14.1 % at most, one attention a stage.
- **cfg7 is not the limit:** 6 phases an expert, 816 at N = 136, 969 at L0 + 155.
- **Static-schedule hazard of the as-built O2 rotation.** `rot = k * npair mod 12` keys the pair subset on the global
  phase index. With the experts' GU phases consecutive, even and odd experts get different pair layouts
  (`layout_identical_all` = false).
  - A routed slot's calendar cannot be legal for both layouts.
  - The release compiler must pin one layout per (op, chunk) for every resident expert. With today's chunking that costs
    64 / expert (`ctl_exp_n1`), not 60.
  - The as-built 116-stage fit is optimistic for this reason.

## Per-stage map (`stage_map.json` = release 97-stage map; `stage_map_116.json` = minimum as-built fit)

- **Rule.** Experts go in (layer, id) order, contiguous over the chain. The attention (dense) of layer L sits on the
  stage holding expert (L, 0). Never two attentions on one stage.
- **Balance.** Stage boundaries are set so the measured worst-pair load (dense intercept + N x 60) is equal.
- **Dies.** Each stage is 4 rank dies; rank r holds row quarter r of every matrix.
- **Not on layer dies:**
  - embed, head and the MTP draft go on the head dies;
  - the Engram tables go in HBM;
  - hc / norms / sinks / small BF vectors go in SU / svc.
- **Copy B** duplicates the dies of the attention stages of layers 2/8/14/20/24/28/32/36, with the same ROM content and
  so the same verdict.
- **Tables.** `stage_table_97.md` and `stage_table_116.md` hold the full per-stage tables: layers, dense, expert ranges,
  N, worst pair, fill %, margin, BF %, cfg7, calendar, verdict.
  - Rows marked "model" carry the probe model. It is within 4 words of the exact run where both exist: R000 model 9,764,
    exact 9,768.
  - The exact all-stage runs are live: `pending_results.txt`, ep9 `out/map97` and `out/map116`.
- **Release 97 (model).**
  - N 144-162; worst R000 (L0 + 155) at 119.2 %. Every stage is over 107 %.
  - The calendar worst is 4,012 rows (two index layers on one stage, margin 84).

## Negative controls

| control | expected | result |
|---|---|---|
| 10-pair layout, L0 + 140 experts (ROMCAP 110-stage case) | FAIL | real writer: ROM depth assert on 122/122 frames; measured 10,656 = **130.08 %** (ROMCAP's modelled 101.6 % understated it) |
| 10-pair layout, 140 experts only | FAIL | 10,080 = 123.05 % (72 / expert) |
| 12 pairs, injected overfull expert-only N = 137 | FAIL | real writer refuses (122/122); measured 8,224 = 100.39 % |
| 12 pairs, N = 136 (positive) | PASS | 8,160 = 99.61 % |
| compile hook, injected one overfull stage in an all-pass map | CompileFault | `hook_selftest.log`: FAULT on R005 100.4 %; all-pass map PASS |
| frame-class dedup vs full run (dense L14) | equal | 0 / 122 mismatches (`--dedup` option) |

## Compile-time check (task 4)

- **Behaviour.** `xs_place.py frame` and `xs_field_calendar.py die` call `xs_capacity.verdict()` before compiling.
  - The default is ON whenever the release layout is compiled (`OT_XS_QPAIRS=12`). `OT_XS_CAPCHECK=0` opts out, for
    single-token component benches only.
  - The check raises `CompileFault` unless every stage of `OT_XS_STAGE_MAP`, or of `OT_XS_STAGE` alone, carries an exact
    xs_capacity verdict that passes.
  - The default map is this `stage_map.json`, the release 97-stage map. **With today's chain it refuses, as it should.**
- **Bench path.** The bench path (`gen`) is not hooked.

## Files and commands

- **Tools:**
  - `tools/s81_dv/layer_prog/xs_capacity.py`: run / bound / verdict. FixN puts N synthetic experts on the real fixture
    rows; `OT_XS_CAP_VDEPTH` is the measurement-only depth raise.
  - `tools/s81_dv/layer_prog/xs_stage_map.py`: build / merge / minstages / table, over the checkpoint header census.
- **Run** on the fleet: `run.sh TAG SPEC COMPACT QPAIRS [--jobs N] [--dedup]` (copy in `probe/`). Fixtures:
  `/srv/opentallas-scratch/claude/s81-calpipe/fixtures`. Die: `toksim-s81b-fwoa/dieref`.
- **Merge** (pending pickup): `xs_stage_map.py merge --map stage_map_97.json --runs out/map97/summary.json` (same for
  116). Then copy it over `stage_map.json` and regenerate the tables.

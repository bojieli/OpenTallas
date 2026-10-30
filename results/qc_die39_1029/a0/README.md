# DIE-QC-39 A0 core clock: standard-stage generator, ESTIMATE FIRST (12.14b)

**Verdict: NO BUILD.** The estimate predicts that standard stages beat TritonCTS FF hold on **NK** but **not on NL**.
core_infra stays OFF (DIE-QC-37-PARK (4)). No placement or CTS probe was launched. No numbers below come from a new
build. Tags: CHECKED means measured or recomputed from signed/probe data; UNCHECKED means model output.

## 1. Inputs (all CHECKED)
| item | NL `a0nl14icg2rr2` | NK `a0nk14icg2rr1` |
|---|---|---|
| TritonCTS FF hold WS / fails (DIE-QC-35) | **-172.53** / 2370 | **-571.84** / 3082 |
| V2 core_infra FF hold WS / fails (DIE-QC-37) | -281.18 / 5080 | -289.88 / 6434 |
| V2 worst by class (probe/hold_all.tcl, slack <= +250 ps; NL 21552 paths, NK 23362) | reg->outport -281.2, reg->reg -224.6, ->macro -177.2 | ->macro -289.9, port -251.5, reg->reg -172.1 |
| kit vclk FF source latency | 601.9 | 202.5 |

- **Standard stage**, from V2 dumps (`scripts/stage_std.py`, `data/stage_std.json`). The window is fo2 with legs 40-60 um, measured at FF 25.02 ± 4.2 ps and TT 32.10 ± 5.97.
- **Off-window stages:**

  | stage | FF delay (ps) |
  |---|---|
  | fo1 leg 60-80 um | 26.2 |
  | fo1 leg 80-100 um | 29.9 |
  | fo1 leg ≥ 100 um | 39.7 |
  | ICG fo1 | 17.5 |
  | 0-20 um filler leg | 12.3 |

- **Early taps** with the standard stage: k = LSL 8, node 8, romleaf 9 stages. These agree at TT and FF, and the corner-agreement check passes.
- **Leaf span** (`data/leaf_span.json`): equal-count leaves cannot hold every sink leg ≤ 60 um. About 100 domain-straggler registers stay more than 60 um from their leaf, and the worst is 200-265 um away. This is true even at leaf size 8.

## 2. Estimate (all UNCHECKED, FF hold WS in ps)
| model | NL p50 / p05 | NK p50 / p05 | beats both? |
|---|---|---|---|
| idealised: every stage standard, V2 topology, leaves of 12, σ 4.2 (`est_std.py`, `data/est_ideal.json`) | -87.3 / -112.4 | -304.8 / -332.2 | yes, but this case is not buildable (see below) |
| idealised with σ 6.0 | -108.8 / -142.6 | -315.3 / -355.7 | yes, same caveat |
| idealised with V2 leaf stages kept | -163.7 / -188.6 | -318.6 / -337.5 | marginal on NL |
| **plan-faithful:** real `gen_a0_tree39 --std-leg 50` slices, measured stage bins per edge, bias-calibrated on V2 (`est_plan.py`) | T22 -168.9/-194.2; T24 l21 -134.1/-157.2; **T26 l21 -112.5/-139.5** | T19 -384.2/-457.4; T20 -394.3/-456.4; **T19 l21 -351.1/-400.0** | NL is not robust |
| plan-faithful, reg->reg class only | T26 l21: **-110.8** | T19 l21: -198.3 | |
| model self-check on V2: predicted vs measured | WS -289.4 vs -281.18; **reg->reg -153.7 vs -224.6** | WS -277.8 vs -289.88; reg->reg -205.5 vs -172.1 | |

**Why NL fails the estimate.**
- The model under-predicts V2 NL reg->reg skew by about 71 ps. On the worst pair, `mp_a0_lddw_35 -> mp_a0_ldtx5_7`, the measured skew is 199 ps and the model gives 87.
- The per-register model error, p01, is -56 ps on NL and -74 ps on NK.
- Applying that gap to the best NL standard plan moves reg->reg from -110.8 to about -182. That is worse than TritonCTS at -172.53.
- Whether NL wins therefore depends on model error, and the estimate cannot claim it.
- NK wins by about 170-220 ps, which is more than any model error measured above.

**Why the plans are not standard.** See `plans/*_rep.json` key `std_stage` and the PNGs, where red marks a leg over 60 um.
- Counts of planned node legs over 60 um:

  | plan | legs > 60 um | of these, through a macro+halo box | legs > 90 um |
  |---|---|---|---|
  | NL T22 | 462 | 275 | 208 |
  | NL T26 l21 | 279 | — | — |
  | NK T20 | 554 | 303 | 254 |

- The macro rows (LSL/node/romleaf banks) leave only the centre corridor and the edge channels.
- The diamond walk snaps around the macro rows. Late fan-out to straggler leaves then needs legs of 90-270 um.
- The NK macro chains need legs of 173-216 um.
- Changing the split factor (`--std-split`) or fan-out (`--std-fan` 2/3) did not help. NK T16/T18 and fan-out 2/3 plans are infeasible: "load deeper than its goal".
- **Insertion delay** (model median registers): NL 355 → 467-536 ps, NK 343 → 410-475 ps. The extra delay comes from the higher stage counts.
- **Macro tap lateness:** k is set by the corner-agreement rule at 8/8/9. With the measured stage there is no tap misfit at either corner, so the macro taps are not what makes NL lose.

## 3. Generator option (results-local, not tools/)
`gen_a0_tree39.py` is the DIE-QC-37 `gen_a0_tree21.py` plus opt-in flags. All are default OFF.
- `--std-leg L`: every spread node is placed exactly L um from its parent.
- `--std-max` (default 60): sets the reach.
- `--std-split`, `--std-fan`: allowed only together with `--std-leg`.
- `--leaf-max` (default 21).
- `--stage-ff/--stage-tt/--stage-src`: given together. They set the early-tap k and write `early_tap_stage_ps`.

Std mode adds the `std_stage` report block.

The equal total stage count is kept, so equal stages remain a rule. Delay-based balancing at unequal stage counts would be a RULE CHANGE and was not tried; it is only noted here.

**Verification (CHECKED):**
- Default OFF is byte-identical to gen_a0_tree21 on the real NL/NK kits on intel2. The slice sha matches the DIE-QC-37 V2 slices `24c075f7…` and `eee98c5f…`, and the report and stdout are also identical (`data/byte_identity_realkits.txt`).
- `test_gen_a0_tree39.py` passes: byte-identity on a synthetic kit for 3 argument sets, std-mode invariants, and flag misuse refused.
- No file under tools/ changed, so this needs no ROOT-MERGE.

## 4. What would change the verdict
1. Corridor-aware standard walks. Route spread legs through the centre and edge channels as chains of standard legs (fo1 repeaters), instead of snapping across macro halos.
2. Straggler leaves. Give each domain straggler its own leaf near the domain gate. This takes a ±1 leaf-count exception, i.e. `load_balance joint_nldm_plan`.
3. Fix the model gap first. Find the cause of the NL `lddw -> ldtx5_7` 199 ps measured skew; the model gives 87.
4. Otherwise, an OWNER/COORD decision on delay-based balancing.

Rerun the estimate only after step 1 or 2. Build only if NL reg->reg is better than -172.5 with ≥ 70 ps of margin.

## Files
- `scripts/`: stage_std, est_std (idealised MC), est_plan (plan-faithful), leaf_span, reach, render_plan.
- `probe/`: hold_all.tcl and run_hold_all.sh, the read-only V2 hold dump (docker on intel2, 12 GB cap).
- `data/`, `plans/`: estimate JSONs, plan reports, PNGs.
- Scratch: `intel2:/srv/opentallas-scratch2/claude/dqc39-a0/`.

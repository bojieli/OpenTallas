# DIE-QC-50/gen47ndr — Route B: gen47 clock under the clock NDR, DRT + RCX (2026-10-30)

**Verdict: QC freeze gate (12.4a) on Route B = NOT MEASURED.** No DRT-routed + RCX clock arrival exists yet. The GRT-only NDR result is an early indicator only.

## Inputs
- Source DB: `/srv/opentallas-scratch2/claude/die-qc-49/g47src/build2/clock_native.odb` (die 31216x26265 um, 541,054 nets).
- Tree: `tree47.json`, sha 4bad7469.
- Plan: `plan_qc49.json`.
- Droop regions: the 313 region trees.
- NDR: CLK2W2S, M8/M9 at width 0.08 / spacing 0.08. With R_sq/0.08 this gives 4.22 / 4.45 ohm/um, against the planned 4.336.
- RCX rules: `rcx_ndr008.rules.gz`, made by main `tools/die_plan/rcx_width_rules.py --widths 0.08`.

## 1. Die GRT incl clock with NDR, 50 iterations [CHECKED grt/grt_ndr_{TT,FF}.log]
- Overflow 0, max H/V 0/0.
- 540,737 nets, of which 48,297 are clock nets.
- WL 604,253,844 um.
- Demand: M8 0.71%, M9 1.28%.
- Runtime 4:40, 20.3 GB.

## 2. Early indicator: die_sta_related on the GRT-NDR estimate [UNCHECKED, sta_grtndr/]
DIE-QC-45 args: `--cppr-lca --clock-ocv table --clock-droop shared --clock-cal spice_edge`.

| corner | intra setup (ps) | seam setup (ps) | skew diag intra / seam (ps) |
|---|---|---|---|
| TT | +64.65 (0 negative) | +179.29 | 196.34 / 192.62 |
| FF | +181.67 | +280.12 | — |

- Worst setup pair: c_E1_bn_11 t12 -> c0.
- Hold: BLOCKED(kits), so UNMEASURED.
- Predecessor comparison:

  | model | TT intra setup (ps) |
  |---|---|
  | set_layer_rc NDR | +38.74 |
  | 1x | -73.93 |

## 3. Why there is no DRT number yet [CHECKED logs in probes/]
**(a) Abstract OBS blocks the street-cross clock cells.**
- All 119 native-source abstract masters carry a FULL-outline OBS on M1-M3.
- Their M4/M5 OBS leave the partition street cross open, which is where the clock cells sit.
- 269 of the 377 partition instances have such a street.
- DRT therefore shorts every clock-cell pin in a street against the abstract.
  - probe_D, 3 nets: 29 Shorts (M3 22, M2 6, M1 1). Evidence: `probes/probe_D/drc.rpt-1.rpt`.
  - Region runs: 2.8k-3.8k violations after iteration 0, at about 1 h per iteration.
- GRT cannot see this because it routes M4 and above.

**Measurement-DB fix (`scripts/obsfix.tcl`, NOT a plan change):**
- Clone each block master with M1-M3 OBS := its own M4 OBS rects.
- Re-create the 377 instances on the clones. `swapMaster` segfaults in 26Q3.
- Result: probe_D2, same 3 nets, gives **0 violations**, iteration 0 in 29 s. RCX is OK. Evidence: `probes/probe_D2`.
- The real fix belongs in the native target abstract emitter (`die_trial.abstract_lef` with landing_infra): open M1-M3 at the street cross the same way as M4/M5.

**(b) Whole-die clock-only DRT does not fit in memory.**
- With native M1-M3 tracks, the per-worker graph is about 300M nodes.
- Run before the fix: OOM above 120 GB at 32 threads.
- Run with the fix: OOM at 160 GB at 32 threads, rc 137, in iteration 0. Log: `probes/drt2_full_oom160.log`.
- At 8 threads it needs about 60 GB and an estimated ~700 thread-h.

**(c) RCX context.**
- PG stripes in the source are OBSTRUCTIONS, so a clock-only RCX has no plane or shield neighbours.
- `scripts/rcx_pg.tcl` turns the 13,304 full-span OBS into SBoxes of a GROUND net, OT_PGCTX.
- probe_D2 net *509107: 9.79 fF -> 15.44 fF (+58%).
- The PG-context SPEF is primary. The no-PG SPEF is INFO only.

## 4. Live jobs at hand-off (epyc2, `/srv/opentallas-scratch2/claude/die-qc-50/gen47ndr`)
| run | nets | ot-run unit | container |
|---|---|---|---|
| path2_C (worst-pair chains) | 180 | oth-ubuntu-3327390-1793408461 | dqc50ndr-path2-C-3327421 |
| reg2_A | 406 | oth-ubuntu-3342031-1793408560 | dqc50ndr-reg2-A-3342085 |
| reg2_B | 406 | oth-ubuntu-3342041-1793408560 | dqc50ndr-reg2-B-3342191 |

- All three use the obsfix DB, run 20 iterations, and write DRT + RCX to `<run>/`.
- Watchers `collect.sh C2 path2_C` and `collect.sh AB2 reg2_A,reg2_B` run the full chain automatically:
  1. DRC summary;
  2. rcx_pg;
  3. mixed region-SPEF readout for TT and FF via ot-run;
  4. tap arrivals;
  5. cmp vs GRT-NDR;
  6. die_sta_related.
- Watcher outputs: `collect_<TAG>.log`, `cmp_<TAG>.json`, `sta_mix_<TAG>.log`.
- Collect: `ssh epyc2 'cat /srv/opentallas-scratch2/claude/die-qc-50/gen47ndr/collect_{C2,AB2}.log'`
- The watchers use the tools in worktree `/srv/opentallas-scratch2/claude/wt/die-qc-50-gen47ndr`. Keep the worktree until both logs say DONE or FAIL.
- Scope: a region or path result shows DRT-routed delay only for the nets it keeps (the worst pairs). The rest of the die stays on the GRT-NDR estimate. That makes it a partial measure, not the full gate.

## 5. Successor recipe
1. Fix the abstract M1-M3 street opening in the emitter, or reuse obsfix.tcl on the measurement DB.
2. Make the DRT tractable: route the clock on a DB whose M1-M3 tracks exist only near the clock cells, or use Route A's drawn prebuild.
3. If routed arrivals give TT intra < 0, the proposal (only a proposal, no plan change) is to refit the early-tap offsets of c_*_1x on the routed stage delay.

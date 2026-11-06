# CODEX bank128 — current continuation

Own branch: `codex/hbm-bank128-wface-1106`, tip `2fff4dbb9e`, pushed to the intel2 hub. Own tree: `epyc6:/srv/opentallas-scratch2/claude/wt/codex-hbm-bank128-wface-1106`. RTL change is still the original default-off `OT_HC128_WFACE`; later commits cover generation, geometry and results.

## Implementation and limits

The write cohort has 525 bits: `write_data[511:0]`, `write_addr[9:0]`, `weight_we0`, `weight_we1`, `x_write`. It gains one rising clock edge; read/go/arithmetic hardware latency stays unchanged. The parent must move programming earlier or defer the first dependent read/go by one edge. TOK records HBM-37; `hbm_projection` owns native lowering and the real component qualification.

Actual top/SRAM-boundary lockstep passed 27,000 checks over 3,000 cycles, including reset and RAW collisions. Data, enable and address mutants were caught. Arithmetic leaves are unchanged and stubbed in this mechanism proof; this is not a whole-projection or token-pass claim.

Geometry review found an inherited 1.032 um halo gap above X SRAM. X moved down 11.76 um, giving 12.792 um clear channels on each side. Same outline/pins. All trials use single-root CTS. Data/address registers are placed at faces by the existing face hook; only the three reset-gated enable flops need a region guide. Actual canonical B placed image shows data pin/flop Manhattan p90/max 7.65/9.65 um and address 7.50/8.00 um. Reviews and retained draft FAIL are in `results/geom_review/codex_bank128_wface_1106`.

## Active jobs

All actual runs are on **intel2**, admitted through ot-run with 48 GB / 16 threads. The source copies on epyc6 do not contain current physical results. Measured prior DRT peak was 17.87 GiB, plus concurrent LEC; 48 GB is deliberate.

Kit root: `/srv/opentallas-scratch2/claude/codex-bank128-wface/kits/ot_hbm_hc_bank128_pair_core_`
Log root: `/home/ubuntu/coord/tmp/codex-bank128-launch/`

| Kit suffix | Form | Client PID | Unit suffix | Log |
|---|---|---:|---|---|
| `7d149b37532c-_shallow_vA` | Original RTL, M6 | 2891638 | `2895666-1793952331` | `A3.log` |
| `7d149b37532c-_wface_vB` | Write stage, M6 | 2891639 | `2895661-1793952331` | `B3.log` |
| `9bf80cdae38d-_wface_vB_rgfix` | Write stage, weight_E pins, M6 | 4098307 | `4104496-1793954667` | `weightE_B_rgfix.log` |
| `7d149b37532c-_wface_vB_m5` | Write stage, original M5 budget | 1004766 | `1009405-1793956480` | `canon_B_M5.log` |

Canonical M6 A/B reached initial GRT zero overflow (log final congestion totals 0/0/0). CTS setup was +84.85 / +38.08 ps; actual TT insertion 393 / 367 ps remains later than the 250 target. A hold repair was -32.16 ps after 20 iterations. B was -68.64 ps after 790 iterations / 1,579 buffers, mostly `wface_data` and `sum_q` input-capture paths. Both remain active. The repair-scope optimization is owned by HBM forms; do not enable its pilots on these baselines without root authorization.

Weight_E resume passes GPL after the guide fix. M5 is one resource alternative, not a sweep: old canonical vA had an initial M5 GRT0 witness; registered drivers and balanced channels address the measured weak direct-port slew cause while retaining the original parent metal budget. No sign-off verdict exists yet for any new form.

## Failures handled

- Initial own waiters were stopped by exact PID before work started, first to remove unused historical plan metadata that blocked SPILL, then to stage inputs on the hub. No progressing job was restarted and no other lane's process was stopped.
- First weight_E attempt (`...9bf80cdae38d-_wface_vB`, client 2873269) failed GPL because a data-only guide selected no movable cells: the face hook had already fixed all 512 data flops. The flow aborted its pre-route LEC with exit 137 and no verdict. Original failure remains intact. Fresh `_rgfix` copies completed synthesis/floorplan objects without hardlinks, verifies equal RTL/SDC/config bytes, and guides only three enables. No RTL/clock/density change.
- Initial target density 0.40 is below the simple free-area estimate, but GPL accepted it. Actual canonical B standard-cell area 14,624.4 / 34,177.1 free core area = 0.4279, within the 0.45 envelope. Do not restart active jobs for density. Future helper default is 0.45.
- Inherited weight_E vB is terminal NOT SIGNED: TT -272.82 ps / 23 endpoints; FF -29.33 / 348; slew 647/320; DRC 5. Canonical vC remained in DRT with 50 violations at last collection. All old runs and evidence are preserved.

## Production preparation and next action

`hc128_native_kit.py` now has default-off `--b128-safe` / `--write-face`, including isolated-Python sibling imports, current pin-face guides and per-write-pin cycle metadata. Actual generation tests passed for both modes (M6 / 0.45 / single-root, generic face cycles 0, write cycles 1 only when enabled). Diagnostic fixtures are explicitly not new proof evidence.

Next: collect GRT/DRT and LEC results; fix measured residuals; re-sign a winner on the current released flow with real parent context. Before adoption, HBM plan owner must reserve actual layer obstruction and reproduce X site `(21.6,96.252)`; projection owner must qualify the write guard. M5 avoids the new M6 parent resource obligation if it closes. No new OWNER? item.

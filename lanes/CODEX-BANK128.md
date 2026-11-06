# CODEX bank128 — current continuation

Own branch: `codex/hbm-bank128-wface-1106`, tip `19323f08a0`, pushed to the intel2 hub. Own tree: `epyc6:/srv/opentallas-scratch2/claude/wt/codex-hbm-bank128-wface-1106`. RTL change is still the original default-off `OT_HC128_WFACE`; later commits cover generation, geometry and results.

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
- Inherited weight_E vB is terminal NOT SIGNED: TT -272.82 ps / 23 endpoints; FF -29.33 / 348; slew 647/320; DRC 5. Canonical vC is terminal NOT SIGNED: TT -225.30 ps / 5 endpoints, FF -34.49 / 368, slew 670/336, caps 40/43 and DRC 3. Trunk buffering did not remove the direct-write failure. All old runs and evidence are preserved.

## Production preparation and next action

`hc128_native_kit.py` now has default-off `--b128-safe` / `--write-face`, including isolated-Python sibling imports, current pin-face guides and per-write-pin cycle metadata. Actual generation tests passed for both modes (M6 / 0.45 / single-root, generic face cycles 0, write cycles 1 only when enabled). Diagnostic fixtures are explicitly not new proof evidence.

Latest collection 2026-11-06 01:44 PST: canonical A is in DRT; canonical B completed multiple hold-repair passes and reports no setup violations before antenna repair; weight_E is in hold repair after initial GRT, and M5 is finishing CTS. No final verdict yet. Projection compiler 329a6b19e1f explicitly prices the one-edge guarded launch for runtime residual positions (160-edge ingress cadence / 250-edge compute cadence), without changing data cadence or charging per input. Actual physical composition remains pending.

Next: collect GRT/DRT and LEC results; fix measured residuals; re-sign a winner on the current released flow with real parent context. Before adoption, HBM plan owner must reserve actual layer obstruction and reproduce X site `(21.6,96.252)`; projection owner must qualify the write guard. M5 avoids the new M6 parent resource obligation if it closes. No new OWNER? item.

## Latest measured continuation (02:06 PST)

Canonical registered B GRT completed: estimated TT setup +121.474 ps, FF hold -2.30929 ps, antenna 0; now DRT. A also DRT. Weight_E is still hold repair; M5 extra GRT iterations. B post-GRT 122,043 stdcells / 15,827 um2, free-area utilization 0.4631 vs placement 0.4279; configured target 0.40 remains unchanged. Root informed of both actual and configured utilization.

Actual B frozen GRT ODB supply probe finds 56 M5 pin rectangles per VDD/VSS, no M6 PG pins and no actual M6 supply special-wire metal. Private ORFS-equivalent GRT abstract has OBS M1..M5 (GRT guides are not routed metal). Final DRT LEF must be checked using gen_phys.core_pg_mode(strict=False): if final OBS includes M6, M5-only PG is buried and cannot be adopted without true PG6 metal/access construction. Existing pg_pin_publish cannot publish nonexistent M6 metal. Root and geometry_forms informed. Probe log intel2:/home/ubuntu/coord/tmp/codex-bank128-launch/pg_grt_B.log; private stage LEF /home/ubuntu/coord/tmp/codex-bank128-pg/grt_B.lef. No active kit edited.

Actual pair arithmetic comparison is running on epyc6 (ot-run 8GB/1thread, unit 447754-1793958898): both pair tops with actual unchanged arithmetic leaves, behavioral SRAM, explicit delayed-write adapter on default-off reference, 3000 randomized runtime write/read/go/reset cycles and known-output gate. No verdict yet. This extends stubbed boundary proof but excludes canonical bankq/cutmap/full parent identity. Native projection owner agrees this is the proper intermediate scope.

PG6 capability READY at `19323f08a0` (includes `ca3f88082a`), bank branch pushed. Shared factory `--pg-top-layer M6`, native common-pair `--pg6`, own helper matching flag. Default M5 PDN byte-identical. Actual private bank pre-PDN checkpoint plus new factory PDN produces 60 real M6 rails and 3,360 VIA56 connections per supply; exported M6 PG / OBS M1..M6 passes actual-LEF mode `grid,M6,M7`. Rendered actual rails inspected PASS-COND before any new route. Review/artifacts committed under `results/geom_review/codex_bank128_wface_1106/pg6`. Explicit nominal M6 rail-width resource 13.33%, parent M6 reservation/M7 landing pending. No new full physical run yet; current runs unchanged.

A completed DRT with 0 violations (empty DRC report), antenna 0, actual M6 signal length 78,900 um; final timing/corners pending. Pre-route synthesis LEC now EQUIVALENT for A 32,365/32,365 and B 32,890/32,890 points; routed LEC remains pending. Arithmetic vehicle still running (real full leaves, no verdict yet).

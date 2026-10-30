# DIE-S81-35/H2G1: H2 protected G1 clock install FAILED (pre-route legality), no G1 geometry produced

Date: 2026-10-30, PDT. Scope: ROOT-authorized ONE protected G1 clock install of the H2 MODEL-admitted tree
(codex/h2-window-1030 @0fbf69224, package calibrated_native_admission, core ddfa7ed81) on the preserved native
3_place (sha 56af214f…), kit copy intel2 /srv/opentallas-scratch2/claude/die-s81-35/h2g1/kit. No SYNTH, GPL, TritonCTS,
GRT, DRT or G2 was run.

## What ran
- GEN: canonical master_slice.kit_apply + plan_tree_cts (main 16f2590f75f), with the admitted slice changed in exactly two
  keys: cell_placements removed, core_tree.install_stage=pre_cts (DIE-QC-36 A0 late install: tree built on the existing
  placement, incremental DPL of the tree cells only, every other instance FIRM, so FF homes are kept).
  prep.json PASS: the admitted slice regenerates the admitted master_core_infra.tcl byte for byte; the late hook has the
  same 1811 cells/masters/xy, 1811 tree nodes and 19747 sink lines; 6 core islands; 0 CTS-open leaves.
- PREFLIGHT: kit_preflight PASS (with --plan-dir to the types worktree for h2_2249/coll_w/plan_pins.json). The first run
  without the plan dir FAILED (pins_canonical unreachable); kept as preflight_noplandir_FAIL.json.
- ONE install: ot-run unit oth-ubuntu-166993-1793382865 (intel2), runner scripts/run_h2g1.sh, official ORFS do-cts.

## Result: FAIL (exit 2, no 4_cts checkpoint)
- OT_CORE_INFRA_LATE_DPL cells=1811 held=76763 max_disp_um=7.074 (bound 20). The negotiation legalizer did NOT converge
  (DPL-0701: 64 violations left). ot_ci_late_legalize does not run check_placement, so it accepted the result.
- Planned tree, leaf-complete: 19692 register clock pins on planned dont_touch nets; TritonCTS not run.
- The kit's POST_CTS (cts_post.tcl) then ran repair_timing -setup (46 buffers, 120 resizes) and its check_placement failed:
  DPL-0033, 11 overlapping pairs of FIRM BUFx24 tree cells (e.g. mp_ck_Tpqtu_r0 overlaps mp_ck_Tpqt_r0).
- Root cause (read-only probe of 3_place, site_probe.json, CHECKED): 1307 of the 1811 admitted converted tree sites are
  occupied by native placed cells. 770 are occupied by sequential cells (FF homes), 751 by combinational cells and 105 by
  TAPCELL (one site can count in more than one class). The admitted converter rule ("no overlap with planned/fixed cells")
  never checked the native standard-cell occupancy. Keeping the FF homes and keeping the admitted exact sites therefore
  cannot both hold: the installed tree cannot match the priced positions.
- INFO only, UNCHECKED (non-legal intermediate, placement RC): POST_CTS OT_TAP_RC sink insertion 230..298 ps (mean 268,
  19747 sinks); setup repair ended at TT WNS -269.2 ps / TNS -16620 (u.u_ep.g_rb_safe.g_address[1].ready_r D).

## Recommended next step (default, needs ROOT/COORD)
(1) Convert the admitted tree once more onto FREE native sites: the converter site rule gains "no overlap with native
placed std cells/taps". Then run one UF3 re-qualification (model only) and install again with a no-op late DPL.
(2) Shared-tool bug fix, separate ROOT-MERGE: ot_ci_late_legalize must run check_placement and fail closed when the
DPL does not converge.
Not recommended: a fresh pre-GPL PLACE (RT/L0r form), because it moves FF homes and invalidates the admitted sink
geometry.

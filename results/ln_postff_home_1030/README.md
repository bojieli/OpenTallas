LN NST112.32um post-FF physical-home repair, prepared for ROOT review only.
No candidate EDA, placement, CTS, STA, GRT or route has been run. Two bounded
read-only ODB snapshots supplied actual rows/TAPs and all8386 FF orientations.
The first epyc2 extraction was NOT RUN at the scratch floor; the exact source
ODB was copied read-only to own intel2 scratch and extraction completed there.

The actual OUT→pure BUF/INV→FF trace covers all1114 output signal ports. The
phase4 chunk ownership left post-FF inverters near their original logical
chunk while outputFFs moved to physical output islands. Example FF1714..17 at
y106..107 drives inverters1665..68 at y51..52, then outputbuffers near y99 and
outputpins: two extra crossings of the offending cut. Only pure post-FF cells
with no unrelated logic/FF/clock fanout are selected. No RTL, net, pin, cycle,
clockroot, master or FF-home change is proposed relative to the native fixture.

Using the UNCHANGED `geom_rules.demand_metrics` M2-M5/36.46tracks-per-um model:

- Native peak column demand1.234 at x50/y97.5.
- First263 post-FF homes exposed the next cut1.107 at x60/y52.5.
-350 affected cells gave0.966. Greedy rollback using strict positive margin and
  occupancy-safe restoration reduced this to109 cells (103INVx1,6BUFx2), peak
  **0.999** at x50/y97.5. This is published model margin0.001, not a physical
  congestion guarantee. The boundary-only111-cell/1.000 attempt and failed
  one-extra-cell attempt are retained in scratch, not promoted.
- Every final target rechecked against exact native row/site/master/TAP and
  ALL35751 placed occupancy:0overlap. Every34211 geom cell matches the copied
  native ODB bbox. Only109 cell rectangles differ; all8386 FFs (including5570
  boundary FFs), ports/nets/clock connections remain identical.

`candidate.png` was rendered AND LOOKed. Selected post-FF hairpins now lie near
actual outputFF islands. Other FF/logic geometry is unchanged in this analytical
candidate; connections shown are topology, not routed wires. Positive-margin
109-cell candidate is review-ready, with the small model margin disclosed.

`native_candidate.json.gz` stores all8386 exact FF masters/homes/orientations/
clock roots and the109 target names/owners/sites. `prepare_recipe.py` prepares
a caller-owned copied kit, never runs EDA, and accepts only the exact6577522
phase4 recipes. It emits a private `ln_postff_home.tcl` data file and hooks:

- Existing phase4 port-buffer affinity runs first at `global_placement` enter;
  the reviewed native FF homes are then reapplied/fixed and only109 BUF/INV
  targets rehomed.89 inherit existing physical output groups;20 follow the
  already-free central outputFFs and are removed only from old chunk ownership.
  All89 target boxes fit their existing home regions. No regions are relaxed.
- Existing PRE_DETAIL release runs first, then exact FF/target homes reassert.
- Whole native FF families are excluded as NEW physical optimizer choices in
  each fresh PRE_GLOBAL_PLACE/PRE_RESIZE process, the same mechanism as
  c87cfe541. Existing FFs remain touchable: no instance DNT, no fake FT packet,
  no synthesis change. Scope covers all8386 actual native FFs.
- POST_DETAIL guard checks every FF master/home/orientation/direct ck_k or ck_n
  root and every selected output chain/target/site/physical group. Actual native
  ORFS has PRE_DETAIL at line5 and POST_DETAIL at line43. Missing/mutated native
  instances or resized masters fail closed. No ignore/skip mode is provided.

Before GPL, movable logic may be legalized around fixed targets; all FF planned
homes and existing fixed/TAP obstacles are checked. After detail placement every
placed occupant is checked. Fresh GPL may therefore change other movable logic;
its actual G1 geometry/demand must be collected, priced and viewed again. FIRM
FFs can expose a placer numeric issue; preserve/diagnose that failure and do not
retry with density or threshold changes.

Only ROOT can activate the ONE reviewed G1 successor. Native G1/FACE/LEC and the
full actual FF/clock/ABI guard must pass. CTS, data repair, STA, GRT and route
remain held for further review. The old16454 EQ is source-identical evidence,
not proof of a newly synthesized or physically changed netlist.

Scratch: `/srv/opentallas-scratch/claude/ln-postff-model/`; source geometry
`/srv/opentallas-scratch/claude/codex-flow-cut-1030/ln/geom.tsv`; native source
`epyc2:/srv/opentallas-scratch2/claude/codex-s81types-1030/ln_nst_phase4/run/results/asap7/kl_ot_s81_mu72_lnland_nst_h2_2249/base/3_place.odb`.

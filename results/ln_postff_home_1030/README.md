LN NST112.32um post-FF physical-home repair. CURRENT STATUS: the ONE ROOT-admitted
G1 failed GPL-0301 and is preserved without retry. No CTS/STA/GRT/route ran.
USER Claude-reset notification arrived afterward; this lane is PARKED.
Two bounded read-only ODB snapshots supplied actual rows/TAPs and all8386 FF orientations.
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

Actual copied kit is prepared on intel2 at
`/srv/opentallas-scratch2/claude/codex-flow-ln-postff-1030/g1_109`.
It carries unchanged native RTL plus cached1*/2* results only; no3_place.odb or
ONE_G1_STARTED marker exists at preparation. `one_g1_command.sh` is the exact
staged script `ln_one_g1_109.sh`; it enforces a single start, runs `make place`
only, and requires the native post-detail guard receipt. The first cached-file
tar glob invocation failed (no run); corrected shell-expanded tar copied1*/2*
with timestamps. Original source/caches/failures were never changed.

ROOT admission command, **not executed during preparation**:

```
ot-run --mem 32 --threads 8 --hosts localhost \
  --dir /srv/opentallas-scratch2/claude/codex-flow-ln-postff-1030 \
  -- bash ln_one_g1_109.sh
```

The hub's localhost is intel2. Actual G1 GEOM, all-FF/target guard, PG and fresh
LOOK must be collected after this run before any further stage is considered.

Terminal admitted G1 (parked handoff): intel2 owned copied kit
`/srv/opentallas-scratch2/claude/codex-flow-ln-postff-1030/g1_109`;
`one_g1_native.log` and
`run/results/asap7/kl_ot_s81_mu72_lnland_nst_h2_2249/base/3_3_place_gp-failed.odb`
are preserved. PREPARED guard confirmed109 cells/all8386FFs before GPL. Native
POST_DETAIL/G1 completion guard was never reached. No density/threshold retry.

Confirmed top-level GPL accounting compared with successful657 phase4 baseline:

| Quantity | Original | New all-FF-FIRM attempt |
|---|---:|---:|
| Core/region area um² |10749.542|10749.542|
| Fixed count |7110|10035|
| Fixed area um² |9887.923|10713.034|
| Movable count |838|464|
| Movable area um² |155.098|50.830|
| Default-region utilization |18.001%|139.230%|

Fixed count7110=5570FF+1540TAP. New10035=8386FF+1540TAP+109buffers.
Actual full FF area is2445.358um²; added2816FFs occupy821.146um².34 existing
EXCLUSIVE regions (VOLTAGE_DOMAIN groups) cover9853.747um², leaving895.795um²
central street. Thus the139.230% reports nearly exhausted default-region free
area, not physical global cell fill. Preliminary cause: newly fixed foreign
region members counted alongside the full exclusive-region blockers. Exact
read-only membership/area dump was already started before parking; its files
`baseline_regions.tsv` and `failed_regions.tsv` are under the owned intel2lane,
with local driver log `/srv/opentallas-scratch/claude/ln-postff-model/regions_driver.log`.
No source/density/region-box waiver was introduced. A possible exact3PLACE
109-cell ECO+DPL was discussed but NOT prepared or admitted; leave it to the
resumed coordinator. No new jobs or next steps after park notification.

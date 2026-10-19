# Exact INT8 bounded CTS request — HOLD

Prepared source-only request, not an executed physical stage. ROOT accepted the exact pin-bound placement at13:19. ROOT must separately
review this source-only kit and give an explicit CTS-only grant; final PG
prototypea92a40171 test receipts are pinned. No shared helper is
activated here. `request.json` pins the final PG helper; no grant is fabricated.

## Exact vehicle and planned operation

Candidate `smh_int8_safe_tie_t1_cts1` imports `placed.odb` SHA256
`95dcd07da7a966ccf351a556ed952bf6460c5a81570b846f88786396adb86341`
from `ot-epyc8:/srv/opentallas-scratch/claude/hbm-int8-tie-place-1019`.
This is the exact da40a2a46 mapped source, physicalized in 121b7ec9a with
266 actual tie cells. Copy the immutable snapshot into a new isolated fleet
directory; preserve original ODB and all failure evidence. No resynthesis,
placement restart, data repair, GRT, route, gate or submission is requested.
The inherited source and mapped connectivity remain the reference; any change
other than clock buffering and legal placement of inserted cells must refuse.

The scripts under `tools/hbm_int8_cts_prepare` load exact ODB, native platform
libraries and RC, establish the source 833.333 ps clock and 60/25 ps uncertainty,
insert a single bounded CTS tree with BUFx24 and 32-sink clusters, bind every new
instance's PG MTerms before protection, and assert coverage over ALL native PG
pins. The PG adapter interface is `set mapping [ot_pg_prepare $block]`,
`ot_pg_bind_before_protect $mapping $inst`, and
`ot_pg_assert_all_native $block $mapping`, owned by `idx_clock_pg_binding`.
Its exact tested code and native voltage-domain/global-rule resolution must be
ROOT-pinned, including ambiguous/unproven mapping refusal; there is no supply-name
fallback. Initial and final all-native coverage is mandatory, with no clock-name
exemption. Existing native geometry contact checker must additionally cover all
new pin rectangles against same-net rails and original vias/conductors; logical
binding or `check_power_grid` alone does not prove physical contact.

`validate_inputs.py` refuses missing authorization, PG test receipt, wrong ODB,
wrong image, or changed ROOT-pinned scripts. The snapshot layout is `input/`
(exact ODB/platform hashes/image identity), `prototype/` (tested adapter and test
receipt), `kit/` (three scripts and SDC), and new `output/`. ROOT must pin these
script hashes in its separate approval JSON. `run.sh` runs only through an
admitted unpinned ot-run command, and only after that grant. No heavy tool has
been run for this preparation.

## Clock and cost model

Actual mapped native pins, independently classified from the exact TT Liberty
clock roles: 2,580 DFFHQNx1/CLK + 202 DFFASRHQNx1/CLK = **2,782 sinks** on the
single actual input clock net. Sum of native `capacitance` is **1,318.324478 fF**
(1ps/1fF Liberty units). This excludes the future CTS buffers' input pins and
wire capacitance, which must be added from the emitted native tree. No old
2,531-sink insertion/spread result applies. Actual register centroid is
(117.131,64.899) um; W entry is y63.55 beside the mass. No clock path is exempted
by its name. Absolute insertion is reported without a 300ps ceiling; qualification
requires TT and FF sink spread <=80ps and exact neighbour-matched boundaries.
The current SDC's root-referenced I/O paths are diagnostic until a real parent
clock reference or compensating landing is supplied. It preserves 166.667ps
input/output budgets, 80fF output loads, 150ps input slew and 260ps max transition.
The later route contract must retain >=30ps I/O hold repair margin. No route is
requested now; placement RC is not routed timing.

Native mapped geometric area is 1,322.53722um2 including 11.63484um2 ties.
Source cost versus identical mapping recipe is +123FF, +48.58056um2,
+57.031273fF clock load, zero additional registered edges. Future tree cell area,
capacitance, electrical results and any moves are separate measured costs.
Existing source ages remain low+2/high+3, one packed line per two edges, with
exactly two ordinary sampled reset assertion and release edges. Stopped-clock
asynchronous reset is not claimed. Compiler calendar is unchanged.

## SAFE eight-item checklist

1. **PASS source; final native recheck required.** All 1,036 ordinary inputs land
   at FFs and all 1,070 outputs have FF roots. Canonical source is unchanged;
   safe source has exact two ordinary sampled reset edges. Original 19,985-check
   lockstep, all-code truth, reset phases/stopped-clock tests and causal mutant
   witnesses are preserved in the source packet. No new data pipeline is inserted.
2. **PASS geometric bound.** Entire 237.6x129.6um outline bounds any point pair
   to 367.2um Manhattan, below 405um. Final cells/pins must stay inside it.
3. **PASS pre-CTS; rerun final.** Full BUF/INV-transparent actual logical census
   max24, 11,407 drivers/22,424 endpoints, real tie fanout1, no missing drivers.
   Clock-only roles come from native Liberty; every nonclock load is counted.
4. **OPEN measurement.** Native TT complete stage max delay/depth, max slew/cap,
   setup and FF hold are not inferred from old source. Save full clock-expanded
   worst paths, all path classes and unconstrained checks, including reset pins.
   If >600ps/~20 levels or timing fails, stop for source structural redesign.
5. **PASS unchanged source inventory.** 2,782 actual FF; no new indexed array or
   three-deep delay chain. New clock buffers are not functional storage.
6. **ROOT geometry accepted13:19.** Legal 464-row placement, no macros, aspect1.833,
   one continuous standard-cell core. Fill4.53% is pin-bound; ROOT personally accepted this exact outline/image. Full N/S faces have >=.192um spacing and <=6pins/um;
   old .096um diagnostic is not selected. The original placement PNG remains
   in `results/arch/hbm_int8_tie_place_1019/placement.png` and durable artifact
   `/home/ubuntu/artifacts/hbm-int8-tie-place-1019/placement.png`.
7. **OPEN CTS/native qualification.** Exact 2,782-sink TT/FF spread, all clock-pin
   arrivals/cap/load, actual roots, reset paths, electrical and matched boundary
   data hold must be collected. Pre-CTS 20,740/20,740 native PG contacts PASS;
   every newly inserted supply pin adds a fresh independent obligation.
8. **PASS unchanged schedule.** +0 functional edges; reset2, low2/high3 ages.
   This packet claims neither full SU/MU token qualification nor achieved rate.

## Required returned packet / stop criteria

Save pre/post ODB SHA256, all source/helper/platform/image/Liberty hashes, native
all-pin graph plus uncapped fanout report, clock pin/master/edge/cap and propagated
arrival tables at TT+FF, source-to-post ordinary-cell connectivity identity,
clock buffer inventory/area/cap, legal placement, final reach/face checks and PNG.
Export raw all-native PG MTerm/ITerm roles and actual net/voltage-domain binding;
intersect every transformed supply rectangle with same-net original rails and
via connectivity, including CTS cells, ties and arbitrary nonclock cells.
Refuse any disconnected, wrong-net, ambiguous, missing or unphysicalized supply.
No clock-name-based exemptions, no protection before supply binding.

Return complete TT max and FF min electrical/path-class/reset reports with the
same clock 833.333/60/25 policy; SS may be retained as sensitivity. The TT script
is only first-stage CTS generation; a distinct read-only FF replay and independent
final native/PG contact export must be pinned in the eventual ROOT grant. Parent
reference and final electrical/hold qualification remain OPEN until actually
measured. Stop after this bounded evidence; no automatic GRT/full gate/retry.

## Concrete kit completion (source preparation only)

`kit_manifest.json` / `tools/hbm_int8_cts_prepare/manifest.json` pin every script,
functional mapped JSON/netlist, ODB, existing tie/PDN helpers, exact image, platform
files and the five real TT plus five real FF Liberty files. FAKE libraries are
never loaded. `run.sh` verifies actual in-container platform and library bytes.
ROOT must pin the manifest SHA256 and helper SHA in a separate approval JSON with
`root_authorized:true`, stage `INT8_CTS_ONLY`, exact candidate, `pg_tests_pass:true`,
and `neighbor_timing_status:DIAGNOSTIC_ONLY`. Absent/wrong grant refuses before
any output directory or physical tool. Source-only kit preparation is complete;
no CTS, read-only STA, native export or gate has run for this new candidate.

The PG helper SHA86ecd58dcc68419006b65d773c832ac6feeaf7ecdcf39dbf9f8f442f868bb5c4
is the testeda92a40171 master-MTerm-complete prototype. `pg_test_receipt.json` retains exact upstream
196864-terminal positive/original644negative and domain controls. Insertion is
followed by fresh mapping, binding every new instance, legal placement, all-native
coverage and only then instance protection. No existing protection is cleared.
The unchanged placement fingerprint is checked before saving the new CTS ODB.

`ff_replay.tcl` reads that ODB in a new OpenROAD process, loads only the five real
FF libraries, repeats exact833.333ps/60ps/25ps constraints, propagates the clock,
estimates placement RC and emits complete min/max/electrical/unconstrained reports.
It writes no ODB and performs no repair. Before/after ODB hashes must match.
Native register pin active-edge wire arrivals/slew use the existing39021
clock_family.tcl API. Root-referenced I/O is explicitly diagnostic; parent match
and routed timing remain unqualified.

`export_metal.py` reuses the exact39021 native shape/via/pin extraction; all clone
mutation is removed. `prove_metal_readonly.py` reuses its same conductor union,
cut-enclosure and all-pin contact proof, removing only historical clone DEF
comparison. Because that original graph groups supply roles, the exporter refuses
anything beyond this candidate's exact VDD/POWER and VSS/GROUND two-net domain.
No generic multidomain geometric claim is made. `export_raw.py` preserves all
instances/masters/native pins/net roles with only source/output path parameters.
The unchanged strict969 oracle and121b replay (plus exact dft Liberty dependency)
are vendored; no alternate fanout graph implementation is introduced.

Validation below is syntax and refusal-path validation only. A first native
execution may reveal tool-interface or physical failures; preserve failures and
stop for review. No result, spread, timing or CTS contact PASS is preclaimed.

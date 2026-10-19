# Shared SRAM Stage A: original visible joins FAIL native RECTONLY

ROOT authorized Stage A only after method aeeb6dd65. No Stage B/C, production
views, signal routing, PG/PDN, timing, or whole-master qualification ran.
Both exact source families fail the selected visible connected-source-join
check. Each of eight actual source-join target nets has TWO native RECTONLY
markers inside its scoring ROI. The two r_ce via-crop ROIs have zero markers;
this is limited sampled visibility evidence. REDESIGN_PROPOSAL.md gives the
concrete next contact-and-lead grid model required before further work.

Sources are exact Qwen5666def40 and SC2e91e03803; input hashes checked by
prepare.py. SC2 model supplies unchanged PG neighbors. Technology SHA256
7694bf4f8ef2f9745e4579f454788a0cf048e8605320f32d1d83ec540ed4ca41.
Image openroad/orfs@sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29;
binary SHA25621eda99eeae7eccb22ca64ad28949c08a6c01dcece3ccb23e2206d635f8d2846,
version26Q3-1510-g6cb3f2b704. Matching native checker source hashes are in
method aeeb6dd65. Actual imported rule objects/flags are in
native/loaded_rules.json; raw source tech is retained. RECTONLY=true,
EXCEPTNONCOREPINS=false, RIGHTWAYONGRIDONLY=true, width/spacing24nm and
non-ORTH width-table identity are actual loaded facts. Numeric width-table
vector/property bindings are unavailable in this Python build; their errors
are retained in native/fixed_pin/actual_property_rules.json. The parser's
non-ORTH DRT import gap remains explicit; no blanket PDK coverage claim.

## Exact geometry, visibility and controls

17 original cases,195 metal rectangles,19 complete VIA45s including neighbors.
Actual native dbWire segments/patches and native via boxes are in the ledger,
DEF and original.odb. All fixed/status distinctions are explicit. Selected
source anchors, complete source polygons, closest neighboring rectangles and
translations are in coupon.json/input JSON. Crops retain all same-net and
cross-net metal (including PG) intersecting +/-500nm; score only inner
+/-200nm. Translation multiples of48nm preserve source phase. Explicit native
M4/M5 TRACKS and GCELLGRID. Complete native VIA45 enclosures/cuts are compared
against exact source boxes. No repair command was invoked. The checked ODB
also contains checker marker metadata, so its hash differs from original;
this is not evidence of routed geometry repair.

Neither source has an east read output. Actual rd_out[0] W and first E pin
wd_in[25]/wd_in[70] are separate cases, preserving their real identities.
Actual r_ce via columns are distant from source joins and get separate crops.
The full original report retains154 markers:134 RECTONLY,6 area,3 width,
8 EOL-keepout,2 metal-spacing,1 EOL-spacing. Crop-edge width/area artifacts are
retained and excluded from any source-join conclusion by explicit inner ROI;
analysis.json contains complete ROI marker geometry/net/layer lists.

Controls: aligned rectangular same-net join0 markers; shifted24+24nm/15nm
overlap join2 RECTONLY; dbWire FIXED equivalent2 RECTONLY;23nm cross-net gap
1 Metal Spacing+2 EOL keepout. The disconnected contact has two independent
geometry components and native spacing/EOL/area failures. Connectivity uses
actual layer/rectangle/via overlap, not net-name or DRC silence. Old12mod48
track phase and33nm width controls are native-silent coverage probes. No
subgrid control was invented: integer1nm DBU equals manufacturing grid.

Source FlexGC_init adds frPathSeg/frPatchWire to GC with isFixed=false even
for a FIXED dbWire. Thus that control does not model a fixed macro pin.
A separate exact two-rectangle FIRM dbBPin control IS fixed pin geometry to
GC and has0 markers, confirming the fixed-polygon suppression risk. This
visibility negative is never called a geometry repair or qualification.
Native input diagrams coupon_a.png and fixed_pin.png show the exact ledger
and native markers; these are geometry plots, not a completed routed master.

## Execution, preserved failures and resources

All OpenROAD execution used unpinned ot-run,1CPU/4GB/2GB admission, no arbitrary
time/address limits. Original native check ep8 unit1941513:0.54s/248488KiB
peak RSS/3,025,270B staged run. ROI pickup ep6 unit3629831:0.59s/248840KiB/
3,052,661B. True fixed pin ep7 unit116765:0.65s/250152KiB/3,244,296B.
Full unit IDs, raw command/return logs and resources.time are committed.

Preserved method failures: missing PATH binary at initial capability launch;
Python dbSigType enum binding failure before geometry; then floating micron
ROI arguments rejected by hidden native INTEGER DBU API. Original full-chip
native report survived the latter. Original17 ROI files were absent, not
zero-marker PASS. Corrected run_roi.py reads the unchanged original ODB,
uses integer DBU/catch/report-existence checks, and preserves all17 reports.
native/run_native_executed.py is the exact original successful full-chip
checker source before its ROI reporting fix; run_native.py is the corrected
reproducer. check_original.tcl contains native Tcl replay commands. Scripts
and all raw failed receipts remain; no failed verdict was overwritten.

Pinned preparatory commits: fcd05121f input preparation;10acf104d original
native geometry driver;f5c59fd4c corrected ROI driver;67f4afd44 fixed pin driver.
No jobs remain live. ROOT personal PNG/result review and new geometry model
choice are next. Existing SRAM clock/reset/K/source-phase/first-use, all-pin
AP/route, every PG contact, timing/energy and token release claims stay open.

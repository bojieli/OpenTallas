KV actual provider PG work, 2026-10-29 08:34 onward.

Input: intel1:/srv/opentallas-scratch2/claude/codex-kv-0822/imported/provider.odb.
Runtime: intel1:/srv/opentallas-scratch2/claude/codex-kv-pg-0834.

Actual source census: 37,967 standard cells = 15,296 retained clock cells +
22,671 provider cells. All 75,934 supply terminals have one actual R0 M1 rail,
18 nm high. There are 45,190 overlapping/abutting native rail groups; every
group has a 50 nm-margin, 128 nm-grid landing slot. No actual top PG metal and
no regular routed signal/clock wires existed in the input database.

Canonical top PG is now materialized in grid3/native_grid.odb. The unchanged
source psm/pdn.tcl defines the regional grid. Its empty macro-connector grid
cannot be drawn until actual macro landings exist; that separate obligation
is explicitly excluded. An initial PDN attempt failed PDN-0233 because the
source already contained its own PG capacity obstructions. The first exact
reservation match incorrectly used regional die_infra.pg_rects and rejected
2,722 missing rectangles before producing a target. Correct source reservations
come from die_trial.pg_stripes: all 13,073 exact rectangles matched, were removed
only while drawing their metal, then all were restored. No other obstruction
was removed. Both failed runs remain immutable in the runtime directory.

Actual grid readback PASS (grid_readback.json): all 38,127 total instances and
31,845 original block obstructions identical; non-PG physical/connectivity hash
cce6226e17592e0d3fde4fa9808970c28dfda5ee15e99794de7fd2354344d4ee unchanged.
VDD/VSS/VDDPHY have 1,711,367 / 1,700,546 / 8,648 actual special-wire shapes.
No standard-cell M1 access, macro-PG closure, global supply continuity, IR,
DRC, loaded clock timing or die freeze is claimed by that top-grid result.

Access planning is based on the existing QC native contact planner. Generalized
mixed-cell import validates exact actual rails rather than CKINV-only names.
Every proposed via uses actual technology-enclosure data; the importer requires
existing actual same-net top-grid conductors and retains the non-PG hash.
A source export that expands every internal array-via box remains live; a
parallel exporter caches each via-array master and uses conservative per-layer
bounding enclosures to avoid that expansion. This representation never omits
actual metal. Neither exporter changes the source ODB.

KV is repairing measured soft-obstruction intersections by applying the existing
clock+provider island union. Before access is adopted, export_overlay must refresh
actual native OBS and native macro PG pins from that ODB, verify the same
non-PG hash and identical standard-cell rails, then plan_access --native-overlay
replaces only those native inventories while retaining actual top-grid metal.

Source tools prepare_inputs.py -> prepare_grid.py -> canonical pdngen ->
readback_grid.py reproduce the top-grid operation. export_native_bbox.py,
export_overlay.py, plan_access.py, render_access.py and apply_access.py form the
remaining contact-planning/import path. These later steps remain preparation
until their actual runtime receipts are collected. No data/control cycles added.

PARKED on explicit Claude reset at 2026-10-29 09:03 PDT.
The fast bbox export completed: 19,798 actual M8/M9 grid wire rectangles,
6,855,538 existing supply rectangles, same 37,967 standard cells / 75,934 rails.
Original array-expanding exporter remains live, unit oth-ubuntu-1683312-1793288610;
no job was killed or restarted. The fast exporter unit1849864 and exact grid
readback unit1772696 finished PASS. Prepared planning input mirror and Shapely/
matplotlib packages exist on epyc2 under codex-kv-pg-0834/plan_inputs; planner,
geometry review of contact paths and access import have NOT RUN.

Remaining source blocker: current provider-only soft abstract islands intersect
14,634 actual clock bodies. KV prepared the full clock+provider type union of
29,431 windows in full_abstracts/*.lef. Attempts to replace master OBS/PG pin
boxes failed closed; no output ODB was produced. Independent tiny actual-master
coupon proves dbBox_destroy and dbBox.destroy leave both master OBS and MPin
geometry unchanged; list and explicit comprehension both enumerate all boxes.
The owner-level probe also confirms dbMPin.destroy is absent from this build.
Counts: OBS 1,699 before/after; VDD 241 before/after. Logs retained here.

The next safe path is the KV owner's fresh full-source rebuild from the reviewed
56 full_abstracts LEFs, then provider import and the same canonical PG operation.
This fresh rebuild was NOT STARTED before reset. Preserve grid3 actual metal and
its exports; only reuse them after verifying the rebuilt source has the same
non-PG circuit/placement hash and matching actual top-grid metal. Refresh native
OBS and native macro PG-pin inventory from the new actual ODB before contact
planning. A projection or LEF alone cannot establish that actual-source gate.

Known PG scope: VDDPHY has physical top stripes but zero connected ITerms in the
current abstract source; that PHY-specific supply binding stays with the die/PHY
owner. No standard-cell local access, macro closure, IR, DRC or freeze is claimed.
No owner question. No further engineering or job launches after reset.

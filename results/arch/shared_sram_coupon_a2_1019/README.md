# A2 representative visible-wire joins: bounded native PASS, full-master HOLD

Exact reviewed c634d1540 new-master model, independently compared before engine:
+39nm core/source attachment, +48nm leads/vias, 120nm PG center+51nm with
conditional internal +12nm attachment, R0 only. Original A2c2d failures stay
immutable. ROOT personally reviewed candidate PNG/checklist before execution.
No model geometry changed after review. No B/C/AP/PDN/production views, route
repair, timing or electrical attachment claim.

All28 actual representative ROIs in BOTH families have zero native target
markers and zero inner-ROI neighbor markers. These include actual clock,
control, read data, first/last W/E source ends and complete first/last via
columns, all true intersecting neighboring signal/PG metal. All target cropped
networks have one independently computed geometry component. This closes the
sampled visible join RECTONLY defect only; it is not all-pin or whole-master
native qualification. All true neighboring OBS identities are retained in
coupon.json as conditional reservations; no hidden OBS or access resolution.

All32 original cases,477 rectangles,130 complete VIA45s were instantiated as
regular routed native dbWire segments/patches/vias. Native via metal/cut boxes
were asserted exact against input geometry.32 integer-DBU native ROI reports,
full raw29-marker report, ODB/DEF, loaded rules and shape ledger are retained.
Full29 markers comprise2 RECTONLY,2 metal-spacing,8 EOL-keepout,1 EOL-spacing,
16 min-area.15 min-area markers are in actual-family cropped/isolated neighbor
via metal OUTSIDE their own score ROIs; exact bbox classification is preserved
per marker in analysis.json, never suppressed. Other14 markers belong to the
three positive failure controls. All raw geometry and markers stay intact.

Controls: aligned rectangular join zero markers; original9nm step exactly2
RECTONLY;23nm spacing exactly1 metal-spacing+2 EOL-keepout; disconnected contact
has TWO independent geometry components plus6 EOL-keepout,1 metal-spacing,
1 EOL-spacing,1 min-area. Connectivity is checked by actual layer/rectangle/via
overlap, never net name or native silence. No fixed BPin hides visible geometry.

Native execution: unpinned ot-run1CPU/4GB/2GB selected ot-epyc7,
unit oth-ubuntu-132415-1792446868, observed2026-10-19T21:54:28Z.
Elapsed0.79s, peak249580KiB RSS, staged disk6988074B, exit0. Actual image inspect
.Id sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29;
actual binary SHA25621eda99eeae7eccb22ca64ad28949c08a6c01dcece3ccb23e2206d635f8d2846,
version26Q3-1510-g6cb3f2b704. Contemporaneous host/memory/disk/image/binary/raw
resource receipts are under native/. Actual host image identity is not the
frozen analytical calibration af971398 identity. Source input commit2825d2ba5;
initial sparse-index add refused, then corrected sparse definition and committed
unchanged bytes while the short staged run completed; no engine input changed.

Remaining HOLD: non-ORTH width-table DRT import/binding and track-rule native
coverage; all121 PG/OBS own-access conflicts; conditional transistor/contact/
internal PG implementation; every all-pin AP, PDN/PG continuity, timing/RC,
orientation beyond R0, source phase/reset/K/first-use and token release claim.
No new stage is launched. ROOT personal result PNG/checklist review is next.

Reproduce prepare.py, preengine.py, then launch.py (fleet only) and analyze.py.
SHA256.json binds every retained file; native/original.odb is the unmodified
checked geometry input, checked_unrepaired.odb additionally retains markers.

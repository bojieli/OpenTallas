# HEAD-R21 clock plan event (s81_head), 2026-10-27

Branch `claude/head-r21-clock-1027` (adopts Codex `codex/head-clock-1355`@e4def21ea1 + `codex/head-1351` attach helper).
Plan sha 7af81995 = HEAD-PLAN-PG plan (9d1bffc6f9) + one delta: `partition_types.hd_serdes.clock.tap_edge_y_um = [77.76]`.

## Root cause of the 192 off-mesh serdes taps
`hd_serdes` (2885.76 x 1226.88, soft) had no tap mode, so `schema.tap_grid` gave it the generic R4 400-um grid:
8 x 4 = 32 taps per tile. All 32 sit inside the VDDPHY window (type y >= 150, no core rows, see
`fallback_land.py` "no core rows"), and the outer two rows (192 taps on 12 tiles) were 688-997 um from the mesh.
The mesh design (head_mesh_r3 `SD_ROW` 77.76, R3) and the plan's `clock.tap_um` already put the serdes clock entry
on the 150-um CORE-VDD digital strip. The fix uses the existing ruled form `clock.tap_edge_y_um` (CLOCK-KV-R8):
one tap per grid column on the strip row, which is the mesh `serdes_row` M8.

## Results (plan level)
- Endpoint census (`edge_tap_census.json`, `census.py`; transform checked by reproducing the old 384 serdes points
  exactly): 3654 endpoints = 1320 native core + 2334 grid; serdes 96 taps, max reach 1.06 um; die max reach 93.12 um;
  0 over 450. Added clock wire: 0.
- G0 PASS 0E/6W; G0C PASS 0E/6W, 16/16 types (on main check.py).
- Actual mesh attachment (`head_attach_actual_mesh.py`, driver_boundary_lowerrows build + driver_rows straps):
  PREPARED_NOT_ROUTE_QUALIFIED, 0 errors: 264 driver groups / 528 units with risers <= 2.5 um, 3654 taps, 15190 vias,
  1 component; encoder 1156 nets, 3100 pin stairs, 3655 port joins (`attachment_receipt.json`, `encoder_receipt.json`).
- Renders viewed: `r21_serdes_taps.png`, `r21_serdes_taps_zoom.png`.

## Alternative tried and rejected (`phy_band_alternative.json`, tools/s81_head/head_phy_band_rows.py)
Unbuffered PHY-band mesh rows (one M8 row per edge in the VDDPHY M8 gap + M9 risers with real M8 bridges, PG-flanked
at 1.0-um clearance): geometry legal, 0 errors at 4 and 8 risers per tile; +54-115 mm wire; analytic Elmore at the far
taps 159-381 ps (UNCHECKED). It needs PHY upper-metal permission and PG-flank shielding and still serves taps that
have no sinks. Codex COPY 0c7b31b74 (all 95 columns extended) was +221 mm / +32.8 pF.

## Still open before freeze
VSS shield tie / ground VIA continuity (`vss_tied` false), mesh variation sign-off, RCX, die GRT0 with the fixed clock
metal, and related-pair die STA (shared die_sta_related.py model). The hd_serdes kit must put its core-clock sinks in
the strip; a partition CTS serves them from the 8 edge taps.

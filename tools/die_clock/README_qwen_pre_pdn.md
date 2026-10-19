# Fixed clock rows before original PDN: source prototype

This branch supplies an isolated MODEL/prototype. It installs no shared GEN or
die-chain hook and enables no timing or production admission. ROOT must review
the ordering/ownership change and the actual physical checks before integration.

The diagnostic input is immutable dv2f16 GEN
1075e50e2dcc1c25d15ab8232757bac665f11a1a, not live dv2f18dh2 or production
SAFE2. Its actual original PDN contains20,308,247 supply special shapes. Native
`define_pdn_grid -existing` stopped with exit137 in the62GB addon container
before any new rail generation. That failed import remains immutable; this
prototype does not retry it.

The existing order builds clock cells in an already powered ODB. The proposed
isolated order is:

1. Use actual immutable source PG geometry as an explicitly source-bound planned
   blueprint. Build fixed regional/spine topology with PG-safe sites before
   reserving cells. Preserve405um actual reach, complete endpoint coverage,
   whole-footprint occupancy,1.08um hard/pad halo, actual master M1 pin shapes,
   opposite-net M8 clearance and both actual planned M9 contact budgets.
2. `qwen_clock_pre_pdn.py prepare` records input/manifest/policy hashes, exact
   long M8/M9 polygons and all actual cell geometry. It installs fixed clock
   rows while preserving existing row coverage and every cell coordinate. It
   requires the row-derived core rectangle to stay exactly unchanged, then
   removes supply SWires only in a new ODB. This is a planned-metal model, not a
   statement that future rails exist.
3. Load that separate `before_original_pdn.odb` and run the **original pinned
   pdn.tcl** and full `pdngen`. Do not run the old movable-constant row hook on
   the clocks again: its default path can relocate them. The prototype already
   retained the original constant coordinates/rows. Keep the existing physical
   supply generation, technology and checker settings; do not import a second
   whole existing grid or synthesize a contact from a model.
4. `verify` requires exactly the prepared manifest/GEN/policy, all unchanged cell
   geometry/core and an exact match between actual generated core M8/M9 polygons
   and the planned blueprint. It then runs explicit actual clock M1 contact,
   native stack-short and strict native VDD/VSS continuity checks. A changed mesh
   rejects; refreshing a blueprint hash is not qualification.
5. Repeat the independent actual ODB endpoint/net/405um/footprint/row audit on
   the powered output. Only after these gates and ROOT review can a separate
   native TT/FF/SS timing candidate be considered. Phase, child insertion
   references and production Q readiness require their own source-bound proof.

The focused shared-file candidate is `tools/qwen_split/die_tie_rows.tcl`:
`preserve_clock_cells` defaults to an empty explicit manifest list. A separate
`ot_clock_rows_candidate` preserves all coordinates/old coverage; the explicit
`ot_clock_pg_contact_check` includes clocks, which the old tie-only contact check
does not inspect. Their use remains opt-in. Generic clock-family census, live
GEN placement, original PDN sources and shared main are untouched.

Ownership diff for ROOT review: die_clock owns the fixed topology/blueprint/
preparation and receipt tools here; a future die-chain/GEN hook owner must move
the clock/row stage before original PDN and skip the movable row hook for these
fixed cells. Original PDN generation/checkers remain with their existing owner.
No such shared scheduling change has been installed.

Actual controls are under `evidence_qphase_1019/physical/pg_safe_sites_1ea`.
The43-cell row control preserves core DBU rectangle
`[0,0,31730346,24288660]`, changing1855rows to1876 with300.564um additional
row length; its absent-rail negative correctly rejects `dc_r343_L1/VDD`.
The whole PG-safe source2c28 geometry has42,981 cells and763/763 endpoints,
zero overlaps/halo/M8-phase violations, max actual routed401.058um and regional
direct365.138um. It still has85,962 unconnected PG pins and42,850 off-row cells,
so the physical gate remains FAIL and no timing has run on it.

# Whole actual PG-safe clock geometry

Source2c28be828, immutable dv2f16 input, fleet unit4126968 exit0. This new plan
uses the actual PG site model before topology:1.08um hard/pad halo, real master
M1 pin shapes/orientation, opposite-M8 clearance and two actual M9 contacts.

Independent actual ODB geometry audit4159935 (expected physical-row FAIL):

-42,981 cells:36,286 regional and6,695 spine,765 regional trees.
-All763 required spine endpoints appear exactly once; no missing/extra endpoint.
-Zero spine or ALL-clock full-footprint overlaps.
-7,457 routed stages; worst actual-pin route401.058um, source entry88.819um.
-Regional actual direct maximum365.138um, zero>405um; fanout12. Spine fanout2.
-42,850 clock cells lack physical rows; this is not a physical PASS.

Independent actual PG audit4159936 exit0 is a constraint receipt, not an
admission result: zero opposite-M8 phase conflicts and zero1.08um halo conflicts
(old unqualified geometry had20,873/17,283). All85,962 new PG pins remain
unconnected before the fixed-row/full-PDN stage. Timing/phase/production remain
unqualified. No native TT/FF timing run was launched on this candidate.

Actual geometry ODB SHA256
f8ba8846473eb8a84fdfc3643583224bbda87ed5e280f057320d7209b9ca3bba;
manifest SHA256
3b4d072193a050b63be678b18d19fe4b69e1f6c38b4c8a6ebd37a3df4c2c9d21.
`geometry_manifest.json.gz` retains all source-bound stage paths/coordinates;
`geometry.json` is the independent audit; `pg.json.gz` retains every actual
clock PG pin/bbox; `replay.log` retains the complete run.

The readonly inventory controls4154611/4154610 both exit0. Original PG has
20,308,247 supply special shapes. The isolated43-clock fixed-row candidate
preserves exact row-derived core `[0,0,31730.346,24288.66]`um, adding300.564um
of row length and changing1855 rows to1876 without moving any cell. The addon
native existing-grid import exits137 at the62GB container before generating
rails; its source and failure remain immutable. The separate source prototype
now prepares fixed clocks/rows before original PDN, with an exact source-bound
planned mesh and mandatory actual generated-mesh/contact/short/continuity
verification. See `../../../../README_qwen_pre_pdn.md` for ordering/ownership.

Remote original artifacts:
`ot-epyc4:/srv/opentallas-scratch/claude/qwen-clock-phase-1019/pg_safe_sites/`
`full_pg/{geometry.odb,geometry_manifest.json}` and `full_pg_audit/`.

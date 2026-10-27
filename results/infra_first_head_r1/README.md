# INFRA-FIRST-HEAD-1 R1: s81_head infra-first plan event, round 1 (D-INFRA-FIRST-HEAD)

Plan: `physical/die_plan/s81_head/die_plan.json` on main 262d070384 (sha256 d7b8d1eb..., unchanged; nothing written
into the plan this round). Runs on intel2:/srv/opentallas-scratch2/claude/infra-head-1027. All numbers are own-tool
outputs. They are UNCHECKED-independent: NUMBER-CHECK is owed.

## Done this round (order 12.7: PG -> clock -> reset -> roads)
1. PG (`die_infra.py pg`, analytic IR model, 5 % of 0.7 V = 35 mV budget) -> `pg.json`. The plan grid (0.48 um at 8.64
   on M8 and M9) gives 87.4 mV: FAIL. The smallest feasible grid is M8 0.48 at 4.32 plus M9 0.48 at 1.728, at 34.34 mV
   (local 21.7 + coarse 12.6). PG then takes M8 29.4 % and M9 70.1 % of the tracks.
   Power basis: core 0.3257 W/mm2, which is the S81 die figure of 84.1 W charged to the head core area (borrowed, not
   head-specific). SerDes PHY 4.37 W per macro.
   The width is fixed at 0.48 in the candidate sweep, so only the pitch varies. Before freeze: a wider-stripe sweep,
   a head-specific worst-case power, and PDNSim (static_ir is NOT RUN).
2. Reset (`die_infra.py reset`) -> `reset.json`: wavefront root sp3, 326 nets, max die hop 378.0 um <= 405, 0 long
   hops, 0 unreachable, max release 80, 60.2 mm of wire.
3. G0 (`check.py --completeness`) on the current plan: PASS, 0 errors / 6 warnings; G0C 16/16 types clean.
4. Master-plan baseline (`die_infra.py master-plan --pg`, no mesh) -> `mp0_gates.json`.
   - Data roads all PASS: reach_gap max 401.742 um (coll_WN3_d), bay_fill max 0.496, corridor_tracks M4 0.379 /
     M5 0.498, entry_pins PASS, lot_fit PASS.
   - Clock items:
     - clock_entry FAIL 5/5: core taps are not at the core centres.
     - core_reach FAIL: the gate reads the old 317.672 outline.
     - early_taps FAIL 5: the plan's core taps are "early" 415.6.
     - core_insertion_model FAIL 2.
     - clock_sites FAIL: hd_serdes taps lie inside the PHY.
     - tree_on_islands FAIL.
     - Every mesh-dependent gate is NOT RUN.
   These are exactly the items the plan event replaces.
5. Island lattice (`tools/s81_head/head_island_lattice.py`) -> `isl_r1.json`; render `isl_r1_zoom.png`, viewed.

## Clock structure decision R1 (12.2a1 / 12.2c / 12.8e1). Plan geometry only, not built yet.
- **In-core islands = centre clock entries.** Each hd_tile has 5: eA0..3 at tile frame (177.12|531.36, 168.48|540.0),
  plus eB at (354.24, 876.96). These are the core centres with the rebuilt lattice outlines elemA 319.68 / elemB
  285.12, the same outlines HEAD-CORE-R12 builds.
- **One plan-delta move: eB origin x 216.00 -> 211.68 (-4.32).**
  - Without it the MY tiles' eB island is 8.64 um off the R0 tiles' lattice (orient asym 8.64). With it the island
    set is MY-invariant (asym 0.000).
  - The die hd_tile islands then form ONE column lattice: 33 columns per half at 177.12 pitch (eA columns at 354.24,
    eB columns between them), with the spine gap 1736.64.
  - They also form 36 rows: 3 per tile row (pitches 371.52 / 336.96 / 328.32, repeating every 1036.8).
- **Continuous mesh (12.8e1).**
  - M9 V straps on every island column (66), plus the turn centre columns and the spine columns.
  - M8 H straps on every island row (36), plus the station-row centre row (frame y 613.44, which is the same frame y
    under MX for the N/S instances) and the serdes digital-strip row.
  - Every island lies ON a strap, so the stub length is 0 and the structure is identical for every instance.
  - The station-row types (1442.88 pitch) are incommensurate with the 177.12 column lattice: offsets 30-88 um.
    They are fed from their own H row strap, which passes through the island, so no V coincidence is needed.
- **Global tree.** Mesh drivers sit at the eB island of every hd_tile: 132 per half, 11 columns x 12 rows at
  708.48 x 1036.8.
  - 11 x 12 is not a power of two, so die_clock_mesh's bisection-congruent lattice mode (KV) cannot build it.
  - The head needs the QC form: a delay-balanced zero-skew merge tree with nodes on straight segments between child
    roots, per-level 8.64 VSS lanes, and plan-computed d1 sizing (`qc_clk_mesh3`, QC R13-R17).
  - That tool has QC constants hard-coded (PER_X 2471.04, 773 seam pairs, the centre channel). It must be
    generalised to read a per-die lattice: that is R2.
- **Open structural items.**
  - (a) hd_serdes taps are inside the VDDPHY area. They need a PHY-side clock entry, with the island in the 150 um
    digital strip.
  - (b) PG M9 at 1.728 pitch leaves 1.248 um gaps: enough for 4W straps, but a 16W trunk needs VSS-phase lanes (QC R14
    lesson).
  - (c) In the plan, the core taps must move to the centre entries (`clock_entry`), and `core_taps: early` 415.6 must
    be replaced by the R12 cores' real insertion (12.3 v5.0).

## Not done (needs R2+)
- Mesh / tree build, GRT >= 50 iterations including the clock, mesh MC sign-off, related-pair STA.
- D-INFRA-FIRST-HEAD stays PENDING, and the 16 types are NOT released to kitting.

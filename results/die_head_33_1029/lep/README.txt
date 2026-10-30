DIE-HEAD-33 HEAD-013 lep_pair  Thu Oct 29 05:51:02 PM PDT 2026  (COORD 07:52 admitted lep0N +198.72 W / lep_pair 777.6x492.48; 17:30 ruling 3)

CHILD KIT (built, running) -- independent of where the parent puts the 4 pairs:
  lep_pair_kit_777.py = die-local driver around main tools/s81_head/head_lep_pair_kit.py (no shared edit):
    plan copy = src25m (intel2 die-head-32/src25m, sha a7435da4) with only the 4 hd_lep0N pair hard cores -> 777.6x492.48
    + pins_file lep_pair_pins_777.json; pin view lep_pair_pins_777.json (Codex LEP V5, head_lep_child_resize.py: 2141 pins,
    W coll_i M4/coll_o M6 y2..464.5, S K-side in M5/out M7 x2..395.4, centre M5 rst_n (388.824,246.24); clk +2 M5 tracks);
    SRAM sites = lep_pair_child_v5.json (Codex V5 55 sites: 36x 256x64 + 19x 32x64).
    Hook fix: main d379a4b741c reformatted face_guard_core.py's guard() call, so head_lep_pair_kit.py's exact-string land
    hook raised 'core face_guard invocation changed'; the driver feeds the hook the old form and keeps straps/dead kwargs
    (face_guard_core.py now: straps + dead + land=kit_land(land_slots.json)).  Shared tool fix belongs to the next shared lane.
  Gen rc 0, kit_hash bd6f57a248ad07b9 (pre interior fix), DIE_AREA 0 0 777.6 492.48, PLACE_DENSITY 0.5.
  Flow: intel2 die-head-33/lep/v1 (rsynced to epyc2, same path), run_kit_hbm.sh place 32 16 via ot-run --hosts epyc2,
    unit oth-ubuntu-2802518 (container hbmcore-ot_s81hd_lep_pair_kit_-2802544).  rtl_lint/sdc_lint/SELRANGE PASS,
    port_bind PASS (0 missing/extra), FACE_GUARD PASS 2140/2140 (CHECKED logs).  GPL running at report time.
  LEC in PARALLEL (12.14f, not a serial gate): kit lec.py renamed lec.py.parallel in v1 so the place flow does not block on
    the ~hours hinted LEC; same 1_2_yosys.v proved by unit oth-ubuntu-2876937 (container dh33-lep777-lec, epyc2) ->
    v1/ot_s81hd_lep_pair_kit/lec/lec.json.  RTL is the one Codex proved EQUIVALENT 73440/73440 at 388.8x432 (3193799).
  AUTO-GEOM: epyc2 watcher geom_after.sh runs tools/autopilot/geom_check.sh (GRT M7, 50 it) on 3_place.odb ->
    epyc2 die-head-33/lep/geom_v1/auto_geom.{json,png}.

ESTIMATE (child, UNCHECKED scaling of the measured trial7 GRT at 388.8x432: H 1.022 / V 1.595):
  V capacity ~ width 777.6/388.8 = 2.00 -> V ~0.80; H capacity ~ height 492.48/432 = 1.14 -> H ~0.90 (demand held equal:
  2140 pins, 55 macros 62,002 um2, 109,242 std cells 16,544 um2 -> std util of free area ~0.05).  PASS est., GRT decides.
  r2r: Codex V5 analytic at this outline/macro map = 1892 captures > 405 (stall artefact); DIE-HEAD-29 coupled register
  moves reach 0 at REFF 378 with 0 added flops (results/die_head_29_1029/lep_repl, sites_legal_378_push.json.gz) ->
  if V1 AUTO-GEOM r2r FAILs, V2 = V1 + those register seeds (kit-only, 0 cycles).

PARENT PLAN EVENT (lep0N +198.72 W) -- ESTIMATE FAILS, NOT BUILT (CHECKED from src25m hd_lep0N fields):
  W landing bands coll_i1/coll_i2 x 17.28-62.64 -> W pair column x >= 69.12; E landing bands coll_i3 x 1345.68 /
  lepk,lepf 1352.16 / unit 1354.32 (90.7-97.2 um inside the E face, y 265-820 = both pair rows) -> E pair edge <= E-101.52.
  2x2 of 777.6 needs 69.12 + 1555.2 + 17.28 (mid halo) + 101.52 = 1743.12 um -> grow >= 300.24 (lattice 302.4 =
  Codex candidate codex-head-0830/head_lep_expand_0830.py, 1745.28).  At +198.72 (1641.6) the E pairs overlap the
  E bands by ~101.5 um.
  K faces: the pair K-side is the S face; Codex candidate puts both rows R0 with a 17.28 gap -> the top row's 1114 K
  wires face the gap (supply ~1110 V/H tracks at 100 %) = FAIL.  Fix: bottom row MX + top row R0 facing ONE central
  K shelf (155.52 um tall, holds the 45 parent SRAMs = Codex bottom-shelf layout), N margin 69.12 (coll_i0 band
  y1164-1210), S margin 17.28.  Pair0 coll from the N window (x160-587 +grow) reaches its E-column face through the mid
  channel: 1026 bits need >= 34.56 um at 50 % (V tracks M3/M5/M7 ~1110 per 17.28 um) -> grow 319.68 (nst4 1442.88 ->
  1123.2, its 4 ft stations at 280.8 um <= 405 reach).

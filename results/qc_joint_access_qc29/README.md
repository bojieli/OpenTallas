# DIE-QC-29 — QC joint clock+PG access: why local PASS and global census disagree; form (a) landing-first

Diagnostic/estimate packet only. No shared tool, RTL or plan edit. Base: codex/qc-joint-access-main-1029@be80ed573.
Data: intel2:/srv/opentallas-scratch2/claude/die-qc29 (g1/, census_grow/, formA/), inputs from intel2 codex-qc-mesh5-1029 (read-only).

## 1. Why local 89,180 PASS0 and the global 0.32-um census (2,469 FAIL) disagree (CHECKED, own reruns)
They check different things, in the wrong order:
* Local 89,180 PASS0 = clock-CELL power contacts/access inside the 119 islands, normal M8 clearance, planned FIRST,
  without reserving the 7,889 native partition M7 clock-pin landings.
* Codex 2,469 census = 7,889 native landings (VIA78 + 0.192x0.08 M8 patch, clock NDR spacing 0.32) against canonical PG
  + clock M8 witnesses ONLY. Reproduced exactly: `census_grow/base_rep_pgonly` 5,420 landed / 2,469 fail.
  Adding the local clock-cell power access (with or without the 1,690 bridges) -> **5,217 / 7,889 fail** (`base_rep*`).
  So the honest combined census was 5,217 fail, not 2,469.
* The 2,469 blockers (classify_native_blockers.py, blockers.json): 933 canonical 0.48-um M8 PG straps, 1,536 other-net clock
  M8 witnesses at 0.32; at 0.16 only the 932 PG remain; at 0.08 only 32 remain, all blocked by the reserved local
  power access (canonical alone clears them) = the 32 `full_prebuild` VIA78 failures.

## 2. Form (a): Codex type-uniform M7 proxy growth + LANDING-FIRST reservation (CHECKED)
* Load: plan_growth_candidate.json == plan_start_native_h800.json except `tap_pin_heights_um` (29 types, 327 pins,
  3,217 instance pins, 0.864..2.048 um, centres fixed). Main `gen_phys.tap_pins` loads all 29 types, 0 errors (in-outline check).
* G0/G1 (main 9cddaa527 tools): base and growth give the IDENTICAL finding set (500 findings; 316 ERROR = 313 clock_landings
  `cland_tstart_in used 0 times` + 3 hard_pinreg, pre-existing in the Codex native plan, not from growth). G1 render VIEWED
  (g1_grow_die_plan.png; pin growth is sub-um, no visible change, as expected).
* Census grown vs PG+witness 0.32: 7,885/7,889 land; 4 fail = PHY pins (io_serdes x3, ucie_kv).
* Grown, but local power access planned first: 3,241 fail -> order matters.
* Landing-first: grown landings reserved -> plan_access.py re-run (joint clock reserved + landings, bridges as reserved
  power): **89,180/89,180 contacts, 0 failed groups** (13,221 access rectangles moved); full global census (canonical PG +
  new access + 1,690 bridges + clock witnesses, 0.32) = **7,885 / 7,889, only the 4 PHY pins fail**.

## 3. The 4 PHY pins (form (b) scope)
Each PHY clock pin (hard IP as-is, pin not growable) sits directly under a full-width canonical VSS M8 strap
(0.48 um): io_serdes y15171.6, io_serdes_1 y3481.7, io_serdes_2 y1157.5 (+ one clock witness), ucie_kv y9633.4.
Two parallel forms (12.17(3)), estimate only, not built:
* (b1) parent M7 clock stub: VIA78 + M8 patch at the nearest clear M8 row just outside the pin (<= ~0.66 um each side;
  growth probe says 1.19-1.32 um equivalent), short M7 clock stub into the pin. Die-local (fixed_tree adapter), no PG change.
* (b2) PHY PG corridor: 4 local notches of the canonical VSS M8 strap, ~0.83 um long (patch 0.192 + 2x0.32), both strap
  stubs stay fed by M9 VSS at 768.6 / 785.9 (UNCHECKED: VIA89 at those crossings) -> IR delta ~0 (UNCHECKED).
  Shared PG generator change -> opt-in + ROOT-MERGE.
Default: (b1) first (die-local), (b2) in parallel only if (b1) M7 stub hits M7 signal/OBS geometry.

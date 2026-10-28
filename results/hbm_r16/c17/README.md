# HBM-R16 / C17 plan delta (on C16r 732240f89458)

Data (intel2): `/srv/opentallas-scratch2/claude/hbm-r16-1027/`
- `c17/`  = C16r + (a) hub core re-pin/orient.   die_plan.json sha 6f226140b1f3, cores/ manifest 6a4be06afd97
- `c17g/` = C17 + (b-i) pin6 re-spread (pin tables only; die_plan.json identical 6f226140b1f3), cores/ manifest ed8bbfe198c7 -> **C17 candidate**
- basis `/srv/opentallas-scratch2/claude/hbm-r15-1027/c16r` untouched.

## (a) G0C core_faces (q_hub_nw / q_hub_ne)
Fast core_faces runs use the same `check_core_faces` as G0C (codex-hbm-plan-1351 check.py), `tools/cf.py`.
1. `tools/apply_hubpin.py` (HBM-MU-QUAD-6 method A, one plan group per RTL port, no copy groups), destination face capped
   at the pin6 limit 5.5 pins/um, accept threshold = G0C away threshold (-0.1): 6 groups re-pinned (u_svg_Q0
   program_active/running W->S core face; u_hb_idx__q_Q__q0 block_head/number/v, head_weight E->N). 147 -> 135 away.
   Method A alone (one face per port for every instance, orients fixed) cannot fix the rest: instances of a shared master
   need different faces.
2. `tools/joint.py`: per master, joint choice of orient per instance + ONE core face per port group (no new types, no
   copies), pin6-capacity-feasible; `tools/apply_joint.py` applies it: 24 orient changes, 116 group moves in 9 masters
   (vms_bank vecd4ae, idx_qctl, idx_query, idx_vm_query, su qcore, coll reduce, coll q3 body, gq_issue, gq_land);
   2 moves refused by placement (vms_bank rr2/rr4, cap). Type clock taps of re-oriented cores mirrored about the core
   centre with the core (clock entry pin itself untouched in the core table).
3. Result (CHECKED, tools/cf.py): core_faces away groups 147 -> 50 (pins away 37148 -> 30329 on c17g), side WARN groups
   160 -> 106. pins off track 0, clock_entry_macro over_macro 0 (tools/tapchk.py, CHECKED).
   Left: 50 away groups in vms_bank (vecd4ae + vec6293), gq_issue/gq_land, coll q3 vm core, xload bdring -- all blocked by
   pin6 capacity on the only facing face (needs outline growth / variant; see overcap table).
4. Station relax (`relax_route.py c17 400 405 --noadd`, `relax_hop.py`): bad_before 0, added 0 cycles.
   NOTE: re-oriented cores move their clock tap positions in the type frame -> die clock taps
   (clock_taps_die.json / H-tree) must be regenerated (retap) before die CTS on C17.

## (b) pin6 face capacity
`tools/respread.py`: (i) re-spread whole groups to a face with cos > 0 for EVERY instance, destination <= cap
(APPLIED in c17g, 19 tables touched); (ii) else grow the side to n/5.5 + 17.28 um with a lot check (NOT applied).
Tables over cap: 35 (c17) -> 29 (c17g), 6 cleared. Full table: `overcap_c17g.txt`.

## Gates
G0 + G0C on c17 and c17g launched via ot-run 17:40-17:45 PDT; collect `c17*/gates/br_g0/g0_report.json`,
`c17*/gates/br_g0c_p/g0_report.json` (+ `.exit`). The chain scripts also start a serial G0C into gates/br_g0c after
G0 (duplicate of br_g0c_p).

Render: `c17g_render.png` (orange = re-oriented, red edge = away ports left, blue = moved pins).

## Gate results (collected 18:12 PDT, CHECKED from g0_report.json)
- c17  G0 PASS 0 err / 484 warn; G0C (br_g0c_p) FAIL 12 err, all core_faces (q_hub_nw 6, q_hub_ne 6 = 5 listed + 1 summary each); away groups 50.
- c17g G0 PASS 0 err / 484 warn; G0C FAIL 12 err, same core_faces only; away groups 50, pins away 30329.
- C16r had G0C FAIL 12 err with 147 away groups: the error COUNT is unchanged because check.py lists 5 per type + 1 summary per type; no new error classes.
- The serial G0C started by chain17.sh/gates17g.sh into gates/br_g0c duplicates br_g0c_p (can be ignored or killed).

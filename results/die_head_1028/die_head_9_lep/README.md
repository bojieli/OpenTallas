DIE-HEAD-9 LEP split (COORD 2026-10-28 06:30 ruling (4)): 4 peer PAIR children ot_s81hd_lep_pair (g_lane[k] lnland + safe8 coll lane), opt-in ot_s81hd_lep0N_core PAIR=1.
- pair_face_census.json: pair-boundary register census on the DIE-HEAD-8 hierarchy-preserving netlist.
- lec/: wiring LEC PAIR=0 vs PAIR=1 (leaves blackboxed, equiv_struct): PASS 18080/18080; mutants rx bit swap (8 unproven) and chb tie (1 unproven) FAIL as expected; default PAIR=0 vs origin/main: PASS, named cells identical.
- lep_pair_pack*.{json,png}, lep_pair_plan_delta.json: packing estimate + plan-form contents[] (lef/lib/origin_um) for all 265 SRAM (4 x 55 child + 45 parent). UNCHECKED estimate; not applied to die_plan.json.

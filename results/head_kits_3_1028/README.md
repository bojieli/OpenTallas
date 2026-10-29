# HEAD-KITS-3 (2026-10-28): one fstart_in face_guard form (ring_start) + lec alias fix

Branch = origin/main b6fd7043d2 (has FSTART a769e0b2de + HEAD-KITS-1 aea82f7b06) + DIE-HEAD-21 ringstart 52a35ca59d (on
landslots 528a7d3edb) + lec.py re-keyed kept-alias fix (cherry-pick of HEAD-KITS-2 1364247ab) + gen_kits.sh no longer runs
head_land_slots.py (gen phys --clock-landing writes land_slots/2 with the ring_start entries; head_land_slots.py would
overwrite it without them).  HEAD-KITS-2 face_guard "starts" form (af7eb1403 / bee0428617) is NOT taken: rule freeze, one
form for the class; ring_start is the stricter one and is in the hd_tile sign-off kit (DIE-HEAD-21 combo 55c66ec4a7).

Proof (regenerated from this branch, plan_hk1, gen.py phys --clock-landing --trial; synth via ot-run epyc2, CHECKED):

| kit | face_guard | ring_start ports | LEC | kept registers |
|---|---|---|---|---|
| hd_st_m | PASS 278 | 2 | EQUIVALENT | 1092/1092 |
| hd_st_n3 | PASS 4136 | 4 | EQUIVALENT | 11798/11798 |
| hd_spn_end | PASS 5090 | 9 | EQUIVALENT | 11119/11119 |

Tests (tools/die_plan): test_face_guard, test_lec, test_clock_landings, test_clock_landing_verify, test_count_straps,
test_land_slots_emit, test_gen_phys_clock_landing: 188 pass / 3 skip.
Run data: intel2:/srv/opentallas-scratch2/claude/head-kits-3/gen (kits + launch logs).

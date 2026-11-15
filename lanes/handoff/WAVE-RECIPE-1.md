# WAVE-RECIPE-1 handoff (owner of FABLE-WAVE-REVIEW fixes 2, 4, 5 + NEEDS-LANE + M9 grant)

Branch: claude/wave-recipe-1-1114 in intel2 ~/wt/wave-recipe-1-1114 (clone of hub main ad97a98d1eb).
Scratch: intel2 /tmp/wr1_* (patch scripts: wr1_patch_kw.py, wr1_patch_kw2.py, wr1_patch_kw3.py apply to any kit_wave.py copy).

## State (2026-11-14 ~19:xx PST)
- M9 (FIX 4 M9 part): HELD per COORD until shapes imported. Per-die answer posted (queue). Code: m8_grant.py layer-generic,
  OT_GEN_M9_GRANT=1 / layer_budget.type_m9_grant -> kit MAX_ROUTING_LAYER M9 + per-track die-M9 obstructions + forced M8 grant,
  M9 grant in m8_grant.json extra_grants (fixlef unchanged runner). Committed 32d070ea315. NOT in any die src yet, NOT in die_gen_env.
- t30 proof (static): signed t30 M9 = 943 segs / 905 tracks; vs S81 die M9 straps 42 shorts + 14 spacing; the M9 grant for all 3
  t30 types obstructs all 54 colliding tracks (126 of 905 used tracks fall on obstructed tracks; type keeps 15364/18036 = 85 %).
- OT_CLAND_STRIP_DENS=1.0 in die_gen_env s81/qwen_kvsys/qwen_compute/s81_head: DONE live (backup kit_wave.json.bak-wr1-1114-ot_cland_strip_dens).
  No kit_wave.json on main (coord-state only).
- kit_wave.py (branch, not yet live at time of writing): NEEDS-LANE gate, killed_attempt + kill_pin (FIX 2), die_env_stale rearm +
  flow_regen (FIX 5). Tests tools/autopilot/test_kit_wave_wave_recipe.py (19).
## Next
1. full test_kit_wave*.py compare vs main (3 form_wait_arm tests failed in full-suite order on branch; check main).
2. deploy kit_wave.py live (timer stop, bak, copy+mv), post first.
3. proof builds: FIX 2 (next killed post-GRT attempt: KILL-PIN log + resume start route), FIX 5 (FLOW-REGEN log lines), NEEDS-LANE (ASK line).
4. M9 per die: overlay m8_grant.py/gen_phys/schema into die src, die_gen_env OT_GEN_M9_GRANT=1, t30 rebuild proof.

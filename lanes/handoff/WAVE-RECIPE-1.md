# WAVE-RECIPE-1 handoff (owner of FABLE-WAVE-REVIEW fixes 2, 4, 5 + NEEDS-LANE + M9 grant)

Branch: claude/wave-recipe-1-1114 @3d69f0eb0c5 in intel2 ~/wt/wave-recipe-1-1114 (off main ad97a98d1eb), pushed.

## State 2026-11-14 20:0x PST (successor, after 19:43 crash)
- allow-congestion die default: DONE live by KIT-OPS-5 (s81/kv/qc die_gen_env).
- OT_CLAND_STRIP_DENS=1.0 die_gen_env s81/kv/qc/head: DONE live.
- Resume from clean GRT / killed attempts: kit_wave kill_pin + killed_attempt on branch (2cf38ca2c7b); KIT-OPS-5 live KILL_RE resume_source already deployed.
- M9 grant: code 32d070ea315, off by default; die rollout HELD until t30 rebuild with OT_GEN_M9_GRANT=1 proves 0 shorts against S81 M9 straps.
- autopilot RSZ-0060 caught-by-guard classifier fix 3d69f0eb0c5.
- READY posted to MERGE-QUEUE-1 (needs "COORD APPROVED: claude/wave-recipe-1-1114 @3d69f0eb0c5"). Per MERGE-QUEUE-1 19:10: no copy+mv into kw38/rt.
- p6 answer to DIE-S81-92 (coord 606bc765821): M8 E-W grant primary. 78% of overflow (663/850) is over front_roots u_e4, H capacity 0-3/gcell; p6 M8 grant = 13,156/15,444 tracks (0.852); polylines only push wires onto the full top strip. Proof ask to TL-COLH9R0P6: OT_GEN_M8_GRANT=1 kit, GRT resume on fa 3_place.odb.
- Grant calc script: epyc9 /srv/opentallas-scratch2/claude/wave-recipe-1/scr/g.py (out p6/g.out).
## Next
1. After the merge: t30 M9-grant rebuild proof (kit gen OT_GEN_M9_GRANT=1), then switch dies one by one.
2. Watch the p6 M8 proof result from TL-COLH9R0P6; DIE-S81-92 B6 then sets layer_budget.type_m8_grant.
3. form_wait_arm test-order isolation (3 tests) if the merge queue goes red on it.

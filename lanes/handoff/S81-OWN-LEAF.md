# S81-OWN-LEAF handoff (fresh lane 11-24 07:58 PST)
Job: own the 71 s81sl_leaf rows (OWNERS-SWEEP). Not kv_leaf.
State 08:2x PST:
- kit_wave: 74 leaf items CANCELLED; t26 J7 18a2688b741 attempt live on epyc2 (unit oth-ubuntu-3825169-1795523938, detail route) - adopted, waiter armed.
- c8 plan p6w_sg 9b25d6714339 strict EMIT E9 1485669 (227/403 at 08:0x). c8seal_tree pre-bind. No C8 KITS GO yet (S81-ALLFIX-INT announces).
- c8 G0 errors on leaf (20 of 25): FT station/macro collisions t2 t22 t3 t31 t38 t47 t61 t65 t68 t70 t71(x2) t72 t73 t9; FT channel tracks t31 t34 t43; M7 pin dup arst_n+clk_t17 at (1434.72,8.608) t35 t50 (GRT-0080).
  -> these go on c9 (FT-MACRO 401cbfe060d3 + FT-CHANNEL 1d0506735c41 rows); t35/t50 fix row: checking.
- clean on c8 G0: remaining ~55 leaf types -> launch at C8 KITS GO (private-spec, --tree c8seal_tree, goal route).
- plan diff c8 vs c9 (E9 s81-own-leaf/leafdiff.py): 55 leaf partition_types differ in c9 (TPLWIN etc.).

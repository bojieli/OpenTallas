# HARVEST-ECO-2350 handoff (2026-11-20 23:5x PST)

Scope: HARVEST-0330 entries in ~/coord/PROTECTED-DBS.txt with class a_hold_le30 (73 of 127 HARVEST rows). Table: lanes/HARVEST-ECO-2350.tsv.

## Census
- 73 a_hold_le30 entries: epyc9 29, epyc2 15, epyc10 8, epyc7 8, intel1 6, epyc8 6, intel2 1.
- 67 REDUNDANT: the type has signed on some plan (signed-store, the counter cache signed_records incl dp_ die-plan records, or an AUTO-EXPORT of a SIGNED signoff.json today: sle_sc_v2, sle_sc_v1, slw_hc0 x2).
  Disk (du per path, hardlinks can overlap): epyc2 14 DBs 190 GB, epyc9 29 295 GB (1 path already gone), epyc8 6 108 GB, epyc10 7 101 GB, epyc7 7 94 GB, intel1 3 43 GB, intel2 1 9 GB = ~840 GB.
- 6 NOT signed (4 types):
  - slw_sc_v2 epyc2: LIVE QC-HOLD-0030 eco_loop (qc-hold-0030-kits/recover1120/slw_sc_v2, iteration 2 i2t, running ~20 h). Not duplicated.
  - sle_st_b_v2__cl14c98df5__pvcd986c42 epyc10 and slw_sc_v1__cl63e5a7a2 epyc7: protected path (ot-jobs/.../work) no longer exists on the host. No DB left to ECO.
  - 3 ECOs launched (below).

## Deletion (OWNER RULING 00:3x 11-21: remove the 67 from the protected list and delete them, on all hosts)
- Re-check passed for all 67. Each type has a sign-off in the store, the counter or a SIGNED export. No ps cmdline/cwd, docker mount or open kit_wave attempt references any of them (the s81 t24 cleece78ec a27 reference is an abandoned 11-19 attempt, and a28-a31 are newer).
- PROTECTED-DBS: the 67 rows were removed via coord-commit (ce3afe13850).
- ot-delete: 13 DELETED (epyc2 2, epyc9 11). 1 was already gone (epyc9 ot-jobs sle_sc_v2). 53 KEPT by guard layers. I did not weaken any guard.
  - 48 by the protected-path list (ot_delete_guard build_protected from kit_wave.json):
    - 44 sit under a protected kit-wave work root: kw43-wave-1109n/runs/{qwen_compute 22, s81 14, s81_head 5}/kit-wave, kw43-wave-1109/runs/qwen_kvsys/kit-wave 3.
    - 4 are themselves protected or contain a protected path: kv-kt-e0 kv3_head_eighth_e0, s81 t38 attempt_6/gen, t7 cl362204c4 attempt_7, type-gunit-l1f g3f (holds a signed signoff.json).
    - The designed narrow exception is ~/.local/state/ot-delete-guard/allow_exact.txt (COORD-ruled, per path, with expiry, per host). COORD must decide whether to use it. I did not use it.
  - 5 by routed_unsigned_refusal: intel1 sle_sc_v1 cl7479a5ec a2, epyc7 sle_hc0 cl929603c0__cl38badc56 a3, epyc8 slw_st_b_v2 a6, epyc9 sle_st_b_v1 pv7b7fafb4 a7, epyc9 slw_fe_v1 a3. These are unsigned routed attempts with no newer routed attempt. This needs a code change, which is not mine to make.
- df avail before -> after: epyc2 scratch2 257 -> 261 GB, epyc9 scratch2 528 -> 560 GB. Other hosts are unchanged (nothing deleted).

## ECOs (HARVEST-ECO-2350, intel1, --priority plan, eco_loop.py rt/current run --mem 112 --cpus 8 --lec)
Out roots /srv/opentallas-scratch2/claude/harvest-eco-2350/<type>/eco1 (outside wave paths: the 11-20 hub watchdog bug stopped prd-eco children of CANCELLED wave parents).
| type | kit (seed) | base TT / core FF | unit |
| slw_sc_v1__cl64543eaf__cl5e017c6f | qc-hold-0030-kits/recover1120 copy (6_final seed) | -36.33 / -6.87 | oth-ubuntu-1639700-1795246176 |
| slw_sc_v1__cl64543eaf__cl4590432d | qc-hold-0030-kits/recover1120 copy (6_final seed) | -28.83 / -11.43 | oth-ubuntu-1642612-1795246179 |
| sle_sc_v3 | wave s29q103S4Q9N3 attempt_3 (6_final seed, 5_2 removed by STAGE-CAP) | +29.77 / -17.82 | oth-ubuntu-1644165-1795246181 |
Prior history: each had 2-3 earlier ECOs end without a verdict (11-19 prd_mk t10 "pass dir not staged"; 00:34 stopped by the hub watchdog; 03:29 recover1120 t10 stalled after eco_post.tcl ~06:14 during intel1 memory <6%, then 143 at 11:16/12:31). If this run stalls at the same point again, do not relaunch. Diff the run env first and look at the t10 repair_timing -setup step on this ~100k-endpoint design.
Result: <out>/eco_loop.json. A PASS with LEC EQUIVALENT is picked up by ot-auto-export (RTX + AGIdock), like the other R-MINIMAL ECOs today.
Client logs (localhost scratchpad): eco_5e017c6f.log, eco_4590432d.log, eco_sle_sc_v3.log.

## Next
- Read eco_loop.json for the 3 units. Check hold FF internal >= 0, TT >= -42, DRC 0, LEC. Post the result per item.
- After COORD/owner releases the 67 redundant rows: remove them from PROTECTED-DBS via coord-commit.sh, then ot-delete (paths are in the TSV, status REDUNDANT).

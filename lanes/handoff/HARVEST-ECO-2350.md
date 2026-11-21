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

## Deletion NOT done (step 2 held)
The OWNER RULING 23:2x covers intel1 HARVEST DBs only and says "skipping PROTECTED-DBS"; it does not release PROTECTED-DBS entries on epyc2/7/8/9/10/intel2.
MEM-RECLAIM-2200 (23:16) also found ot-delete refused all 13 intel1 candidates on two guard layers that an owner release does not lift.
So no PROTECTED-DBS edit and no ot-delete. A COORD/owner release is needed. Each HARVEST row says "keep until re-signed or owner release". The 67 rows are ready to release.

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

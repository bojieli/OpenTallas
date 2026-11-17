# FABLE-PLAN-QC-N: structural review of QC plan event N (S4q9n)

2026-11-17 09:37-09:50 PST. Read-only. Plan `zz_s29_qc103_s4q9n.json` sha 175b9337614e (M5 cf3ee3ca9c40 + lockup keys +
N START + SC reset + R-REACH-4), bind s29q103S4Q9NBR on epyc2 `/srv/opentallas-scratch3/claude/qc-plan-r3-n-1117/`
(unit oth-ubuntu-2347000-1794935556, ended 09:45:55 rc 1). Pilot bind read: epyc2 `qc-types-r/bind_tap0/out3`.
Probes were inline python3 -I reads of plan JSON, bind RTL and bind_report (no heavy job).

## Verdict: do NOT launch cb kits on N as composed. Three blocking findings, all with numbers.

| # | finding | number |
|---|---|---|
| B1 | The `latch_except` / `latch_except_hb4` rows are inert. They are keyed on `qfd_tile_nk_a0c` (the plan hard-core name); the bound cell is `qfd_tile_nk_rp2_romleaf_rr` | 68 of 68 tiles in 18 of 18 cb types keep `ot_dp_lk #(.W(508)) u_lk_nk_*_tap`; 0 x W(507); 0 x `u_hdly_lk_*`. Same in the NBR RTL and in the pilot bind out3 |
| B2 | `gen_phys._lockup_pad_type` is true for every type under `"all": true`, so the PRE_FLOORPLAN hook `OT_HOLDPAD_LK ... no pad cell` errors on every type without a pad | 133 of 133 types get the hook (0 have `hold_hb4` in-buses); 115 non-cb types can never have a pad; with B1 the 18 cb types have none either |
| B3 | NBR failed: 74 errors = 44 HARD_CORE_PARAM_WRAP + 30 R8_STALE. The chain stops on the 44 (non-R8), no BQ pass | 11 st_a types x 4 rows, `HI_PAD` bound = plan + 1 on all 44; R8 = 1 bus (`c16_E0_1.u_fab.u_x_2_0.b_d` <- dvs_E0 xh2.s_d), bound 29 vs table 28. Cause is the N START / SC reset part (+90 lane cycles on 78 lanes), not the cb rows |

Proof of B1 (function call on the N plan, type cbn_q01__clab6e67f2, port tap): module `qfd_tile_nk_a0c` -> xbits {0},
hb4 3; module `qfd_tile_nk_rp2_romleaf_rr` -> xbits {}, hb4 0. bind.py line 4168-4170 looks up `c.module`, which is the
as-built name (`qfd_tile_nk_rp2_romleaf_rr u_u_t_0_2 (... .tap(lk_u_t_0_2_tap))`, NBR rtl line 3471 / 3516).
So the "pilot closed post-CTS" numbers (TT hold >= +120, FF >= +93.9 over 2,032 pins) are the in-memory ECO on
xj_join only. No bound kit has ever carried the row. The pilot bind out3 would have built the old latch form.

## (1) Tap offsets and tap[0] rows on M5 geometry

- Offsets: 18 cb types, 2,076 port rows. N == M5 on every row (0 moved). N against the pilot plan
  (`zz_s29_qc103_s4q9l2tap0.json`): 0 rows outside tolerance, max move 0.3 ps. tap_window rows equal in all 18 (N = M5 = pilot).
- Geometry: hard_cores equal to M5 in 17 of 18. M5 moved nothing the rows depend on. N itself changes one cb type:
  cbn_q00__cldbcda913 (10 instances), `cl_nb_i00` origin x 1129.68 -> 1086.48 (-43.2 um) plus 5 fclk source repoints
  (R-REACH-4, hops 543..975 um -> 15..64 um). Its 122 rows were measured with the old tap site: not re-measured.
- Against the pilot plan 8 cb types differ in `count_straps` only (RTL widths, QC-CLK-R2: a00_i / nb_i12 7 -> 6).
- The tap[0] rows do not hold: B1.
- One pad count for 18 types is not shown. The pad was sized on cbn_q01__clab6e67f2 (core ports TT -416.2..-400.2,
  FF -358.8..-346.5). Shifting the pilot margins by the core-port offset of each type (capture side only; an
  estimate, the launch tap per tile is not mapped):

| type | core port vs pilot | estimate |
|---|---|---|
| cbn_q11__cl49ae4555 (10 inst) | 80.3 ps earlier at TT | TT setup +90.6 -> about +10 |
| cbn_q11__cl5cc92dfe (14) | 52.6 earlier TT, 42.1 later FF | TT setup about +38, FF hold about +52 |
| cbx_q10__cl89936551_h (10) | 44.6 earlier TT | TT setup about +46 |
| cbn_q00__cldbcda913 (10) | 38.5 earlier TT, 22.5 later FF | TT setup about +52, FF hold about +71 |
| cbn_q00__cl622f65d2 (13) | 78.9 ps later at FF | FF hold +93.9 -> about +15 |
| other 13 types | within 22 ps | TT setup >= +69, FF hold >= +70 |

## (2) BIND_GROUP_MASTER

- The check is the same file everywhere: `bind_strict_src.py` ea949e990b9a on origin/main 5a5a7f84f43, in event_tree_N
  and in the D3 copy. It is not a tree-age effect.
- It fires when the `lib` list of `asbuilt_sources.json` names files that do not exist. Pilot out3: 39 of 39 lib paths
  point at `/srv/opentallas-scratch2/claude/kw45/src_qc_pin_eb1e73448bd0_s4q9l2/...` (an E8 path, absent on epyc2) ->
  1 BIND_SRC_MISSING (39 paths) + 36 BIND_GROUP_MASTER (the su_lane products cannot find `ot_hdc_sfu_exp_t / rcp_t /
  rsq_t` in `rtl/hdc/ot_hdc_vstream_sfu_t.sv` and `qfd_dv_s5_lrly` in `qfd_dv_s5_leaves.sv`).
- N: the lib list is the hard-linked L2BQ seed pointing at treeJ on epyc2, 39 of 39 present. Measured: NBR has 0
  BIND_GROUP_MASTER and 0 BIND_SRC_MISSING. It will fire on N only if N is re-bound from a relocated / published copy on
  another host, or after treeJ is cleaned.
- Fix: not `bound_groups.register_masters`. main bind.py (fbb4b3528bf6, line 4852) takes the lib paths as recorded. Rebase a
  lib entry that is not a file onto `B.base` by its repo-relative part (the 3d763393b4 kit-rtl mapping), and report the
  count. For the pilot now: bind on the host that holds the named tree, or hard-link the seed `asbuilt_sources.json`.
  bind_tap0/out4 (running, same command as out3) repeats the 37 errors unless its paths were changed.
- Not checked: main `bound_groups.py` fba8f26dcacc differs from the N tree 690eaf2749fa (2 commits); effect on N unread.

## (3) Clock / hold risk; other lockup modules

- Yes: `qfd_tile_nk_rp2_romleaf_rr` is the module that needs the rows. It is the bound name of all 68 a0c tiles
  (192 die instances of the 18 types, 720 tiles). `qfd_tile_nk_a0c` matches 0 bound cells. `qfd_tile_nl_a0c` (4 tiles in
  the cbx types) is not in `modules` and has no lockup.
- With the rows inert, every cb build keeps the four tap[0] latch ends at -27..-127 TT (the known class).
- With the rows fixed: FF hold is the thin side on types whose core port is later than the pilot (table above, down to
  about +15); TT setup on the earlier ones (about +10). `latch_except_hb4` is per module, so one N for all types.
- n_a / n_b / rst_n: no change in N, no negative end in the 06:00 read.
- Still no routed cb result: every cbn_q01 attempt stops at 4_cts.

## (4) Congestion, PG, pin access on M5

- Pads: 12 HB4 per 4-tile type, 9 per cbx type. No area or congestion effect.
- plan_gate_pre on N: PASS, 0 findings; GEOM-INHERITED 40 station / relay sites over hard cores (tolerated, same as M5).
  R-REACH after the fix: 0 errors, 35 R-REACH-3 warnings. G0 on N: no output yet at 09:46 (log 0 bytes).
- The `cl_nb_i00` move of 43.2 um in cbn_q00__cldbcda913 is not checked against PG straps or the cland bin sites by me.
- Inherited: 820 taps above 320 ps slew (hc1 / hc2, not cb). Region mode: QC holds 9 of the 17 DRT-0255 kits.
- E8 scratch2 is at 38 GB, below the 50 GB floor: an N tree publish (about 60 GB) cannot start there.
- Not checked: PG and pin access of the 18 cb types on a routed DB (none exists).

## (5) Check, fixes, stop list

Single check before kits (bind gate, seconds): on the bind RTL, `u_hdly_lk_*` instances == 68, tap latches W(507) == 68,
W(508) tap latches == 0, and every module key of `latch_except` / `latch_except_hb4` matches at least one bound cell
(else bind error). Today: 0 / 0 / 68.

Ranked fixes:

1. QC-PLAN-R3: key both rows on `qfd_tile_nk_rp2_romleaf_rr`. Add the unmatched-key bind error (tool, QC-TYPES-R3).
2. QC-TYPES-R3: `_lockup_pad_type` per type: hook only where the bound RTL has pads, expected count 3 x tiles.
   Without it 115 non-cb types stop at PRE_FLOORPLAN.
3. QC-PLAN-R3: split the event. NA = M5 + the two lockup rows only (no latency, R8 or param change; expected bind
   delta = 68 latches W508 -> W507 + 68 pads). Bind and release cb on NA. N START + SC reset + R-REACH-4 follow as NB once
   the 44 `HI_PAD` rows (11 st_a types, +1) and the 1 R8 bus (+1) are resolved. This revises stop item 6 of
   FABLE-PLAN-QC-M5: the bundle coupled cb to a failure it does not cause.
4. QC-TYPES-R3: pilot = a real bound kit to route on cbn_q01__clab6e67f2 (TT setup >= +60, FF hold >= +50 on the four
   tap[0] pins), plus the two edge types cbn_q11__cl49ae4555 (setup) and cbn_q00__cl622f65d2 (FF hold) before the other 15.
5. QC-PLAN-R3 (tool): lib-path rebase in bind.py for the BIND_GROUP_MASTER / BIND_SRC_MISSING class.
6. QC-PLAN-R3: re-measure the 122 rows of cbn_q00__cldbcda913 only if R-REACH-4 stays in the cb event.

Stop list:

1. Any cb kit, pilot or wave, on plan 175b9337614e or on the out3 / out4 pilot bind.
2. The R8 derive + BQ pass on NBR: the 30 R8 bits are not the blocker.
3. Rebuilding st_a masters for `HI_PAD` before the split is decided.
4. Editing `register_masters` or adding lib files for BIND_GROUP_MASTER.
5. Quoting +120 / +93.9 as a bound-kit result.
6. A rows re-fold for cb: 0 of 2,076 rows moved.

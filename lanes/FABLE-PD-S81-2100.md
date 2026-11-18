# FABLE-PD-S81-2100 2026-11-17 21:0x PST: S81 plan event D8c (structural PD review)

Reviewer: PD-REVIEW-S81-D8C (Opus, standing in for Fable). Read-only. Technical PD only.
Marking: **V** = opened the file myself. **I** = inferred from V data. **R** = reported by a lane.

Evidence (V), epyc8 `/srv/opentallas-scratch2/claude/s81-die-r3-e8/`:
`d8c/r1/{bind.log,g0.log,g0/g0_report.json}`, `d7w/r1/{bind.log,g0/g0_report.json}` (baseline),
`proto/plan_d7w.json` vs `proto/plan_d8c.json` (full JSON diff), `d8/cut_try2.log`, `d8/tapsplit_d8.log`,
tree `kw45/src_s81_pin_3c913dbdfb23_d8c_1117_work/tools/die_plan/`. Hub `/srv/opentallas-scratch2/claude/s81-die-r3-hub/proto_d8c.log`.

## Summary

- **D8c is not publishable as built (V).** Bind exits 1 (D7w: 0) and G0 has 8 new ERRORs. The cut ERRORs dropped from 5 to 0, but the moves put 3 hard cores on top of ft station sites.
- **The cut moves work on the census (V).** 10 segments over 0.6 before, 0 after, and 0 over 0.58. The worst die segment goes from 0.923 (s_4N_L1@20000) to 0.577 (s_5S_L0@10750, a line no move touched). No new segment over 0.58.
- **Core-shape freeze holds (V).** The plan diff has 109 entries: 12 `origin_um[1]` changes, the 11 serdes clock blocks, `die.hold_ff_margin_ps` 25, and notes. There is no change to w/h, orientation or the outline.
- **ist_rows is not in the D8c tree (V).** `tools/die_plan/ist_rows.py` is absent and `kit_istations.py` has no call to it. `cut_census.py` (r645) is absent too. col_h9_r1 gets no station rows from D8c.

## Ranked findings

| # | finding (numbers) | class | owner |
|---|---|---|---|
| 1 | **BLOCKER. The moved macros sit on ft station sites.** There are 8 G0 `geometry` ERRORs (D7w had 0), 2,296 station bits in all: t2 ft0 105 (u_vsw); t22 ft0 105 (u_vsw), ft2 326, ft5 71, ft6 71 (u_vn.u_b); t3 ft1 1,105, ft8 172 (u_vn.u_b); t43 ft2 341 (u_vn.u_a, +680.4 um). `cut_wall_fix.py` checked KITFIT and taps but not station sites (V log: "KITFIT 0 TAPS_BAD []"). This is the check Fable asked for at 19:2x (lever 6.1: ft stations paired with moved cores). Fix: re-site the stations of those 8 slots off the new macro footprints (or choose another dy that clears both the cut line and the station rows), then re-run G0. Expect 0 ERRORs. | structural | S81-DIE-R3 |
| 2 | **BLOCKER (reset reach). The tap split broke two serdes local-reset anchors.** Bind rc 1: `serdes__t1__clfe1f0815 landing_local_resets.fstart_face_ft0_o: raw 'rst_rl_170' has no registered wavefront driver` (G0 R-REACH-5 start_raw_net, new). There is also a new R-REACH-5 on `serdes__t15__cla3d02796`: `fstart_face_ft0_o <- rst_rl_244` is 690 um against a 405 um edge reach. Mechanism (I): `added_taps` feed the reset tree (`clock_landings.py:880`, "added_taps -> reset_tree"). The +4 taps on each type re-number the `rst_rl_N` relays, so `raw` names written into the plan now point at nothing or at a far relay. Both types gained 4 taps in D8; the error check is identical in the D7w and D8c tools. Fix: regenerate `landing_local_resets[].raw/xy_um` for every serdes type that carries it (t1 clfe, t15 cla3d, and any other) against the D8 reset tree, using the generator, not by hand. Then expect bind 0 and no R-REACH-5. | structural (family: serdes) | S81-SERDES-GEN (S81-DIE-R3 applies) |
| 3 | **col_h9_r1 station rows are absent.** r652 `ist_rows.py` is not in the D8c tools (main ed283ee1be + cb2ca1b). D8c therefore cannot release h9r1. The ir1 re-measure (TT -181.27 / FF -58.3, R) cannot run on this tree. Fix: carry claude/s81-ist-rows-1117@9e8f65db (the new file plus the 2-line kit_istations.py patch) into the D8 rebuild. Then S81-TYPES-R3 regenerates the col_h9_r1 kit with OT_IST_ROWS=1 and checks that the row sites lie inside free rows. Carry r645 cut_census.py at the same time. | tree content | S81-DIE-R3, then S81-TYPES-R3 |
| 4 | **Tap cap 1700: no tap over the limit in the SIM, but the margin is thin and mostly estimated.** `tapsplit_d8.log`: GROUP-CAP REFUSED 0, UNSIZED 0. Only t13 is a CTS census (max 1,646). 10 of 11 types are ESTIMATEs from t13. Seven types fill to exactly 1,700 (t12, t14 with 3 taps at 1,700 and no added taps, t16, t1 x2, t2); the other types reach 1,423 to 1,623. The G0 log has no tap or landing ERROR on serdes. Landing reach: the clock side shows no new finding. The reset side is finding 2. Ask: on each type's first kit, read the per-tap sinks at CTS. Any tap over 1,700 gets one more added tap; this is not a re-plan. | measurement | S81-SERDES-GEN |
| 5 | **Lattice: the moved origins are off the 8.64 um lattice.** There are 10 new `hard_cores` WARNs (moves on the 2.16 grid; e.g. t43 u_vn.u_a [622.08, 939.6], t2 u_vsw [120.96, 352.08]). A sub-lattice origin moves the core pins off the M5/M7 track pattern. Fix while re-moving for finding 1: snap dy to a multiple of 8.64, or set `track_offset_um`. | geometry | S81-DIE-R3 |
| 6 | **Channel and face streets: a small net change.** New `face_street` on t2 (3, 43.20 < 56.16 um) and t22 (2, 43.20 < 51.84 um). Street and station_alley counts fell by 1 to 3 on t14, t2, t22, t32, t43 and t52. u_vsw in t2/t22 (dy -252.72) now faces away from its partner u_vs: 66 pins at cos -0.79 (`core_faces`, new), which adds wire through the leaf. There are two new R-REACH-3 window_far entries on t73 and t8 (597 b x 207 / 239 um); those types are unmoved, so the cause is the tool rebase. None of these is blocking. Fold them into the finding 1 re-move. | advisory | S81-DIE-R3 |
| 7 | **Hold margin.** `die.hold_ff_margin_ps` 25 is in the plan and the schema in the tree has the key. 76 col rows still carry item_env `OT_HOLD_FF_MARGIN_PS` 10, which overrides the die key. Fable 19:2x suggested 40 for col and slice. 25 matches the 1100 port-margin finding. | config | S81-TYPES-R3 (drop or raise the 76 rows) |
| 8 | **Lane latency: not measured on D8c.** The bind stopped, so there is no LATCHECK. Crossings are unchanged (873, 606,281 bits, V), and the moves are intra-partition, so I expect 0 cycle change. The finding 1 station re-site can lengthen hops on t2, t22, t3 and t43 (slice_station t22/t43 already WARN 1,335 um > 3 x 405, unchanged). Re-run LATCHECK after the fix and expect 873/873. | measurement | S81-DIE-R3 |

The die GRT proto on plan_d8c (`proto_d8c.log`) is admitted on epyc10, unit oth-ubuntu-3998997-1794976261, with no result yet. The D7w A/B arm is unit oth-ubuntu-3989135-1794976234. Read it for congestion on s_4N_L1 (y 19.77-21.0 mm) and total overflow. It cannot clear finding 1, because station cells under macros are a placement-legality issue, not a congestion one.

## Stop list

1. Do not publish, gate or apply D8c (bind rc 1, G0 8 geometry ERRORs). Do not baseline the 8 geometry ERRORs or the R-REACH-5 findings into a G0 baseline.
2. Do not hand-edit `rst_rl_N` names in `landing_local_resets`; regenerate them from the D8 reset tree.
3. Do not release h9r1 or post col-h9r1-rows on any D8c-derived tree until ist_rows is in it.
4. Do not read the cut census or the proto as a route result for the moved leaves before the stations are re-sited.
5. Do not re-shape any core to clear the stations (core-shape freeze): move or re-site only.

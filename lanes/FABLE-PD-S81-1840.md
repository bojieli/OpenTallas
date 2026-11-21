# FABLE-PD-S81-1840 (2026-11-20 19:05 PST): S81 physical review for J6: serdes DPL-0033 cause, J6 row risks, J5 placed census, unplanned long legs

Reviewer: FABLE-PD-S81-1840 (Fable). Read-only. Nothing cancelled, signalled or patched. One geometry dump launched (two ODBs, see section 6).
Marking: **V** = I read the file or computed the number this round. **R** = reported by the named lane. **I** = inferred. **P** = proposal.
Scripts: scratchpad `dplscan.sh`, `rsz.sh`, `enc.py`, `cen.py` / `cen_sum.py`, `bk.py`, `delta.py`, `vp.py`, `legs.py`.

## 0. Headline

1. **serdes DPL-0033 is the new `serdes_tx_encoder` placement region, not the `coll_i0` stations (V logs + netlist, I mechanism).** The logs were not lost: epyc10 still has `3_5_place_dp.log` and the failed ODB of t3 and t4. All 11 serdes types carry the region; 3 of 3 that reached detail place on J5 failed.
2. **The J6 rows most likely to fail at place:** the seqhost `u_win` region (same construct, unproven), the vp_sr placeholder stations (9,211 rows, 603,116 bits on a site already used), and bk_sel face rows (three 276-bit stations on one point; plan legs to 562 um).
3. **J5 placed census (53 types, 0 past CTS):** no J5 kit has reset legs (inst_taps 0 of 53). The open classes are reset / START scalars, monitor pins, core-pin legs and unregistered reads. Slew 320 is in every kit and is not what limits them.
4. **Unplanned long legs (COORD add):** 42 % of the listed long pairs and 49 % of their bits are core-boundary legs (a core pin or its `u_y_*` relay register). One lever, seating the core-pin relay at the pin, removes the largest share.

## 1. serdes__t3 / t4 DPL-0033

### Evidence (V)
- Logs: epyc10 `kw43-wave-1109n/runs/s81/kit-wave/s81/224567138ab/items/serdes__{t3,t4}/gen/serdes__*/run/logs/asap7/*/base/3_5_place_dp.log`; failed DB `.../results/.../3_5_place_dp-failed.odb`. intel1 has the same failure for `serdes__t1__clb45db5be`.
- Signature, all three: negotiation legalizer phase 1 stuck at 10,990 / 9,291 / 10,946 violations (4,390 illegal cells on t4); diamond recovery leaves 27 / 48 / 44; final check: 110 / 171 / 155 cells off site, 1 to 3 overlaps; `ERROR DPL-0033`.
- The cells left illegal are anonymous logic and repair buffers (t4: 80 `_N_`, 28 `wireN`, `load_slew`, `fanout`). No station flop, no FIRM cell.
- Same tool, same form, before J5: 9 serdes detail-place logs on events b05c98f7919 and 465cb9fe2d3 pass with no stuck phase (t3 on 465c: stuck at 66, passed). OpenROAD build is identical (26Q3-1510-g6cb3f2b704).
- Not slew 320: `repair_design` inserts 41,465 to 76,544 buffers on J5 and 29,140 to 78,952 before J5, per type the same within 4 %.
- Not the `coll_i0` sites: `is_packed_exact_banks` checks every site for row / site grid, core, hard macro and reservation before placing, and the log prints "verified". t4: 5 stages x 513 flops, each a 23.9 x 16.5 um block (17 abutted columns, every second row), stages 278 um apart. No station is in a PMA keepout or outside rows.
- What J5 added to the serdes kits besides `coll_i0` (diff of the t3 kit, 465c attempt 7 against J5): two `coll_o0` stations, four defines, and `place_regions` = `serdes_tx_encoder {^u_bound[.]u_core[.]u_enc[.]} util 0.5 centre (1500, 860)` on all 11 types.
- The region (3_3 log): 5,925 cells, 1,556 um2, box (1470.6, 830.5)-(1529.4, 889.7) = 58.9 x 59.1 um.
- Netlist of t4 (`1_2_yosys.v`): the cells named `u_bound.u_core.u_enc.*` are 5,926 flops and nothing else. 5,975 anonymous gates touch a `u_enc` net; none of them is in the group. Repair buffers are not in it either.

### Mechanism (I)
The group holds only the encoder flops. Global placement pulls the encoder gates and their buffers to the same box. Detailed placement keeps region sites for group members, so every non-member inside the box must leave it. The box half-width is 29.5 um; the legalizer cap is 500 sites / 100 rows = 27 um. Cells near the centre cannot reach a free site, and the ring around the box fills. This is the count that stays stuck.
Not proven yet: the positions of the illegal cells. The dump of section 6 answers it (in the box or within 30 um of it = confirmed).

### Fixes, ranked
| # | Fix | Owner | Check |
|---|---|---|---|
| 1 | Flow: drop the `ot_region_*` group and region at PRE_DETAIL_PLACE (in `face_flops_release.tcl`), so the region steers global placement only. Then relaunch t4 on J5. No plan event needed. | S81-DIE-R4 (J5 ops), with FLOW-NOADV-R3 for the push | t4 `3_5_place_dp.log`: no DPL-0700, 0 site problems |
| 2 | J6 plan: remove `place_regions` from the 11 serdes rows unless fix 1 is in the J6 tools pin. | S81-J6-ASSEMBLY | plan diff |
| 3 | Tool: `place_regions.tcl` must refuse or extend a group whose members are under about half of the cone (add cells whose nets are all cone nets; size the box on the cone area). Print members / cone in the OT_PLACE_REGION line. | S81-J6-ASSEMBLY (tools pin), serdes lane | t4 line shows the gate count |
| 4 | If the region is wanted through detail place: `keep_hierarchy` on `u_enc` so gate names carry the path. Costs a synth + LEC round. Not for J6. | serdes lane | - |

Also (V): the region centre is (1500, 860) on all 11 types although their macro and station positions differ (t4 last `coll_i0` stage at x 1292-1315, t3 at x 1487-1510, y 674-690). Derive it per type (`near_re` on the last `coll_i0` stage).

## 2. J6 structural review

J6 has no candidate plan yet (epyc10 `s81-j6/cand` holds a dry test only; gates A and B are in bind). I checked the row files that will be folded in.

| Item | Finding | Mark |
|---|---|---|
| Hops over 300 | vp_sr delta rewrites `internal_stations` on 79 leaf types: 7,282 of 23,299 rows keep a leg over 300 (max 405). slice C delta: 7 of 140 rows, including the 416 um `leafdn_o0` leg of iq_C t1 (over the 405 check). r1_frame: `frame_int_i0` 401 / 380 / 386, `frame_int_o0` 3 x 344. bk_sel face rows as drawn: cb / ca / xtier_i0 547 / 517 / 486, idx_i0 last leg 562, tp_i0 557, xtier_i1 496 (the row counts on `relay_sites` of `u_bin` and `u_vm.r` for the missing stages); `u_vm.o -> u_rs -> u_g` 305. | V |
| Station-site overlaps | vp_sr: the +1 SR stage is co-sited with the old first stage on 9,211 rows, 603,116 bits, all 79 types (zero-length leg). `ho_site.py` (real sites) is waiting for memory on epyc10. bk_sel: `tl_o0`, `tp_o0`, `tp_o1` station 0 all at (2024, 1085), 828 flops on one point; `tp_o0` / `tp_o1` stations 1 to 4 are 5.5 to 22 um apart. bk_sel `relay_sites`: 307 exact collisions, 33,488 same-row neighbours under one flop width (aim points; R3 placed them FIRM with 0 unmatched, so this is density, not an error). | V |
| Monitor pins | J5: 62 types over 300 um, 37 over 500 (R, S81-J6-ASSEMBLY census). The fix is unpushed; its bind proof waits for memory. No J6 row exists to check. | R |
| Reset legs | Rows exist for 3 S81 types only (leaf t60, lepe nh_mus LP t1, lepe mu LP t2). They are per bind: the tool must run on the J6 bind. 0 of 53 placed J5 kits carry `inst_taps`. | V |
| bk_sel face rows | Lane deltas +1 / +1 / +1 / +8 / +7 on the five vmux inputs, +4 on the loop (L4), outputs +3 to +11. The six vmux inputs move by different amounts, so the schedule must be recompiled and run through the token sim; LATCHECK does not see it. tp in +7 and tp out +11 add 18 cycles on that path. L4 delays core reset release by 6 cycles. No placed hop maximum is measured yet (last value 2,591 um, R2 form). | V rows, R rest |
| Leaf no-growth classes | 13 sub-classes, 34 members folded, 0 overlaps, mismatches 0 (R). Private bind is waiting for memory. Landed spare slots still have no dormant protocol on main. The representative carries the union of ft windows on bands that are already the GRT top tiles. | R |

Rows most likely to fail at place or CTS:
1. **seqhost `u_win` place region** (`j6_delta_seqhost.json`, marked CANDIDATE, no kit proof). Same construct as section 1. It passes only if the kept hierarchy puts the gate names under `u_win`. Check members / cone before the bind, or carry fix 1.
2. **vp_sr with co-sited placeholder stages.** It doubles the station flops on the leaf band tiles that J5 form C already loaded (t7 peak tile 4,190 -> 21,442 bits, PD-1100).
3. **bk_sel__t2 rows.** Place density at (2024, 1085) and along the y = 135 station row; CTS / timing on the unrecompiled vmux schedule; four links still need the unpushed L4 RTL.
4. **Leaf class representatives** on the east band.
5. **iq_C t1** keeps the 416 um leg and loses the `rb_v` / `rb_d` rows.

## 3. J5 placed census

53 types past place on 224567138ab (5 hosts, newest attempt per type). 0 have a CTS report. The leaf representatives t2, t10, t39, t52 are not past place; leaf has only t25 (-174, input port to `u_ft_ft1_o_0`) and kv_leaf t5 (-273). Every kit: slew limit 320 in the report, `inst_taps` absent. Numbers are post-place, ideal clock: class evidence only, not release or cancel evidence.

| Class (worst path) | Types | WNS range | Covered by |
|---|---|---|---|
| Reset relay to flops (`u_rrl_N` / `g_rsreg.rq`, asynchronous group; 14 to 24 buffers) | col_h9_r0_p2 cl9f71 x2 (-272), p1 x2 (-125 second), col_h10_r0_p4 x2, iq_C (-566), kv512_C (-247), gunit (-1,085), bk_sel (-824), kv_leaf t5 (-163) | -85 to -1,085 | reset legs (J6, tool on the J6 bind) |
| `u_rrl_N` -> `cland_fstart_*_o` sync reset; `cland_origin/s1` -> fstart | col_h9_r0_p1 x2, p3, col_h10_r0_p4, slice_station t29, t6, t51 | -141 to -424 | reset legs / START pipeline |
| `cland_origin/s2` -> `cland_reader_start_*` (one bit, 12 to 20 buffers) | slice_station t18 (-885), t45 (-612), t37 (-237) | -237 to -885 | START pipeline; no J6 row seen |
| Monitor (pin far from seat, or ring `oh -> glo0` half cycle) | iqf (-1,040), slice_station t36 (-766), seqhost second (-625), col_h10_r2 x3 (-258 to -339), col_h10_r1 pv86f5 (-194) | -194 to -1,040 | S81-MONITOR-PIN-1745 |
| Core pin legs (core -> core, relay -> core pin) | col_h10_r1 x3 (-102), col_h10_r2 x2 (-75), col_h9_r0 p2 / p4 / p5 x7 (-29 to -55), p6 (-139, wire 532), col_h10_r0_p4 pvcc16 (-149, wire 730), gunit (-2,341, wire 1,404), bk_sel (-2,696, wire 1,584) | -29 to -2,696 | **open**: no J6 row for col; bk_sel rows; gunit none |
| Unregistered memory read | lepe mu LP t2, lepe nh_mus LP t1, lepw mu LP t2 (-590 to -660), eng t1 (-165) | | RIP1 in J6; eng none |
| Logic depth / memory fan-out | seqhost (-1,015), kv512_C (-997), iq_C (-1,432: 53 buffers to a bank memory pin) | | hwin adoption; kv512 held; iq_C **open** |
| Clean or landing-input only (`fclk_in_*`) | slice_station t24, t43, t49, t52 (0), t41 (-24), t27 (-71), t22 (-100) | | none needed |

Still open after slew 320 + reset legs + sparse-exit: (a) core-pin legs on col (the 7 col_h9_r0 types at -29 to -55 are inside or near the -42 gate; col_h10_r1 at -102 is not); (b) the single-bit START broadcast on slice_station; (c) iq_C memory fan-out; (d) gunit core-to-core 1.4 mm; (e) eng `u_h1` read.

## 4. Unplanned long legs (COORD add, data of ADOPT-CENSUS-1800)

Source (V): epyc9 `adopt-census-1800/placed/*.placed.json`, one record per S81 type (170 types), 3,447 listed endpoint-pair groups over 300 um, classified by endpoint names.

| Class | Pairs | Bits | Types | Top families |
|---|---|---|---|---|
| Core boundary: a core pin, or a `u_y_*` core-pin relay register, at one end | 1,431 (42 %) | 285,162 (49 %) | 76 | col_h9_r1 488, leaf 247, col_h9_r0_p2 138, col_h9_r0_p5 99 |
| Soft logic flop to flop | 679 (20 %) | 105,646 (18 %) | 72 | leaf 266, kv_leaf 61, serdes 51, c1x_C 34 |
| Reset / START / landing scalars | 560 (16 %) | 38,500 (7 %) | 94 | leaf 240, col_h9_r0_p5 69 |
| Planned station or pad chain (the part the plan models) | 429 (12 %) | 109,974 (19 %) | 71 | leaf 125, col_h9_r1 88 |
| Pin register to unsited logic | 232 (7 %) | 38,413 (7 %) | 53 | leaf 110, seqhost 33 |
| Strap ports (static) | 116 (3 %) | 1,150 | 6 | slice_station 102 |

The raw leg counters of the same records agree: core 670,675, logic 318,624, strap 15,878, channel 5,511.
- Core boundary examples: `u_y_xa_N_0.o -> u_tN` 842 um, 283 bits; `u_y_xo0_1.o -> u_bout_xo_o0` 688 um, 276 bits; `u_lpad_x_i0.q -> u_y_xo0_0.o` 577 um. The relay register exists; it is placed by global placement instead of at the pin.
- **Lever (P): seat every core-pin relay register (`u_y_*`, `u_y_xd_*`, `lpl` chunks) at its core pin**, as stage sites generated from the core LEF pin position, and add `relay_depth` by pin-to-pin distance / 300 where one stage is not enough. This is one generator rule (KIT-RD with stage sites, as reset form M already does for reset pins). It addresses about half of the unplanned bits and the col core-pin class of section 3.
- Second lever: place regions for soft cones, only after fix 3 of section 1.
- Third: reset legs and START pipeline (already owned).
- Census change: strap ports should be dropped from the measured legs; CORE_WIRE should be computed from pin positions for all core pins, not as a lower bound.

## 5. Stop list

- No relaunch of any J5 serdes kit to place before fix 1 or fix 2 is in its inputs. The 18:31 relaunches of t4 / t12 / t13 changed only env keys and will fail the same way. (I do not cancel them.)
- No reading of the serdes failure as a station-site or PMA problem; no `coll_i0` re-siting for it.
- No new `place_regions` row in J6 without the members / cone count from a real netlist (seqhost `u_win`).
- No vp_sr fold with the co-sited placeholder stages.
- No bk_sel rows in J6 without the recompiled vmux schedule through the token sim, and a placed hop maximum.
- No release or cancel decision from the post-place numbers of section 3.
- No more J6 proof jobs pinned to epyc10 alone: at 18:55 it admitted 0 GB and the J6 `val_f1`, vp_sr `run_ho`, the leaf class bind and the monitor proof were all waiting there.

## 6. Not checked / pending

- Positions of the illegal cells. Dump job: intel2 `~/fable-pd-s81-1840/w.sh` (detached; ot-run to epyc10, waiting for memory at 19:00). It posts `RESULT-ADD` with the in-box / ring counts. Outputs epyc10 `/srv/opentallas-scratch2/claude/fable-pd-s81-1840/{t4,t3}.json`. A second client from my session waits on the same script (serialized, idempotent).
- Whether detailed placement in this build excludes non-members from region sites: taken from the tool's known behaviour, not read in its source.
- The 11-19 t3 DPL-0033 on event 3fa87b84b18 (attempt 13): log lost; whether that kit had the region is unknown.
- No J6 plan exists, so no J6 census (hops, monitor distance, reset) was run; no leaf class plan geometry was opened.
- Section 3 has no CTS or hold data: no J5 type is past CTS.
- Section 4 uses the top listed pairs per kit (about 18 per record), classified by name patterns; it is not every leg.

## 7. Addendum 19:10 PST: dump result (V)
Dump ran (epyc10 unit oth-ubuntu-1271679-1795229027, exit 0; `fable-pd-s81-1840/{t4,t3}.json`). Section 1 mechanism is confirmed by position:
- t4: 683 cells named by the failed checks, 683 within 30 um outside the region box, 0 inside it, 0 elsewhere on the type. All 110 off-site cells are in that ring. 375 of the 683 have a `u_enc` net.
- t3: 638 cells, 638 in the ring, 0 inside, 0 elsewhere. All 171 off-site cells are in the ring. 410 have a `u_enc` net.
- The ring bins hold anonymous gates (`_N_`) and `wireN` buffers. Box + 10 um: row area 4,895 um2, movable 2,293 / 2,368 um2 (util 0.47 / 0.49), so it is exclusion from the box, not lack of area.
- No hard macro, blockage or PMA edge is near the failing cells (nearest macro edge: PMA RX at y 951 to 953, 61 um north of the box).
The detached waiter (section 6) will post one more RESULT-ADD with the same numbers when its queued client runs; it does not rerun the dump.

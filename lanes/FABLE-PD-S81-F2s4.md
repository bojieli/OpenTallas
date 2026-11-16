# FABLE-PD-S81-F2s4: r199 structural review of S81 plan event B6gF2s4 (2026-11-16 13:4x PST)

Plan: epyc10 /srv/opentallas-scratch2/claude/s81-b3-clk/ev/B6gF2s4.json, sha256 d3897871b8b535a3 (checked).
Base: ev/B6gF2s4strip4.json 4433a2c54ff8 (checked); reference ev/B6gF2s3.json 012db35daaea.
MEASURED = my reads of the three plan JSONs, the row files, the strip3 bound RTL and the bind tree. No render, no kit result.
At 21:40 UTC neither bind had a verdict: strip4 is in strict bind, F2s4 has finished elab (no error line) and is in G0. No BIND_RC / LATCHECK / G0_RC yet.

## Verdict: ADOPT-OK

No measured number fails a released type. Subject to DIE-S81-92's own gates on the F2s4 bind (BIND_RC 0, LATCHECK 873/873, G0 new 0 against strip4) and three conditions:

1. The six serdes generation+route holds stay. Adopting the START/reset rows does not release t1clfe / t15cla3d.
2. The published wave tree must carry d5bd6d74 (rrelay_nl depth parser) and 55b26f (ct_group_owned guard) before those two types are generated. Neither string (actual_rrelay_nl, ct_group_owned) is in the bind tree src_s81_pin_3c913dbdfb23_f2s3_mainref_d1 or in ovl_F2s4_strip.
3. Read the boot count from the F2s4 bind, not from strip4. 779 is a strip4 number (see section 3).

## What F2s4 changes against strip4 (MEASURED, whole-plan diff)

Top-level die, partitions, ports (2,330), lanes (873), latency, clock, reset, budgets: identical. Four types differ:

| type (instance) | key | change |
|---|---|---|
| ot_s81sl_leaf__t75 (s_1N_L1) | ft_slots ft1, ft3, ft5 | station sites only (regs_um, bit_sites_um) |
| ot_s81sl_leaf__t43 (s_4N_L1) | ft_slots ft5 | station sites only |
| serdes__t15__cla3d02796 (lk_EN0) | clock.landing_reader_start / writer_start / local_resets | new, depth 9 / 9, 5 + 5 branches, 5 reset leaves |
| serdes__t1__clfe1f0815 (lk_WN1) | same three keys | new, depth 9 / 9, 3 + 3 branches, 3 reset leaves |

ev/B6gF2s4_sidecar.json has the same size and time as the strip4 sidecar: it is the strip4 copy; the run writes sidecar_new.json.

## 1. strip4 seams, stages, pricing, boot

- Lanes F2s3 -> F2s4: 14 lanes change, sum 14,679 -> 14,715. 11 are the strip1 transport rows (+33), 3 are the +1 data lanes: coll__lk_WS0__s_0S_LP 50 -> 51, ctrl__s_0N_C__seqhost 77 -> 78, dn_s_2N_L0 27 -> 28. Matches the Codex ledger.
- The three depth changes are in the plan: serdes__t12 ft4 1 -> 2 (514 bits), slice_station__t8 ft4 3 -> 4 (571), dsdv_slice_c1x_C__t10 dn_s_2N_L0x1 2 -> 3 (597). No other ft slot changes depth.
- All 873 latency rows: cycles = natural + pad, pad >= 0. 225 lanes have lanes[].fixed_cycles != latency.fixed in all three plans (same set in F2s3): not from this event.
- Slot hops, same-bit site to site, all 1,128 slots: strip4 and F2s4 add no slot over 405 um. strip4 removes leaf t8 ft0 / ft1 (417.4 / 411.5); F2s4 removes leaf t75 ft1 (413.6 -> 321.8).
- 16 slots unchanged since F2s3 still read over 405 um on that measure: svc_hi t1 ft2 568.6, t5 ft0 572.4, t5 ft2 569.7, t6 ft8 622.1, svc_lo t6 ft2 406.6, leaf t14 ft0 443.3 / ft5 446.9, t23 / t62 / t67 ft0 439.0, t67 ft1 415.5, t72 ft1 411.5, t58 ft7 463.6, t75 ft0 442.8, t43 dn_s_4N_L0x1 418.2, dsdv_slice_c3x_C__t1 ft1 406.8. Station-centroid hops are <= 405 on all but svc_hi t1 ft2 (462.6) and c3x_C t1 ft1 (406.8). My pairing is by bit index; the lane tools may pair differently. Advisory, successor rows; svc is held anyway.
- NOT checked by me: die-level seam hops between parts (Codex 401.665 um on 47 changed slots), the reset tree (max release 154) and the 16 monitor relays. Those rest on the strip4 bind and LATCHECK.

## 2. Geometry

- Die 32,693.76 x 25,980.48 um, inside 33 x 26 mm. 398 partitions: 0 outside the die, 0 overlaps, 94.0 % of die area.
- t8 1,598.40 x 1,278.72 and t28 1,589.76 x 1,278.72, one instance each (s_0N_L1, s_2N_L1), abut s_1N_L1 without overlap.
- t43 / t75 rows: outline, faces, widths, windows, layers and station counts (8 / 7 / 8 / 8) unchanged. 0 duplicate bit sites, 0 sites outside the outline, 0 inside a hard-core rect. Station-to-station hop improves: t75 ft1 413.6 -> 321.8, ft3 361.3 -> 282.2, ft5 361.3 -> 205.2; t43 ft5 355.0 -> 233.5.

## 3. Serdes START/reset rows against FABLE-FIX-S81-SERDES

- No conflict of scope. The two types are identical in F2s3 and strip4 (0 differing keys), so rows derived on F2s3 apply unchanged. All 30 + 18 raw reset names exist in the strip3 bound RTL. Only lk_EN0 moves (X +449.28, rigid).
- Stage hops: max 317.6 um (t15 ft2_i, t1 ft1_i), 309.5 on the writer side. 0 stage sites outside the outline or inside a hard core.
- The rows fix the distance part only (the 2,104 / 2,009 ps data paths). The whole-form class (413 ps RX half-cycle skew, 553 ps reset-relay skew, 464 ps origin to reader_start skew) is clock cohort work. Each long branch crosses 8-9 reset/tap regions (rst_n_t15 -> t14 -> t13 ...), so every stage pair is a related-sink pair across tap trees. Without the cohort guard (55b26f) a CTS pilot on these rows will show the same skew class per hop. That is why condition 2 exists.
- Two same-site stage pairs: t15 reader ft1_i stages 2 / 3 at (2849.04, 456.636 / 456.637) and t1 reader ft0_i stages 2 / 3 at (2849.04, 340.128 / 340.127). Hop 0.0, then 68.9 / 95.1 on the stage before. Legal if the sites are anchors; a DPL overlap if they are fixed. Fix in the row generator, not a blocker.
- Reader stages end inside the landing bands (coll_i0 5 stages, ft0_i 2, ft1_i 2); band use is 0.48-0.50 against target 0.50. The area is a few um2; the bands are ring-ff FIRM, so the GEN must leave those sites free.
- Boot: the report prices reader boot +8 and writer +9 on these two types (K + W - R, pair K +1), and says cross-type straps and start-tree receipts regenerate in the next full bind. The 780 -> 779 ledger was made without these rows. UNMEASURED until the F2s4 bind reports.
- Bind risk: clock_landings.py in the bind tree accepts ot_dp_rrelay_nl at lines 1400 / 1477 / 2402 but not at 1406. If the bind stops with a landing_local_resets depth error on these two types, the cause is the missing d5bd parser: add that file to the overlay, do not drop the rows.

## 4. What the pilots and the corridor rows need

- Corridor rows (epyc2 fable-die-s81/ev/rows_corridor_F2s4b_on_strip4.json): all 54 die.channels equal the F2s4 plan, 0 rect_um added or changed, 0 overlaps with partitions. They are a no-op on F2s4; nothing to merge for F2s4b from that file.
- Col pilots: no col type changes in F2s4 against strip4. Reset-chain sites stay conditional on a pilot hop over 405 um.
- Svc pilots: svc_lo t6 ft2 stage 9 (277 sites, Y +21.6) is not in F2s4; svc_lo t6 ft2 reads 406.6 um here. It belongs in F2s4b with the 4 svc_hi slots above.
- Not in F2s4, by design: serdes relay / ready94 cohorts, t14 four type-local RRL edges over 405 um, serdes FT0 row (PENDING_G_CTS), native_e pin row.

## Not checked

Routed timing, hold, PG, the clock kit (R3), renders. G0 and LATCHECK results of either bind.

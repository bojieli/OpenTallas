# FABLE-PD-HEAD-NF15a: r199 review of HEAD plan event NF15a

2026-11-16 PST. Technical PD only, read-only, no build. MEASURED = I read the file or ran the check. REPORTED = lane post.
Reviewed: epyc7 `/srv/opentallas-scratch2/claude/fable-die-head/prep21z20NF15a/prep`, plan sha 88f7ab5a6f2e (MEASURED),
sidecar aef151594c56. Against NF15pg only `ot_s81hd_lep0N.sv` differs among the 26 published wrappers (MEASURED, cmp).

## Verdict: ADOPT-OK. The hd_lep0N hold can be lifted. Four advisories, none blocking.

## 1 Relay hops (MEASURED, `sb_audit.py --limit 405` rerun on the NF15a wrappers)

| hd_lep0N class | worst hop, NF14r | NF15a |
|---|---|---|
| status | 694.6 um | 377 um |
| start | under 405 | 324 um |
| reset of collect / start | 453.6 um | 288 um |
| raw relay | 494.4 | 494.4, 417.1 (placed), 434.3 x2 (estimated position) |

- The 694.6 and 453.6 um hops of the NF14 review are closed.
- **The two ring reset relays at 494.4 and 417.1 um are flops without a load.** `u_cland_rst_lepf_i0` and
  `u_cland_rst_coll_i3` both take `rst_rl_93` (`u_rrl_93`, depth 6, at (1755.0, 426.6)) and drive
  `cland_reset_lepf_i0` / `cland_reset_coll_i3`. Each of these nets appears twice in the wrapper: the wire and the
  relay output. Nothing reads them. Of the seven ring reset relays only `coll_i0` has a reader
  (`cland_start_raw`, 333.0 um). Synthesis removes the other six, so neither hop becomes a timed path.
- The composer's support ("four signed types carry the same form at 435-484 um") does not prove it. In the signed
  hd_tile (2dd0d8c9fd, intel1 `autopilot/closed/s81_head`) `u_rrl_27` is placed at (287.9, 703.9) but
  `u_cland_rst_i` is absent from `6_final.v`; `rst_rl_27` feeds only `u_rrl_28/29`. The signed layout never timed
  that hop. In the current wrappers hd_tile 448.0, hd_turn_a 443.0 and hd_spn ad_i 435.2 um do have a reader; hd_spn
  bd_i 483.5, hd_st_str 480.8 and hd_ctl_n 429.1 do not. Those are other types and not part of this event.
- Cheap cleanup for the next hd_lep0N row delta, 0 cycles: drive the two relays from a nearer depth-6 raw relay
  (`u_rrl_72` is 144.5 um from the coll_i3 pin, `u_rrl_26` 159.6 um from the lepf_i0 pin), or do not emit a ring
  reset relay that has no reader. The audit should skip relays without a load.
- 434.3 um x2 (`u_rst_in` / `u_run_in` -> `u_rrl_203` / `u_srl_203`) is an estimated position, unchanged from
  NF14r. Read it from the placed DB.

Gates (MEASURED from nf15a_gate and nf15a.chain.log): bind PASS (nested 7,157, 0 unbound), cohort 26/26,
LATCHECK 329/329 delta {}, G0 1 error / 230 warnings.

## 2 M1-M7 walls: gone (MEASURED on the plan)

| | NF14r / NF15pg | NF15a |
|---|---|---|
| hd_lep0N rects / area / longest side | 289 / 6,094 um2 / 292.7 um | 628 / 1,465 um2 / 2.16 um (all 2.16 x 1.08) |
| hd_mesh rects / area / longest side | 225 / 2,938 um2 / 47.0 um | 633 / 1,477 um2 / 2.16 um |
| largest group of touching rects | the walls | hd_lep0N 3 rects, 4.6 x 1.6 um; hd_mesh 7 rects, 3.8 x 2.2 um |
| rects on a hard core / outside the outline | 0 / 0 | 0 / 0 |

- East of `g_pp[3].u_pair` (the old 2.7 x 292.7 um wall, 648 pins behind it): 62 rects now cover 53.5 of the
  292.7 um of face (18 %), 4.4 % of the channel area to x 1756.62. The densest stack is 8-9 rects over 23.2 um
  with gaps of about 2 um. 185 of the 1,026 pins of that face have a 1.08 um island straight ahead within 20 um
  (pin match +/- 0.3 um, an upper bound); the other three pair cores have 62 to 150 per face.
- East of the rx_mem banks (old 2.7 x 98.3 um wall, 891 pins): 23 rects cover 19.4 of 98.3 um (20 %). Worst bank
  69 of 198 pins with an island ahead.
- Centre street (old 153.4 x 1.6 um strip): 13 rects cover 22.1 of 153.4 um. The whole N-S street x 846.72..967.68
  holds 91 rects, 0.15 % of its area.
- Sideband stage / anchor / reset points on a rect: 2 of 305 (12 within 1 um). My point list is 305, the NF14
  review counted 610, so compare the share: 5.7 % before, 0.7 % now.
- hd_mesh: worst SRAM face 41 of 106 pins with an island ahead within 20 um; no strip is left.
- Coverage: against the kit tree the rows were built from (`base/head/fdh_st/tree/kit/clock/tree.json`, sha
  c1cefe644d83, 45,100 sites) every die clock cell of the two types sits on a rect: hd_lep0N 628 of 628 (1
  instance), hd_mesh 734 of 734 (3 instances). The fine rects have no margin (cell size exactly).

## 3 Risk left: advisories

1. **Rows are keyed to the kit tree, not to the frozen file.** `prep21z20NF15a/die_clock/stamped_fdh_st.json`
   (7f09fd2e) holds 44,543 sites, 28,749 site names in common with the kit tree, 808 of those at another xy.
   Against that file alone 2 hd_lep0N and 62 hd_mesh cells are off a rect (0.16 to 37 um). Why the two differ I
   did not establish (la300 in the kit step is the likely source). Freeze the kit `tree.json` c1cefe64 with the
   die clock set, or show that the frozen inputs rebuild it bit-equal, before either type is routed.
2. **Rects in the N-face pin row, unchanged from NF15pg.** hd_lep0N: 3 rects 0.54 um from the N edge inside the
   coll_i0 / coll_o0 windows (514 / 512 pins, M5 + M7, 0.40 um pitch): about 5 pin positions under each M1-M7 rect,
   about 16 pins. hd_mesh: 4 rects, two of them touching the outline, about 21 pins of coll_ia / coll_oa (the old
   15.8 um strip there is now 4.3 um). No build has shown the pin access result. Read it at the first detailed
   route of each type; the fix is a pin skip at those positions or an M1-M4 cut for those 7 rects.
3. One M7 contract pin per type sits on a reserved rect (hd_lep0N `rst_start_raw_1` (859.1, 1107.0), hd_mesh
   `rst_start_raw_0` (588.0, 405.0)); 11 and 5 raw export points are on rects. Same in NF15pg. Check in the kit
   that the pin is cut out of the obstruction.
4. The two dead ring reset relays (section 1).

## Not done

No build, no timing run: hop lengths are geometry. The pin counts in 2 and 3 use plan pin files and window pitch,
not a placed DB. hd_ctl (status 437.1 um, estimated) and the other types in `audit405.tsv` are not part of this
event. hd_tile proof plan NF15t not reviewed.

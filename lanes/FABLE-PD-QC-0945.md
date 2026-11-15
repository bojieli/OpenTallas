# FABLE-PD-QC-0945: S4q3 / S4q3b against the QC failure classes, S4fw4b, sta_region masters

2026-11-15 10:3x PST (18:3x UTC), FABLE-PD-QC-0945. Technical PD and plan only. Read-only; nothing launched, stopped or changed.
Read: FABLE-PD-QC-0700, PD-QC-SUC-0800, PD-QCC-0740, FABLE-CLOSURE-STRATEGY levers 4 and 6, `failure_breakdown.py` (09:51),
QC `KIT-WAVE FAIL` 06:20-09:57, queue to line 14105, handoffs STRAP-MASTER-1115 and QC-PHYSERDES.

MEASURED = read or computed by me today from a plan json, bind report, bound RTL, placed report, placed dump or sign-off json.
REPLAY = `qc_fabric_transport.derive` (the bind's own code, the 0700 harness) on the bind's own `bus_groups.json` + derived table.
REPORTED = from a lane post or an earlier review. INFERENCE is marked.
Work dir: epyc9 and epyc8 `/srv/opentallas-scratch2/claude/fable-pd-qc-0945/` (`pdiff.py`, `fam.py`, `rd.py`, `wp.py`, `zl_*.out`).

State change during the review: DIE-QC-103 posted READY+ADOPT of S4q3b at 18:0x UTC (queue 14105). Sections 1-2 judge it as adopted.

Not available: no S4q2 kit is past placement (the kits are 2 h old), so there is no CTS, GRT or route report on the current
plan. Placed reports are ideal-clock. No kit exists on S4q3b or S4fw4b. I ran no STA.

## 0. Answers

1. **S4q3b is a 2-item delta and closes none of the six named classes.** MEASURED diff S4q2 -> S4q3b: 32 values
   (SKEW_N / SKEW_S on 16 `param_wrap` rows of the 4 st_a_v2 types) + `budgets.r_dly_spread = ["cbf_","cbn_","cbx_"]`.
   Nothing else. S4q3 differs from S4q3b in that one key only. No station row, no sidecar row, no phy field, no clock-site row.
2. **The st_a_v2 fix in S4q3b is half done and is now a functional hazard.** The 16 rows carry the bound parameters
   (9/10, 9/11) but still name the old masters `sta_region_nb0_h17_n6_s7`, `h18_n6_s7`, `h18_n6_s8`. Those three masters
   are signed and archived with depth 6/7 and 6/8. `hard_core_param.py` compares parameters, not the master name, so it
   reports 0 mismatches. The 4 parents were released at 18:0x UTC. The right masters exist and are signed (section 3).
3. **S4fw4b, the delta that does carry the su_c / fw / st_b rows, does not bind.** MEASURED `S4FW4BBQ` and `S4FW4BQ`
   bind_report: 1 error, `PARAM_REGEN W5: r_d of region 0 is not the latest`. It is the S4x error of 0700 section 2.1.
   LATCHECK 1921/1921 passes on it and hides this. Cause and fix in section 2.
4. **S4fw4b is built on S4q2, not on S4q3b.** It has the old 6/7 skew rows and no `r_dly_spread`. Adopted as built it
   undoes S4q3b.
5. **Two families are in no delta at all: sc (9 types) and fe (9 types).** MEASURED on S4q2 placed kits: slw_sc_v3
   -366 ps on a 771 um one-cycle hop; sle_fe_v1 has 7,686 zero-logic bits over 405 um. Section 4.
6. **The hc0 / hc1 / hc2 / su_l0 / su_l1 placed WNS of -47 to -225 ps is not a failure class.** It is the forwarded
   landing clock at placement (section 4.2). Do not open lanes on it.
7. **CORE-ROWS-1115 (COORD addition): no structural failure.** 15 of 16 builds are SIGNED after one hold ECO. The
   "13 NOT SIGNED" are the base verdicts before the ECO. Section 3.

## 1. Class by class

| class | in S4q3b | in S4fw4b | verdict |
|---|---|---|---|
| su_c one-cycle crossings (3 types) | nothing | rows of SUC-0800 section 3 on 3 types (18 / 18 / 9 station rows) | open until S4fw4b binds |
| fw one-cycle crossings (11 types) | nothing | sle_fw_v1 / v2 +48 rows each family, slw_fw 15 -> 75, 10 -> 50, 5 -> 22 | open until S4fw4b binds |
| st_b (11 types) | nothing | 3 rows per type | open; st_b logic path at -42 ps placed is not addressed by either (0700 2.3) |
| hc / st_a_v1 | nothing (byte-equal to S4q2) | nothing | no plan defect measured (section 4.2); st_a_v1 fails on kit inputs, not design |
| st_a_v2 (4 types) | params fixed, master name not | old rows (6/7) | wrong hardware by name (section 3) |
| cb (15 held types) | `r_dly_spread` list form, warn mode | not carried | partial (below) |
| slw_hc3 LEC, xl3 l3 read path | nothing; type RTL changed at S4q2 already | nothing | not a plan item; open until the S4q2 LEC reruns |
| phy_serdes, phy_serdes_b, phy_ucie_kv | nothing; QC-PHYSERDES fields not folded | nothing | flow error stays (section 5) |
| die clock-cell sites (strategy lever 1) | nothing | nothing | every QC type signed now re-keys once more |

cb detail (REPORTED, TYPE-QCCB-GEN and 0650): gate-mode proof on cbn_q11 took zero-logic hops over 405 um from 3,804 to
1,539; the pad chain and d-chain go to 0. The 1,539 left are ring -> `u_bin_bc_i*` -> `u_st` tap_d, whose fix was the
bc_i stations + sidecar of S4v / S4v2. S4v2 is dropped and S4q3b has the small sidecar (6.7 kB, against 25.6 kB in
S4fw4b). The 2 reset-relay hops of 1,411-1,466 um and the cbn_q11 CTS -861 ps have no named endpoint yet. S4q3b runs
the hook in warn mode, so a stage-count shortfall does not stop a cb kit.

## 2. S4fw4b PARAM_REGEN: cause and fix

MEASURED from the derived tables (`rd.py`, W5, same on all 12 slices):

| lane | S4q3b bound / landed | S4fw4b bound / landed |
|---|---|---|
| `st_a__x_st_a_ctl` (r_d, regions 0-3) | 7 / 20 | 9 / **20** |
| `st_a__x_st_a_fe` (nb_od, regions 0-3) | 18 / 18 | 20 / 20 |
| `st_b__x_st_b_ctl` (r_d, regions 4-7) | 8 / 8 | 8 / 8 |
| `st_b__x_st_b_fe` | 5 / 5 | 7 / 7 |
| `x_st_a_st_b` into regions 4-7 | +11 | +13 |

QC-FWST added +2 fixed_cycles on the st_a ctl return lane (0700 lever 3). The derive step then cut the R8 pad on that
lane from 13 to 11, so the landed depth stayed 20. Region 4 moved by +2, region 0 did not: the 0700 warning ("check
landed after the derive, not only fixed_cycles"). The fe lane has no pad and did move.

REPLAY on `S4FW4BB` with the landed depth of r_d regions 0-3 raised:

| r_d(0-3) landed | nb_od(0-3) | result |
|---|---|---|
| 20 (as built) | 20 | FAIL, same message as the bind |
| 21 | 20 | OK, RD_PAD {0, 12} |
| **22** | 20 | **OK, RD_PAD {0, 1, 13} (the S4p shape), SKEW_S 10..11, SKEW_N 9, HI_PAD {15, 16, 17, 28, 29, 30}, 218,768 flops** |
| 23 | 22 | OK, RD_PAD {0, 2, 14} |

Fix: keep the pad of the 12 `sl_*_st_a__x_st_a_ctl` members at 13 (landed 22) by pinning those members in the R8
table, as KV did for its 91 pad members. No more fixed_cycles; the nb_od lane needs nothing.

Two consequences:
- The bound st_a_v2 parameters in `S4FW4BBQ` (HI_PAD 0, SKEW 14 / 14) are the defaults of a failed regen. They are not
  a target. No master may be built or strapped to them.
- With the fix, SKEW_N / SKEW_S stay 9 / 10..11 but the HI_PAD set moves from {17, 18, 19, ..} to {15, 16, 17, ..}.
  INFERENCE: the st_a_v2 rows go from HI_PAD 17 / 18 to 15 / 16, so the fixed-depth masters signed today (section 3)
  are stale again after S4fw4b. Only the strap master with `strap_hi_pad` survives it.

Other S4fw4b facts (MEASURED): G0 did not run on S4fw4 or S4fw4b. Both logs end in `FileNotFoundError ...
tree7/.../sink_bins/hf1c/slw_su_c__cl19bb38ef.json`. The same file is the `KIT_NOT_SELF_CONTAINED` wave failure of
slw_su_c__cl19bb38ef (07:14-07:34). The S4q3b adoption post names no G0 run either.

## 3. sta_region masters (CORE-ROWS-1115) and the st_a_v2 rows

MEASURED on epyc9 `core-rows-1115/eco_*/eco_loop.json` and `i1/signoff/signoff.json`:

| set | builds | base verdict | after 1 hold ECO (margin 5) |
|---|---|---|---|
| n6_s7 / n6_s8 (S3R3 depth) | 3 | DRC 0, TT +13..+21, FF hold -2.7..-7.0 | 3 SIGNED |
| p = S4p depth (n8_s9, n8_s10), util 0.4 and 0.5 | 6 | DRC 0, TT +8..+19, FF -2.9..-6.9 | 6 SIGNED |
| q = S4q2 depth (h17_n9_s10, h18_n9_s10, h18_n9_s11) | 6 | DRC 0, TT +7..+20, FF -3.4..-5.6; q_h18b_u5 SIGNED at base (FF +0.26) | q_h17_u5, q_h18a_u4, q_h18a_u5, q_h18b_u4 SIGNED; **q_h17_u4 ECO failed** |
| `sta_region_strap_s2` (skew + HI_PAD straps), u4 and u5 | 2 | DRC 0, TT +9.7 / +11.0, FF -0.9 / -3.5 | 2 SIGNED (17:29, 17:37 UTC) |

- Shared cause of every NOT SIGNED base verdict: `min_hold_only` true on all 16, FF hold -0.9 to -7 ps on a few
  non-port endpoints, zero DRC, positive TT setup. This is risk R2 of QCC-0740 (SRAM clock branch + zero-logic pad
  stages). It is not utilisation: both 0.4 and 0.5 show it, and the spread between twins is within 3 ps. It is not the
  strap form: the strap masters have the smallest violation. One ECO closes it every time it routes.
- q_h17_u4: `[ERROR DRT-1231] Pin u_r.u_sks.g_out[1].u_v/q/RESETN does not have access point` in the ECO detail route
  (route_rc 2). One pin, after hold cells were placed beside the flop. Its twin q_h17_u5 is SIGNED, so nothing waits on it.
- Fix for the class (flow, CORE-ROWS-1115): keep "base build -> one automatic hold ECO" as the recipe and report the
  post-ECO verdict only. Build one twin with `HOLD_SLACK_MARGIN 25` in CTS when the next master is needed (untested).
  For the pin-access case, the ECO should keep hold buffers off the row sites next to a flop's RESETN / D pins or retry
  once with another buffer site.
- CORE-ROWS-1115 posted the same reading at 10:29 PST (queue 14137). Its table shows signed builds with a residual
  negative FF hold (for example p_h17_u4 -1.42 on 2 endpoints). Those builds carry the `io_hold_parent` check, so the
  residue should be port hold left to the parent; CORE-ROWS-1115 should state that per build, since hold >= 0 is a blocking gate.
- So all three S4q2-depth masters are signed (h17_n9_s10 = q_h17_u5; h18_n9_s10 = q_h18a_u4 / u5; h18_n9_s11 =
  q_h18b_u4 / u5), and the strap master is signed too.

The gap (MEASURED, plan `zz_s29_qc103_s4q3b.json`, 4 types, rows u_r0..u_r3):

| type | `module` in the row | params in the row | bound RTL `S4Q3BBQ` |
|---|---|---|---|
| sle_st_a_v2__pv4242de79 | sta_region_nb0_h17_n6_s7 | HI 17, N 9, S 10 | 17, 9, 10 |
| sle_st_a_v2__pv30dda31f | sta_region_nb0_h18_n6_s7 | HI 18, N 9, S 10 | 18, 9, 10 |
| slw_st_a_v2__cl9f076a5c, __clf4365a62 | sta_region_nb0_h18_n6_s8 | HI 18, N 9, S 11 | 18, 9, 11 |

`param_wrap.wrap_bound` matches the parameter text and writes `<module> inst (`. The text now matches, so the parent
netlist instantiates the n6 master, whose signed view exists under that name. Result if the kits build: 4 types (48
region instances) with 3 cycles too few on both skew lines, no check failing. I did not run a kit to prove the view is
picked; HCPARAM-ALL's built-parameter check reports "116 no built record" on QC, so it does not cover it.
Fix: one rows-only change, `module` (and `physical_master` if set) -> `sta_region_nb0_h17_n9_s10`, `h18_n9_s10`,
`h18_n9_s11`, with the view packs of the signed q builds registered on all hosts. Hold the 4 parents until then.

## 4. Families that fail again

### 4.1 Will fail on S4q3b as built (and on S4q2 today)

| family, types | mechanism | evidence (MEASURED unless marked) |
|---|---|---|
| su_c, 3 | one register feeds both side faces; no station rows in S4q3b | slw_su_c__cl19bb38ef a5 on S4q2 (epyc8, placed 17:57 UTC): WNS -835.8, TNS -552,232; path `procdff_60309_q[205]` -> `u_bout_x_su_l1_o`, 18 buffers. The wave launched it on S4q2 at 08:30 PST and again at 10:04 PST (attempt 6) against the QC-FWST hold |
| fw, 11 | 0 station rows on sle_fw_v1 / v2; slw_fw old 1-station rows | REPORTED 0700: sle_fw_v2 -467.6 placed, 7,097 hops over 405 um. S4q3b rows are byte-equal to S4q2 |
| st_b, 11 | 0 station rows | REPORTED 0700: 854 hops over 405 um, WNS -42.2 placed on S4k |
| sc, 9 (sle / slw sc_v1, v2, v3) | `u_bin_x_fe_i` -> hard core `u_core.dn_i` and `u_core` -> `u_bout_x_fe_o` cross the type in one cycle; the core clock is 156 ps early, which takes that much from the input path | slw_sc_v3 a10 on S4q2: clk-group WNS -366.5, TNS -504,931, 9 buffers. Dump: bin_x_fe_i -> core 47 bits 765 um; core -> bout_x_fe_o 48 bits 784 um; core -> bout_x_ctl_o 119 bits 496 um. sle_sc_v2 at CTS (S2, 11-14): -104.7, TNS -162,803, and core -> `u_bout_x_fe_o` -31.5. 0 `internal_stations` in S4q3b and in S4fw4b |
| fe, 9 (sle_fe_v1..v3, slw_fe_v1, v2) | pass-through and core-output buses cross the type; ring -> `u_bin` far | sle_fe_v1__cl1cbb7497 a12 on S4q2: 7,686 zero-logic bits over 405 um in the dump. `u_core.se` -> `u_bout_x_stm_p1_o` 544 bits, mean 757; `u_bin_x_stm_i` -> `u_bout_st_wo` 544 bits, mean 833; `u_core.se` -> `u_bout_x_stm_o` 517, 837; ring -> `u_bin_ard_wi` 512, 677; ring -> `u_bin_dd_wi` 449, 662; `u_bin_x_sc_i` -> `u_bout_sc_wo` 48, 1,034. 0 station rows in both plans. The placed clk group is still positive (+91), so this is the route-length risk of the 405 um rule (8-11 buffers per hop), not yet a measured timing failure |
| st_a_v2, 4 | wrong master by name | section 3 |
| cbn_q11, cbf_q11 (3 types) | ring -> u_bin -> tap_d hops not covered; reset-relay hops | REPORTED: 1,539 hops over 405 um left after the spread; CTS -861 ps unexplained |
| slw_hc3, 2 | LEC, not plan | REPORTED: 17 points x 3 xl3 leaves on the S3R form; the S4q2 form has new RTL and no LEC result yet. Last wave line for clccfc3e6b is a `plan geometry / site` place failure at 08:28 |
| phy_serdes x3 | hard wrapper needs a placed macro with LEF and TT/FF views | section 5 |

### 4.2 Not a failure class: placed WNS on the landing input groups

MEASURED on the 22 S4q2 placed kits (5 hosts): the WNS of hc0 (-119), hc1 (-136, -178), hc2 (-47), su_l0 (-85, -116), su_l1 (-153 to
-225), fe_v1 (-134) is in path groups `fclk_in_*`: input port -> `u_cland_*/u_ring` negative-edge capture at 416.5 ps
with a forwarded clock that has 0 insertion at placement. Control: slw_su_l0__cl1e5219ea and sle_su_l0__cl7a55c676
reached CTS on S4C today with WNS 0.00, TNS 0. In the `clk` group the same kits show hc1 -3.7 (xl1 logic, 28 stages),
slw_su_l0 -34.6 (station -> lane core), hc0 and hc2 no violation. The hc dumps have 37-193 long bits, all straps, reset
relays or single fault bits. So there is no plan defect on hc0 / hc1 / hc2 / su_l0 at placement; they should be left to route.
The placed TNS (-120 k to -350 k) should not be used to rank QC types before CTS.

### 4.3 Wave failures 06:20-09:57 (MEASURED from the log): no design class

274 lines. Pruned bind worktree sources (`treeA/... redstn2_gsafe.sv`, serdes `_bb.v`): 52. `count frame files not found:
feed_s29.json` and other gen tool refusals: about 130 (06:33 burst). `INFRA-VIEW-MISSING sle_cland_w517_n_s10_1` on sle_ctl: 18.
`prov_view` input not staged on st_a_v1: 17. `place RC=0, no 3_place.odb`: 17, and 17 more of the same quoted as
"plan geometry / site". `KIT_NOT_SELF_CONTAINED` (sink_bins of slw_su_c__cl19bb38ef; cland `signoff.json` of sle_ctl and
st_a_v1): 11. Missing S4P attempt RTL on sc / stm: 10. LEC: 1 (slw_hc3__cld86a7ad4). The one design line is the LEC.
The rest are kit inputs on the die-qc-103 trees; S4q3b changes none of them.

## 5. phy_serdes

MEASURED: S4q3b rows of phy_serdes / phy_serdes_b / phy_ucie_kv are those of S4q2 (phy_serdes_b still names
`ot_qfd_serdes_112g_x12_phy_s597`, no lef / lib / origin fields). The QC-PHYSERDES fields (approved 07:1x, handoff
`lanes/handoff/QC-PHYSERDES.md`: lef, lib, origin_um, the `_e` master for serdes_b, `local_reset_pins` for `phy_rst_i`)
are in no delta. The wave error stays `hard wrapper ... requires a placed macro with LEF and TT/FF views`.
Either the fields go into the next delta or the 3 types leave the wave count as hard IP (the COORD change in that handoff).

## 6. Fix list, ranked

| # | fix | owner | evidence | unblocks |
|---|---|---|---|---|
| 1 | Hold the 4 st_a_v2 parents. Rows-only delta on S4q3b: `module` -> the signed q masters (h17_n9_s10, h18_n9_s10, h18_n9_s11); register their view packs on all hosts; then release | DIE-QC-103 (rows), CORE-ROWS-1115 (views) | section 3 | 4 types; removes a silent 3-cycle error |
| 2 | S4fw4b: pin the R8 pad of the 12 `st_a__x_st_a_ctl` members at 13 (landed 22); rebind; read `bind_report.errors`, not LATCHECK | QC-FWST | section 2, replay OK | S4fw4b binds: su_c 3, fw 11, st_b 11 |
| 3 | Rebase S4fw4b onto S4q3b (carry `r_dly_spread` and the fix-1 rows) as S4q4; one bind chain with `bind_chain3.sh` | QC-FWST builds, DIE-QC-103 adopts | section 0 item 4 | no regression of S4q3b |
| 4 | S4q4 st_a_v2 rows: `sta_region_strap_s2` with strap ties from the bound RTL of the passing S4q4 bind (HI_PAD moves) | DIE-QC-103, HCPARAM-ALL (wrap_bound strap ties, branch param-wrap-straps-1115-2) | section 2, section 3 | 4 types on every later station event; no master rebuild |
| 5 | sc family, 9 types: station rows on `x_fe_i` (bin -> core, +2) and `x_fe_o`, `x_ctl_o` (core -> bout, +2 / +1), or move `u_core` to the middle of the x_fe run; list the family first from the slw_sc_v3 a10 dump | new lane (QC-SC-STN), rows into S4q4 if ready, else S4q5 | section 4.1 | 9 types |
| 6 | fe family, 9 types: rows on x_stm_o, x_stm_p1_o, st_wo, x_fw_p1_o, sc_wo, rd_wo, hr_wo; sidecar `u_bin` mid-hop for ard_wi, dd_wi, st_wi | QC-FWST after fix 2 (same generator), or the new lane of fix 5 | section 4.1 | 9 types |
| 7 | Placed-dump scan (`zl.py`, 580 um, non-strap groups) on every S4q2 placed kit now, table to DIE-QC-103; ignore `fclk_in_*` groups and `PIN:strap_*` rows | PLACED-SCAN-1115 | sections 4.1, 4.2; my 10 outputs are in `zl_*.out` | finds the next sc / fe before route |
| 8 | Stop slw_su_c__cl19bb38ef a5 / a6 on S4q2 and set the su_c hold key for all 3 types; copy `sink_bins/hf1c/slw_su_c__cl19bb38ef.json` into tree7 and the kit staging so G0 runs on S4q4 | KIT-OPS-5 (hold), DIE-QC-103 (file) | sections 2, 4.1 | frees the slot; G0 on the next delta |
| 9 | cb: bc_i stations + the large sidecar (S4v2 content) re-cut on S4q3b; switch the cb list to gate mode after the first cb kit passes the stage count | DIE-QC-103, TYPE-QCCB-GEN | section 1 | cbn_q11, cbf_q11; the other 12 cb types get the spread now |
| 10 | Clock-site reserve rows for QC into S4q4, before the 54 running types sign | CLKSITE-RESERVE-1115 | strategy lever 1; none posted | one re-key of all QC types avoided |
| 11 | phy fields of QC-PHYSERDES into S4q4, or drop the 3 PHY types from the wave | DIE-QC-103, KIT-OPS-5 | section 5 | 3 flow errors |
| 12 | slw_hc3: read the S4q2-form `lec.json` when it lands; open the l3 cone diff only if the 17 x 3 points return | DIE-QC-103 | queue 14042 | 2 types |
| 13 | Core masters: report post-ECO verdicts; `HOLD_SLACK_MARGIN 25` twin on the next master; ECO buffer sites off RESETN access | CORE-ROWS-1115 | section 3 | no false "NOT SIGNED" tables |

Order: 1 and 8 now (minutes). 2 + 3 next, one bind. 4 in the same bind if the strap ties are in `wrap_bound`, else the
q masters carry S4q3b and the strap rows follow. 5-7 in parallel.

## 7. Stop list

1. No kit of the 4 st_a_v2 types on the S4q3b rows as written (n6 master names).
2. No adoption of S4fw4 / S4fw4b as built: bind error 1, based on S4q2, st_a_v2 rows old.
3. No master and no strap tie at HI_PAD 0 / SKEW 14 / 14: those are the defaults of the failed regen.
4. No further fixed-depth sta_region masters (p, q or a new set for S4q4). The strap master is signed; q_h17_u4 needs no rerun.
5. No more fixed_cycles on the st_a ctl / fe return lanes; the pad is what must be held.
6. No su_c, fw or st_b launch on S4q2 or S4q3b; stop the running slw_su_c__cl19bb38ef attempt.
7. No lane, re-floor or ECO for hc0 / hc1 / hc2 / su_l0 / su_l1 from the placed WNS: it is the `fclk_in_*` groups before CTS.
8. No reading of LATCHECK PASS as "the delta binds": S4FW4BBQ passes LATCHECK with a PARAM_REGEN error.
9. No relaunch of sc or fe types as a fix; they need rows.
10. Still in force: 0700 stop list 1, 4, 5, 6 and the strategy stop list items 8, 10, 13.

## 8. Not verified

- That a parent kit really resolves the n6 view by name (section 3): read from `wrap_bound` behaviour as described in
  QCC-0740 and STRAP-MASTER-1115, and from the plan rows; no kit run.
- The HI_PAD values of the st_a_v2 rows after the S4fw4b fix: the replay gives the set, not the per-type value.
- sc and fe station counts: from box and dump distances of one type each (slw_sc_v3, sle_fe_v1__cl1cbb7497), no
  street or track check, no PARAM_REGEN replay of the lane bumps. sle_fe_v2 / v3, slw_fe and sle_sc_v1 dumps not read.
- cb numbers are TYPE-QCCB-GEN's and 0650's; no cb kit exists on S4q3b.
- The fw and st_b rows of S4fw4b were not re-checked for the slw_fw face error of 0700 2.2 (QC-FWST reports 0 hops over 405 um).
- tt_ctlm placed WNS -165 (TNS -62,508): group not identified.

# FABLE-PD-QC-SUC-0800 (11-15 07:4x PST): su_c boundary register far from its source

Scope: NEEDS-FABLE of KIT-OPS-6 (su_c vmr proof, slw_su_c__cl92142dac, epyc8). Technical PD only.
MEASURED = placed dump `geom.tsv` (3_place), bound RTL, plan json, CTS report. No STA or what-if run by me.
Tool: `zl.py GEOM LIMIT_UM N` (zero-logic links: flop / macro / pin -> buffers only -> flop / macro / pin, Manhattan length;
macro end = nearest point of its box, so macro lengths are lower bounds). Copies and outputs: epyc8 and epyc9
`/srv/opentallas-scratch2/claude/fable-pd-qc-suc-0800/` (`suc.out`, `suc580.out`, `others.out`).

## 0. Answers

1. **Why far:** one source register feeds two output buses on opposite faces. `g_u_suvm_procdff_60309_q[255:0]`
   (suvm_rp1.sv:54) drives `u_bout_x_su_l0_o` (E face, x 1221, y 110-270) and `u_bout_x_su_l1_o` (W face, x 5, y 123-283).
   The type is 1,226.88 um wide. The placer put the source at the E face (mean x 1194, y 167), beside its own drivers
   (`u_obs` 1156,368; `u_rabs` 1143,433). The W bus then runs 1,207 um mean (1,248 max) in one cycle: 22 buffers.
   The pin windows are right (su_l1 is the W neighbour, su_l0 the E one) and the bout flops are on their pins.
   It is not a placement anchor error. The cause is a missing plan row.
2. **The fix already exists on the east type and was not carried west.** `sle_su_c` has
   `internal_stations bus:x_su_l1_o`, 4 stations, hops 157 / 311 / 311 / 336 / 231 um (CODEX SU_OUTPUT_REACH 11-13),
   lane E `x_su_c_su_l1` fixed_cycles 8. Both `slw_su_c` types have no such row and lane W is 3. This holds in S3R (the proof
   kit plan has no internal_stations at all), S4p, S4q2 and S4fw3.
3. **Class size: the 3 su_c types only (12 instances): sle_su_c x6, slw_su_c__cl92142dac x5, slw_su_c__cl19bb38ef x1.**
   The 7 su_l0 / su_l1 types are clean (section 2). The two slw_su_c types are near-duplicates (G0 says so): one fix.
4. **x_su_l1_o is the worst bus, not the only one.** sle_su_c with the 4 stations still has CTS WNS -487.4 ps, TNS -138,878
   (S3R attempt_8, epyc9), worst path `u_suvm_u_su8 -> u_bout_x_su_l0_p1_o`. Fixing x_su_l1_o alone on slw moves it
   from -735 to about -490, not to sign-off. All output buses and two input buses of su_c need rows (section 3).
5. **Owner:** QC-FWST writes the rows into the S4fw3 line (it has the su re-site tooling); DIE-QC-103 binds, replays
   PARAM_REGEN and adopts. No su_c relaunch before that; the three types cannot close on any form or LEF today.

## 1. Measured, slw_su_c__cl92142dac (proof kit, 3_place)

Zero-logic links over 405 um: 7,037 bits in 636 groups; over 580 um: 3,453 bits. Wire rate from the worst path:
1,500 ps over 1,207 um = 1.24 ps/um, so about 580 um is what one 833 ps cycle carries; 405 um is the plan rule.

| source -> end | bits | over 580 um | mean / max um |
|---|---|---|---|
| procdff_60309 (Q) -> bout x_su_l1_o (W) | 255 | 255 | 1,207 / 1,248 |
| su8 core -> bout x_su_l0_o (E) | 510 | 510 | 892 / 945 |
| su8 core -> bout x_su_l1_o (W) | 511 | 0 | 499 / 553 |
| vm8out oa, ob -> bout x_su_l0_p1_o (E) | 256 | 256 | 917-1,009 / 1,215 |
| su8 core -> bout x_su_l0_p1_o (E) | 125 | 125 | 722 / 735 |
| vm8out oc -> bout x_su_l1_p1_o (W) | 128 | 81 | 662 / 898 |
| su8 core, red.orr -> bout x_ctl_o (N) | 91 | 91 | 911-1,095 / 1,099 |
| bin x_ctl_p1_i, x_ctl_p2_i (N) -> twb | 1,034 | 843 | 720-751 / 1,180 |
| twb -> core u_pg | 923 | 322 | 552 / 708 |
| bin x_su_l0_i, x_su_l0_p1_i (E) -> rda | 100 | 83 | 779-822 / 1,296 |

GRT repair has 473 failing endpoints, TNS about -100,000 ps: the Q and su8 output groups above.
Same picture on slw_su_c__cl19bb38ef (S2 attempt_6: 4,584 bits over 580) and on sle_su_c (3,226 bits over 580;
x_su_l1_o is no longer in the list, the other rows are as above: su8 -> x_su_l0_o 854 um, oa/ob -> x_su_l0_p1_o 1,003-1,009).

Structure behind it: the type holds the flattened `u_suvm` glue and 9 hard cores across 1.23 x 1.40 mm. Each glue stage
is one register for a bus that goes to both side faces or to cores 550 um apart (twb feeds u_pg at x 43-302 and u_bt at
x 838-1132). No siting can serve both ends in one cycle.

## 2. Other su types (newest placed dump each)

| type | dump | links over 405 / 580 um | what they are |
|---|---|---|---|
| slw_su_l1__clcc9d0155 | S3R a3 | 35 / 33 | count straps (static), 3 flt bits |
| sle_su_l1__clc6d66f5b | S3R a5 | 180 / 48 | count straps, 4 flt / epoch bits |
| slw_su_l0__cl76fb247e | S3R a5 | 33 / 21 | count straps only |
| sle_su_l0__cl086d85ba | S4C a3 | 38 / 26 | count straps only |
| slw_su_l0__cl1a1c1f8f | S4C a6 | 34 / 21 | count straps only |

Not in this class. The one real row is `u_bin_flt_su_c_i -> u_ist_flt_su_c_i` (1 bit, 717-1,020 um) on su_l1.
slw_su_l1__cla2a78701, sle_su_l1__cl5ea486db, sle_su_l0__cl7a55c676, slw_su_l0__cl1e5219ea: same generators as the
rows above, dumps not read. Other die families (fw, st_b, cb) are covered by PD-QC-0700 / 0300 and S4fw3; not re-scanned.

## 3. Fix: internal_stations rows on the 3 su_c types (one delta on S4fw3)

Form: the sle x_su_l1_o row (FIRM banks in the macro-free street y 315-346, payload + epoch, cycles in the lane
fixed_cycles). Stations sized for hops <= 405 um from the core box / source home to the face window.

| lane (su_c side) | bus | stations to add | fixed_cycles W | fixed_cycles E |
|---|---|---|---|---|
| x_su_c_su_l1 | x_su_l1_o | slw: copy the sle row (4) | 3 -> 8 | 8 (done) |
| x_su_c_su_l0 | x_su_l0_o | 2 (su8 E edge to E face about 910 um) | 3 -> 5 | 3 -> 5 |
| x_su_c_su_l0_p1 | x_su_l0_p1_o | 3 (core va to E face about 1,130 um) | 3 -> 6 | 3 -> 6 |
| x_su_c_su_l1_p1 | x_su_l1_p1_o | 2 (core vc to W face about 870 um) | 2 -> 4 | 2 -> 4 |
| x_su_c_ctl | x_ctl_o | 2 (su8 / red to N window about 1,100 um) | free +2 | free +2 |
| ctl x_ctl_su_c_p1 / p2 | x_ctl_p1_i, x_ctl_p2_i | W has 1 (hops 471-523, G0C warns): make 2; E has 0: make 2 | 3 -> 4 | 2 -> 4 |
| su_l0 x_su_l0_su_c / _p1 | x_su_l0_i, x_su_l0_p1_i | 1, on the 50 rda bits or the whole bus | 3 -> 4 | 3 -> 4 |

Cost: W +5 on one lane, +1 to +3 on seven more; E +2 to +3 on six. About 15 station banks per type, near 9,000 flops
(type has 408 k cells). Plus one generator anchor at 0 cycles: site `u_twb` at the mid-point between u_pg and u_bt
(x about 570) so that both branches are under 405 um; today it sits on u_bt.
The E / W lanes then have equal depth again (today E l1 is 8 and W is 3; W ctl_p1/p2 is 3 and E is 2).

Cheaper later option for x_su_l1_o, not for now: `u_rabs -> u_obs -> procdff_60309 -> bout` is four registers with no
logic, all within 300 um at the E face. A W-side copy of u_obs and procdff sited along the street would carry the Q bits
with 2 fewer added cycles (512 flops, RTL change, LEC by register duplication). Closure first: take the station form.

Checks that go with it (DIE-QC-103 / KIT-OPS-5):
- G0 does not see this class. S4q2 G0C reports only the two `x_ctl_p*_i` hops on slw_su_c, although `core_conns.json`
  declares `u_suvm_u_su8.gb -> bus:x_su_l0_o, bus:x_su_l1_o`. Glue sources have no plan site, so R3-INTERNAL has no
  length for them. Add the placed-dump scan (`zl.py`, 580 um, non-strap groups) to the post-place gate of every type:
  it costs 20 s and would have stopped this build at 3_place.
- sle_su_c S3R attempt_8 ended at `global_route.tcl 195 DRT-0073` (pin access), a separate flow error to triage.

## 4. Not checked
- PARAM_REGEN / latency groups for the new fixed_cycles: not replayed. The sle +5 on x_su_c_su_l1 bound in S4p, which
  suggests the lanes are padded elsewhere, but each row needs the `qc_fabric_transport` replay before the bind.
- Station counts are from box-to-window distances, not from a routed street plan; the y 315-346 street holds the sle
  x_su_l1_o banks already and its capacity for more banks is not measured.
- No timing run with the rows. The -490 estimate for "x_su_l1_o only" is the sle_su_c CTS result, not an slw run.
- The vmr LEF statement ("not the cause") is KIT-OPS-6's; I did not compare LEFs.

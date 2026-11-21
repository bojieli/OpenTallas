# FABLE-CLOSURE-STRATEGY 2026-11-20 17:35 PST (lane FABLE-CLOSURE-1730, the 17:30 round): the held S81 rows at -600 to -1,015 are fixes that are on main but not in the J5 source tree, plus landing-monitor pins that J5 moved up to 2,900 um from their monitor

Reviewer: FABLE-CLOSURE-1730 (Fable). Read-only: no job launched, cancelled or patched; no STA run, no DB opened.
Gate: DRC 0, routed TT >= -42 ps at 833 ps, internal FF hold >= 0, LEC, bind + LATCHECK. Hop cap 300 um. No die or outline growth. Nothing below is a new gate or hold.
Marking: **V** = I opened the file or ran the read this round. **R** = reported by the named lane. **I** = inferred. **P** = proposal.
Delta on 15:15. Its levers and stop list stand. Scripts: `scratchpad/r1730/ps.py` (worst path per group, buffer / gate / wire split), `mon.py`, `monc.py` (monitor seat against its pins), result `monc.tsv`.

## 0. Headline

1. **None of the held S81 rows at -600 to -1,015 is set by slew, a reset leg or a missing lockup (V).** They are three other mechanisms (section 1): a proven RTL fix that the pinned J5 source tree does not carry (seqhost; lepe / lepw LP), landing-monitor pins that J5 placed far from the monitor (iqf, slice_station t36, seqhost second group), and one form S start leg (slice_station t6).
2. **J5 regression, new (V): the `cland_dn_ready_* / cland_dn_fault_*` pins are no longer at their monitor.** slice_station t36: pin (1329, 1224), monitor seat (31, 465), 2,057 um; the same type on event 3fa87b84b18 has 31 um. Of 79 J5 types with a monitor and a generated kit, 29 are over 300 um and 17 over 500 um. Most of these have not reached place yet and will be held the same way.
3. **The family lever after slew, reset and lockup is adoption, not a new construction rule.** What is proven on main is not what the wave builds: S81 source pin 3c913dbdfb23 (hwin file dated 11-16), KV tools 413 commits behind main, HEAD 904 behind (R, TOOLS-LAG posts 16:30). Each event has to carry the proven source and re-pin tools.
4. **KV hub_Eo (-747) is a class neither reset tool covers (V):** a reset forward from a face register into a hard-core reset pin. `reset_leg_plan` skips macro sinks since 73717f6992; `fwd_reach` checks declared stations only.

## 1. What sets the worst path on each held row

Source (V): `3_detailed_place.rpt` of each held kit, placed, ideal clock, worst path per group. Delay split = buffers / logic gates / wire, in ps.

| Kit (event) | WNS | Worst path | Split | Mechanism |
|---|---|---|---|---|
| S81 seqhost t1 (J5) | -1,015, TNS -2.0 M | `u_win.pe[4][1]` -> `u_win.mu_c[22]` | 19 buf 669 / 19 gates 986 / wire 166; no slew over 163 | logic depth in `dsdv_mu_hwin`. A |
| same, second group | -625 | port `cland_dn_ready_1` -> `u_cland_monitor_1/u_ring.s_d` | 13 buf 604 / 1 gate / wire 463 | monitor pin 1,726 um from seat. B |
| S81 iqf t1 (J5) | -1,040 (`fclk_in_cland_dn_0`), -730 (`clk`) | port `cland_dn_fault_0` -> `u_cland_monitor_0 ... u_wcc/m`; `u_rrl_17_t` -> `u_cland_monitor_0/align_c` | 17 buf 817 / wire 624; 16 buf 790 / wire 636 | monitor pin 2,337 um from seat. B |
| S81 slice_station t36 (J5) | -766, -724 | port `cland_dn_fault_0` -> monitor ring; `u_rrl_268_t` -> monitor `oh[3]` | 15 buf 718 / wire 553; 14 buf 693 / wire 563 | monitor pin 2,057 um from seat. B |
| S81 slice_station t6 (J5) | -424 | `u_rrl_168` -> `cland_fstart_ft3_o` | 11 buf 561 / wire 520 | form S of 15:15; no monitor in this type |
| S81 lepe_mu_LP t2, lepe_nh_mus_LP t1, lepw_mu_LP t2 (J5) | -590, -630, -660; TNS -197 k to -505 k | SRAM `g_rx[1] ... u_rx_mem.g_bank[*].u_m/rd_out` -> `u_u_lep.u.rid[*]` | 13 to 14 buf 641 to 675 / SRAM + 4 gates 418 to 424 / wire 338 to 383 | unregistered memory read fanned over the type (rid class). A |
| KV hub_Eo a3 (D25e3) | -747 | `u_bin_i_host_die_rst_n/q` -> core `u_astk_EN` pin `g_phys_fault_u_fault__rst_n[0]` | 23 buf 844 / wire 442 | reset forward into a hard-core pin, no stage. C |
| KV hub_Wo a9 | -1,040 | `u_bin_i_astk_WN ... ep_zo/eq` -> `u_u_efault.fault` | 37 buf 1,143 / wire 539 | efault one-cycle reduce (PD-KV-1500) |
| KV sys_c a7 | -987 | `u_bin_i_serdes_E_tx_up/q` -> `u_bout_o_dcal_dob/q[2]` | 29 buf 1,094 / wire 642 | L356 stations on the wrong bus (KV-PLAN-R2) |
| QC sle_ctl padE0 a3 (A4) | -528 | `u_lpad_x_fw_p2_i.q[74]` -> core `u_u_ctl/cmd_q[108]` | 8 buf 403 / wire 382; one wire 117 ps at slew 371 | pad to core pin distance; `u_ctl` move (PD-QC) |

**A. Source lag (seqhost, lepe / lepw LP).**
- seqhost. The path is the same on three events: D8i attempt 16 -900, b05c -969 (CTS -946), J5 -1,015 (V). Floorplan WNS with zero wire is already -218 (V), so no placement, slew or relay row closes it. The fix exists: main 8e20268b5d83 (11-19, FABLE-FIX-S81-SEQHOST), a 0-cycle restructure of `dsdv_mu_hwin` with `keep_hierarchy`; gate depth into u_win flops 30 -> 13, u_win ends under 0 at CTS 4,895 -> 778 (R). The J5 tree file `kw45/src_s81_pin_3c913dbdfb23_d8j5_1117_work/rtl/dsrom_sys/s81_dv/unit/dsdv_mu_hwin.sv` is dated 11-16, sha1 c312e4ec, with 0 `keep_hierarchy` (V, epyc8 and epyc9; same sha in the J5 kit `rtl/`). What stays after adoption (R): mu_c 134 ends at -997 and mu_rc 43 at -966, a reach class with a row in `FABLE-FIX-S81-SEQHOST-reach-row.json` (+2 / +1 source stations, mu_c / mu_rc seated at the core).
- lepe / lepw LP. The reset proof moved the reset path to +212 and left WNS at -652 because this path was always the kit WNS. It is the rid class that RIP1 removed in proof6 (post-CTS -530 -> -404, R). The J5 kit `rtl/ot_s81sl_slice_lep.sv` has the `OT_S81SL_LEP_RIP1` branch and no define in `config.mk` (V). This is the owner rule "registered memory reads" not applied; leaf SRAMREG (0 of 75 types in the J5 base, R) is the same lever.

**B. Landing-monitor pins (J5).** `landing_placement.tcl` seats `u_cland_monitor_N` FIRM where it sat before; `io.tcl` places the pins from `landing_contract.pins[].xy_um` (`landing_contract.io_tcl`, V). On J5 the two disagree:

| Type | Monitor seat | `cland_dn_fault` pin | Manhattan um |
|---|---|---|---|
| slice_station t36, event 3fa87b84b18 | (31, 465) | (2, 467) | 31 |
| slice_station t36, J5 | (31, 465) | (1329, 1224) | 2,057 |
| iqf t1, J5 | (185, 31) | (1329, 1224) | 2,337 |
| seqhost t1, J5 | (185, 31) / (906, 31) | (848, 3) / (1441, 1224) | 692 / 1,728 |

- Census (V, `monc.py` on the newest gen dir of every J5 item on six hosts): 79 types with a monitor, 29 over 300 um, 17 over 500 um: svc_hi pvso_entry t1 / t2 2,901 / 2,904; svc_hi svc_rs t5 2,877; c1x_C t4 2,361; iqf t1 and lepw_mu_C t1 2,337; slice_station t36 2,057; seqhost 1,728; kv_leaf t2 1,610; slice_station t18 1,251; c1x_C t10 and col_h10_r1 pv69c7e9a6 1,163; c1x_C t1 895; serdes t3 619; svc_rs t2 529; col_h10_r2 cl8b686b3e 513. Between 300 and 500: leaf t7, c1x_C t3 / t5, iq_C t1, kv512_C t1, kv_leaf t3 / t4 / t5, gunit, col_h9_r0_p4 x2, col_h10_r2 clac068e56, lepw_mus_C t1.
- Cause (I): J5 is the existing-clock form with no `start_tree.provider`; its bind was accepted with 84 `cland_mon_*` hops up to 5,005 um and 0 relays (R, S81-DIE-R4 12:05). The pin went to the new die-side source edge and the seat did not follow. Two types share the exact pin (1329, 1224).
- The forwarded clock of the ring enters at the same pin, so part of the port-path number returns after CTS. The `u_rrl -> monitor` paths at -724 / -730 in group `clk` do not.
- Fix (P): one rule in the landing contract: a monitor and its `cland_dn_*` pins are one site. Seat the monitor ring at the pin (the old form), and let J6 item 9 (die reset + monitor relays, e9af887233) deliver the hop on the die side. Where the monitor must stay (it also reads local taps), add in-kit stages on the two scalar pins and the forwarded clock at 300 um; scalar bits, flops in the tens.
- First check, no build: `monc.py` on the J6 private bind kits. 0 types over 300 um.

**C. Reset forward into a hard-core pin (KV hub_Eo; also lepe land D > 4).** `u_bin_i_host_die_rst_n` is a data lane ending on a core reset pin about 1,400 um away (23 buffers). Form R re-taps soft sub-instances and now skips macros; the right row for a macro reset pin is the KIT-RD-1 sink `relay_depth` (D = ceil(L / 300) - 1) that form L already writes for `u_u_land.rst_n`. The schema cap of 4 is too low: lepe nh_mus land needs 337 um per hop at D 4 (R).

Side reading: on KV hub_Wo / hub_Eo / sys_c 15 to 30 `fclk_in_*` groups sit at -42 to -242 with 5 to 7 gates and 1 to 3 buffers (V). That is the ideal-clock reading of a landing input (PD-KV-1500 section 3), not a path class. Sort held rows on the `clk` and `asynchronous` groups, or on buffer count.

## 2. Next family lever

1. **Adoption per event (new).** S81 J6: `dsdv_mu_hwin.sv` at 8e20268b5d83 with `native_hwin_calendar.py`; `OT_S81SL_LEP_RIP1` + rows 1 to 4 on the four LP lep types; SRAMREG into the base. KV D27 and the next HEAD event: tools re-pin after a proof gen (r708 missing on both, R). Check per event: one diff of the event tree against main for every file named in a FIX lane's PUSHED post since the pin.
2. **Landing infrastructure pins at their consumer** (section 1 B).
3. **Reset generator completed:** macro reset pins by sink `relay_depth`; cap 4 -> 8 for reset sink rows; `--stage-sites` default if lepe r2 confirms (r1 bunched k0_1..3 at one spot, R); split of replicated relays with copy radius over 300 um (lepe `g_reset_balanced`, 454 / 687 um, R). After slew, the worst path of leaf t60 (CTS -493, `lpad_leafdn -> crr_vsw / vp rr.rst_n`) and QC cbf (-296, `rrl_500`) is this class (R, CORE-LIB-LIMITS 17:05).
4. Lockup stays third: no J6 lockup row before proof2 (latches on the launch flop's leaf, ends-only) shows an "after" line. At my read proof2 was at place, WNS -305 (V).

## 3. Rows per event

- **J6 (S81, cut 11-21 13:00), in this order:** 1 source adoption: hwin + seqhost reach row; RIP1 + lepe rows 1 to 4; reset rows from the tool, not hand item 6 (5 types at -590 to -1,015 cannot sign without it). 2 monitor pin rule with item 9 (29 types). 3 col masters routed with the latch on the launch leaf (120 types). 4 leaf: reset-leg rows from the tool on every leaf type (t60's worst after slew), SRAMREG, per-lane spread rows; the leaf class floorplan only if its strict bind is 0 by the cut, else J7. 5 slice C finish leg D = 3 and taps (11 types). 6 slice_station / col `u_rrl -> cland_fstart` stages (form S).
- **V1 (QC, cut 09:30):** 1 fabric strict 0 (q3: TYPE_SPLIT x4, SC_X3 open). 2 `reset.inst_taps` on every cb* type from main >= 73717f6992 (drop the `u_t30` row). 3 st_a `rs_s0` / `rs_s1` on one occupancy map (11 types, a global-place stop). 4 sle_ctl `u_ctl` move, and a sink `relay_depth` D 1 on `x_fw_p2 -> u_ctl/cmd_q` if the moved estimate stays under -42. 5 pad hoist + merged-class rows (ph6). 6 su_c `x_sc_o` 3 stations.
- **D27 (KV, cut 11-21 20:00):** 1 efault staged form (4459f7ee18; 29 types). 2 sys_c: stations on `o_dcal_dob[2]` at 300 um, and the six 405-era rows re-sited. 3 core reset pin rows on hub_Eo / hub_Wo `host.*` forwards (section 1 C) + `reset.inst_taps` on pv / sys_c / hub_Wo. 4 pv: pad depth on the owner-response lines, see lever 6. 5 hgi_v1 collector leg stage. 6 tools re-pin; hub_C view re-freeze.

## 4. Levers, ranked by impact

| # | Lever | Evidence | Root cause | Fix | Owner |
|---|---|---|---|---|---|
| 1 | Adopt proven source into J6 | seqhost -1,015 on 3 events, zero-wire -218; lepe x3 -590 to -660; J5 tree hwin sha c312e4ec of 11-16; RIP1 define absent (V) | wave tree is pinned; a push to main reaches no kit until an event takes it | section 2 item 1; diff check per event | S81-DIE-R4 (J6), with OPUS-FIX-S81-LEPE |
| 2 | Monitor pins at the monitor | 29 of 79 J5 types over 300 um, 17 over 500; t36 31 -> 2,057 um; -625 to -1,040 at place (V) | J5 existing-clock form moved the pin, seat unchanged | section 1 B; `monc.py` check on the J6 bind | S81-DIE-R4 + RESET-RELAY-GEN successor (`reach_relay_plan`, landing contract) |
| 3 | Reset generator: macro pins, cap 8, stage sites, relay split | hub_Eo -747 (V); lepe land 337 um / hop at D 4; t60 CTS -493, cbf -296 after slew (R) | macro sinks skipped; cap 4; `relay_mid` does not spread | section 2 item 3 | RESET-RELAY-GEN-1530 successor; rows to the three die owners |
| 4 | S81 col masters | 120 types on 2 builds, none routed (R) | synth host admission; latch form not yet proven | route both on the launch-leaf latch form after proof2 | S81-DIE-R4, LOCKUP-STATION-1130 |
| 5 | KV D27 status and forward stages | hub_Wo -1,040, sys_c -987, hub_Eo -747 (V); efault form and hop check on main (R) | one-cycle die-crossing wires | section 3 D27 rows 1 to 3 | KV-PLAN-R2 |
| 6 | KV pv pad depth | v8p `dly_spread` max hop 1,485 -> 1,228 um, chains over 300 um 7,163 -> 5,807, fail 32 (R, watcher 16:20) | `pad_min_stations` cuts segments, it adds no stages: D 7 to 11 over 3.1 to 3.6 mm is 330 to 510 um per stage (I) | raise D on the astk owner-response and vport pad lines to ceil(L / 300), +cycles; first name the 1,228 um chain and its D | FABLE-FIX-KV-PV-R2 -> KV-PLAN-R2 |
| 7 | HEAD hd_lep0N: price the 56 default taps on the r14 form | 56 of 251 tap ports at default [-169.8, 0], 16,035 sinks; cross-tap flop ends 13,428 -> 2,171 without the modelled window (R); tr1 insertion 2,365 ps (R) | kit SDC window, not the tree | build with the 56 taps priced and core taps at pin + 553; tr2 root trunk only as second arm | FABLE-FIX-HEAD-LEP0N, HEAD-R14 |
| 8 | QC V1 fabric + st_a + sle_ctl | 11 st_a global-place stops; sle_ctl -428 to -528 (V) | PD-QC-1600 | section 3 V1 | QC-PLAN-R5, UNIFY-TOOLS-R3 |

## 5. Stop list (15:15 stands; plus)

- No route, repair, retry or new row on the J5 seqhost and lepe / lepw LP kits. Their source cannot meet -42 (seqhost fails at zero wire).
- No new RTL work on `dsdv_mu_hwin`, and no station row for u_win, before the 8e20268b5d83 form is in the tree and read.
- No slew, reset-leg or lockup reading of iqf, slice_station t36 or any of the 29 types before the monitor pin distance is read. No relaunch from place of those types "for the slew limit".
- No ranking of held rows by an `fclk_in_*` group at place unless the path has 10 or more buffers.
- No hand reset row (lepe item 6); no re-tap of a macro reset pin by its centre; no reset sink row silently cut at D 4.
- No J6 lockup row before the proof2 "after" line; no col master route on the midpoint latch.
- No D27 pv row from `pad_min_stations` alone; v8p still has 5,807 chains over 300 um.
- No HEAD sign-off on a 2.4 ns root insertion.
- No FIX lane counted as landed on its PUSHED post. Landed means the event tree file matches.

## 6. Not checked

- Whether main HEAD still carries the 8e20268b5d83 hwin form (I read the J5 tree and kit only), and its GRT TT: kit2 / kit3 were never read after CTS.
- Who placed the J5 monitor pins and whether J6 item 9 (e9af887233) already moves them: the cause in 1 B is inferred from two files and the bind note. The census read one gen dir per item; 45 items have no monitor or no gen dir on the six hosts.
- How much of the port-to-monitor number returns after CTS. No J5 kit with a far pin has a CTS report.
- All paths are placed, ideal clock, worst per group. End counts per class were not read; TNS is the only size measure.
- kv512_C t1 (-997 at place, in the census) and lepw_mus_LP t2: path not read.
- hub_Eo: whether the core registers `rst_n` internally. The pv arithmetic in lever 6 and the 1,228 um chain: not read from the kit.
- reset r2 proofs (cbx, lepe) had no place report at 17:2x; pv r1 pending. HEAD lever 7 is taken from the lane's own census, no build exists.
- KV D26 R3c gate, QC q3, t7 GRT iteration 10, leaf class floorplan: no result when read.

# FABLE-CLOSURE-STRATEGY 2026-11-20 15:35 PST (lane FABLE-CLOSURE-1515, the 15:15 round): a late reset or start leg is the worst placed path class on three dies; the lockup proof moved the port classes through the clock taps; two proofs that later rows wait on are not running

Reviewer: FABLE-CLOSURE-1515 (Fable). Read-only: no job launched, cancelled or patched; no STA run, no DB opened.
Gate: DRC 0, routed TT >= -42 ps at 833 ps, internal FF hold >= 0, LEC, bind + LATCHECK. Hop cap 300 um. No die or outline growth. Nothing below is a new gate or hold.
Marking: **V** = I opened the file or ran the read this round. **R** = reported by the named lane. **I** = inferred. **P** = proposal.
Delta on 13:25, FABLE-PD-KV-1500 and FABLE-FLOW-1400. Their levers and stop lists stand.

## 0. Headline

1. **Question (a): yes, it is a family, and it is wider than "reset flop at the port" (V).** I read the worst path per group of every `3_detailed_place.rpt` written in the last 3 days on six hosts (scan `scratchpad/r1515/rs.py`). 207 kit builds have a negative path that starts at a reset relay or ends on a reset pin. On the current or recent events: QC A4 10 of 11 kits read are under -42 (8 under -300); S81 D8i / b05c / J5 28 of 31 kit builds on the relay form (19 under -300, the kit WNS on 19); KV D25e3 5 of 5, the three pv kits under -300 (section 1).
2. **Question (b): the port_out rise is a clock-tap effect, not new paths (I from V numbers).** On the t39 proof the port_in worst end also moved, -33.5 -> -128.3, with no latch on any port path; same_tap rose 41 -> 238; setup before repair fell -354.6 -> -471.2. The latches add about 24,400 instances (+8.2 %), each a clock sink on a launch tap (section 2).
3. **Two proofs that J6 rows wait on are not running (V).** lepe proof7 (`epyc9 fable-lepe/opus-p7/run.log`) ended exit 2 at 23:55 PST on 11-19 on a missing `s81/plan_h2_2249.json`; no lepe container is up; the handoff calls it queued. The slew-limit proofs `core-lib-limits-1330/proof/{t60,cbf}` have no run directory 1.5 h after launch.
4. **No new-plan type signs off tonight on any die.** Tonight's count is the residual hold pass and old-plan base routes, as at 11:20 (section 3).

## 1. (a) Reset and start legs: one family, three forms

Source (V): scan above; one worst path per path group and kit, placed, ideal clock. So the counts are lower bounds and the values are before CTS.

| Form | Path | Where (kits under -42 / read; worst) |
|---|---|---|
| L. Module-local relay outside the kit reset tree | `ot_rst_relay u_rstr` / `u_rr`, `g_rsreg.rq`, `u_vport.rst_q` to or from its module | S81 lepe_nh_mus_LP `u_u_land.u_rstr` -456 and -620 (22 to 25 buffers); lepe_mu_LP proof6 -348.5 after GRT (R); S81 leaf `lpad_leafdn_i0.q[0]` -> `u_vp.u_rr.rst_n` 16 / 28, -511 (14 buffers); bk_sel `g_rsreg.rq` -740; col_h9_r0 / col_h10 `g_rsreg.rq` 5 / 5, -84 to -119; KV pv `u_vport.rst_q` -1,015 (D23H) |
| R. Kit relay `u_rrl_*` to a sink more than one hop away | to `u_bin_*.eq` face ranks, fab `u_st.g_seg` counters, `u_xg.u_r` | QC A4 cbx / cbn / cbf 9 / 9, -293 to -1,746, 17 to 36 buffers; KV D25e3 pv_v2 -2,218, pv_v2n -2,145, sys_c -242, hub_Wo -120; S81 gunit -1,107, c1x_C -473, iq_C -396, kv512_C -318 |
| S. Kit relay to a clock-landing start or monitor flop | `u_rrl_*` -> `cland_fstart_*`, `cland_monitor/u_ring` | S81 leaf 4 / 5, -982; iqf -388; col_h9_r0 7 / 7, -167; slice_station -353 to -543 on earlier events; J5 slice_station t36 -724 (monitor ring, the kit's second worst), t6 -424 |

Reading.
- Form L root cause (V for the script, I for the placement). `reset_taps.tcl` seats one synchroniser per clock tap and re-points FIRM flops only; its header says leaf flops keep their RTL synchroniser. A module-local relay is in no tree row and has no site. It is a short flop chain between a 2-pin net from the kit tap and one wide net to its module, so wirelength is the same wherever the long leg falls. On lepe it fell after the relay (the relay sits at (1430.9, 8.1), 1,300 um from land); on leaf it fell before `u_rr`. 397 RTL files mention `ot_rst_relay*` (V, grep; tests and copies included), 76 of them under `s81_dv` and `s81_ph`.
- Form R is the 300 um reset rule applied to relay-to-relay hops only. The last leg, relay to sink, is not counted. QC A4 carries the 300 um reset tree and still shows 17 to 36 buffers on that leg.
- Form S is not a predictor on slice_station: that family signed off on old plans with -353 to -543 at place (ideal clock on a forwarded-clock flop). It is real where the buffer count is high (leaf t72 / t8 / t56, 13 to 26 buffers, 13:25 class C).
- The lepe / lepw LP rows `u_rrl -> u_u_ln3` at -979 to -1,939 with 0 to 1 buffers are the unbuffered core-pin class of 13:25, not this family. KIT-RD-1 covers them.

**Generator-level fix (P). Owner: the relay-tool helper under S81-DIE-R4 (`reach_relay_plan.py`, J6 item 9), used unchanged by QC-PLAN-R5 and KV-PLAN-R2.** One rule: every reset or start sink has a position, and the leg into it is a hop.
1. Sink list from the bound netlist, not from tap ids: FIRM face ranks (`u_bin_*`, `cland_fstart_*`, monitors; XY known from `face_flops.tcl` / `landing_placement.tcl`), hard-core reset pins (LEF pin XY; KIT-RD-1 does this), and every module-local relay instance (`ot_rst_relay*`, `g_rsreg`, `rst_q`), found by module name.
2. A local relay's last stage is seated FIRM at the centroid of its fanout, from the newest placed kit (`placed_scan.json`) or else the module's region rect. It goes into `reset_taps.tcl` before global place. For lepe that is item 6 as OPUS-FIX-S81-LEPE wrote it by hand.
3. Leg from the nearest kit relay to each sink over 300 um: add `relay_depth` stages on that sink (`kit_relay_depth.py`), pitch <= 300 um, and pad every sink of the type to the same depth so release stays one cycle. +cycles of reset latency only; `rst_n` already holds 64 clocks.
4. A local relay whose fanout box is over 300 um half-perimeter gets `REGIONS` raised and split by placed quadrant. The parameter exists.
5. PRECHECK prints the legs over 300 um per type from plan and pin XY. Estimator only.

First check: run steps 1 and 5 on QC cbx_q10 (A4) and S81 leaf t60. The list must name `u_rrl_424 -> u_st.g_seg` and `lpad_leafdn_i0 -> u_vp.u_rr`. No build needed.

## 2. (b) Port classes after the lockup pass

t39, before the pre-GRT repair (V, `pregrt_ff_hold.log` of both builds):

| | baseline D8i | proof (131 RTL latch arrays, 28,323 bits, + 1,583 netlist latches) |
|---|---|---|
| instances | 296,538 | 320,974 |
| hold ends | 17,372 | 7,181 |
| cross_tap | 14,281, worst -275.3 | 3,221, worst -289.9 |
| port_out | 1,884, worst -152.8 | 2,513, worst -117.6 |
| port_in | 1,167, worst -33.5 | 1,210, worst -128.3 |
| same_tap | 41, worst -43.8 | 238, worst -97.2 |
| TT setup before repair | -354.6 | -471.2 |

- Contract in both: `in_min` -40, `out_min` 68, vclk latency 364.5, tap window 208 (V). A port end is the face flop's tap arrival against a fixed virtual clock. Port counts moved in both directions and same_tap rose, so tap arrivals moved. The proof's repair "after" line was not written at 15:15 (repair started 13:38).
- Cause (I): each latch is a clock sink on its launch tap. 24,000 to 30,000 more clock pins on 56 taps were not in the sink counts the tap rows were solved for.
- The remaining 3,221 cross_tap ends have a worse worst end than before. Which pairs they are was not read.

**Structural fix (P), in this order. Owner LOCKUP-STATION-1130 for 1 to 3; die owners for 4.**
1. Solve the tap rows after the lockup spec, with latch clock pins counted (`tap_resolve`, cap 1,000, span 300 um, S81-SLICEC-R3 38cdd37cec9d). This is 11:20 section 1.4 with the latches included.
2. Each latch on the same tap leaf as its launch flop and seated next to it. A latch at the hop midpoint (the J6 col master form) takes whichever tap is nearest there.
3. Prefer the netlist form on the ends that violate (`OT_PREGRT_OPEN_BEFORE=1`, `derive --hold-ends`) over the RTL register form on every pair. The baseline has 14,281 violating cross-tap ends on 23,153 pairs; the proof latched 28,323 bits.
4. Port classes close at the seam, not by buffers: the sender's out-face rank carries the launch-side latch (type-root lockup, owner decision 11-20), and the receiver's `in_min` is raised by what the latch guarantees. That removes the port_in residue every repaired kit still shows (t39 1,142; col_h10_r1 1,651; c1x t1 2,936; slw_fe_v2 3,558; hd_lep0N 8,396 before repair). Limit (I, arithmetic): half period 416.5 >= die tap window + seam hop delay, so it fits abutted seams with the first rank at the pin; a 300 um channel hop under a 208 ps window does not fit and keeps its buffers or gets a narrower window.

First check, one read on the two kept t39 CTS DBs: clock sinks per tap, and the port_out ends by tap. Then the proof's "after" line: hold cells against 47,483, and the path at -471.

## 3. What blocks the first new-plan sign-offs

| Die | State (failure_breakdown 15:13, V) | Tonight | Tomorrow |
|---|---|---|---|
| S81 | types 44 / 394; 192 held for the plan event, 157 running | Old-plan exports only. J5 (applied 13:14): 21 rows past gen; leaf held behind t7 (relaunched 13:59); post-apply bind rerun at 160 GB open; five of six hosts admit 0 GB (R, FABLE-FLOW-1400) | J6 cut 14:00. Needs both col masters routed with the latch (synth still queued on epyc8), item 9 relay tool, lepe row 4 + item 6 unproved (headline 3) |
| HEAD | 25 / 26; hd_lep0N running | r14 in CTS on epyc7. Nothing in r14 changes the 140 ps window, so expect about 15,000 hold ends and the same GRT band (11:20). epyc7 has started no container since 14:38 (R, BKSEL-R2 15:12) | lockup + tap split rows are on the next HEAD event, not in r13r; no sign-off before that event builds |
| QC | 37 / 130; 53 running, 20 placed route-held, 15 global-place errors (sle_ctl) | A4 kits launched 09:43 reach route late tonight at best. cb* kits carry form R at -293 to -1,746 | V1 cut 09:30: fabric strict (q2 / q3) and the merged-class bind (ph6, 36 errors: 30 R8_STALE re-derived, 5 unpriced stations priced, R) |
| KV | 6 / 56; 20 running, 9 placed route-held, 8 hg held | D26 R3b gate admitted on epyc7 15:0x for the 20:00 cut: same container risk. It fixes hg generation (8 types) and head-core hold (19 types) | hub_Wo, sys_c, hgi_v1 collector and pv reset legs have no row before D27 (cut 20:00) |

## 4. Levers, ranked by closure impact

| # | Lever | Measured evidence | Root cause | Fix | Owner |
|---|---|---|---|---|---|
| 1 | Reset / start legs as hops, by generator | section 1: form R / S on 43 of 47 current-event kit builds read under -42, the kit WNS on 22; form L on 23 more (S81) | last leg and local relays are outside the reach rule | section 1 steps 1 to 5 | S81-DIE-R4 relay tool; rows to QC-PLAN-R5 (V1), KV-PLAN-R2 (D27) |
| 2 | Core-pin slew limit on every new gen | t60 -964 -> -288, TNS -47,016 -> -7,015, pins over 320 ps 950 -> 0 (R; no legalised CTS A/B yet) | core libs carry no limits | e7ebced0c4e + f2e64e5d3b2 are on main; run the two proofs (not started, V); regen the 3 SLEW-LIMITED QC rows and sys_c | CORE-LIB-LIMITS-1330 successor; die owners |
| 3 | Lockup with taps re-solved | section 2: cross_tap -77 %, all ends -59 %; port, same_tap and setup worse | latch clock pins overload launch taps | section 2 steps 1 to 4 | LOCKUP-STATION-1130; S81-DIE-R4, HEAD-R14 |
| 4 | S81 col masters (120 types on 2 builds) | bind, SDC, synth isomorphic (R); no routed master | synth queued on a host that admits 0 GB | move both masters to a host that admits; route before the J6 cut | S81-DIE-R4 |
| 5 | KV efault staged reduce | hub_Wo -1,040 (2,700 um, 1 end); hgi_v1 -410; cell in 29 of 56 types (R, PD-KV-1500) | one-cycle reduce across the die | local reduce + 300 um relays, +cycles on a status path | KV-PLAN-R2, D27 row 1 |
| 6 | lepe row 4 + item 6 | proof6: hold +4.6 after GRT, setup -154 on 692 ends; land reset 1,300 um (R) | form L; roq | relaunch proof7 with the plan file path fixed; RSZ-0074 catch around `repair_timing` | OPUS-FIX-S81-LEPE; FLEET-WATCH for the catch |
| 7 | KV pv pad segments | v8m / v8c `dly_spread` max_hop 1,404 um, fail 70 / 66 (R, PV-R2) | form C makes one segment one station | `pad_min_stations 16` (branch not pushed) + flip rows after the v8m / v8c GRT iteration 5 read | FABLE-FIX-KV-PV-R2 -> D27 |
| 8 | QC pad hoist + sle_ctl | ph5: five merged classes bind as one module each; sle_ctl -483 / -528 at place and 15 global-place errors (R, V) | per-instance pads inside the type; hub cores 8 um apart | ph6 bind, then `u_ctl` move in V1 | UNIFY-TOOLS-R3, QC-PLAN-R5 |

## 5. (c) Which rows matter most

- **J6 (S81, 11-21 14:00):** 1 col master latch rows + SDC envelope (120 types); 2 item 9 with the section 1 scope (every J5 type with a landing monitor or a local relay); 3 leaf: per-lane spread rows, SRAMREG into the base, core-pin stages on t60 / t57 / t43 and kv_leaf t1 / t4 (75 types); 4 slice C finish leg D=3 and taps (11 types); 5 lepe row 4 + item 6 (4 types, unproved). svc H8 and bk_sel A3P only if their binds are green in time.
- **V1 (QC, 11-21 09:30):** 1 fabric option (a) at strict 0, since every QC type regenerates on it; 2 reach rows for `u_rrl -> u_st.g_seg` on cbx / cbn / cbf (new this round); 3 st_a `rs_s0` / `rs_s1` stages (11 types); 4 sle_ctl move + hoisted pads; 5 re-bin and retap the 25 stale-bin types. No latch rows yet: slw_fe_v2 has 0 cross-tap hold ends; su_l0 / su_l1 need a census first.
- **D27 (KV, 11-21 20:00):** 1 efault staged reduce (29 types); 2 reset legs on pv, sys_c, hub_Wo by the same tool as J6; 3 pv `pad_min_stations` + flip (16 types); 4 astk `sc_v` register and tap split (8 hg types); 5 sys_c L356 stations (1 type).

## 6. Stop list (13:25 and FABLE-PD-KV-1500 stand; plus)

- No hand rows per type for local reset relays after lepe item 6; the generator rule replaces them.
- No reading of a placed `u_rrl -> cland_fstart` end as unsignable on slice_station; check the buffer count on the path.
- No regen of QC cbn_q00, cbx_q10 or cbf_q01_s2 "for the slew limit" expecting them to pass: each has a second class at -293 to -1,746 from form R.
- No lockup spec applied to a wave kit without re-solved taps; no RTL register form where the netlist form on violating ends covers it; no J6 master with the latch at the hop midpoint until its tap is checked.
- No pair or end count from the t39 proof reported as a win before its "after" line and the -471 setup path are read.
- No port hold buffers as the plan for port_in / port_out on a type that gets a seam latch.
- No waiting on lepe proof7 or on the t60 / cbf proofs as if they ran.
- No route or repair retry on KV pv_v2 / pv_v2n D25e3 for the -2,145 / -2,218 reset legs.

## 7. Not checked

- Section 1 is worst path per group, placed, ideal clock, 3-day window, old events included in the 207. Endpoint counts per form were not read. Whether J5's 300 um reset tree shortened the last legs was read on 3 J5 kits only.
- Why the placer leaves a local relay at the port is inferred from the net shape; no placement was opened.
- Section 2: the tap-load cause is inferred from class counts. Sinks per tap, the port_out ends by tap and the -471 path were not read; two CTS runs can differ by this much without latches (no repeat build exists).
- The half-period arithmetic of the seam latch; no kit carries it.
- proof7: I read `run.log` and `docker ps` on epyc9 only; a client waiting on another host would not show there.
- epyc7 container stall and host admission are taken from BKSEL-R2 and FABLE-FLOW-1400.
- HEAD r14 pre-GRT line, KV D26 gate result, QC q2 / q3 and ph6 results: none written when read.
- Several handoff update stamps (OPUS-FIX-S81-LEPE "15:45", "16:30") are later than the wall clock at my read (15:10); I used post times.

# FABLE-CLOSURE-STRATEGY 2026-11-20 13:25 PST (lane FABLE-CLOSURE-1315): the held kits at -300 to -1,500 ps are mostly one unbuffered wire into a hard-core pin; hold cells are not shown to cause GRT overflow

Reviewer: FABLE-CLOSURE-1315 (Fable). Read-only: no job launched, cancelled or patched; no STA run. Technical PD only; S81, HEAD, QC, KV; HBM parked.
Gate: DRC 0, routed TT >= -42 ps at 833 ps, internal FF hold >= 0, LEC, bind + LATCHECK. Hop cap 300 um. Nothing below is a new gate or hold.
Marking: **V** = I opened the file this round. **R** = reported by the named lane. **I** = inferred. **P** = proposal.
Delta on 11:20. Its sections 1.2 to 1.4 and 2 stand. Its headline 1 is corrected in section 1 below.

## 0. Headline

1. **Correction to 11:20: hold cells are correlated with GRT stalls, not shown to cause them.** lepe proof6 carries 32,839 hold cells (8.9 %) and GRT ends at extra iteration 6 with overflow 0 and usage 9.55 % (V). Do not cancel or hold a build on its hold-cell count (section 1).
2. **Seven placed kits have the same worst path: one unbuffered wire, slew 2.6 to 5.0 ns, wire delay 815 to 1,586 ps (V).** Five end on a hard-core pin. The core view libs carry no `max_transition` and no `max_capacitance` (V on `ot_s81sl_vs_tt.lib`), so place repair sees no violation on those nets (I). The post-place WNS that ROUTE-RELEASE used is therefore set by a flow default on these kits, not by the plan (section 2).
3. **Three more leaf kits are set by a single-bit clock-landing start or reset relay net** with 13 to 26 buffers in series (V).
4. **The generate-block gap: fix it at the netlist, not in the RTL parser; no latch for SRAM-wrapper internals** (section 3).

## 1. Is hold-cell congestion causal?

No evidence that it is. Four reads against it, one open test.

| Build | Hold cells | Share | GRT |
|---|---|---|---|
| S81 lepe_mu_LP t2 proof6/r2 (V, `5_1_grt.tmp.log`) | 32,839 | 8.9 % | overflow 0 at extra iteration 6; usage 9.55 % |
| HEAD hd_tile (11:20 table) | 25,166 | 18.0 % | type is signed off (R) |
| HEAD hd_lep0N r3 (11:20) | 17,151 | 3.7 % | 46,652, flat |
| QC sle_ctl (11:20) | 6,998 | 1.4 % | stalled |
| S81 leaf t39 D8i baseline (V) | 47,483 | 13.8 % | 20,000 markers (report cap) at iterations 5, 10 and 15 |

- The largest share on any type routed and signed off. A type with 3.7 % has the worst overflow. So the count is neither sufficient nor necessary.
- What moved overflow by two orders of magnitude was structure each time: lepe RIP1 removed the rid class (R); coll_core read register 75,675 -> 529 (R); KV hgi split clock rows 10,201 -> 4 (R).
- Reading (I): the families with wide tap windows are also the bus-heavy families with core arrays, so both numbers rise together. Hold cells add demand only where the tile is already near capacity.
- What hold cells do cost on proof6 (V): 20,362 s of repair before GRT; then 200 more buffers in GRT moved setup from -149.06 to -217.71 and the setup guard stopped the pass. So the cost is hours and setup, which is still a reason for the lockup form.
- QC slw_fe_v2 (R, LOCKUP-STATION-1130): 41,091 cross-tap pairs and 0 cross-tap hold ends at a 57.8 ps window. The window makes the ends, as 11:20 section 1.4 says.

**The one controlled test:** `proof_t39` (epyc7, same kit with 131 latches) against the baseline above. It was in CTS at 13:14 (V). Its handoff says to stop it before GRT. Keep it to GRT iteration 10 and read markers against the baseline. That answers the question with one build.

## 2. The held kits: common setup mechanism

Source (V): `3_detailed_place.rpt` worst max path and `geom/placed_scan.json` of each kit, event D8i 465cb9fe2d3 (QC A4 for cbf). Scripts `scratchpad/sig.py`, `held.py`, `rel.py`.

| Kit | Place WNS | Worst path | Largest single delay / slew (ps) | Buffers on path |
|---|---|---|---|---|
| leaf t60 | -1,123 | core `u_vsw/o_f` -> core `u_vs/sw_fi` (66 bits, 423 um, no flop) | 1,576 / 4,998 | 0 |
| kv_leaf t4 | -955 | `ln_15 cst_hi` src flop -> lane core `g_ln_12/c3` | 1,586 / 4,998 | 0 |
| kv_leaf t1 | -708 | `ln_9 cst_hi` src flop -> lane core `g_ln_5/y` | 1,296 / 4,101 | 1 |
| leaf t57 | -306 | `cst_sw` src flop -> core `u_vsw/i_d` | 815 / 2,578 | 0 |
| leaf t43 (not in the 12) | -779 | src flop -> core `u_vq/m_v` | 1,342 / 4,253 | 2 |
| slice C c1x t9 | -1,278 | `xf driver go_c` -> finish core `g_cp_0/go` | 1,291 / 4,082 | 6 |
| QC cbf_q01_s2 | -1,523 | `d3 t_1_2 t_out.q` -> `pc_nk t_0_2 n_b.q` D pin | 1,261 / 3,995 | 3 |
| leaf t72 | -1,381 | `cland_origin/s2` -> `cland_reader_start_ft0_i_0` (net `cland_start`) | 70 / 48 | 26 |
| leaf t8 (not in the 12) | -982 | `u_rrl_18` -> `cland_fstart_ft10_o` | 74 / 68 | 18 |
| leaf t56 | -484 | `u_rrl_554` -> `cland_fstart_ft1_o` | 74 / 68 | 13 |
| leaf t1 | -739 | `vp g_wr1 hi_sw` -> `wdo_q[0][80]` (soft logic) | 85 / 270 | 18 |

Three classes.

**U. One unbuffered wire (7 kits).** The final net has slew 2.6 to 5.0 ns. Place `repair_design` ran on t60 (62,289 buffers in 31,995 nets) and left this net alone. `ot_s81sl_vs_tt.lib` and `ot_s81sl_vsw_tt.lib` have 0 `max_transition` and 0 `max_capacitance` lines, so a net whose loads are core pins has no limit to violate (I for the link; the cbf case ends on a flop D pin, so it has a second cause I did not find). The scan's own buffered estimate for the t60 hop is 525 ps against 1,576 measured.
- With the wire buffered, t60 is about 208 (core clock-to-out) + 525 + 85 (setup) + 257 (macro clock tree) - 833 = -242 (I). t57 goes under the release line. kv_leaf t4 at 716 um stays near -500 and needs a stage.
- Every core input also loses 227 to 309 ps to `macro clock tree delay` against the ideal 250 ps clock at this stage. Whether the tap offset gives it back after CTS was not read. Slice C p1/p2 (R) show the same wire after CTS at -953 / -998, so CTS does not cure the class.

**C. Clock-landing start and reset relay, single bit (t72, t8, t56; second path on t60, t56 at -374 to -391).** A broadcast or relay net crossing the type through 13 to 26 buffers in one cycle. Few bits, so the cost of pipelining is flops in the tens.

**S. Soft logic spread (t1).** One kit; `vp g_wr1` write path. Not a family signal yet.

Two side results.
- `placed_scan` bits over cycle do not rank the kits: t68 726 bits at -125, t56 80 bits at -484, t72 212 bits at -1,381 (V, 24 D8i leaf and kv_leaf kits). The scan uses a buffered estimate and does not see class U or the core pin budget.
- The split at -300 kept t57 (-306, class U) and passed kits whose worst path is real logic. Class, not the number, should sort them.

## 3. Is the generate-block latch gap worth a tool fix?

Yes for a small fix in another place; no for the two obvious ones.

Numbers (R, LOCKUP-STATION-1130): lepe 5,271 of 10,237 cross-tap pairs covered; roq/rop generate regs 1,123 pairs; core and SRAM-wrapper internals 5,531. hd_lep0N 17,066 of 44,659.

- **Pairs are not hold ends.** lepe has 7,622 cross-tap ends on 10,237 pairs; QC fe has 0 ends on 41,091 pairs. Coverage has to be counted on the pre-repair ends in `pregrt_ff_hold.log` joined to the spec. That is one read on the kept `4_cts_pre_tt.odb`, and it comes first.
- **Do not extend the RTL scope parser into generate blocks (P).** `zl_pairs.tcl` already names the exact launch flop instances in the placed netlist. Insert the launch-side latch on those instances in the kit's synthesized netlist; generate scopes, parameter widths and module scoping stop mattering. `ot_dp_lk` and its LEC see-through are on main. Whether the kit flow has a post-synth hook for it was not checked.
- **lepe roq/rop: no fix.** Row 4 rewrites roq (per-column copies, IN_PIPE 2), so its names and pairs change in J6. Re-derive after.
- **SRAM-wrapper and core internals: no latch.** Pairs inside one wrapper mean its flops are split across taps. Put a wrapper's registers on one tap in the tap rows (11:20 section 1.4).
- **hd_lep0N is the type that pays:** 62 % of pairs uncovered and it is the one unsigned HEAD type. Its other half, 8,396 `port_in` ends, is a sender-side class no latch in this kit covers.

## 4. Levers, ranked by types unblocked per day

| # | Lever | Evidence | Types | Owner | First check |
|---|---|---|---|---|---|
| 1 | Limits on core pins, so place repair buffers core-pin nets: `max_transition` / `max_capacitance` in the core view lib, or `set_max_transition` on core pins in the kit SDC | section 2 class U, 7 kits (V) | 5 of the 12 held now; every type with hard cores on four dies; count not known | kit flow owner (WAVE-FLOW-R2) with S81-DIE-R4 | t60 `3_place.odb`: set the limit, `repair_design`, re-read WNS. Minutes, via ot-run. Predicted about -240 (I) |
| 2 | KV D26 at the 20:00 cut | hg GEN_LINT is the ECTL cycle (R); krsp lanes 5 -> 6 | 8 hg types generate again; 19 hg/hgi get the head-core lockup | KV-PLAN-R1 | R3b gate log |
| 3 | S81 J6: a stage at the core pin on core-to-core and src-to-core hops over 300 um (`relay_depth` sink rows, KIT-RD-1 on main); slice C finish leg D=3 | t60 core-to-core 423 um with no flop; kv_leaf 623 to 716 um, no row; finish leg 941 um (R) | leaf and kv_leaf with a class U end (5 of 24 read); slice C 11 | S81-DIE-R4, S81-SLICEC-R3 | after lever 1, list the core-pin ends still under -42 |
| 4 | Pipeline the clock-landing start and the reset relay to `cland_fstart` at 300 um, same depth to every reader | class C: t72, t8, t56 (V) | 3 of 24 leaf kits as WNS; generator class, so every type with landings | S81-DIE-R4 with the landing generator owner | count `cland_start` and `rrl -> cland_fstart` ends under -42 on the 24 placed reports |
| 5 | lepe row 4 + item 6 (`u_u_land.tag`) | proof6: GRT 0, TT -149 (R, V) | 4 LP lane-core types | OPUS-FIX-S81-LEPE | path report on `land.tag`, then proof7 |
| 6 | Lockup station by netlist instance (section 3) | t39 proof in CTS; col 120 -> 2 and hd_lep0N wait on it | col, leaf, hd_lep0N; 0 until a kit shows hold ends before repair near 0 | LOCKUP-STATION-1130; HEAD-R14 | t39 pregrt class line; then GRT iteration 10 A/B |
| 7 | QC V1: rows on `rrl_369 -> fab u_st.g_seg` (80 bits, 710 to 1,228 um, no row) and `d3 t_out -> pc_nk` | cbf_q01_s2 (V); V1 priced at +15 cycles (R) | cbf family; V1 feeds all QC | QC-PLAN-R5 | send LOCKUP one kept su_c or coll_core `4_cts.odb` |
| 8 | Sort placed kits by worst-path class before the WNS line | section 2 side results | re-sorts the 12 held; t57 first | ROUTE-RELEASE successor / S81-DIE-R4 | `sig.py` on the queue rows |

Lever 1 is ranked first because it is a flow default, costs one line, and changes the number every triage lane reads. It is predicted, not measured.

## 5. Stop list (11:20 stands except as corrected; plus)

- No cancel and no route hold on hold-cell count alone. This withdraws my 11:20 reading and the "over 10k cells: cancel before GRT" plan that HEAD-R14 took from it. Read GRT iteration 10 instead.
- Do not stop `proof_t39` before GRT iteration 10.
- No release or cancel judgement from a post-place WNS whose worst net has slew over about 1 ns. Class it first.
- No `placed_scan` bits-over-cycle count as a predictor of WNS.
- No pair coverage reported as hold coverage.
- No RTL-parser work for generate-block latches; no latch rows for SRAM-wrapper internals; no lepe roq/rop lockup rows before row 4.
- No further slice C build without the finish-leg stages (p1 and p2 ended on the same path).
- No further lepe proof without row 4; roq is measured.
- No KV hg relaunch before D26 applies.

## 6. Not checked

- Why the class U nets stay unbuffered: the missing lib limits are a fact, the causal link is inferred, and cbf_q01_s2 ends on a flop pin. No `repair_design` trial was run.
- The -240 prediction for t60 and whether CTS returns the 227 to 309 ps macro clock term.
- Whether J5 / J6 rows already station the named leaf hops; I read D8i kits only.
- Where hold cells sit against hot tiles (still open from 11:20). The t39 A/B replaces it.
- hd_tile sign-off is taken from the 25-of-26 count, not from its export.
- Post-synth hook for netlist latches; LEC on any latch spec (LOCKUP ran none on lepe).
- HEAD r14 pre-GRT line: nothing in the log at 13:14. KV D26 gate and QC V1 strict runs were not opened.
- Leaf sample: 24 placed D8i leaf and kv_leaf kits on five hosts, worst path only.

# FABLE-CLOSURE-STRATEGY 2026-11-20 11:20 PST (lane FABLE-CLOSURE-1115): the hold repair before GRT adds 9 to 14 % of the cells on the families that stall in GRT; hop stations, hold and lane pads are one construction rule

Reviewer: FABLE-CLOSURE-1115 (Fable). Read-only: no job launched, cancelled or patched; no STA run. Technical PD only; S81, HEAD, QC, KV; HBM parked.
Gate: DRC 0, routed TT >= -42 ps at 833 ps, internal FF hold >= 0, LEC, bind + LATCHECK. Hop cap 300 um. Nothing below is a new gate or hold.
Marking: **V** = I opened the file or ran the read this round. **R** = reported by the named lane. **I** = inferred. **P** = proposal.
Delta on 09:05 and on FABLE-PD-QC-0945, FABLE-PD-KV-0945, FABLE-PD-S81-1100. Their fixes and stop lists stand; this section adds what crosses dies, and HEAD.

## 0. Headline

1. **Hold repair before GRT is a congestion source on every die (V, new).** I read the `OT_PREGRT_FF_HOLD after` line of 80 running builds on epyc8 / epyc9 / epyc10. The repair adds 1 to 4 % of the instances on the col types and 9 to 14 % on the families that stall in GRT. It takes up to 7.3 h. The count follows the type's clock tap window (section 1.1).
2. **The 300 um rule is drawn for reset on all four dies and for data on none (R, the three per-die reviews).** S81 J5: rows with a leg over 300 um 5,408 -> 8,064. QC A4: 1,030 of 4,692 hops. HEAD r13r and KV D26: reset and a few named rows. Where data was re-stationed in packed banks (S81 leaf form C) the station bits per tile rose 2 to 5 times on the GRT hot tiles.
3. **hd_lep0N, the one unsigned HEAD type, has the same two classes (V).** Tap window 140.3 ps; 14,941 to 17,040 hold ends before repair on three builds; 17,151 hold cells; then GRT flat at 46,652 with 79 % of it in one band. The r14 kit changes relay sites and one band; it does not change this.
4. **hd_serdes proof is not running (V).** `sdr2` ended exit 143 at 10:18; `sdr2b` has waited on epyc10 since 10:19 (admits 0 GB, 16 waiters).
5. **Only one lever is measured in sign-offs: the residual hold pass on kept routed DBs.** 11 of the 17 exports today came from an `eco_*` directory (12 of 18 on 11-19) (V, `posts/AUTO-EXPORT.md`). Every other lever is measured at bind, place or GRT at most (section 3).

## 1. Cross-die levers

### 1.1 Hold cells before GRT (V)

Source: `docker logs` of each `dpkit-*` container, last `OT_PREGRT_FF_HOLD after ... hold_cells N insts M ... secs S` line, and the `OT_HOLD_GATE structural limit` line. 80 builds; script `scratchpad/hc.sh`.

| Family (builds read) | Tap window (ps) | Hold cells | Share of instances | Repair time | wns after (ps) |
|---|---|---|---|---|---|
| S81 col_h9 / col_h10 (44) | 40 | 1,800 to 9,475 | 1.0 to 4.3 % | 0.2 to 2.0 h | -36 to -71 |
| S81 leaf (19) | 186 | 3,189 to 60,455; 16 of 19 over 20,000 | 1.4 to 13.8 %, median about 10 % | 0.1 to 2.4 h | -1 to -252 |
| S81 slice C c1x t1 / t6 / t9 | 154 | 55,131 to 64,552 | 8.2 to 10.0 % | 5.3 to 7.3 h | -221 to -263 |
| S81 lepe_mu_LP t2 | not read | 32,839 | 8.9 % | 5.7 h | -116 |
| QC sle_su_c / slw_su_c (4) | 229.6 | 55,664 to 66,197 (one at 9,326) | 10.0 to 11.5 % | 2.4 to 3.4 h | -82 to -129 |
| QC coll_core (2) | 57.1 | 52,026 and 54,813 | 11.2 and 11.5 % | 5.0 and 5.6 h | -54 and -75 |
| QC slw_fe_v2 | 75.9 | 46,576 | 10.2 % | 1.8 h | -121 |
| QC cbf_q00, sle_ctl | not read | 23,021; 6,998 | 5.9 %; 1.4 % | 2.4 h; 0.3 h | -83; -86 |
| HEAD hd_lep0N (r3) | 140.3 | 17,151 | 3.7 % | 2.8 h | +4.4 |
| HEAD hd_tile, hd_spn | 106; not read | 25,166; 18,485 | 18.0 %; 7.5 % | 0.5 h; 0.3 h | +2.4; -113 |

Reading.
- The families with over 20,000 hold cells are the ones GRT-TRIAGE lists as STALLED (leaf, slice C, coll_core); the su_c builds are in GRT extra iterations now. The col_h10_r1 rows, at 40 ps, are CONVERGING there. sle_ctl is the exception: 1.4 % and stalled, and FABLE-PD-QC-0945 already names its cause (two hub cores 8 um apart).
- hd_lep0N congestion report at iteration 10 (V): 34 % of the net references in the hot band are buffer-made nets (`netN`); 91 % of the 13,968 markers there carry at least one. That count includes setup and placement buffers, so it is an upper bound for hold.
- The repair does not finish the job either: after it the remaining ends are `port_in` (col_h10_r1 1,651 at -44.8; c1x t1 2,936 at -221; slw_fe_v2 3,558 at -121). Three QC kits and hd_lep0N print `cross-tap guard not applied (no tap window lines in the kit SDC)`.

**Root cause (I).** A type whose taps arrive within 40 ps needs almost no padding. A type with a 150 to 230 ps window needs every short register-to-register path between two taps padded by that much: several buffers per end, placed where the stations are. The hop rule then adds more zero-logic hops between taps (tap radius 200 um, hop up to 300 um), so the next 300 um event raises the count again.

**Not measured.** Which hold class takes the cells (the log has the class split only after repair), and where the cells sit against the GRT hot tiles. Both are one read on a kept `4_cts.odb`.

### 1.2 One station rule for all dies (P)

The per-die reviews each propose a piece of this. Put together it is one generator rule, in the shared station / landing compiler, not rows per family:

1. **Count from length.** Stations per bit lane n = ceil(pin-to-pin / 300) - 1. CBC-ALL-0200 R11 already sizes rows this way.
2. **Site per lane, on its own line.** Each bit's stations sit at equal pitch on that bit's own source-to-sink route, so stage k of a bus is a line across the bus width, not a point. The bus keeps its spread and no bit detours to a bank. This is the S81 `S81-LEAF-SPREAD-J6` form (a station per lane, hops <= 295 um) and the opposite of J5 form C (distinct sites 13,878 -> 7,339; peak tile 4,190 -> 21,442 bits on t7). A packed bank is allowed only where one tap radius holds the whole bank and the consumers are within one hop of it.
3. **First rank at the pin.** Stage 0 is seated FIRM at the port or core pin window before any stage is counted (09:05 lever 6; QC fe 744.6 -> 189.8 um at 0 cycles).
4. **Lockup in the station cell.** When the launch tap and the capture tap of a zero-logic hop differ, the generator emits the launch-side transparent-low latch with the station. KV has the cell and the LEC see-through on main (`ot_dp_lk`, 8899ba10e9); S81 has it in two private J6 masters; QC has 0 latch rows on 2,941 cross-tap hops; HEAD has none. One primitive, four dies, 0 cycles.
5. **Two numbers before a build.** Peak station bits per 100 um tile, and detour = sum of legs / pin-to-pin distance per bit. FABLE-PD-S81-1100 section 1.3 computed the first from plan JSON in minutes and matched 7 GRT top tiles. Both go into PRECHECK as estimators.

Margin of item 4 (I, from the KV arithmetic): half period 416.5 ps against tap-to-tap skew + library hold. It holds for windows up to about 290 ps; the widest read here is 229.6.

First check: the t39 `tree_SP` against `tree_Cc` A/B that S81-DIE-R4 already runs. Read hold_cells and overflow at iteration 10 on both. Then one su_c kit with item 4 only.

### 1.3 Lane pads become hop stations (P)

Evidence (R). UNIFY-TOOLS-R2 11:04: per-instance lane pads still split every merged class; sle_ctl `x_su_l0_i` is 1 / 3 cycles on the E instances and 29 / 30 on W, 457 bits wide. QC-PLAN-R5 10:01: A4 holds a 12-stage R8 pad at the fabric root; V1 raises 264 legs for 395k flops, most of it 300 um repricing. FABLE-PD-S81-1100: 3,279 `ft_slots` legs at 301 to 405 um, held back because re-pitching changes lane latency.

The ruling (hoist the pads out of the partition) and the 300 um rule ask for the same flops. A pad is a delay chain at the end of a long lane; a 300 um lane needs more stations along that same lane. So:
- Spend each lane's pad cycles first as stations on that lane's route in the parent (channels, `ft_slots`), at 1.2 item 2 pitch. Lane latency is unchanged, so LATCHECK dates do not move.
- Only the remainder stays a chain, at parent level, never inside a type.
- The type then holds stations that depend on its own geometry only, so its hash is the same for every instance and `class_merge` binds one module.

It also takes the delay chains out of sle_ctl, the congested QC type (up to 30 x 457 bits per W instance).

First check (estimator, PRECHECK-1119 with UNIFY-TOOLS-R2): per lane, pad cycles available against stations needed at 300 um. Count the lanes where pad >= need: those re-pitch at 0 cycles. I did not compute it.

### 1.4 Tap window as a plan number (P)

col has 40 ps and closes hold with 2 % cells; leaf has 186 and su_c 229.6. KV astk (FABLE-PD-KV-0945): the 1,200 sinks-per-tap spill makes taps 565 to 588 um wide and 1,862 cross-tap ends. QC: 125 types with a tap over 1,000 sinks, 25 with stale bins. hd_lep0N: 800 sinks per tap, insertion 441 to 486 ps, skew inside one tap up to 107.3 ps (r3) and 152.9 ps (r8b `clk_t95`) (V).
Rule: tap rows are made after the station rows (bins from the newest placed kit), each tap's sink box inside the 300 um span, and the window that the kit SDC declares is the plan's. Where the window stays over about 100 ps, item 1.2.4 carries the hold, not buffers.

## 2. HEAD

State (V unless marked): 25 of 26 types signed; hd_lep0N open. Five hd_lep0N builds run on four plans.

| Build | Plan | Stage | TT after repair | FF hold before repair |
|---|---|---|---|---|
| epyc9 `dpkit-hd_lep0N-579160` | r3 private | GRT run 9, 44 h | -121.63 | -270.08 on 14,941 ends |
| epyc10 `dpkit-hd_lep0N-304519` | r8b wave | pre-GRT hold, quiet 5.4 h | -88.44 | -277.89 on 15,914 |
| intel2 `dpkit-hd_lep0N-830501` | r8b (Codex) | pre-GRT hold | -293.24 | -292.29 on 17,040 |
| epyc10 `dpkit-hd_lep0N-2362622` | r11b | CTS, 3 h | not reached | not reached |
| epyc7 `dpkit-hd_lep0N-3749933` | r14 `lep_hop300` + h4 band | resumed at floorplan 11:0x | not reached | not reached |

### 2.1 hd_lep0N
- Hold (V): structural limit -240.3 = `in_min` -90 + tap window 140.3. All three builds are beyond it before repair. r3: 17,151 hold cells in 10,156 s, guard 45 ps, ends at +4.37 with 0 ends. So the base hold closes by buffers, each time.
- GRT (V, r3 `congestion-10.rpt`): overflow 49,837 at iteration 5, 46,652 at 10, nine GRT runs. 36,845 (79 %) lies in x 800 to 1300, y 500 to 700; vertical 64 %; zero-capacity 3 %. Net owners in that band: flat logic 51.6 %, `g_tx` 13.7 %, `g_rxh.g_l` 8.3 %, `g_rx` 7.1 %, `g_inpipe.rop` 5.4 %. This is demand in open area, not a wall. Utilization 65 %, place density 0.5.
- r13r / r14 (R, HEAD-R14 10:46): four global-place failures on the `mlwd_h4` band (80 flops in a 5.13 um channel between two SRAM banks); the band moved; two reset anchors at 299.16 / 298.08 um.

Reading (I). r14 fixes the place failure. Nothing in it changes the tap window or the band. If its post-CTS line again reads about 15,000 ends beyond -240, it will add about 17,000 cells and reach the same GRT.

Fixes, ranked (P; owner HEAD-R14):
1. Read r14 at post-CTS: `OT_HOLD_GATE INFO` ends and, after repair, `hold_cells`. If over about 5,000 cells, stop reading that build for GRT and take fix 2 into the HEAD event.
2. Tap window lines in the LEP kit SDC (the guard and the class split are off without them), then 1.2 item 4 on the cross-tap zero-logic classes; `g_pin.g_s[].u_st` is the one end the log names.
3. Split the 800-sink taps whose own skew is over 100 ps (`clk_t93`, `clk_t95` on r3; `clk_t95` on r8b).
4. The band: view the r3 `3_place.odb` density in x 800 to 1300, y 500 to 700 against the tx / rx bank positions before any row. I did not open it.
5. Old builds: r3 (44 h, flat at 46,652 at iteration 10, TT -121.6) does not meet the cancel rule yet (no iteration 20 read: each GRT run restarts before it). It can still sign in principle, so it stays; it is not evidence for r13r.

### 2.2 hd_serdes
- R (FABLE-FIX-HEAD-SERDES-R2 09:35): the live plan lost `OT_S81_RM_STAGED` and `OT_S81_KP4_ENC_LA` from `verilog_defines`; a8 and the NOMCAP kit build the unstaged rate matcher (-878 ps at place, 538.8 um reset box). The signed sd9he form (11-18, TT -27.16, hold 0) had all four. Landing reset 513.6 um is a parent choice; the row exists (`serdes_r1_300_trial_v2.json`, worst hop 233.5 um).
- V: `sdr2` (signed defines + RLEAF) ended exit 143 at 10:18, no cause in the client log. `sdr2b` queued 10:19 on epyc10 and is not admitted.

Fixes (P):
1. Run `sdr2b` where memory admits (ot-run spill to another host at plan priority). It is the only proof of the staged form on r13r pins.
2. HEAD-R14 carries both rows in the next HEAD event: the five-define list and the reset parent row. Until then every new serdes kit builds the form that cannot sign.
3. No more reading of a8 or the unstaged NOMCAP place for timing; keep NOMCAP only as the tap-census comparator Codex asked for.
4. hd_serdes counts as signed on sd9he (any plan). The r13r re-sign is spare-capacity work; hd_lep0N is the type that moves the HEAD count.

## 3. Levers: measured or predicted, and types per day

| Lever | Furthest measured point | Sign-offs from it | Types per day |
|---|---|---|---|
| Residual hold pass on kept routed DBs (09:05 lever 5) | sign-off | 11 exports today by 11:05, 12 on 11-19 (V) | about 1 per h while the queue lasts; about 25 open builds at 01:25, so one more day |
| Base route, old plan (S81 slice_station) | sign-off | 6 today (5 S81) (V) | about 0.5 per h |
| Reach from the bound plan / A4 live (lever 1) | gen | 0; QC 252 launches in 1 h (R); reset-identity refusals 33 of 305 gen logs in 2 h against 723 of 816 in 6 h (V) | feeds every QC type; first sign-offs about 24 h after 09:43 |
| S81 col 120 -> 2 (J6) | bind + SDC + synth: identical `constraint.sdc`, `config.mk`, isomorphic netlists (R, S81-DIE-R4 10:13) | 0; every D8i col kit read is at -36 to -71 after the pre-GRT hold repair (V) | 120 on two builds, largest on any die; predicted; needs the latch in both masters and the relay form settled |
| Proposal 3 split clock rows (KV) | GRT: hgi k13i overflow 10,201 -> 4 (R, V in FABLE-PD-KV) | 0; kR ended TT -310 | 0 until D27 astk rows; clears 19 hg / hgi for congestion only |
| coll_core read register (pkw4) | GRT round 5: 529 against 75,675 (R) | 0; -479 on 392 ends at place | 1 type |
| First rank seated (QC fe) | private place | 0; not in A4 | predicted |
| M5 halo (QC st_a) | place-only pass | 0; route held | 11 types, predicted |
| Leaf spread rows | plan geometry only | 0 | 75 leaf types depend on it; predicted |
| class_merge / role strap | tools on main, tests green | 0; binds still split on pads | 0 until 1.3 |
| GRT triage cancel | 25 of 40 long jobs cancelled (R) | frees hosts, signs nothing | - |

Answer. Today's count comes from the residual hold pass. It is a backlog and runs out in about a day. The largest predicted gain is J6 col, and it is gated by the same thing as leaf, su_c, slice C and hd_lep0N: hold by structure (1.2 item 4, 1.4). So the lockup station is the lever with the most types behind it, and it has no built kit on any die yet. One representative per die with it (a J6 col master, QC su_c, hd_lep0N, a KV R3 hgi) is the most useful set of builds to start today.

## 4. Stop list (09:05 and the three per-die lists stand; plus)

- No packed-bank station form on a bus whose consumers are more than one hop apart (S81 leaf form C, QC st_a 405 reseat as the V1 form).
- No 300 um re-station of data by adding bits to existing bank sites; count from length, site per lane.
- No lane or R8 pad chain inside a partition type in a new event; no `class_merge` acceptance run before the pads are out.
- No hold-buffer repair read as closure on a type whose tap window is over about 100 ps: check `hold_cells` first. Over about 20,000 cells, do not wait 30 GRT iterations; read iteration 10.
- No new kit without tap window lines in its SDC (the cross-tap guard and the class split are off without them).
- No further hd_lep0N build on r3 / r8b / r11b geometry. The five in flight stay.
- No hd_serdes kit without `OT_S81_RM_STAGED` and `OT_S81_KP4_ENC_LA`.
- No J5 leaf wave on form C before the t7 iteration-10 read (already ACKed by S81-DIE-R4).
- No kv512_C route: hops 1,560.7 / 1,142.3 um, pre-CTS -1,603 ps (R, S81-SLICEC-R3). It needs the +5 / +3 stages first.
- No QC st_a relaunch that stops at global place on the rs_s0 / rs_s1 collision with unchanged rows; no KV hg kit relaunch on the `kiss_st_cols` GEN_LINT guard with unchanged inputs.

## 5. Not checked

- 1.1 is a correlation over 80 builds on three hosts. I did not read the hold class before repair, nor place the hold cells against the hot tiles. Tap windows are from one build per family.
- 1.2 and 1.3 are proposals. No kit carries the lockup station outside KV R3 (not built) and the J6 masters (synth queued). The pad-against-need count per lane is not computed.
- The 290 ps bound of the latch form is arithmetic.
- HEAD: I did not open any placed image, the r13r plan, or the r14 kit; the r11b and r14 builds had not reached CTS. The `netN` share is an upper bound for hold cells.
- Why `sdr2` got signal 15.
- Whether the S81 serdes types (11) have a define list edited the same way as hd_serdes.
- The KV `kiss_st_cols` guard, the QC A4 collision and the kv512_C numbers are taken from the brief and the lanes, not re-read.
- Sign-off exports include re-signs of a type already counted (sle_su_l1 twice today), so exports are more than the count gain.
- Token, ROM content, LEC and procedural items are out of scope.

# FABLE-CLOSURE-STRATEGY 2026-11-20 09:05 PST (lane FABLE-CLOSURE-0905): one tool default stopped kit generation on three dies; the count is flat because nothing new can start, not because builds fail timing

Reviewer: FABLE-CLOSURE-0905 (Fable). Read-only: no job launched, cancelled or patched; no STA run. Technical PD only; HBM parked.
Gate: DRC 0, routed TT >= -42 ps at 833 ps (fixed; the 1000 ps reading is withdrawn, sign profile 96d058623b7), internal FF hold >= 0, bind + LATCHECK.
Marking: **V** = I opened the file or ran the read this round. **R** = reported by the named lane. **I** = inferred. **P** = proposal.
Delta on 01:25. Its levers stand unless changed here. Count 09:02 (V, `failure_breakdown.py`): 474 any plan / 409 current plan. S81 types 44/394, QC 34/130, KV 6/56, HEAD 25/26.

## 0. Headline

1. **723 of the 816 kit `gen` attempts of the last 6 h ended on one message (V, grep over hub `autopilot/kit_wave/*/a*/gen.log` newer than 6 h).** `gen phys: ERROR type X: physical collector_tree differs from captured bound reset identity`. It is the only gen error in the window. Distinct types: S81 74, QC 59, KV 32 = 165. This is the whole NO-ADVANCE alert (S81 67, QC 25, KV 12 at 08:51 / 09:01, all `@gen`).
2. **Cause (V).** `cbc_rules.REACH_UM_PER_HOP` became 300 on main at 01:34 PST (42694ec68fe, owner 11-20 #6). `gen_phys.install_bound_native_reset` re-solves the reset collector tree with the tool default and compares it with the tree captured at bind. The live binds (S81 D8i, QC V0E, KV D25e3) were captured at 405. Example `cbn_q01__clab6e67f2` a11: captured reach 405 / max hop 380 / depth 11 / 683 relays, solved 300 / 275 / 14 / 790. The guard is right; the reach it solves with is not a property of the tool, it is a property of the bound plan.
3. **Effect.** No new kit can generate on S81, QC or KV until each die binds a 300 um event (S81 J5 cut 14:00 PST, KV D26 20:00, QC V1 22:00). The wave relaunches the same input meanwhile: up to 12 attempts per item (`seqhost__t1`, `slice_station__t6`, `cbn_q01`, `sle_su_l0`). Lanes ACKed the class as PLAN and wait for the events (R: DIE-S81-92 07:07, KV-D23-COMPOSE 07:08). Nobody proposed reading the reach from the bind.
4. **Builds in flight are slow in GRT, not failing sign-off (V, `NOPROG.tsv` 08:52).** 100 jobs in `5_1_grt`: 28 for 12 to 24 h, 11 over 24 h, most in "extra iteration N/30" at about one iteration per hour (leaf t43 / t44, hd_lep0N 42 h, kv3_hg_v1p6 35 h, sle_ctl 24 h, lepe_nh_mus_C 27 h). 55 in `5_2_route`.
5. **Three near-miss builds signed overnight on a residual ECO at 833 ps (R, HARVEST-0330, QC-HOLD-0030):** HEAD LEP pair TT +28.66, coll_ft +23.38, slw_hc1 -32.99, all hold 0/0. One did not: HC-E0 at -0.05 ps on 1 end, no second pass. One lost its sign-off run to the memory guard (slw_st_b_v2 i2r, both corners rc 137).
6. **S81 col (120 types to 2 layouts, J6) is the largest single count on any die and is not a build yet.** Private strict + LATCHECK 873/873, all date fields equal to D8i, 4 GEN pass (R, S81-DIE-R3 07:56). Open: the R1 / R2 pairs differ in measured SDC and in 43 ROM instance identities each. On the live D8i col kits the CTS FF hold after CORETAP is -45 to -53 ps median (r2 -95), 0 signed (R, S81-GEOM-OPUS 08:58).

## 1. Levers ranked by types unblocked

| # | Die | Lever | Unblocks | Owner |
|---|---|---|---|---|
| 1 | S81, QC, KV | Reset reach comes from the bound plan, not the tool default; no relaunch on an unchanged PLAN refusal | 165 types can generate again today; 723 wasted attempts per 6 h | FLOW-FIX-2045 (`gen_phys` / `reset_tree`), WAVE-FLOW-R2 (retry key) |
| 2 | S81 | J6 col 120 -> 2: close the two open proofs (SDC superset, ROM identity by personalization), with the `bin -> lpad` lockup in the two masters | 120 types by 2 builds | S81-DIE-R3, FABLE-FIX-S81-COL, UNIFY-TOOLS-0300 |
| 3 | all 4 | Superset pinout for the other classes: 0 of 275 classes inherit today | S81 leaf 75 types -> 23 to 46 classes; QC 31 classes, KV 7 | UNIFY-TOOLS-0300, SIGN-PROFILE-0400, plan lanes |
| 4 | S81, QC, KV, HEAD | GRT that does not converge: read the overflow trajectory at iteration 10, fix the wall, do not wait 30 iterations | 39 kits over 12 h in GRT; KV hg / hgi 19 types | LONG-RUN-0315 (list), FABLE-FIX-KV-HG, die owners |
| 5 | QC, HEAD, S81 | Residual hold pass at 833 ps on kept routed DBs; sign-off corners serialized | about 25 builds (01:25 lever 1), 3 signed tonight | QC-HOLD-0030, HARVEST-0330, FLOW-FIX-2045 |
| 6 | all 4 | Seat the first rank, then stage: the placed-pin census now gives the numbers | col_h10_r1, lepe_mu_LP, hd_tile, QC fe / ctl, slice C 11 types | LONG-LEG-0040, PRECHECK-1119, kit generator owner |
| 7 | QC, KV, S81 | 1.296 um M5 halo on hard-core pin faces | 11 st_a types; kv3_pc 6; col_h9_r2 to confirm | QC-SUST-MACRO-1119, KV-PC-PG-2330 |
| 8 | KV | pv shared trunk: anchor the mapped inverter at the trunk end | kv3_pv family (v5, v5n, v6n, v8, v12 seen) | FABLE-FIX-KV-PV-2140 |

### Lever 1. Reach is a plan property
**Evidence (V).** Headline 1 to 3. Code on main a67025cea20: `tools/die_plan/cbc_rules.py:7` reads `OT_CBC_REACH_UM`, default 300; `gen_phys.py` near line 9010 calls `RT.for_type(P, tn)` and raises when the solve differs from the captured tree; `tools/conftest.py:15` already pins 405 for suites drawn at the old rule. The captured tree carries `reach_um` and `plan_reach_um` (`reset_tree.py:699`).
**Root cause.** A die-wide rule change went in as a tool default while three live plans were bound under the old value. The plan does not carry its own reach into the kit generator.
**Fix (P).**
1. `install_bound_native_reset`: solve with the captured tree's `plan_reach_um` (fall back to the default only when the tree has none). The identity guard stays as is; a bind from another plan or an edited graph still stops.
2. Until that is on `rt/current`: the wave sets `OT_CBC_REACH_UM` per plan event from the bind's captured value (405 for D8i, V0E, D25e3) in the kit_rtl / gen environment. One marker field, no tool change.
3. New events bind at 300 and carry 300; nothing changes for them.
4. Retry key (FABLE-FLOW-0245 class 2, still open): digest of the item inputs without the rt sha, so a PLAN-class refusal is not relaunched until an input changes.
**Check.** After the fix, `gen` on `cbn_q01__clab6e67f2` and `seqhost__t1` passes the guard with 0 changed fields. If any field still differs, that item has a second cause and goes to its die owner.
**Limit.** Kits on D8i / V0E / D25e3 are at the 405 reach. They count under the any-plan rule and keep the fleet on real builds for the 5 to 13 h until the 300 um events bind.

### Lever 2. S81 col 120 -> 2 (J6)
**Evidence (R).** Headline 6. J6 repaired 2 colliding union taps; 120 reset trees within 185.4 um at unchanged boot depth; miter 28,800 neutral + 6,000 live comparisons pass (CODEX-LOG 03:52, 05:03, 06:48). Live col kits: `u_bin_* -> u_lpad_*` zero-logic cross-tap ends (01:25 lever 2), hold -45 to -100 at CTS after the subtree balance.
**Root cause of the two open items (I).** R1 and R2 are one layout with different measured boundary dates and different ROM content. Both are personalization, not structure.
**Fix (P).**
1. SDC: one SDC per master = per-port worst case over the members (earliest arrival for hold, latest for setup). Members sign by inheritance when their own window is inside the master's. Estimator first: the window spread per port over the 60 members; if it is under about 40 ps it costs nothing.
2. ROM: the 43 instance identities differ by content only if the macro LEF and timing view are the same. Bind them as one ROM master + per-instance mask (owner yes on ROM / name inherit, 11-20). Check the 43 for equal LEF and lib before anything else.
3. Put the `bin -> lpad` lockup latch (launch tap, hop under 200 um) into the two masters in the same event. Without it the two builds fail hold as the 24 D8i kits do.
4. Run the two masters as representatives first (owner: reps first); no 120-kit wave.

### Lever 3. Superset pinout on the other classes
**Evidence (R, SIGN-PROFILE-0400 02:26).** 275 classes, 681 members hashed, 0 classes inherit. Members differ in cland link count and direction (S81 68 classes), clock tap ports (68), straps (64), reset / start outputs (54).
**Done tonight (R).** UNIFY step 1b 30852a695c8 on main; class-window solver 97335512bc7; leaf VQ 4-bit SID strap 71d94ae0db0 GREEN 139/139; t40 native alias strict 0 errors, LATCHECK 873/873, 0 added data cycles.
**Fix (P).** Same four moves per class, in class-size order: (a) link ports to the class maximum, unused ones tied neutral at the parent; (b) one tap set per class (union, then `tap_resolve`); (c) ID as `strap_*` pins tied at the parent (owner 10-25); (d) reset / start outputs to the class maximum. Then re-run the structural hash: a class is done when its members hash equal with ROM masked. S81 leaf first (FABLE-SUPERSET-0415 section 9.2, no growth), then station, then QC st_a / st_b / su.

### Lever 4. GRT that does not converge
**Evidence.** Headline 4 (V). R (FABLE-FIX-KV-HG 03:22, 08:53): kR with reserved clock sites on M1 to M3 only went 3,581 -> 1,223 -> 195 overflow by iteration 20, 191 of 195 inside head-core boxes; it then ended at TT -310, FF hold -489.5 (PLAN-TRIAGE, a timing class separate from congestion). k13i split form: overflow 6 against 42.
**Root cause.** Overflow at zero capacity (reserved rects, core boxes, PG stubs) cannot be removed by iterations. The 11-14 rule removed the early stop, so these run 30 iterations at about 1 h each.
**Fix (P).**
1. LONG-RUN-0315: for each kit over 12 h in GRT, one row with overflow at iterations 5 / 10 / 20 and the share at zero capacity. Falling by 3x per 10 iterations = keep. Flat or over half at zero capacity = measured unable to sign; the owner's cancel rule applies, and the row names the wall.
2. Reserved clock sites M1 to M3 + one via column becomes the generator default (01:25 lever 7; kR measured it for congestion).
3. This is an estimator on the congestion report, not a new stop inside the flow.

### Lever 5. Residual hold pass at 833 ps
**Evidence.** Headline 5 (R).
**Fix (P).** (1) Up to 3 residual passes on ends still negative; HC-E0 at -0.05 ps / 1 end is the case. (2) Sign-off corners run one after the other under measured admission; slw_st_b_v2 i2r needs only the sign-off rerun on the kept `6_final.odb`. (3) Watchdog fix a7b3fb1f2ac (ECO runner is not the cancelled parent row) is GREEN 45/45 and still in a gate; it stopped 4 ECOs last night. Merge it before more ECOs start.
**Limit.** Small ECO on understood local ends only (owner 10-25). The zero-logic cross-tap classes take the latch (lever 2 item 3), not buffers.

### Lever 6. Seat first, then stage
**Evidence (R).** LONG-LEG pin3 scan 08:52: col_h10_r1 peak 879.8 um; lepe_mu_LP t2 1,529.3 um, of which a macro-pin leg of 1,457.9 um. PRECHECK 08:26: hd_tile worst 988.4 um (cached scan, 8 s). QC-PLAN-R3 08:41: slw_fe_v1 with 10 existing registers seated, worst hops 744.6 -> 189.8, 707.5 -> 179.1, 731.3 -> 147.6 um, 0 cycles added. OPUS-FIX-S81-SLICEC 08:41: kv512_C needs +5 / +3 stages (8,840 flops, 56 taps against 40) and fits at 299.6 / 299.9 um.
**Fix (P).** Order per type: (1) seat the existing first-rank registers FIRM at their plan sites (the QC fe form) and re-scan; (2) only legs still over the reach get a stage row (owner: setup by pipeline stages), priced as kv512_C was. The pin3 scanner (86cf00e2c53 GREEN) is the measure; one table per die before its cut.

### Lever 7. M5 halo on core pin faces
**Evidence (R, QC-SUST-MACRO-1119 08:21).** 1.296 um halo, A/B on epyc10: M5 near-signal pins 78 -> 0; all 20 macro VDD / VSS contact counts equal (minimum 231) in both arms; 0 overlaps. Place-only pilot queued on E7.
**Fix (P).** If the pilot's detailed route shows 0 of the 72 M5 violations, the halo is the construction rule for every hard core with M5 signal pins: QC st_a (11), kv3_pc (6), and col_h9_r2 `u_u_t6` when a J-event kit reaches route.

### Lever 8. KV pv shared trunk
**Evidence (R, FABLE-FIX-KV-PV-2140 04:36, 07:46).** v8h / v8j post-CTS setup -8,430 / -8,287 ps on the east owner-response pad trunk. The mapped inverter sits at (480.7, 1019.3) and drives 1,908.8 um to the terminal Q; folded chain about 3,437 um.
**Fix (P, the lane's).** Anchor the inverter at (1775.5, 596.2): two legs of 192 um, same cycle count. Generic form: a cell on a relay trunk inherits the site of its sink register. v8j's routed result says nothing about the latch form until this is in.

## 2. Closed by Codex tonight (do not redo)

| Item | State (R, CODEX-LOG 03:23 to 08:13 and lane posts) |
|---|---|
| QC V0E | applied on 6 hosts; bind 0, LATCHECK 1,921; controller common master G0 + strict + LATCHECK pass; 130 soft START windows closed at 300 um |
| QC R4 / A3 | strict + LATCHECK 1,921/1,921; A4 fixes one stale release number (2c1e1ca66262); G0 running |
| KV D25e3 | BIND 0 / LAT 2,404 / G0 0; applied; post-apply bind PASS 08:03 |
| KV D26 draft | 56 types; G0 + precheck pass; dc02d274deb3 corrects 77 START roles; strict running |
| S81 D8i bind | wave used the source-tree bind (121 of 125 attempts on differing RTL); sealed bind pointer d8810348da8 + manifest restored on 5 hosts; breaker closed 03:24 |
| S81 J6 | private strict + LATCHECK 873/873, dates equal to D8i, 4 GEN pass |
| S81 J3 | sealed on 5 hosts, parked: bk_sel placed form BAD (reset fanout, south data return) |
| S81 t40 / t7 | t40 native alias strict clean; t7 private strict + LATCHECK pass |
| HEAD r13r | strict bind 26 masters / 358 instances / 0 unbound; LATCHECK 329/329; NOMCAP SerDes + LEP GEN pass; 6 retained r9 routes R-MINIMAL (5 at 833 ps, CTL north 846.7) |
| Signed | HEAD LEP pair (+28.66), coll_ft ECO i1 (+23.38), slw_hc1 residual i2r (-32.99) |
| Flow on main | 100 fallback refusals 4f48b414967; QC external-stop taxonomy e6e6213ad88; UNIFY 1b 30852a695c8; reset-identity evidence classifier ca8544530de |
| Flow in gate | watchdog ECO a7b3fb1f2ac; native GRT FF fallback e56a64de3b8; bind selection a56b75ebec5; fixed-833 sign profile 96d058623b7 (GREEN) |
| Measurement | LONG-LEG pin3 scanner 86cf00e2c53; PRECHECK cached fanout scan 79511d24b72; QC SUST halo A/B; kv512_C corridor price; QC fe reseat |

## 3. Stop list (01:25 stands except its 1000 ps items, plus these)
- No relaunch of a kit whose `gen` ended on the reset identity message with unchanged inputs. No bypass of that guard either.
- No waiting for J5 / V1 / D26 as the only way to generate kits; lever 1 item 2 is one environment value.
- No reading of -209 ps anywhere: 833 ps is fixed and the sign profile refuses -43.
- No late-repair retry of KV kR (TT -310, hold -489.5 after the congestion fix); the hg class is timing now.
- No v8h / v8j result read as proof or disproof of the latch form before the trunk inverter is anchored.
- No J3 apply (parked BAD). No cw9a / cw9b DME form: tap legs 425.9 to 477.5 um against 405, and the J3 fix / no-fix pair both read FF intra -301.91 ps (R, S81-CLOCK-WINDOW 09:00).
- No die hold verdict from the legacy comparator (KV base / v3 -240 / -165 with zero real-view coverage); the type-root clock + boundary lockup proof replaces it.
- No 120-kit col wave before the two J6 masters route. No J6 master without the `bin -> lpad` lockup.
- No station row before the first rank is seated and re-scanned; no east xring station centres for kv512_C (all four hit fixed macros).
- No number from `sta_st_a.sh` (+25.1 ps, no parasitics; the hook result is -121.75).
- No second serdes rck form kit until one of R1 / H25 / T15P is read: T15P ended at setup_est -606 at GRT; R1 and H25 ended exit 2, cause not read.
- No hold-buffer ECO on a zero-logic cross-tap class (unchanged from 01:25).

## 4. Not checked
- Lever 1: I read the guard and the default, not `relay_um`; whether `for_type` takes the reach as an argument or needs a plan field. I did not run gen with `OT_CBC_REACH_UM=405`. The 165 types are distinct kit_wave directory names in 6 h; some may be the same type under two class hashes.
- Whether 300 um on the current binds changes any signed type's captured tree (signed kits are not regenerated, so no).
- Headline 4: `NOPROG.tsv` labels 96 of 358 jobs `stage_odb_cap` (the last log line, not the build stage), so the GRT counts are a lower bound.
- Lever 2: the SDC window spread and the ROM LEF / lib equality are not measured; both are named as the first checks.
- Lever 4: I did not open the congestion reports of the 39 kits; the kR numbers are the lane's.
- HEAD: 16 eligible rows with 0 launches for 67 min at 08:50 (r13r gates); LEP relay place found 27 FIRM overlaps with macros (HEAD-CROSSING 08:54). Not analysed.
- Token, ROM content, LEC and procedural items are out of scope.

# FABLE-CLOSURE-STRATEGY 2026-11-20 01:25 PST (lane FABLE-CLOSURE-0530): what the routed builds say after the 11-20 decisions; the 1000 ps rule signs nothing without a hold pass; three measurement bugs move the die tree down the list

Reviewer: FABLE-CLOSURE-0530 (Fable). Read-only: no job launched, killed or patched; no STA run. Technical PD only; HBM parked.
Gate (R-MINIMAL): DRC 0, routed TT >= -42 ps (owner 11-20: up to 1000 ps on the same routed DB, i.e. >= -209), internal FF hold >= 0, bind + LATCHECK.
Marking: **V** = I opened the file this round. **R** = reported by the named lane. **I** = inferred. **P** = proposal.
This round builds on FABLE-CONVERGE-0215 and the owner decisions of 11-20. Levers below are either not in those decisions and lanes, or covered ones whose evidence says they fall short. The 23:15 list stands where not changed here.
`failure_breakdown.py` 01:11 (V): technical rows are S81 leaf t42 detail_place, serdes__t16 global_place, KV kv3_hub_Wi (no plan view until D25f2). All else is running.

## 0. Headline

1. **Sign-off verdicts of the last 26 h, all hosts (V, `route_results.py --collect` on 7 hosts, then each kit's `signoff/signoff.json` and `eco_*/eco_loop.json`): 80 verdicts, 66 NOT SIGNED.**

| Class | Builds | Detail |
|---|---|---|
| Internal FF hold only (DRC 0, TT >= -42) | 34 | worst -41.4 ps, at most 308 ends, median about -14 ps. 9 of them then passed the late ECO; 25 are open: ECO ERROR 12, EXHAUSTED 8, no ECO 5 |
| TT between -42 and -209, with internal hold also failing | 9 | hd_ctl x3, hd_host_w, sle_su_l1, slw_fw_v2, slw_sc_v1, slice_station t40 / t41; hold -0.4 to -21 ps on 1 to 47 ends |
| S81 col_h9_r2, old plan | 16 | TT -397 to -553 (read loop; J3 moves the ROM); 8 also have 4 or 8 DRC |
| DRC only | 3 | hd_host_n, 3 violations, TT +28 to +32, hold clean, on three plans |
| QC st_a | 4 | 72 DRC each, TT -67 to -100 |

2. **The 1000 ps rule alone signs 0 of the 66.** No build fails on setup alone inside -209. With internal hold brought to zero on the same routed DB it signs 25 + 9 = 34 builds, about 26 distinct types (24 QC, slice_station t40 / t41). The hold pass is the lever; the period is what gives it room.
3. **Buffer padding for hold is what breaks setup at GRT (R, FABLE-FIX-HEAD-MESH 00:28 / 00:48).** hd_tile 3sa: +0.61 at placement RC with 17,047 hold cells, then -711.75 at GRT RC (-201.86 after 1,573 repair cells). 3s, same netlist with no hold cells kept, was at -78.55 and converging. hd_host_w: 28,963 + 30,158 pad cells, -153 at GRT RC, -56.32 routed (R, FABLE-PD-HEAD-0015).
4. **The kit-side clock fix is measured; three die-tree forms are measured worse.** `subtree_balance` before `tap_balance` (main 7109ee911ef): taps over 60 ps 11 -> 0 of 31, worst in-tap range 165 -> 41 ps, FF hold gate -120.2 / 3,603 ends -> -58.2 / 3,201 (R, DIE-CORETAP 00:18, A/B on one col_h9_r1 kit). cw8 is slightly worse than cw6 on every line (R, FABLE-PD-S81-0015).
5. **Two DRC classes repeat with identical counts across plan events (V).** QC st_a: 55 shorts + 17 spacing on M5 at hard-core edges, on the 4.32 um PG lattice. hd_host_n: 3 "Rect Only" on M7, one net.
6. **Placed hops exceed the plan cap in almost every placed kit, even on the box measure that under-reports (V, PRECHECK KIT-SCAN posts 23:27 to 00:59).** S81 13 of 14, 8 of 8, 4 of 4, 7 of 8 kits; every QC kit scanned. A 300 um plan cap does not bound these by itself.

## 1. Levers ranked by closure impact

| # | Die | Lever | Unblocks | Owner |
|---|---|---|---|---|
| 1 | QC, S81, HEAD | Internal hold to zero on the routed DB: ECO re-run, residual passes, GRT hold margin sized to the measured GRT-to-route loss | 34 routed builds, about 26 types | QC-HOLD-0030 lane with flow owner (FLOW-FIX-2045); COORD for the iteration rule |
| 2 | all 4 | Latch, not buffers, for cross-tap hold; a second lockup proof on a fast type; half-cycle rule for every latch | hd_tile, hd_host_w, QC hc / st_b / sc chains, S81 col bin -> lpad; the die-wide decision | FABLE-FIX-HEAD-MESH (proof), QC-PLAN-R3, COL-CENSUS-1119, FABLE-FIX-KV-PV-2140 |
| 3 | all 4 | Tap table from a placed census as the generator default; regenerate kits in flight with the subtree balance | S81 col 216 + slice C 11 + 30 more types; QC 24; hd_host_w, hd_lep0N; KV hub | generator owner (`gen_phys` / `tap_resolve`), DIE-CORETAP-1119, per-die plan owners |
| 4 | all 4 | Placed hop = planned hop: pin-centroid and clock-edge census, firm site for the first rank after a face register | every type with a hard core or a negedge face; the routed TT misses of -50 to -130 with no named class | LONG-LEG-0040, PRECHECK-1119, kit generator owner |
| 5 | QC, KV, S81 | Core M5 pins against the parent M5 PG lattice: static check and one construction rule | 11 st_a types, 6 kv3_pc, col_h9_r2 (60, to confirm on J3) | FABLE-CBC-QK-0130 (rule), QC-SUST-MACRO-1119, KV-PC-PG-2330, PRECHECK-1119 |
| 6 | HEAD, S81 | DRC residue ECO: rip up and re-route the named nets on the routed DB | hd_host_n on the current plan; any build with under about 10 DRC | flow owner (late ECO), HEAD-CROSSING-1119 |
| 7 | KV, then all | Reserved die-clock sites block M1 to M7; limit them to M1 to M3 plus a via column | KV hg / hgi 19 types; HEAD and S81 channels under clock rows | FABLE-FIX-KV-HG-0000 (kR / kSR read), DIE-CORETAP-1119 |
| 8 | all 4 | Re-time die hold on related pairs with the core-tap pricing fix before any further die-tree form | order of work on S81 / KV / QC die clocks | DIE-LEVEL-CHECK-1119, S81-CLOCK-WINDOW-1119 |

### Lever 1. Internal hold to zero on the routed DB
**Evidence (V).** Table in section 0. Per kit: `signoff.json` `internal_hold.wns_ps` / `violators`, `eco_loop.json` verdict. Examples: slice_station__t41 -0.38 ps / 1 end (TT -127.3), t40 -0.99 / 3; sle_sc_v1 -1.38 / 2; slw_sc_v1 -6.87 / 1; slw_hc1 -30.66 / 104; sle_hc0 -41.41 / 308.
R (QC-HOLD-0030): the GRT hold repair ended at +1 to +27 ps on GRT RC with margin 40 in every kit; routed lands -1 to -41. 12 ECOs failed on `prd_mk.sh` "pass dir not staged" (fixed on main 8f3d1679753 / 7e9768a9388); 6 EXHAUSTED kits are within 0.07 to 2.1 ps on 1 or 2 ends; ECO is one iteration by an 11-07 rule.
**Root cause.** The hold repair is sized on GRT RC and the routed RCX moves each end by up to about 65 ps. One ECO pass then pads to a 10 ps target and stops. The setup guard stopped 4 GRT repairs early because setup had no room at 833 ps.
**Fix (P).**
1. Re-run the late ECO on the 12 ERROR kits with the current `prd_mk.sh` (QC-HOLD-0030 action A). No rebuild.
2. Residual passes: up to 3 ECO iterations, each on the ends still negative. This is in FABLE-CONVERGE move 1, which the owner accepted, but QC-HOLD-0030 left `MAX_ITER` at 1 as an owner rule. COORD to state that the 11-20 decision lifts it.
3. Carry the 1000 ps rule into the hold tools: the setup floor of the GRT hold guard and of the ECO is -209 + margin, not -30 (`hold_margin_family.py SETUP_GUARD_PS`, changed 0 -> -30 tonight on main 503558b280b).
4. New kits: GRT hold margin per family = 40 + the measured GRT-to-route loss (p90 of routed minus GRT-RC hold on that family's last builds; about 40 ps on QC hc). An estimator table from the 34 kits, no gate.
5. The 9 builds with TT -46 to -127 sign at 1000 ps once their 1 to 47 hold ends are padded.
**Limit.** This harvests old-plan builds (N3, N4, 3fa87b84b18). They count under the any-plan rule; they do not prove the current plans.

### Lever 2. Latch instead of buffers; do not wait for v8j to route
**Evidence.** Headline 3 (R). R (FABLE-PD-HEAD-0015): each cross-tap pair is padded to window + 25 ps uncertainty + 45 ps guard, so the window is paid twice; form A needs 9,200 fewer cells than the r8 windows and still loses 700 ps at GRT. R (QC-HOLD-0030 class C): the QC internal ends are zero-logic flop -> flop chains (xl write data, lpad / ist pads, st_b hi_pad). R (FABLE-PD-S81-0015): col_h9_r1 has 1,334 cross-tap ends on the zero-logic `u_bin_* -> u_lpad_*` transfer. R (FABLE-FIX-KV-PV-2140 01:07): v8j is in global place; routed not before about 14:00 PST; it carries 32 chained trunk pieces that will fail TT for a reason unrelated to the latch.
V: the latch form is older than KV form C. `ft_hop_lockup_item_event.py` (FTLOCK-S81, 11-10) puts `ot_dp_lk` on the launch station's tap, FIRM at the hop midpoint, 0 pin cycles; `kit_zl_lockup.py` and `test_core_input_lockup.py` are on main. I found no routed record of it in the lane files.
**Root cause.** Buffers buy hold with delay on a shared net, and the delay lands on the setup path at routed RC. A launch-clocked latch buys half a cycle of hold with no delay cell.
**Fix (P).**
1. Read v8j at CTS, not at route: the `pregrt_ff_hold.log` class split (cross_tap near 2k from 47.5k) is the proof of the latch form. Its routed TT will be coloured by the 32-piece class.
2. A second proof on the fastest round trip (HEAD, 2.1 h median): hd_tile with latches on its cross-tap zero-logic and low-logic transfers, pre-GRT hold build off for the cross_tap class. FABLE-FIX-HEAD-MESH owns the kit. If it holds TT near +0.6 through GRT RC, the 700 ps loss is confirmed as the pad cells.
3. Same form as rows for QC hc / st_b / sc chains (QC-PLAN-R3 V1 cut) and S81 `bin -> lpad` (J5). These rows are already asked; this sets their rank above any hold-buffer work.
4. Rule for every latch, to go into PRECHECK as a row (I, from the latch timing; FABLE-PD-KV-2300 A3 found the same on KV): the latch is clocked by the launch tap, and the leg from the latch to the capture flop has T/2, about 200 um. A latch in the receiving type on the receiver's clock adds no margin against skew between the two types. For "a lockup at every type input port" this means the latch sits in the sending type, or the boundary hop is split so the latch is within 200 um of the capture station. Check this on the die-wide design before it is bound.
5. Until latches land on a type: set the pre-GRT cross-tap guard from 45 ps to 0 to 10 where a per-port window already covers the pair (FABLE-PD-HEAD-0015 B.3). A setting on private kits first.

### Lever 3. Tap table from a placed census, as the default
**Evidence.**
- R: hd_host_w: 40 taps in one quarter of the outline, seven near 3,000 sinks, routed NOT SIGNED -56.32 / -21.08 (V in my verdict table). hd_lep0N: 33 taps over the 800 cap, clk_t130 6,597 sinks. Slice C: 53 taps for 95,939 flops (clk_t31 15,011), tap means 217 to 733 ps, about 5,800 ends to -972. QC: placed / planned sink ratio 0.26 to 2.64 on 20 types (QC-PLAN-R3 00:04). S81 J3: 221,868 new station flops on existing taps, TAP-CAP on 84 types, 30 non-col types at 1,028 to 1,936 per tap (S81-DIE-R3 00:58).
- R (FABLE-FIX-S81-SLICEC-0045): `tap_resolve --span-um 300 --target 1000` on placed registers: 53 -> 171 taps, predicted spread 13.7 ps.
- R (DIE-CORETAP 00:18): 508 of 1,499 register taps over 60 ps in 45 D8i kits before the fix.
**Root cause.** The tap table and sink bins come from a census older than the stage tuple, and the kit balancer pads to the latest sink. Each lane found this separately tonight (HEAD r13, QC N46V0, slice C, J5 col taps).
**Fix (P).**
1. Generator default on all four dies: any event that adds or moves stations re-derives taps for the touched types from the newest placed DB of that type (`tap_resolve`, span 300, target 1000), with the die clock rerun in the same event. Types with no placed DB take a density estimate from the plan sites.
2. Kits in flight keep running; a kit that stops after CTS with FF hold under about -60 on cross-tap ends is regenerated on tools >= 7109ee911ef rather than resumed.
3. S81-GEOM-OPUS: the 00:56 table still reads -120.2 median on 24 col_h9_r1 kits "after CORETAP". Check for the `delaybuf_otstb_c*` cells in one of them; if absent, CTS was not re-run and the number is the old one.
4. KV has no such pass yet (hub_Eo, ingest_eng 117 ps internal range): KV-D23-COMPOSE takes it into D26.

### Lever 4. Placed hop = planned hop
**Evidence.**
- R (FABLE-CBC-HEAD-0130): `placed_scan` measures to the macro box. hd_lep0N coll_i3 is 861 um to the pin against 467 scanned; 272 bits over one cycle against 7.
- R (FABLE-FIX-S81-SLICEC-0045): hops from a negedge face have T/2: xr <-> eg 725 to 923 um, wire alone 1,000 to 1,280 ps, 131 ends at -1,422. The station sites were drawn from one source core of a bus.
- V (KIT-SCAN posts): on the box measure, `u_bin_x_i0 -> u_lpad_x_i0` 528 and 547 um on col_h9_r0_p4; `u_bin_leafup_i3 -> u_lpad_leafup_i3` 508 um on c1x_C t6; QC slw_fe_v2 `u_bin_x_stm_p1_i -> u_lpad` 508; tt_ctlm 509; hd_tile 568; kv3_pv_v1n 1,360. The plans of these types pass REACH at 405.
- R (FABLE-PD-S81-0015): `OT_RELAY_POLY WARN` relay chains at 416 to 867 um per hop as placed on five col families.
**Root cause.** Reach is checked on plan sites and measured on placed cells with a box-centre shortcut. The first rank behind a face register is not held at its site, and legs into hard-core pins are not seen.
**Fix (P).**
1. LONG-LEG-0040: finish the pin-centroid and edge-class census (classes: full cycle 405, half cycle 200) and re-summarise every placed kit from raw. One table per die before its next cut: S81 J5 14:00 PST, KV D26 04:00Z, QC V1 06:00Z, HEAD r13.
2. Kit generator owner: the first rank after each face register (`u_lpad_*.r[0]`, relay heads) is placed FIRM at its plan site, as `keep_firm` does for leaf stations. Estimator first: plan site against placed centroid for these ranks on ten kits.
3. Station and relay tools measure from every source core of a bus, and site the last relay at a half-cycle sink (the slice C rule).
4. The 300 um default (S81-DIE-R3 J5) is applied by generators on plan sites; it needs item 2 to hold in the kit.

### Lever 5. Core M5 pins on the parent M5 PG lattice
**Evidence.**
- V (intel1 `.../s29q103S4Q9N46C/items/sle_st_a_v2__pv4242de79/.../5_route_drc.rpt`): 72 = 55 Short + 17 Metal Spacing, all M5, 0.024 um wide, at x 295.836, 300.156, 304.476, 308.796, 313.116 (pitch 4.32) and at y 567.6 / 913.2 / 1250.2, the edges of `u_u_r1 / r2 / r3`. Sources are `pd5_x_hc1_i_*` nets against VSS or against the core. The same 72 on four builds of three types over two events (fable-fix-qc-sta k5 and N46C).
- R (FABLE-CBC-QK-0130 00:58): kv3_pc form B leaves 0 of 688 core PG stripes connected; die M5 stripes stop 1.8 um outside the core, pins start 4.3 um inside; core origin 0.384 um off the 4.32 lattice.
- V (epyc8 `ot-jobs/col_h9_r2__t1__clce45cab5__pv06a1adf6-route-*/work`): 4 M5 shorts of one net against the `u_u_t6` obstruction at (743.2, 49.1) and (744.6, 52.0); the same count on 7 builds.
**Root cause (I for st_a).** Signal pins of a hard core on M5 sit on tracks where the parent's M5 PG stripe ends at the core edge, so the pin access shape shorts to the stripe stub or the core obstruction.
**Fix (P).**
1. PRECHECK row `PG-PIN` (static, LEF + plan): for each hard core, M5 / M4 signal pin shapes against the parent PG lattice at the placed origin and orientation, and core PG pins against parent stripes. It would name st_a and pc before a build.
2. Construction rule (FABLE-CBC-QK form): a core is fed by orthogonal crossings only, and the parent stripe of the pin layer is cut one pitch before a pin face (`sstn_m5_block.tcl` is the existing hook for stations).
3. QC-SUST-MACRO-1119: apply to the 11 st_a types in V1. S81-GEOM-OPUS: read the col_h9_r2 DRC on the first J3 kit; if the 4 shorts remain, the same rule on `u_u_t6`.

### Lever 6. DRC residue ECO
**Evidence (V).** hd_host_n on r3 / r6e / r8b: `5_route_drc.rpt` has 3 "Rect Only" on M7, all on net `rst_start_raw_0` near (510.2, 339.2). TT +28.45 to +32.23, hold gate PASS. The late ECO ran and ended EXHAUSTED: it only handles hold.
**Fix (P).** A DRC scope in the late ECO for builds with few violations: delete the routes of the named nets, re-route them, re-extract, re-sign. For hd_host_n one net. Flow owner; HEAD-CROSSING-1119 runs it on the r8b DB. The type is counted from an older plan, so this is for the current plan and for die composition.

### Lever 7. Reserved die-clock sites as walls
**Evidence (R, FABLE-FIX-KV-HG-0000).** hgi_v1: 106,508 overflow at 9.9 % usage, growing with iterations. 151 reserved rects obstruct M1 to M7; they close 95 of 95 um of the h3mid channel at y 644 and y 1255, and 46 of 95 um of the middle gap. Kits kR / kSR (M1 to M3 only) are in GRT.
**Fix (P).** If kR or kSR clears the capacity-0 overflow, the generator default for reserved clock sites becomes M1 to M3 plus one via column per site, on all dies. HEAD r12 and S81 use the same reservation form; PRECHECK counts channel width lost to reserved rects per type as an estimator.

### Lever 8. Die hold: measure before another tree form
See section 2, bug 1. Order (P): (1) related-pair re-time of S81 cw6, KV D25e v3 and QC with the type-latency fix; (2) kit-side levers 2 and 3; (3) only then cw9 relation clusters within 200 um, on the pairs that remain.

## 2. Do tonight's measurement bugs change the priorities? Yes, in three places

| Bug | What it distorted | Change |
|---|---|---|
| 1. `die_sta_related` prices core taps at the type latency (R: a 450-override type reads about 200 ps late against its own flops) | The die hold bounds -302 / -355 / -248 / -165 and every "window need" derived from them. cw7 / cw8 / `actual_max` were judged on this metric, which also carries 12 to 17 ps per tap of build noise | Die-tree form work drops below the kit-side levers. No die-tree choice and no latch sizing from these numbers until the related-pair re-time with the fix. The latch decision does not depend on them: it tolerates T/2 |
| 2. `placed_scan` / `placed_hops_or.py` measure to the macro box or instance centre (R); they also filter at 0.9 x 405 and hide half-cycle legs | KIT-SCAN "legs > 405", AUTO-GEOM NEED-STATION classes, and every station row chosen from them. Hard-core legs are under-reported by up to 2x | Lever 4 moves up: the pin-centroid census comes before each die's daily cut. Routed TT misses with no named class (st_a -67 to -100, hd_ctl -86 to -99, sle_su_l1 -79, slw_fw_v2 -76, slice_station t41 -127) get this scan before any new row |
| 3. Stale logs copied into kits (R: serdes H23 "-73.5" is the H21 file; hd_tile `pregrt_ff_hold_fallback.log` from tilecomb2) | The 23:15 lever 8 serdes ladder; any fork-kit number | The serdes rck hub-at-pad form has no GRT number: no rck star row for 11 types until H23 or R1 reads at GRT. Kit fork scripts exclude result logs; readers compare log mtime with the run start |
| 4. New (V): `signoff/ff/ep_ff.tsv` port-start rows carry slack values near -7.7e13 ps (slice_station__t24__cl64811a5d) | Any per-end read of port hold from that file | Advisory only; internal rows look sane. Signoff tool owner to fix the unit on port rows |

Also (R, FABLE-FIX-HEAD-MESH 00:28): after `RSZ-0074` inside the GRT TT repair, the step falls back to the unrepaired DB, so `OT_POSTCTS_GATE` -642 on 3s is not a repaired number.

## 3. Stop list (the 23:15 list stands, plus these)
- No further hold buffers for cross-tap or zero-logic classes on any die; no pre-GRT hold build of more than a few thousand cells read as progress.
- No reading of the 1000 ps rule as a harvest by itself; no rebuild of a type whose routed DB is within -42 ps of hold on under about 300 ends.
- No cw8-form build, no port of it to KV or QC, no cw9 before the related-pair re-time; no tree verdict from one build's worst pair.
- No die hold number quoted from an all-pairs or pre-fix run.
- No station row chosen from a box-measured scan on a type with hard cores; no hop judged at 405 um when either end is a negedge face.
- No relaunch of st_a on unchanged M5 pin / stripe geometry; no kv3_pc kit on PDN form B.
- No relaunch of hd_host_w, hd_lep0N, c1x_C or iq_C on their current tap tables; no latency-target balancing of taps over about 2,000 sinks.
- No relaunch of hd_host_n from synthesis for 3 DRC on one net.
- No rck star rows for the serdes family from the H23 number; no log in a forked kit read without its mtime.
- No lockup latch placed at the launch flop of a hop longer than about 200 um, and none clocked by the capture side.
- No J4a / J4b bind (withdrawn); no D8i col kit resumed in place without `resume.json`.
- No wait for the v8j routed TT as the only proof of the latch form.

## 4. Not checked
- The 26 h window: builds whose kit directory was cleaned are not in it. I did not dedupe exactly by type; "about 26 types" is from the names.
- Whether the 25 open hold-only DBs still hold `5_1_grt.odb` / `6_final.odb` (QC-HOLD-0030 verified its 12).
- Lever 2 item 4 is reasoning from the latch form, not a measurement; I did not read the die-wide type-root design, which is not written yet.
- Lever 5: the st_a cause is read from the DRC report geometry only; I did not open the core LEF or the PDN script. col_h9_r2: I did not trace net84128.
- Lever 4: which end moved on the `bin -> lpad` legs (no placed-against-plan diff run).
- Whether any FTLOCK-S81 latch kit ever routed (no record found in lanes/).
- kR / kS / kSR, v8j / v8k, R1, p1, proof_rxr, pkw4, r1be / rae at GRT: none had a number when read (01:1x).
- `lanes/LONG-LEG-CENSUS.*` and a `FABLE-SUPERSET-0415` lane file do not exist yet; I read `posts/LONG-LEG-0040.md` and the 01:17 superset census post.
- FABLE-PD-QC-2300 and FABLE-PD-KV-2300 were read through the 23:15 round; their per-path numbers are R.

---

# FABLE-CLOSURE-STRATEGY 2026-11-19 23:15 PST (2315): setup closes where the plan rows landed; the open class on every die is clock spread between related flops, in the die tree and inside the kit's own taps

Reviewer: FABLE-CLOSURE-2315 (Fable). Read-only: no job launched, killed or patched. Technical PD only; HBM parked.
Gate (R-MINIMAL): DRC 0, routed TT >= -42 ps, hold >= 0, bind + LATCHECK, hops <= 405 um. Nothing below is a new gate, hold or freeze.
Marking: **V** = I opened the log or file this round. **R** = reported by the named lane or Fable report. **I** = inferred. **P** = proposal.
`failure_breakdown.py` 23:12 (V): technical rows are S81 leaf detail_place 3 (t21 +2) and 2 "other flow error" (t52 +1), KV kv3_hub_Wi 1,
KV core qkd_pv_fin_s8_pin (no recipe). Everything else is running. TAP-INSERTION advisory: kit tap skew max S81 288 ps, QC 208 ps, HEAD 77 ps.

## 0. Headline

1. **The first D8i col kits close setup at CTS (V).** 11 of 11 col_h9_r1 kits that have a TT repair log on epyc8
   (`s81-geom-opus-d8g/d8i/tree6/kb_d8i/kits/*/gen/*/tt_setup_repair.log`) read -15.4..-16.0 -> **-13.5..-13.6**, tns -131 (old plan -181).
   Stage census of the 114 builds (V, intel2 `~/s81-geom-opus-d8i-watch/cur.sorted`, 22:58): place 82, CTS 28, GRT 4. No GRT TT yet.
2. **The same kit shows where it fails next (V, `pve3f8a86c/.../run_finish.log`, `hold_gate.log`).** `OT_HOLD_GATE PASS FF wns -120.21
   endpoints 3603` against a structural limit of -140. Tap balance ends with every tap's latest flop near 460 to 499 ps, but the
   earliest flop of a tap is far below it: clk_t9 318..483 (98 sinks), clk 378..469 (1,084), clk_t27 380..487, clk_t14 382..482,
   clk_t10 365..469. Tap means are 388..479 against `OT_TAP_WINDOW` 40. The spread is inside one tap's CTS subtree.
3. **Per-pin offsets on the die tree are measured worse and dropped (R, S81-CLOCK-WINDOW 22:20).** cw7 intra hold TT / FF -336 / -288
   against cw6 -309 / -266; kit-contract FF -269 against -100. KV `actual_max` 300 is also worse (seam -213 against -122), 200 fails
   to build (R, DIE-CORETAP 23:13). Both lanes name one cause: the worst related taps share no tree node for about 17 stages.
   cw8 (clusters of <= 16 taps as one matched sink) built its kit at 23:09 and started GRT (V, epyc10 `s81-clock-window/die/runs/s81/cw8/CHAIN.log`).
4. **HEAD hd_tile at placement RC, one CTS pass (V, epyc10 `fable-fix-head-mesh/tilecomb3*/gen/hd_tile/tt_setup_repair.log`).**
   Control -52.63; ring status + guard registers and flt stations (3s) **+1.18**; the same with form A windows (3sa) **+16.83**.
   All three are in route. r11 (ring registers, `reserved_pg_cut` tools) applied 21:54 (R).
5. **Two QC types and one S81 family fail on a memory read that cannot fit one cycle.** coll_core SRAM 434 ps + 278 ps logic leaves
   49 ps of wire (R, FABLE-PD-QC-2300); pkw3 with the rec_tx stations starts at -628.05, pkw2b at -607.23 (V), so stations do not
   touch it. tt_ctlm r1b -106.09 on two ROM read ends with 591 / 520 ps access (V repair log; R paths).
6. **QC N46T was rebuilt before bind as N46T5** after FABLE-PD-QC-2300 found 59 station rows that stop kit gen and 899 bit sites in
   hard cores (R, QC-PLAN-R3 23:15: FORM 0, LEAF 0, INSIDE 0). Fall fold is N46U4, still timed on the old clock n46ct_e.
7. **KV D25e2 did not bind** (ECTL round trip 25 / 26, R). D25e3 is in G0; D25f rebases on it and lacks five items (R, FABLE-PD-KV-2300).

## 1. Levers ranked by closure impact

| # | die | lever | unblocks | owner |
|---|---|---|---|---|
| 1 | all 4 | related taps within few unshared stages (cw8 form); in-tap range inside the kit; zero-logic chains on one tap or a lockup | die hold on 4 dies; S81 col 216 + slice_station 37 + svc 13; QC cb / hc / su_l0 about 30; KV pv 16; hd_host_w | S81-CLOCK-WINDOW-1119, DIE-CORETAP-1119, DIE-LEVEL-CHECK-1119, FABLE-FIX-KV-PV-2140 |
| 2 | S81 | col: read the 114 D8i kits by family at GRT; bind event J3 (face-bus chains, read loop, SWR), then J4 with START-TREE | 216 col types (incl. 30 h9_r0 p4 to p6 and 60 h9_r2) | S81-GEOM-OPUS, S81-DIE-R3, COL-CENSUS-1119 |
| 3 | QC, S81 | memory read path: register at the macro or early macro clock, as a family rule | coll_core, tt_ctlm; 60 col_h9_r2 (read loop); any type with a ROM / SRAM read cone | OPUS-FIX-QC-COLLCORE, QC-TTCTLM-1119, COL-CENSUS-1119 |
| 4 | QC | N46T5 bind, then proof kits by family; sink bins from placed kits; U4 re-timed on a rebuilt clock | 26 st / su + 22 pad-leg types of 98 | QC-PLAN-R3, QC-SUST-MACRO-1119 |
| 5 | KV | D25e3, then D25f with its five missing items; hg hop with a core between stations; pc PDN | hg / hgi 19, pv 16, pc 6 of 50 | KV-D23-COMPOSE, FABLE-FIX-KV-HG, FABLE-FIX-KV-PV-2140 |
| 6 | S81 | leaf form C sites into the next event (apply first), SWR already in J; keep_firm release | 75 leaf types | FABLE-FIX-S81-LEAF-2140, S81-DIE-R3 |
| 7 | HEAD | hd_tile routed read of 3s / 3sa; hd_host_w tap balance; r12 hd_serdes | last HEAD type; HEAD die hold | FABLE-FIX-HEAD-MESH, HEAD-CROSSING-1119 |
| 8 | S81 | singles: lepe proof6 (RIP1), serdes H25 (AMPIPE), bk_sel core view; bound the in-GRT setup repair | 3 families, about 15 types | FABLE-FIX-S81-LEPE, FABLE-FIX-S81-SERDES, S81-GEOM-OPUS |

### Lever 1. Clock spread between related flops: tree, tap and chain
**Evidence.**
- Die tree. S81 rv4 (R, DIE-LEVEL 22:51, tools d358c674ba): FF intra -301.91, TT hold -309.05; worst FF pair slice_station__t22
  clk_t18 -> clk_t15 with 74 ps of die clock damage on a per-port view; the TT worst is still an in-type range bound (record on rtx-pro only).
  QC (R, FABLE-PD-QC-2300, `kitwin.json`): port window p50 / p90 / max 43 / 92 / 283 ps over 15,964 ports; 30 % need more than the
  57 ps the kits carry; cb tiles up to 283, hc1 / hc2 168, su_l0 200. The -355 pair has 42.8 ps of real die difference.
  KV (R, FABLE-PD-KV-2300): on 466 related pv_N_0 tap pairs the damage is p95 48, max 115 ps; 4 pairs exceed the 75 ps kit window.
  HEAD (R, DIE-LEVEL 21:44): hd_host_w tap means 343 (clk_t1) to 459 (clk_t36) FF, plus 16 flops on one depth-18 leaf at 509.
- Window need follows unshared stage count (R, S81-CLOCK-WINDOW 21:44, cw6): 0 to 2 stages median 1 ps; 6 to 8 median 16;
  18 to 20 median 47 (p90 93). Every limiting partner is in the same partition.
- Inside the kit (V, headline 2): in-tap range 100 to 165 ps on five taps of col_h9_r1; 3,603 FF hold ends at -120 after CTS.
- Chains (R): KV pv has 142,464 zero-logic stage transfers, 37.6k of 47.5k cross-tap ends inside `ot_dp_dly`; coll_core `ur_rec -> u_d5`
  has clocks 198 ps apart and 8,826 hold buffers at 336k cells.
**Root cause.** Three layers of one fault. (a) The region tree balances to one target, so related taps hang on sub-trees that part
17 stages up. (b) The kit balancer lines up each tap's latest flop; the earliest flop of a wide tap stays early. (c) Zero-logic
delay lines are spread by distance, so neighbours land on different taps. Offsets cannot fix (a): the re-tree moves its own error.
**Fix (P).**
1. S81-CLOCK-WINDOW-1119: read cw8 on two marks per family: unshared stages between related taps (target about 5) and port window
   (target <= 40 ps TT and FF). Re-run on tools >= d358c674ba; the cw7 run predates both pricing fixes. If the marks hold, DIE-CORETAP-1119
   ports the same env-gated patch to KV pv regions and QC cb tiles / hc1 / hc2 / su_l0 first (the families over 150 ps).
2. Kit balancer (owner of `OT_TAP_BALANCE`; S81-GEOM-OPUS has the 114 kits to measure on): report min / max per tap as it does now and
   act on range, not only on the mean: a tap with range over about 60 ps gets its CTS sub-tree rebuilt with a smaller sink cluster
   diameter, or is split in the plan by PRECHECK `TAP-CAP` style rows. Estimator first: count taps over 60 ps on the D8i col kits.
3. Chains: KV form C (lockup at each tap-group boundary, 0 cycles, main 29d0a6105e4c) is the general form. When v8h / v8j place,
   take it for QC pad-delay stages (`u_d5`) and the S81 slice_station chains with the same plan key. No hold buffers for this class.
4. DIE-LEVEL-CHECK-1119: die STA on connected pairs only (bind net graph), and pass the partition type to `common_latency_ps`
   (R, S81-CLOCK-WINDOW item 5: a 450-override type reads about 200 ps late against its own flops). Until then quote the
   port-window table per die, not -302 / -355 / -248 / -165.

### Lever 2. S81 col: from CTS to sign-off, and event J
**Evidence.**
- V: headline 1 and 2. R (S81-GEOM-OPUS 22:58): every D8i build was launched with GOAL=finish, which skipped the FF GRT step, so
  col kits stop in `grt_nonport_hold.tcl` ("must explicitly select FF"; V on pve3f8a86c). Fixed on main bf63fa6b676 (R, FLOW-FIX-2045);
  the watcher resumes each stopped kit with GOAL=route. 4 builds died rc 247 at about 7.4 GB peak with no earlyoom line (R).
- V (intel2 `~/s81-die-r/build_j3_r6.log`): J3 r6 admitted on intel1, plan f925a42b1336. R: r5 failed elab on three blackbox
  masters now inside provider cores; r12 / r13 of D8i C6 failed on an absolute path in asbuilt (both fixed in the tree).
- R (COL-CENSUS 21:55): J col rows = 252 face-bus chains in 156 types (108 re-sited, 144 +1 station), form A on 30 h9_r0 p4 to p6
  types (far bit 892 um, 2 stations, 297 um), read loop c12_6 405 -> 59 um on 60 h9_r2. 162 lanes repriced, 174 (type, bus) +1.
  The die side of the frame_int +1 is static only. cc3 bank rows were refused once: 126 banks sat on a tap keepout edge (fixed, cc3b).
- R (S81-CLOCK-WINDOW 22:52): START-TREE on J3 passes CA 0 / 2330; CORE-EARLY-v2 must not go in with J3 (it needs its own tree).
**Fix (P).**
1. S81-GEOM-OPUS: per family, post CTS TT, pre-GRT FF hold ends by class (same tap / cross tap / port) and GRT TT. h9_r1 needs no
   further plan row for setup; its risk is the 3,603 hold ends, so read `OT_PREGRT_FF_HOLD` hold cells and the setup after it.
2. S81-DIE-R3: bind J3 as it is; its LATCHECK is the first measure of the frame_int +1 on the die side. J4 = START-TREE table
   + leaf form C sites (lever 6). Keep D8i kits running; an any-plan sign-off counts.
3. COL-CENSUS-1119: the bank-in +1 stage (CC-BANK-2S) only for families whose cc3b kit is under -42 on `o_x -> xs_q`.
4. The rc 247 kills at 7.4 GB are not a memory size problem; read `dmesg` / cgroup events on one before the resume repeats it (not checked).

### Lever 3. Memory read in one cycle (QC coll_core, tt_ctlm; S81 col_h9_r2)
**Evidence.**
- R (FABLE-PD-QC-2300, `pkw2b_coll/.../4_cts_post_hook.rpt`): SRAM clk -> rd_out 433.6, 8 cells 278.1, 13 buffers 656.6;
  budget for wire 49.5 ps. V: pkw2b -607.23 -> -558.72; pkw3 before repair -628.05 (epyc9 `fable-fix-qc-collcore/opus/pkits/`).
- V (epyc7 `qc-ttctlm-1119-r1/{r1a,r1b}/gen/tt_ctlm/tt_setup_repair.log`): r1a -143.66 -> -128.48; r1b -106.09 (repair to -95.66 raised
  tns to -909). R (QC-TTCTLM 23:13): the two ROM ends are check paths (`fault`, header `h_good`), ROM input slack 607 to 652 (cal)
  and 176 to 211 (leaf); early ROM clock estimate on the r1b DB: -106.09 -> -25.55.
- R (COL-CENSUS): the h9_r2 cfg ROM read loop is the same shape (access time plus a 405 um loop), closed by moving the ROM.
**Root cause.** Macro access time is 52 to 71 % of the period; whatever follows it in the same cycle has under 250 ps.
**Fix (P).**
1. OPUS-FIX-QC-COLLCORE: pkw4 (read one cycle earlier, register at the SRAM column, cycle-neutral, LATCHECK delta 0) is the right
   form; read it by class (sring -> out_data, sring -> g_xf), not by WNS. Keep the `u_d5` chain for lever 1 item 3.
2. QC-TTCTLM-1119: r1be (early ROM clock, no cells) and the registered-read form in parallel; because both ends are checks, a
   register on `fault` / `h_good` costs a cycle on a flag only. Read r1b at GRT TT first: 123 ps of the calrom path is buffers.
3. PRECHECK-1119 (estimator row, all dies): for every ROM / SRAM in a type, macro clk -> Q + 150 ps against the period, and the
   placed distance from its `rd_out` pins to the first register. One row per type; it would have named all three families.

### Lever 4. QC: N46T5, proofs, bins
**Evidence (R unless marked).** N46R3 applied 22:40 (hard-core overlaps 0, straps in cores 70 -> 0). N46T5 (plan 94ab55a0a9ae) and N46U4
(b4381fc956ea) binding; `station_rows_check.py` and the fixed macro-site generator are on main be5f37c39b. PRECHECK 22:49 on N46R3:
STALE-BINS on 24 types, e.g. sle_st_a_v1 kits see 25,855 clock sinks where the plan bins hold 97,712 (0.26x), sle_ctl 1.69x.
V: pk46_cbf1 after TT repair +28.46 (in FABLE-PD-QC-2300); pk46_s2b measures the old bind.
**Fix (P).**
1. QC-PLAN-R3: when N46T5 binds, proof kits to GRT TT side by side: one st_a (per_bit rows), slw_st_b_v1__cle6023ec2 (generator
   sites), one v3-row st_b, one fw, one sle_ctl. Read `OT_TAP_BALANCE` spread and empty taps in each (23 types have moved macros
   under N46R3 clock inputs).
2. Next event: `sink_bins` rebuilt from those placements for the 24 STALE-BINS types; a tap planned for 4x its real load is a tap-spread source (lever 1).
3. U4: re-time TT + FF on a die clock built from the N46T5 plan before it applies; min margins 123.2 / 118.6 sit on a clock
   whose per-port offsets differ by tens of ps between builds.

### Lever 5. KV: D25e3, D25f content, hg and pc
**Evidence.**
- R (KV-D23-COMPOSE 23:10): D25e3 = D25e2 + 4 ECTL rq rows, PRE pass, G0 running, bind after it.
- R (FABLE-PD-KV-2300): staged D25f lacks `r_dly_spread_station_um`, `r_dly_lockup`, pc core-tap v2 rows, depth-16 sidecar rows, M2;
  every DIE-CORETAP tree is on the D25c tap set (127 of the v8b kit's 343 taps are not in it). hg k10: 54 % of 21,073 overflow is
  inside core outlines, 8,504 over head2_e6 (tN hop r0 -> s1 with e6 between its stations), 3,431 where the hst3 leg crosses the
  clock entry cluster. k11 (M2) 19,249, moves the load into the middle column gap. rls rows put 807 bits through an 8.64 um gap on 7 hg types.
- V (epyc9 `opus-kv-hg/{k10,k11}/gen/.../tt_setup_repair.log`, `pregrt_ff_hold.log`, `4_cts_post_hook.rpt`): k10 -204.52 -> -187.44;
  k11 -198.63 unchanged. The first five k11 ends start at input port `ri_head2_u_score_rst_n[0]` and end on reset relays
  `u_rs_ri_head2_u_score_rst_n_r*`; pre-GRT FF hold is all `port_in` (166 ends, -107.2; same-tap 0, cross-tap 0).
- R (23:14, lane just started): kv3_pc pilot stops at PDN-0006: pcc core LEF has M5-only PG pins under M6 / M7 obstructions; 6 pc types.
**Fix (P).**
1. FABLE-FIX-KV-HG: no new polyline round. Re-site the tN stations so no hop has head2_e6 between its ends, and move the hst3 leg
   off (639, 760). On the 7 hg_v1-family types either widen the krsp gap to about 19 um or split the 807-bit trunk over both sides.
   The k11 WNS is a reset input port to relay path: check the reset port's input delay and first relay site before reading it as a station result.
2. KV-D23-COMPOSE: D25f = rebase on D25e3 + tools >= 29d0a6105e4c + rows_C + pc core-tap v2 rows with the v3 tree, together.
   DIE-CORETAP-1119 reruns v3_pvsnake on the D25f tap set before quoting -165 / -156 for it.
3. pc PDN: take the kit-side pdngen cut first (no re-harden of 4 signed cores); the M5 / M6 / M7 core PDN variant only if the cut
   leaves the core rails unconnected. Owner: the lane that posted 23:14.
4. FABLE-FIX-KV-PV-2140: on v8h / v8j, read clock sink count per tap first (54,196 new latches with `OT_TAP_CAP_RECHECK=0`), then hold by class.

### Lever 6. S81 leaf
**Evidence.** R (FABLE-FIX-S81-LEAF-2140 21:55 to 22:53): form C sites `plan_famC.json` 750f33553a0e; tree CW = C + 5 SWR rows + WREG in
strict bind on epyc9 (V: `fable-fix-s81-leaf-2140/cw/build_CW` at 22:29, no kit yet). t21 / t60 DPL-0033 = `keep_firm` station flops on
TAPCELL / PHY_EDGE (fixed, main 069b960d0b85); t42 DPL-0033 = shared bank g_hig_3 split (the form C class); t52 HPWL 1.40x.
SWR is in J (5 nibbles, netlist 3340107e82f0). No leaf GRT number exists for C or A.
**Fix (P).** Under r712, S81-DIE-R3 takes the form C site rows into J4 now (0 cycles, sites only, 16 / 16 banks out of cores) and
FABLE-FIX-S81-LEAF-2140 proves t28 / t31 / t60 / t42 alongside. Marks unchanged: GRT overflow 0 inside 5 extra iterations, HI path under
one cycle. Form A only where the corridor check still shows bits over core tracks. The permanent rule goes into `kit_istations`.

### Lever 7. HEAD
**Evidence.** V: headline 4. V (`pregrt_ff_hold.log`): 3sa ends the pre-GRT hold build with 17,047 hold cells, setup 16.83 -> 0.61,
cross-tap +45, and a final line "after wns -89.34 endpoints 2300"; control 26,274 cells, setup -52.63, "after -91.37 endpoints 2269".
I did not read which class the 2,300 ends are. R: hd_host_w (lever 1); r12 = hd_serdes 37-tap table and a ring reset copy (main 4691070201).
**Fix (P).** FABLE-FIX-HEAD-MESH: routed TT and FF hold of 3s and 3sa decide; take 3sa's windows into the wave kit if both route, since
it needs 9,000 fewer hold cells than the control. Name the class of the 2,300 residual ends before route ends. HEAD-CROSSING-1119:
hd_host_w tap balance to the 390 ps band and the leaf_74 tail in r12, then re-time die hold with its per-port view.

### Lever 8. S81 singles
**Evidence (R).** lepe proof5: DRT-0073 gone with the corrected LEF, GRT overflow 0, then 9 h and 3,200 iterations of in-GRT setup
repair stuck at -270.3 on `u_u_lep.u.rid[834]/D`, killed, no DB. proof6 (RIP1) has 151 flops FIRM, max hop 382 um. serdes H23 GRT TT -73.5 (H22 -179, H18 -192; rck span 89 ps), left on the decoder `am_ok -> xs` path; H25 (AMPIPE,
+1 rck) registers that path, in synth; T15P resumed on epyc10. bk_sel G0 street gap 2 -> 0, core re-harden running.
**Fix (P).** Flow owner: the in-GRT setup repair writes its DB and stops when WNS has not moved for a set number of iterations, so a
structural path costs minutes and leaves a DB to time (a setting, not a gate). The lanes: no change; read proof6 and H25 at GRT TT.

## 2. The 21:15 levers: outcome

| 21:15 lever | outcome |
|---|---|
| 1 valid proof flow | Landed: cleaner and route start (main de25a4bcef8, 77973bd52d2), GOAL=finish runs the FF GRT step (bf63fa6b676). Not yet confirmed on a fresh wave kit (R). hd_tile re-proved on one pass (V). GOAL=cts still skips TT repair (pk46 numbers withdrawn by their lane). |
| 2 S81 col window, bank hops, event J | cw7 measured and dropped; cw8 kit built 23:09. cc3 bind refused on a keepout edge, redone as cc3b. Rows went into J3 (binding, r6). First D8i number -13.5. |
| 3 leaf HI corridor | No GRT number. Tree CW in bind; SWR on main and in J; keep_firm DPL fix on main. |
| 4 QC N46R3 then one event | N46R3 applied. N46T rebuilt twice (KITFIT overlap, then the row-form findings) and is binding as T5. Generator fixed on main. |
| 5 KV next event | D25e2 bind failed on one ECTL error; D25e3 in G0. pv form changed from A to C (lockup). v3_pvsnake adopted as clock config. |
| 6 HEAD r11 | Applied 21:54 with ring registers, flt stations, cut tools. 3s +1.18, 3sa +16.83 at placement RC. Seven-tap cluster: e5c rerun in DME. |
| 7 die hold per-port | S81 re-timed (-438 -> -302 FF) with 28 per-port types; KV and QC classes separated by the two Fable reports. HEAD not re-timed. |
| 8 QC singles | tt_ctlm depth class closed (-17.6), ROM ends named. coll_core wall form -559, cause is the SRAM read. cbf sibling +28.46. |

## 3. Stop list (the 21:15 list stands, plus these)
- No further per-pin offset round on any die tree (cw7 worse on every number), and no `actual_max` round on KV (300 worse, 200 does not build).
- No die hold verdict from an all-pairs number; no S81 CORE-EARLY-v2 on the cw6 tree.
- No coll_core kit read by WNS while the SRAM read is single-cycle; no further wall or station row for the sring -> out_data class.
- No tt_ctlm relaunch of r1a or r2a; no further repair pass on r1b (it raised tns).
- No third hst3 polyline, and no M2 rows from k11 (19,249, load moved into the clock entry gap). No rls rows on the 7 hg_v1-family
  types as they are (807 bits through 8.64 um).
- No pv setup or hold number for D25f from a D25c-plan clock tree; no D25f without tools >= 29d0a6105e4c.
- No quote of a GOAL=cts kit as a TT number; no D8i col kit relaunch from synth for the GRT FF stop (resume from CTS).
- No lepe relaunch unchanged after a stuck in-GRT repair; no hd_tile PICK_SPLIT (3s closes without it).
- No QC exact bit-site rows without `station_rows_check.py`; no N46U4 called proven on n46ct_e.

## 4. Not checked
- cw8 STA (kit only); J3 r6 and D8i C6 r13 bind results; any col family other than h9_r1; any D8i GRT TT; the cause of the rc 247 kills.
- Why the kit balancer leaves 100 to 165 ps inside a tap (lever 1 item 2 is from one kit's `OT_TAP_BALANCE` line; I did not open the CTS tree).
- The class of the 2,300 residual pre-GRT hold ends on hd_tile; routed results of 3s / 3sa / control; r12 content beyond the posts.
- N46T5 and N46U4 bind results; the 24 STALE-BINS types beyond the two examples; pkw3 after repair; pkw4 and r1be (queued / started).
- The slack of the k11 reset-port ends (I read endpoints, not the path table); D25e3 G0; v8h / v8j past gen; the pc PDN lane's forms.
- Leaf tree CW bind and its kits; lepe proof6, serdes H25 / T15P, bk_sel kit; whether S81 slice_station has the zero-logic cross-tap pattern.
- FABLE-PD-S81-2040 and FABLE-PD-HEAD-2040: read for state and stop lists; their per-path numbers are quoted as R, not re-measured.

---

# FABLE-CLOSURE-STRATEGY 2026-11-19 21:15 PST (2115): several proofs were built by an FF-only second pass; the die hold numbers are range bounds; four type families now have a named structural cause

Reviewer: FABLE-CLOSURE-2115 (Fable). Read-only: no job launched, killed or patched. Technical PD only; HBM parked.
Gate (R-MINIMAL): DRC 0, routed TT >= -42 ps, internal FF hold >= 0, bind + LATCHECK. CBC hop 405 um.
Marking: **V** = I opened the log or file this round. **R** = reported by the named lane. **B** = stated in the COORD brief. **I** = inferred. **P** = proposal.
State (V, failure_breakdown 21:10): types signed S81 44 / 394, QC 32 / 130, KV 6 / 56, HEAD 25 / 26; cores S81 64 / 64, QC 70 / 70, KV 68 / 69,
HEAD 5 / 5. The breakdown again lists no technical class (rows are running, lint advisory or "other flow error" QC 15); the classes below
come from kit logs and lane posts since 19:15. Events since 19:15 (R): HEAD r9 20:01 and r10 20:54, KV D25e 20:41, QC N46Q 21:07 applied.

## 0. Headline

1. **Which proofs the stage-ODB cleaner spoiled (V, my scan of `run_route.log` on epyc7 / 9 / 10: CTS passes and TT-repair lines).**
   - Two CTS passes, no TT repair after the second: hd_tile `tileproof`, `tileproof_m4`, `tilecomb2`, `tilecomb2n`, `tilecomb3`. Their
     post-CTS and routed timing is not a setup or hold proof (R, FABLE-PD-HEAD-2040: pass 2 is FF-only, no hold gate, no pre-GRT hold build).
   - Two CTS passes, but repair lines after the second: hd_tile `tilehold`, `tilecomb`. I counted lines only and did not read the corner.
   - One CTS pass, TT repair before GRT: KV `k8`, `k9`, `k10`; S81 leaf `l8_t60`, `l8_t74`, `t31wreg`; QC tt_ctlm `r2a`. These stand.
   - Not scanned (no log found at the path I tried): KV pv `v8b` / `v8d`, QC `pk46_*`, `pkw2b` / `pkw3`, `ps_suc_h`.
2. **Numbers from 19:15 that change.**
   - hd_tile: -139.5 is FF setup of the unsized pass-2 DB; the 1,083 ps pick cone (-274 / -387) is the same unsized netlist. The valid
     number is -52.16 after TT repair (R, reproduced by FABLE-PD-HEAD-2040). PICK_SPLIT is not needed on today's evidence.
   - tilecomb2n "keepouts cost about 0 on WNS, hold -80 vs -147": FF pass-2 numbers. Only its GRT overflow 0 stands.
   - Die GRT overflow results (cw6, kv_7yhr, e5c) are die_trial runs, not the kit flow. Unaffected.
   - Wave kits (R): one CTS pass, so their sign-off numbers stand. Their route job re-places from floorplan, so the routed DB is not
     the placed DB that the visual, AUTO-GEOM and PRECHECK leg scans read. Leg classes hold (same plan); single-leg lengths may not.
3. **Die hold with real views is a bound on three dies (R, DIE-LEVEL 20:06).** S81 -438, QC -355 and HEAD -248 charge a type's whole
   insertion range to every pair (S81 worst pair is col_h9_r2 to itself; HEAD is hd_host_w, 211 ps range at FF). Only KV -119.9
   (1,692 pairs, core ETM pins) is close to a measurement. Per-port arrivals are on main `7c9608fcb5`; 79 types are being extracted.
4. **New structural causes found since 19:15 (R).** Leaf: shared hi-quad banks are sited at a centroid inside a core on all 75 leaf
   types. KV pv hold: 90 % of 47,549 cross-tap ends are stage k -> k+1 of zero-logic pad delay lines. QC st / su: macros on a
   quarter-height grid. HEAD: landing ring built without STATUS_REG on a half-cycle crossing. Each is a generator rule, not a kit setting.

## 1. Levers ranked by closure impact

| # | die | lever | unblocks | owner |
|---|---|---|---|---|
| 1 | all 4 | route stage never rebuilds from floorplan; re-run only the spoiled proofs | every proof read; hd_tile decision | FLOW-FIX-2045; FABLE-FIX-HEAD-MESH-O |
| 2 | S81 | cw7 per-pin tap balance -> col window 40 ps; cc3 bank moves; event J | 216 col + 37 slice_station + 13 svc types | S81-CLOCK-WINDOW-1119, COL-CENSUS-1119, S81-DIE-R3 |
| 3 | S81 | leaf HI-corridor: bank sites out of cores (form C), lane gaps >= 30 um where needed (A) | 75 leaf types | FABLE-FIX-S81-LEAF, S81-DIE-R3 |
| 4 | QC | N46R3 then one event N46T: SUST-MACRO rows + PADLEG B / A + su-lane rows; macro siting by connectivity | 26 st / su + 22 pad-leg + sle_ctl types of 98 | QC-PLAN-R3, QC-SUST-MACRO-1119, QC-PADLEG-1119 |
| 5 | KV | next event: 17-type rls rows, pc v3 offsets + pv DME, pv delay-line station spread | hg / hgi 19 + pv 16 of 50 | KV-D23-COMPOSE, FABLE-FIX-KV-HG, FABLE-FIX-KV-PV, DIE-CORETAP-1119 |
| 6 | HEAD | r11: ring status + guard reg, flt site, 7-tap spine cluster at 55 ps, strap-cut tools | hd_tile = last HEAD type; hd_serdes re-sign | HEAD-CROSSING-1119, FABLE-FIX-HEAD-MESH-O |
| 7 | all 4 | die hold: per-port views, then same-tap or lockup form on zero-logic cross-tap chains | die hold on 4 dies | DIE-LEVEL-CHECK-1119, DIE-CORETAP-1119 |
| 8 | QC | singles: tt_ctlm R1 + R2 together; coll_core w3; cbf_q00_s2 re-pick | 3 to 5 types | QC-TTCTLM-1119, OPUS-FIX-QC-COLLCORE, QC-PLAN-R3 |

### Lever 1. A valid proof flow
**Evidence.** R (FABLE-PD-HEAD-2040, `tilecomb2 run_route.log`, `stage_odb_cap.log`): STAGE-CAP deleted `2_1..3_5` and `4_1_cts.odb` during
pass 1; `make grt CORNER=BC` then rebuilt from `2_1_floorplan` with FF libraries only and went to GRT with no TT repair, no hold gate.
Pass 2 balanced taps to 450 ps at FF; the same DB has 590 ps at TT, 140 ps off the type contract. V: scan in headline 1.
**Root cause.** A make chain whose prerequisites can be deleted under it, and a GRT target that carries one corner.
**Fix (P).**
1. FLOW-FIX-2045: the cleaner never deletes a stage file that a later target of the same kit still lists as a prerequisite; the route
   job stops with a named error when `4_cts.odb` prerequisites are missing instead of rebuilding.
2. Same lane: the route job starts from the placed DB the review read, in the TT + FF session. One log line `OT_FLOW_PASS n=1 corners=tt,ff`
   so a reader can check a proof with one grep. This is an estimator line, not a gate.
3. FABLE-FIX-HEAD-MESH-O: relaunch one hd_tile proof only (Lever 6 rows in it). Do not re-run tileproof, tilecomb2, tilecomb2n as they were.
4. FABLE-FIX-KV-PV, QC-PLAN-R3, OPUS-FIX-QC-COLLCORE: run the same two greps on v8b / v8d, pk46_s2b, pkw2b before quoting their numbers again.

### Lever 2. S81 col and slice_station: the 40 ps window from the tree, bank hops, event J
**Evidence.**
- R (S81-CLOCK-WINDOW 19:24): ports needing more than 40 ps on cw6: col 4,532 / 10,199, leaf 2,132 / 5,425, slice_station 660 / 2,016,
  svc_rs 993 / 1,571. All nominal skew (median need 50 to 69 ps, derate share about 0). cw6 residual before balance: regular
  p5 / p95 -32 / +27 ps, core -26 / +41.
- V (epyc10 `s81-clock-window/die/runs/s81/cw7`): kit built 21:07 (`stage_check PASS`), GRT TT / FF started; no STA line yet. It carries
  per-pin sink offsets on 21,383 DME taps and CORE-EARLY-v2 on 2,950 signed pins.
- V (intel2 `col-census-1119-build3.log`): `CC3_BUILD_DONE`, bind exit 0. plan_cc3 = CC-BANK-1 + 1b + WIN40 + CC-BANK-2: hw pval -> e_r0
  222 -> 123 um; bank-in 237 to 306 -> 194 to 207 um on 768 banks, near the floor for one bank serving two ROM halves (R).
- R (S81-DIE-R3 21:06): D8i C6 rebinding as r11 after a schema-probe timeout on epyc8 (load 290 / 96). C5 failed on two real items:
  leaf SWR stations against `CS_SWR_D` 0 in the bound RTL, and svc H8 rows whose 7 per-type defines the die bind did not elaborate.
  slice_station__t51 carried two hard cores that no bound instance has.
**Root cause.** Unchanged from 19:15: the region DME balances to one target, so one instance's ports sit in different sub-trees. New:
the residual is nominal, so per-pin offsets can remove it; the derate-sharing reading is withdrawn by its author.
**Fix (P).**
1. S81-CLOCK-WINDOW-1119: read cw7 against one mark: port spread per col / slice_station instance <= 40 ps TT and FF. DME delivered
   p95 error 52 to 68 ps on KV (R, DIE-CORETAP 19:57), so expect a tail. Ports still over 40 go to cw8 with the e5c composite-sink
   form on those instances only; HEAD-CROSSING-1119 has not yet pointed to that patch (R 19:24), and it is not on main.
2. COL-CENSUS-1119: first CTS TT of the cc3 kits decides bank-in. If any family is under -42 on `o_x -> xs_q`, take CC-BANK-2S
   (+1 stage, bound in parallel as cc3s) for that family; no third move round, 195 um is the floor.
3. S81-DIE-R3: event J as posted (t51 fix, 7 asbuilt defines, START-TREE rows, cw7 offsets). Do not wait in J for the SWR define:
   leaf closes through Lever 3, not through SWR alone.
4. Bind host: the C6 bind lost a round to a 180 s probe on a host at 3x load. Run die binds on epyc10 or epyc9 (P, host choice only).

### Lever 3. S81 leaf: the HI corridor
**Evidence (R, FABLE-FIX-S81-LEAF 19:30, 20:27; V for t31wreg single pass).**
- Hot gcells are not capacity 0: t27keep 668 hot, 1 at capacity 0; t28 sample 700, 41 at 0. 619 / 668 and 604 / 700 lie inside a
  hard-core box (lanes, vn_a), where only M6 + M8 horizontal remain: 6 tracks per 0.57 um gcell against usage 7 to 12.
- Demand: each g_hig group is a 1,025-bit two-stage bus; on t28, 844 and 942 of 1,025 bits of two groups cross a lane box.
- `kit_istations` sites each shared hi-quad bank at the bit-weighted centroid of its lanes. That point is inside a core for 5 / 8 banks
  on t28 and t31 and for 1 to 8 of 8 on all 75 leaf types. The placer splits the bank, and the bus crosses the core twice.
- t31 with WREG: CTS TT -1,263 -> -1,044.6; the bank path left the worst list. New worst: g_ln_8 cst_hi q[70] -> g_ln_12, 1,906 ps.
**Root cause.** A station site rule (centroid) that ignores hard cores. My 19:15 capacity-0 inference was wrong.
**Fix (P).**
1. FABLE-FIX-S81-LEAF: forms C (sites only, 16 / 16 banks out of cores, max hop 359.7 / 403.0 um) and A (lane gaps >= 30.24 um) are
   binding. Read each at GRT: overflow 0 inside 5 extra iterations, and t31 HI path under one cycle.
2. If C passes on t28 and t31, ship C on all 75 types in event J (0 cycles, no lane move). A only on types where the `s81_hi_corridor.py
   check` row still shows bits crossing above over-core tracks (10 / um). B (remap) breaks reach on 103 rows; stop it unless A fails.
3. S81-DIE-R3: make the rule permanent in `kit_istations`: a shared bank site must be outside every hard-core box + halo, else the
   nearest free channel site. The checker stays an estimator row.
4. C's 403.0 um hop on t31 has 2 um of margin to 405; if the placed hop exceeds it, add one bank stage on that quad (+1 cycle).

### Lever 4. QC: N46R3, then one event for macro sites and legs
**Evidence.**
- R (QC-PLAN-R3 20:53, 21:08): N46Q applied (bind + LATCHECK rc 0, 133 / 133 types). N46R3 in bind: 90 real halo straps on 8 types
  (the 408 stale-`contents[]` pins stay), x_ctl_i first hop 378 -> 252 / 252 / 252 on 11 fw types, cbf_q00_s2 collector children
  re-picked by position (max 209.7 um, was 1.3 to 3.0 mm; cause of -1,972), PADLEG 59 rows.
- R (QC-SUST-MACRO 19:54 to 20:54): `add_macro_sites.py` put st macros on a quarter-height grid. Legs are inside closed leaves
  (u_r4 / u_r7 g_pin -> SRAM 450 to 540 um; u_r0 -> btab 627 to 739 um), so no station row can reach them. Rows v2: 218 rows, 26 types,
  +12 regs; st_b far corner 607 to 676 -> <= 347 um, st_a 626 to 739 -> <= 259 um, su_c worst leg 1,216 -> 354 um (+2 cycles per bus).
  The st moves change the solved reset collector tree and add clk_t116, so they need a re-bind. Proof `ps_suc_h` is running.
- R (KV-CROSSING 20:26, QC-PLAN-R3 20:53): seam / pad-group rules on main `82706ebbc0b`; QC port-to-lane mapping fixed `de95785cb6`
  (before it one group row would have pulled every `sl_*` crossing to one latency). Seam groups CS_TXS, CS_RXV, SC_TX, SC_X3.
- V (failure_breakdown): QC "other flow error" 15 types (cbx_q10 + 14). R (SONNET-FIX-QC 20:00): sle_su_l0 gen fails on a SIGNED tap
  label without a contract file; 28 family rows ready.
**Root cause.** Site rules on a generic grid (macros, straps, stations at `leaf_um`) instead of on the pins they serve.
**Fix (P).**
1. QC-PLAN-R3: N46T = SUST-MACRO v2 + PADLEG section B (sle_ctl, 38 rows) and A (fw pass-through, 18 rows) + su-lane family rows, one
   bind. Proof kits on the bound event: one st_b, one sle_ctl, one fw, to GRT TT.
2. QC-SUST-MACRO-1119: change `add_macro_sites.py` itself: a macro goes to the free site nearest its leaf's pin flop, then
   `check_ft_macro_sites` (v1 put ft bit sites inside moved macros: 10 errors). Otherwise the next plan event regenerates the grid.
3. Fall fold: ship as its own event after N46R3 and re-time on a clock built from that plan (R, FABLE-PD-QC: proof clock n46ct_e is older).
4. Read the 15 "other flow error" rows by message once (P, SONNET-FIX-QC): if they are the contract or receipt class (`053f093adedb`),
   they close with N46T tools; I did not open them.

### Lever 5. KV: the event after D25e2
**Evidence.**
- V (epyc9 `opus-kv-hg/k8`, `k9`, `k10`): one CTS pass each, TT repair, GRT started. R (FABLE-FIX-KV-HG 20:04): k9 (section M) post-CTS TT
  -171.9 on 4 ends, all NORAWB FSTART ends that the D25e raw-branch regen removes. eq +694 (was -51.8), eN -> hst3_g +362 (was +10 at
  1,047 um). Every placed hop <= 405 um; station slacks +290 to +632. k8 GRT round 5: 27,571 with the two k7 strips cleared.
- R (19:56): rls rows for all 17 other hg / hgi types (34 t2 leaves split 807 / 1,063 / 807), dry-applied 34 / 34; 14 sites in narrow channels.
- R (FABLE-FIX-KV-PV 20:25, v8b `hold_rows.tsv`): 52,111 hold ends; cross-tap 47,549, of which 42,662 are stage k -> k+1 in zero-logic pad
  delay lines (`dly_spread` puts each stage at span / (n+1), so neighbours land on different taps), 4,270 top tap -> join core tap (-135.1).
  Form A (stages grouped on ceil(L / 405) - 1 stations) on main `9cdfbe5bc0f`, kit v8f building; form B lockup latch queued.
- R (DIE-CORETAP 21:08): v3_pvdme (pcc +30, pcf 0, DME on 16 pv regions): CA 3,915 / 3,915, intra hold -170.9 TT / -164.2 FF, seam
  -122.3 / -123.9, kit-contract -99.6. v2 (pcf -64) made the seam -181. DME on hg / hgi made intra -251 / -234.
- R (KV-D23-COMPOSE 20:46): D25e applied on old tools, so it carries the TRUNK-CHAIN defect (194 merged tail flops).
**Root cause.** hg: one trunk without splits per channel. pv setup: tool defect. pv hold: a delay-line site rule that ignores taps.
**Fix (P).**
1. KV-D23-COMPOSE: next event = the 17-type rls rows + v3 pc offsets + pv DME (15 regions) + `budgets.r_dly_spread_station_um` on the pv
   types when v8f reads hold. Core-tap v2 rows and the v3 tree go in together or not at all.
2. FABLE-FIX-KV-PV: accept form A if cross-tap ends on v8f fall below about 5,000 (the 4,270 join-tap ends remain); those take form B
   or a join-tap sink offset. No hold buffers: the kit is at 539k cells.
3. FABLE-FIX-KV-HG: k9 and k10 GRT round 5 decide the hst3 polyline; port M to the 17 types only through the rls rows, and read the
   14 narrow sites in each type's first kit.
4. No pv setup verdict from any D25e kit: wait for a D25e2-bound kit (merged 0).

### Lever 6. HEAD r11: hd_tile and hd_serdes
**Evidence (R, FABLE-PD-HEAD-2040, measured on the pass-1 repaired DB, placement RC).**
- -52.16: landing ring ctl_w -> `u_cland_i/rv` on the T / 2 crossing (`set_max_delay 416.5`), ring built without STATUS_REG. Same for
  the r8 window and the 50 ps window. -43.4: `flt_h[1] -> flt_x[1]`, one free-placed hop of 944 um (689 um on the r9 wave kit).
  Ten pick ends at -13.2 at most. With the ring path registered and seven spine taps (t3, clk, t7, t8, t10, t12, t13) at 55 ps: +14.43, 0 negative.
- r10 keeps the r7 window rows (84..123); the e5c cluster omits t3 and t13. The r9 / r10 snapshot tools lack `reserved_pg_cut`: access
  passes on 0 / 264 tiles without the M6 strap cut. hd_lep0N: 329 / 390 tap checks outside the offset band, up to 116.7 ps.
- hd_serdes: same ring without STATUS_REG; reset fan 554.6 um; `assign pma_tck = clk`, so the export value 600 / 500 is unmeasured.
- V: `tilecomb2p` (PICK_SPLIT 3) and `tilecomb3s` have no CTS line yet.
**Fix (P).** One event r11, owner HEAD-CROSSING-1119:
1. `landing_status_reg` + `landing_guard_reg` on hd_tile and hd_serdes (0 lane cycles).
2. flt_h sited mid-channel; station rows for u_x line -> u_ad1 (128 b), rir -> u_ad1 (68 b), u_tenh.
3. Die clock: tile cluster grown to the seven spine taps; hd_tile windows re-derived from data-related pairs on that tree; lep0N offsets re-derived.
4. Tools overlay with `reserved_pg_cut` + rail keeper (main `c113ccf41e5`, `909708562a2`) before any hd_tile kit counts.
5. FABLE-FIX-HEAD-MESH-O: one valid proof (Lever 1) with `OT_TT_SETUP_MARGIN 40`. PICK_SPLIT stays at 0 unless that routed proof is under -42;
   it costs +2 cycles on go -> result and its motive was the unsized DB.

### Lever 7. Die hold on all four dies
**Evidence.** R (DIE-LEVEL 20:06): FF intra, contract | real views: KV -174.2 | -119.9 (1,692 pairs); HEAD +1.43 kit-contract | -248.4
(518,810 pairs, 518,784 negative, same-tap pairs included); QC -263.4 | -355.2; S81 -218.8 | -438.3 (104,310 measured, 1,234,034 not).
R 20:23: KV TT intra setup -95.28 is two unconnected core pins (worst pin x worst pin). R 20:42: `port_pinflops` on main, validated on
hd_turn_a (875 / 875 pin flops, insertion equal to the record); extraction running on 79 types.
**Root cause.** The type view has one insertion range per type; the die tool pairs worst pins without connectivity.
**Fix (P).**
1. DIE-LEVEL-CHECK-1119: re-time with per-port views; then split negative pairs into (a) zero-logic cross-tap, (b) core tap late,
   (c) rest. Pair core views only on connected pins (bind net graph) in the same change.
2. Class (a) is closed in the type kit, by construction: stages of a zero-logic chain share a tap (KV form A) or take a lockup latch
   (form B). PRECHECK-1119: count stage k -> k+1 cross-tap pairs per type on placed S81, QC and HEAD kits (estimator); I expect the
   S81 slice_station and QC pad chains to show the KV pattern (I, not checked).
3. Class (b): per-pin sink offsets where the DME can deliver (pv yes; hg / hgi no, measured worse).
4. HEAD-MESH-O: read `OT_TAP_INSERTION` on the running hd_host_w kit; a 211 ps FF range on a 450 ps target is a tap-tree fault in that type.

### Lever 8. QC singles
- **tt_ctlm (R, 19:22, 20:00; V r2a single pass, at CTS repair).** Cause: all 74,051 generic gates are kept `qfd_bmath` cells mapped one by one
  (216k cells, mux = 3 levels). R1 (+1 cycle start register) cuts ends at >= 24 levels 891 -> 105 but the max stays 33 levels. P: r1b (R1 + R2
  un-keep) is the candidate; R1 alone and R2 alone are controls. LEC of the un-kept netlist is required before any count.
- **coll_core (R 19:46).** w3 bind green (wall + rec_tx stations, LATCHECK 1,921 / 1,921); pkw2b / pkw3 placing. No GRT read yet.
- **cbf_q00_s2.** Fixed in N46R3 (child re-pick); proof = pk46_s2b again to CTS TT on the N46R3 bind.
- **S81 serdes, lepe, bk_sel:** no post since 19:15. Not checked.

## 2. The 19:15 levers: outcome

| 19:15 lever | outcome |
|---|---|
| 1 S81 matched clusters + core taps | cw7 built 21:07 as per-pin offsets on all 21,383 taps (not the composite-sink form); no STA yet. Col window rows withdrawn, CC-WIN40 in cc3. |
| 2 col half-cycle hops | CC-BANK-1b and CC-BANK-2 written and bound (cc3 done); 84 h10 rows adopted; CC-BANK-2S bound in parallel. No CTS number yet. |
| 3 QC station geometry | PADLEG 59 rows in N46R3; x_ctl_i re-spaced; strap rule corrected to `hard_cores[]` (90, not 498). Sections B / A and the `leaf_um` rule not landed. |
| 4 KV D25e2 | D25e applied instead (old tools); D25e2 binding with tail_clear rows and M splits on hgi_v1. k9 proves M at CTS. v2 tree rejected for v3. |
| 5 leaf hot spot | Located. Cause is the bank centroid inside cores, not capacity 0. Tool on main `adc8824d`; forms A / C binding. WREG worth 218 ps only. |
| 6 die hold on real views | Run on 4 dies; result is a bound. Per-port record on main. KV split done by class; S81 / QC / HEAD split waits on extraction. |
| 7 HEAD e5c | r10 carries e5c and the clipped keepouts. Windows not re-derived, 2 spine taps missing, strap cut missing from the snapshot tools. |
| 8 singles | tt_ctlm cause found (kept bmath cells), R1 built. cbf_q00_s2 fixed in plan. coll_core w3 bound. serdes / lepe: no post. |

## 3. Stop list (the 19:15 list stands, plus these)
- No setup or hold reading from tileproof, tileproof_m4, tilecomb2, tilecomb2n, tilecomb3. No `OT_CTS_POST_TIMING` quoted as TT without
  the session corner. No census from a `4_cts.odb` that has not been through TT repair.
- No PICK_SPLIT in the hd_tile plan row on today's evidence. No further hd_tile window change to move WNS: the window moves TNS and ten ends.
- No die hold verdict from -248, -355 or -438, and no tree rebalance to move them or the all-pair -96.
- No DME on KV hg / hgi regions (-251). No pcf late offset (-64): it moves the phy -> pc seam to -181. No more KV tree offset rounds for hold.
- No hold buffers on the pv cross-tap class (47,549 ends, 539k cells). No pv setup verdict from a D25e (old tools) kit.
- No station row for the QC st_a / st_b macro legs (they are inside closed leaves). No private st kit on the N46Q bind (stops at PORT_BIND).
- No QC strap scan with the `contents[]` rule; no fall fold called proven on n46ct_e.
- No further leaf GRT run on the centroid bank sites; no WREG-only leaf kit; no rigid form B remap (103 rows over reach, 622 um).
- No third move round on the col bank-in hop (195 um is the floor); the next step is the +1 stage.
- No tt_ctlm kit with the bmath cells kept; no abc delay-target sweep (r2a and r2b netlists were byte-identical).
- No hd_tile or hd_spn_wshim_rx sign-off counted as e5c-compatible from tools without `reserved_pg_cut`. No use of pma_tck 600 / 500.
- No KV die setup row from the hub_Wi -95 pair (unconnected pins).

## 4. Not checked
- The session corner of tilehold / tilecomb pass 2; double-pass state of pv v8b / v8d / v8f, pk46_*, pkw2b / pkw3, ps_suc_h and of any wave kit.
- cw7 STA (kit built only); any cc3 col kit timing; D8i C6 r11 bind result; forms A / C leaf kits.
- k9 / k10 GRT round 5; v8f hold; v3_pvsnake / v3_snakeall (started 21:08); D25e2 bind result.
- N46R3 bind result; the 15 QC "other flow error" messages; the QC-SUST-MACRO row file content (I read the lane's posts, not the 218 rows).
- Whether S81, QC or HEAD kits have the zero-logic delay-line cross-tap pattern; the cause of the hd_host_w insertion range.
- S81 serdes H23, lepe proof5, bk_sel (no post since 19:15). FABLE-PD-S81-2040 had not landed at 21:20.

# FABLE-CLOSURE-STRATEGY 2026-11-19 19:15 PST (1915, the 20:0x round): crossings are closed; the open items are tap balance inside a type's port set, half-cycle ROM hops, and station geometry

Reviewer: FABLE-CLOSURE-STRATEGY-20xx (Fable). Read-only: no job launched, killed or patched. Technical PD only; HBM parked.
Gate (R-MINIMAL): DRC 0, routed TT >= -42 ps, internal FF hold >= 0, bind + lane latency.
Marking: **V** = I opened the log or file this round. **R** = reported by the named lane. **B** = stated in the COORD brief, not found by me in a
post or log. **I** = inferred. **P** = proposal.
State (V, failure_breakdown 19:10): types signed S81 44 / 394, QC 32 / 130, KV 6 / 56, HEAD 25 / 26; cores S81 64 / 64, QC 70 / 70, KV 68 / 69,
HEAD 5 / 5. The breakdown lists no technical class this round (rows are running, superseded or lint); the classes below come from kit logs and
lane posts since 18:00.

## 0. Headline

1. **Die crossings pass in fall form on S81, KV and QC (V and R).** S81 caV1t 0 / 2,330 TT and FF with start-skew 0 / 635 (39 retime start
   stages). KV F1 0 / 3,915, repeated by DIE-LEVEL p5f. QC n43cb and n46ct_e 0 / 2,993, no crossing under 100 ps. The bound KV sidecar is not
   fall-safe as it stands: 32 of 3,595 ports fail, 21 negative, worst hi -232.0; the K rows are in D25e2. Lever 1 of 18:05 is done.
2. **The S81 col types cannot absorb the cw6 windows (R).** At 87 to 140 ps every family lands at -95 to -170 against routed -44.75 and
   -41.49 today. The ends are fixed-latency config-ROM read loops and half-cycle ROM hops, so no stage can be added. The window has to stay
   at 40 ps, and the tree has to deliver it. Lever 1.
3. **The same tree fault is the S81 die hold (R).** All 200 worst intra pairs capture at a core tap that the region DME lands 33 to 142 ps
   after the launching tap; 144 TT / 155 FF of them are attn_hcore. HEAD e5c shows the fix form works: a matched sub-branch merged as one
   composite sink took the hd_tile cluster worst from 82.7 to 44.2 TT and 35.8 FF without moving the tile root. Lever 1.
4. **My 18:05 reading of the S81 sink tree was wrong.** I inferred the -266 ps was the declared-against-signed difference. Under a plan with
   signed insertions the sink tree is still -510 and cw6 -274 (R, DIE-CORETAP 18:04). The cause is the target file: it priced every core at
   common 250 where most S81 core types have a 450 budget, and it used one value per module where pins differ (capc5r 167 / 103 / 293).
5. **QC legs over 405 um are station geometry, not pad sites (V, `QC-PADLEG-rows.json`).** Every QC kit scanned has them (R: 509, 456, 612 um).
   The first hop is planned from the window centre and the last hop to the core centre. Lever 3.
6. **Three leaf kits use all 30 extra GRT iterations for a residual of a few hundred tracks (V).** t27relay ends at total overflow 344 on
   6.3 % usage; t27stb stops with GRT-0232 at 679. That is a local hot spot, not a capacity problem. Lever 5.

## 1. Levers ranked by closure impact

| # | die | lever | unblocks | owner |
|---|---|---|---|---|
| 1 | S81 (form shared with HEAD) | matched port cluster per col / slice_station instance and core-tap balance in the cw6 region DME; col window stays 40 ps | 216 col + 37 slice_station + 13 svc_rs types; S81 die hold -242 -> about -120 | S81-CLOCK-WINDOW-1119 (tool: DIE-CORETAP-1119) |
| 2 | S81 | col half-cycle ROM hops: CC-BANK-1 (BANK-OUT), CC-BANK-2 (BANK-IN), RDLOOP; D8i hop rows | the same 216 col types (internal setup) | COL-CENSUS-1119, COL-H10-1119, S81-GEOM-OPUS, S81-DIE-R3 |
| 3 | QC | station geometry rule (first hop from window extremes, last station at the consumer centroid) + strap pins off core halos | 22 pad-leg types and 17 strap types of 98 unsigned | QC-PADLEG-1119, QC-PLAN-R3 |
| 4 | KV | D25e2 as one event: hg section L, sidecar fall rows, pv +500, TRUNK-CHAIN tools, pv reset tail; section M next | hg / hgi 19 + pv 16 of 50 unsigned; KV crossing gate on the bound form | KV-D23-COMPOSE, FABLE-FIX-KV-HG, FABLE-FIX-KV-PV |
| 5 | S81 | leaf: WREG stage on the write port; locate the residual GRT hot spot | 75 leaf types | FABLE-FIX-S81-LEAF, S81-DIE-R3 |
| 6 | all 4 | die intra hold on real views: per-pin core-tap targets; structural hold on zero-logic tap-to-tap pairs | die hold on 4 dies | DIE-LEVEL-CHECK-1119, DIE-CORETAP-1119, die clock owners |
| 7 | HEAD | e5c as the r9 clock row; keepouts off the x 6.38 VDD strap; hd_serdes 590 um leg | HEAD die hold; hd_tile re-sign; hd_lep0N | HEAD-CROSSING-1119, FABLE-FIX-HEAD-MESH-O |
| 8 | S81, QC | singles with a known cause: serdes H23 form, lepe RIP1, tt_ctlm retime, coll_core stations, su_c LEF | serdes 16, LP 4, QC 6 types | FABLE-FIX-S81-SERDES, FABLE-FIX-S81-LEPE, SONNET-FIX-QC, OPUS-FIX-QC-COLLCORE |

### Lever 1. S81 clock: deliver the 40 ps window and the core taps from the tree
**Evidence.**
- R (S81-CLOCK-WINDOW 18:28): 7,630 of 21,610 ports are short of the plan window. col_h9_r1 1,879 / 2,700 (gap 100), col_h9_r2 1,619 / 2,400
  (98), slice_station 359 / 2,016 (97), col_h10_r1 599 / 828 (90), svc_hi rs 235 / 807 (79). cw6 delivers median 34 to 49 ps with tails to 87 to 121.
- R (COL-CENSUS 19:08): with the wider rows col_h9_r2 -44.75 -> about -140, col_h9_r1 -41.49 -> about -141, h10_r2 -96 -> about -170,
  p6 about -118 to -133. V (S81-GEOM-OPUS 19:11): the 114 D8i col kits and the 192 CC1 kits carry the flat 40 ps window.
- R (S81-CLOCK-WINDOW 18:39, `cw6/holdpairs.json`): worst 200 intra pairs TT -242.4 to -215.1. Class A attn_hcore 144 / 155 pairs, core tap
  +124 to +142 ps late (plan ins 364, lib max 376, budget 450, need 0). B vn_a / vn_b / ve_m in leaf +52 to 82. C capc5r +43 to 54.
  D bksel_c / gunit_l5 +33 to 38. No trunk or seam pair in the top 200.
- R (HEAD-CROSSING 18:34): e5c cluster spread worst 82.7 -> 44.2 TT, 78.3 -> 35.8 FF; all-tap tile spread 112 -> 95.1; die numbers unchanged.
- R (DIE-CORETAP 11:44, 18:04): the sink-offset tool delivers. KV 482 / 512 ports within 50 ps; S81 5,961 / 6,256 within 50 ps of the (wrong) targets.

**Root cause.** The region DME balances all sinks of a region to one target and treats a core tap like a leaf. Ports of one type instance
come from different sub-trees, and a core tap gets its own long last leg. The spread inside one instance is then tree depth, not distance.
**Fix (P).**
1. S81-CLOCK-WINDOW-1119: in the cw6 kit config, build the clock ports of each col_h9 / col_h10 / slice_station instance as one matched
   sub-branch and merge it into the region DME as one composite sink with snake (the e5c form; do not join at the region root cut).
   Pass mark: port spread per instance <= 40 ps TT and FF on all 216 col types, 50 at most on named exceptions.
2. Same build: core-tap sink offsets from `S81-CW6-CORE-EARLY-v2.json` (per pin, schema budget) for classes A to D. Pass mark: capture
   minus launch <= 25 ps on the 200 pairs; intra hold about -120.
3. The D8i follow-up event carries the tree, the v2 rows and the START-TREE K / DEPTH together, re-planned on the D8i clock.
4. p6 (one port at 129 ps) and col_h9_r2 (rows up to 76 ps from the F2s pilot) still carry wide rows in plan_h3_d8i; set them to 40 in the
   same event, or their kits measure the wrong contract.

### Lever 2. S81 col: the half-cycle ROM hops
**Evidence (R, COL-CENSUS 19:07; reads from 70 kits with a report left).**
- BANK-OUT: hw ROM `pval` launches on the falling edge. p6 e0_u_w -> bn0 -30 to -45 at GRT; h10_r2 e13_u_w -> bn13 -96. Plan hop 214 to 348 um.
- BANK-IN: qbank_S.o_x -> hw `xs_q`, 241 to 306 um in every family; h9_r0_p2 bs1 -78.7 at CTS on 557 ends. No row yet.
- RDLOOP: h9_r2 c12_6 -> s12 -44.75 routed, one end; h9_r1 u_s5 / q6 -41.49. HOP class: covered by D8h / D8i rows in every family.
- V: CC-BANK-1 = 210 bank moves in 132 types, 0 cycles (plan_cc1 8865a8a00190). The tree_cc1 bind is past elab; D8i C5 bind r9 `ELAB_RC=0`.

**Root cause.** A half-cycle path with a 620 ps ROM clk-to-q has room for about 180 um of wire; the banks sit 214 to 348 um away.
**Fix (P).**
1. COL-CENSUS-1119: write CC-BANK-2 now from plan distances (same script, S banks, hop <= 180 um), not after the first CC1 read. BANK-IN is
   in every family and already measured at -78.7.
2. r0 bn0 can move only 39 um (211.68 left). If p6 still shows bn0 under -42 at GRT, shift c2_2 after a read-loop check. Parallel form
   (P, not measured): a capture-side lead on `e_r0` as D8f did on bn11 / bn12 (lead -45).
3. RDLOOP is a 2.75 ps miss on one end: take the c12_6 move (CC-RDLOOP-1); it also gives margin against Lever 1 residue.
4. COL-H10-1119: BANK-OUT on h10_r1 bn8 (348 um) and h10_r2 bn12 / bn13 uses the same rule. Write the h10_r1 west-trunk row for
   lpad_frame_int_i0 -> lpl_7/8/9 now: 815 to 881 um placed is two hops over reach, so the GRT read cannot pass.

### Lever 3. QC: station geometry as a generator rule
**Evidence.**
- V (`lanes/handoff/QC-PADLEG-rows.json`, 19:12): legs over 405 um by family: sle_ctl other -> ist 13,120 and ist -> ist 5,150; sle_fw pad -> core
  2,301; slw_fw pad -> core 1,668, bin -> pd 1,540; slw_fe bin -> pad 1,578; qfd_qc core -> ist 1,877. Cause as written there: first hop 387 to
  435 nominal becomes 456 to 509 placed (bits span about 100 um of window plus pad spread); consumers spread y 500 to 1,190 while `leaf_um`
  is the core centre, so the last hop is 530 to 612 um; out-buses launch 150 to 400 um south of the plan leaf.
- R (PRECHECK 18:15 to 18:44): legs over 405 um in 9 of 9 QC kits scanned; worst 509.0, 456.2, 611.7 um.
- R (QC-PLAN-R3 18:58): 498 strap pin sites inside hard-core halos on 17 types (cbx_q10 x4 70 each, cbn_q11 x2 48, slw_su_l1 x2 35); moved in N46R.
- R (SONNET-FIX-QC 18:23): su_c DRT-0073 was a blanket M6 OBS over 5 pins of qfd_dv_s8x_vmr; override on main `d2c3111be0`, 0 of 1,513 pins without access.

**Fix (P).**
1. QC-PLAN-R3: take the QC-PADLEG rows in the event after N46R (+cycles pre-approved).
2. Make it a `region_form` rule so the next event does not regenerate the legs: first hop measured from the window extremes plus pad
   spread with 85 um margin; last station aimed at the consumer centroid (CBC r713), not `leaf_um`; out-bus first station at the launch flops.
3. The halo scan (footprint + 5.4 um, clock sites + 1.08 um) runs on every plan as a PRECHECK estimator row; HEAD and KV have not been scanned (not checked).
4. sle_ctl has 13,120 + 5,150 station-to-station legs: that is a trunk laid without intermediate sites, not a pad class. Read it separately before pricing cycles.

### Lever 4. KV: D25e2 in one event
**Evidence.**
- V (epyc9 `opus-kv-hg/k8`, post-CTS): setup wns -198.98, hold gate PASS FF -102.3. R (FABLE-FIX-KV-HG 19:05): 5 failing ends (k7 had 12); 4 are
  NORAWB FSTART ends that the D25e raw-branch regen removes; 1 is a dead flop `eq` at (437, 972). hst2 slacks +293 to +597. eN -> g3 is 1,047 um
  at +10 ps because GPL put g3 at (594, 1265).
- V (epyc8 `fable-fix-kv-pv-1119/compose/kit/v8b`, `v8d`): CTS TT -1223.2 -> -674.8 and -1175.2 -> -533.4 after repair; hold PASS -135.1 / -120.8.
  R: the worst path is the TRUNK-CHAIN defect: Yosys merged 194 tail-copy flops on 32 command buses, a 43 um pair built 2.2 mm. Fixed on main `1b95661b75`.
- R (KV-CROSSING 18:21): sidecar fall rows 30 ports K - 1, 2 ports K + 1; a lower bound, start-edge ambiguity not included.

**Fix (P).**
1. KV-D23-COMPOSE: D25e2 as composed (L + fall rows + pv +500 + tools at or after `1b95661b75` + reset tail class R needs `6e2f4ee27af8`).
2. Add the two section M site keys that cost nothing to D25e2 if the bind head has not started: g3 at (451, 948) and `eq` at (44, 40). A
   1,047 um hop at +10 ps is a GPL accident away from failing. The rest of M (tN station, hst3 polyline, t2 split at x 650) waits on k9.
3. First read after the D25e2 bind: pv_v8 worst 50 at CTS. -533 after repair includes the merged flops; no pv row before that read.
4. Time the D25e2 bound sidecar in fall form with the real bind JSON (`write_fall_ports` printed). The 32-port set is a lower bound.

### Lever 5. S81 leaf
**Evidence.**
- V (epyc10 `fable-fix-s81-leaf/proof`): t27relay at extra iteration 30 / 30, total overflow 344 (M5 92, M6 80, M8 74) at 6.32 % usage; t27keep 23 / 30;
  t28wide 10 / 30; t27stb `GRT-0232` in `tapbal_grt.tcl`, overflow 679. t31wreg is in CTS, no TT yet.
- R (FABLE-FIX-S81-LEAF 18:21): WREG on main `6496be9f9175`: one register between the vpw write decode and the bank registers, bench 10 / 10; rows
  `S81-VPW-WREG-ROWS.json` for all 75 leaf types, write availability +1 clock. Target path t31 `sw_a_q -> wmw_q` -1,263 (5 gates + about 40 repeaters, 11 hops).

**Root cause (I).** A few hundred overflowed tracks at 6 % usage means gcells with almost no capacity, as on col_h9_r0_p2 (two capacity-0 gcells
at lpad_xo_i0.q, 77,186 layer-assignment overflow). I did not open the congestion report by gcell.
**Fix (P).**
1. FABLE-FIX-S81-LEAF: dump the overflowed gcells of t27relay (x, y, layer, capacity). If they sit under a keepout, a halo or a pad-station
   column, the fix is a site or blockage row, and 30 iterations are not needed. Pass mark: overflow 0 inside 5 extra iterations.
2. WREG goes into the D8i follow-up for all 75 types when t31wreg posts CTS TT >= -42 on the write-port group.
3. Classes B (vn_a / vn_b / ve_m, +52 to 82 ps) are leaf core taps; they ride Lever 1 item 2.

### Lever 6. Die intra hold on real views
**Evidence.**
- R (DIE-LEVEL 19:02): `bd65fc7d872` wires signed views into die STA. Coverage: S81 cores 37 / 66, types 36 / 395; HEAD 0 / 13, 20 / 26; QC 60 / 80,
  27 / 133; KV 38 / 68, 4 / 56. V: the rv1 runs exist on epyc10 with no result yet (S81 `no die_sta_related.json`).
- Contract numbers (R): S81 -242.4 / -218.8; KV -182.6 / -174.2; QC -267.9 / -263.4; HEAD e2 -186.2 / -172.3 on the r8 snapshot tools.
- R (S81-CLOCK-WINDOW 18:39): a budget-to-budget pair fails once skew passes about 1.5 ps (clkq_min 51.6 - hold 25.1 - uncertainty 25).
- R (HEAD-CROSSING 18:34): kit-contract -73.64 with 37,504 negative pairs on e2, where DIE-LEVEL has +1.4 and 0 on r8. The worst pair sp0 hd_spn
  clk_t4 -> clk_t25 is charged to clk_t25 (row 95) by kitwin and to clk_t4 (row 13) by the gate.

**Root cause.** Zero-logic tap-to-tap paths have 1.5 ps of hold margin, so no tree closes them; they close through the type window (in-kit hold
cells) or a structural stage. The targets fed to the trees used the wrong basis on S81 and probably on KV and QC (same common 250).
**Fix (P).**
1. DIE-LEVEL-CHECK-1119: when rv1 posts, split each die's negative pairs into zero-logic tap-to-tap, core-tap late, and other. Only the
   second class is a tree item.
2. DIE-CORETAP-1119: regenerate KV and QC targets per pin from `schema.core_tap_early_ps` before any new sink build (QC 1,081 taps "short"
   was counted on common 250).
3. HEAD-CROSSING-1119 with DIE-LEVEL: fix the window attribution (the pair's need goes to the port the gate reads) before r9 rows are derived.
4. Zero-logic cross-tap pairs that exceed the 40 ps window after Lever 1: lockup latch or a half-cycle stage on that link (owner 10-27, both forms).

### Lever 7. HEAD
**Evidence.** R: e5c numbers as in the headline; 3 tiles over 40 ps TT by at most 4.2. V (epyc10 `tilecomb2n`, `tilecomb2` run_route.log):
`OT_PG_RAIL_CHECK rows 9680 bad 8`, rail without stack via at x 4.320 to 6.642, y 646.1 to 648.3; both kits are in global placement, no timing yet.
R (FABLE-FIX-HEAD-MESH 18:56): that rail's only VDD M5 strap (x 6.384) runs through the M5-M7 keepouts at x 4.832 to 6.508, so the die clock
cell there has no type VDD path. R (PRECHECK 18:16): hd_serdes u_bin_coll_i0/q -> u_phy.u_link.u_enc.dN 590.3 um.
**Fix (P).**
1. HEAD-CROSSING-1119: e5c is the r9 clock row. Re-derive the keepouts from the e5c tree with one added rule: no M5-M7 keepout within 0.3 um
   of a VDD or VSS strap that is the only strap of a rail segment. Check all 264 tiles, not only the one found.
2. FABLE-FIX-HEAD-MESH-O: tile proof on the e5c windows (five ports at about 50 ps). tilecomb2n decides the keepout effect only.
3. hd_serdes: one station on coll_i0 -> u_enc (+1 cycle) or the bin site moved to within 405 um of u_enc; owner HEAD-CROSSING-1119 for the row.

### Lever 8. Singles with a known cause
- **S81 serdes (V, epyc9 `fable-fix-s81-serdes3/H23`):** `OT_STB_SPAN io_pma_rck[0] sinks 26234 min 1705.3 max 1794.3 span 89.0 limit 110.0 PASS`.
  T1P on the H18 form: span 225.4 FAIL. H22 missed on u_dec.u_syn am_ok -> xs[*], 955 ps of data with a 12-buffer wire chain (R). P: H23 form on
  every serdes type; a station on am_ok -> xs (+1 cycle) if H23 GRT TT still shows that path; H24 M8 trunk only for the insertion (1.7 ns).
- **S81 lepe LP x4 (R, 19:08):** proof5 GRT overflow 0, no DRT-0073, but TT setup -530.5 at CTS. RIP1 rows 1 to 3 are final; rows 4 and 5 wait on the post-GRT report.
- **QC tt_ctlm (R, 19:08):** 49 of 50 worst ends are one cone of 24 logic levels from u_core.u_75259 (541 to 602 ps of cells). P: R1 retime (+1 cycle) in the
  qfd_hp13_cpub39 RTL; R2 fanout split recovers about 100 of 200 ps and does not close alone.
- **QC coll_core (R 13:57; B for the pkw2b / pkw3 split):** -998 = about 60 % SRAM-read detour at the wall, 25 % g_wd -> g_sxo distance (906 to 976 um in one
  cycle), the rest START raw resets. V: pkw2b is at the start of GRT; no pkw3 kit dir exists on epyc9 yet. The form to adopt is w3 (wall + rec_tx stations, latency 21 -> 23).
- **QC su_c x3:** vmr LEF override proofs are in GRT (V, epyc10); N46Q carries the tools.

## 2. The 18:05 levers: outcome

| 18:05 lever | outcome |
|---|---|
| 1 fall-form crossing plan | **Done on 3 dies.** S81 0 / 2,330 + start-skew 0 / 635; KV 0 / 3,915; QC 0 / 2,993. Bound KV sidecar: 32 ports, rows in D25e2. |
| 2 HEAD e6 | Built as e5b / e5c. e5c meets every mark except 3 tiles at <= 44.2 TT. The one-tap parallel form was not tried. No tile proof number. |
| 3 S81 core taps | **My cause was wrong.** Targets were wrong (450 budget, per pin); sink tree withdrawn. The hold classes A to D are now known. |
| 4 D8i | C4 stopped; C5 (core taps back to step C values) binding, elab done. WREG on main. t28 worst path still not printed. |
| 5 KV D25e2 | Composing with L, fall rows, pv +500. k8 confirms the split (12 -> 5 ends). Section M drafted. |
| 6 bk_sel | No post since 18:05. Not checked. |
| 7 QC | w2 bind green; N46P bind green; cbn_q11 running privately with the stretch stop off; pkw2b in GRT. |

## 3. Stop list (the 18:05 list stands, plus these)
- No cw6 per-port window rows on col_h9 / col_h10 or slice_station. A col kit closed against 87 to 140 ps is not a result.
- No S81 sink tree or plan row from `S81-CW6-CORE-EARLY.json` v1 (common 250, one value per module). No core-tap lateness count on common 250 for any die.
- Do not try to close zero-logic tap-to-tap hold with the tree; the margin is 1.5 ps.
- No die hold verdict from a contract number; the gate number is the real-view run (`MEASURED-HOLD` above 0).
- No pv row and no pv verdict from a bind older than `1b95661b75` (194 merged tail flops). No hgi verdict from a kit without the D25e raw-branch regen.
- Do not ship the d25d4 sidecar K unchanged: it fails 32 ports on the fall and 37 on the rise.
- No pad-site or port-edge move for the QC legs; the cause is station geometry. No QC station row aimed at `leaf_um`.
- No relaunch of tt_ctlm as it is, and no station or core-move row for it (0 long hops, 0 detour).
- Wall rows alone do not close coll_core; do not adopt w2 without the rec_tx stations.
- No subtree-balance tap pre-pass on the leaf as built (GRT-0232). No further leaf GRT run to 30 iterations before the hot gcells are located.
- No H22 or H18 rck form on a new serdes kit. Do not read col_h10_r1 from `4_cts_final.rpt` (the -208 is before the tap hook).
- No M5-M7 clock keepout across a rail's only strap. No su_c kit without the vmr LEF override.
- col_h10_r1 lpad_frame_int_i0 -> lpl at 815 to 881 um: do not wait for a GRT read to write the row.

## 4. Not checked
- Any routed TT / FF of a D8i, CC1 or col_h10_r2 col kit (binds still running); whether a matched col cluster fits the cw6 sink and reach caps.
- rv1 real-view hold on all four dies; KV and QC core-tap counts on the schema basis.
- pkw2b GRT round 5 and pkw3; the brief's 60 / 25 split is the 13:57 pk45 read, not a pkw result.
- H23 GRT TT; t31wreg CTS TT; lepe proof5 post-GRT TT; tilecomb2n timing; k9.
- Overflowed gcell positions on t27 / t28 (the capacity-0 cause is inferred).
- The QC-PADLEG rows themselves (I read the header, the class table and the type count 22, not each row); bk_sel; halo scans on KV, HEAD and S81.

# FABLE-CLOSURE-STRATEGY 2026-11-19 18:05 PST (1805): the kit-side window is spent on hd_tile; three dies need a fall-form crossing plan

Reviewer: FABLE-CLOSURE-STRATEGY-18xx (Fable). Read-only: no job launched, killed or patched. Technical PD only; HBM parked.
Gate (R-MINIMAL): DRC 0, routed TT >= -42 ps, internal FF hold >= 0, bind + lane latency.
Marking: **V** = I opened the log or file this round. **R** = reported by the named lane. **I** = inferred. **P** = proposal.
State (V, failure_breakdown 17:49): types signed S81 44 / 394, QC 32 / 130, KV 6 / 56, HEAD 25 / 26. Since 13:15: HEAD r8b applied
13:51; no S81, KV or QC event applied (D8i C4 bind, D25e bind and N46P bind are running). Lanes were quiet 14:00 to 17:45.
Wave rows changed in the last 6 h (V, `kit_wave_state.json`): technical stops are only S81 `KIT_TOPOLOGY_BIND_STALE` 46 rows (col_h10 and
others, wait on the D8i bind), QC `OT_XSTN_STRETCH` 2 (cbn_q11 132 and 147 paths), QC sle_su_l0 gen contract 1. Nothing below is a hold (r703).

## 0. Headline

1. **Every crossing verdict before 13:30 was rise-form; the fall form fails on three dies (V and R).** S81 caV0 136 / 2,330 (hi -304.4),
   KV p4f 252 / 3,915 (hi -174.2) and the p4f2 bind refuses the plan (61,972 MC violations, R), QC n43cb 258 / 2,993 (hi -302.3) and
   n46ct_e 395 (R). The fall-aware planner is on main `ce33771ee32` (V). S81 caV1f with it: plan fail 136 -> 2 (V). Lever 1.
2. **The hd_tile window proofs reached GRT and both fail setup and hold together (V).** tilehold (78 to 114): TT setup_est -271.4, hold_est
   -189.6. tilecomb (84 to 123, M1-M4): TT -157.5, hold_est -219.8; its hold pass stopped after 202 buffers because setup fell to -178.7.
   The related-pair window and the per-port offset forms charge the same 80 to 113 ps (R). No kit-side form is left. Lever 2.
3. **The e5 die-tree cluster meets the target and breaks the rest of the tile (R).** Cluster spread worst 82.7 -> 45.0 TT / 36.2 FF, but
   all-tap tile spread worst 112 -> 160 and kit-contract +1.4 -> -90.4. The join point is wrong, not the idea. Lever 2.
4. **The S81 per-port sink-offset tree reads -508.6 / -451.0 against -242.4 / -218.8 (V).** Skew 141.7 -> 522.2 and setup +466 -> +200:
   the same 266 ps on both sides. The STA plan still declares the old early values, so a tap built early by its signed need is read as
   skew (I). Not a tree verdict yet. Lever 3.
5. **bk_sel was bound with 0 stations because plan defines take bare names only (V, main `e21f466924d`).** Lever 6.

## 1. Levers ranked by closure impact

| # | die | lever | unblocks | owner |
|---|---|---|---|---|
| 1 | S81, KV, QC | fall-form crossing plan on the bound form; depth 16 where the fall lag passes depth 8 | die crossing gate on 3 dies (580 types bind to its K / DEPTH) | S81-CLOCK-WINDOW-1119, KV-CROSSING-1119, QC-PLAN-R3 |
| 2 | HEAD | balance clk / t7 / t8 / t10 / t12 inside the tile DME tree; keepouts in two steps; r8b kits for 3 types | HEAD die hold; hd_lep0N (last type) | HEAD-CROSSING-1119, FABLE-FIX-HEAD-MESH-O |
| 3 | S81 | core taps: signed early rows in the plan and the offsets in the tree, timed together | S81 die hold (3,614 of 6,255 taps late) | DIE-CORETAP-1119, S81-CLOCK-WINDOW-1119 |
| 4 | S81 | D8i C4 on main tools; first reads; leaf write-port stage | 46 stale rows now; leaf 78, col about 150 | S81-DIE-R3, FABLE-FIX-S81-LEAF |
| 5 | KV | D25e2: t2 split in 3 copies + west channel at x 40 + K6 | hg 8 + hgi 11 of 50 unsigned | OPUS-FIX-KV-HG, KV-D23-COMPOSE |
| 6 | S81 | bk_sel: `OT_BKSEL_A2P` define + BK-PLACE row + re-harden dsdv_bksel_c | bk_sel__t2 (16 links over 405 um) | bk_sel lane (author of e21f466924d), S81-DIE-R3 |
| 7 | QC | coll_core wall rows w2 to a GRT read; N46P; cbn_q11 b_d siting | coll_core, cbn_q11 x2, st_a, cbf_q00 | OPUS-FIX-QC-COLLCORE, QC-PLAN-R3 |

### Lever 1. Crossings: plan for the edge the ring writes on
**Evidence.**
- V (epyc10 `s81-clock-window/die/runs/s81/cw6/caV1f/ca`): `count_align_plan.json` fail 2, max_path_ambiguous_cycles 3, max_depth 8, note
  "K/DEPTH chosen for lag L + T/2". CHAIN.log: CA_PLAN 1, CA_BIND 1, STA_CA skipped. caV1g (`--max-depth 16`) has ca_plan and ca_ocv only.
- R (S81-CLOCK-WINDOW 17:49): the 2 fails are xtier s_4S_C <-> bk_sel, width 5,202 ps, L_hi + T/2 = 6,387 > 6,143. Fall ports take K - 1:
  S81 lat_total_vs_old3 -1,478 against -477 in rise form, so the fix lowers latency.
- R (DIE-LEVEL 17:4x, QC-PLAN-R3 13:58): KV and QC numbers as in the headline. QC low side keeps 278 to 294 ps; all fails are the high guard.
- R (KV-CROSSING 13:36): the KV RTL carries the d25d4 sidecar (1,688 parts, K up to 69). Its driver is lost. P4 and ST4 are re-plans in
  another form (ST4: 280 parts, K differs on 3,595 / 3,595 ports).

**Root cause.** `count_align_plan` chose K and depth on the unshifted lag; the gate adds T/2 for a fall write, so each fall port lands T/2 high.
**Fix (P).**
1. S81-CLOCK-WINDOW-1119: post the caV1g gate STA. Pass mark 0 / 2,330 TT and FF with `write_fall_ports` printed in the STA output.
   The new K / DEPTH table rides the event after D8i (with RIP1); D8i is not held for it.
2. KV-CROSSING-1119: the open number is the bound sidecar, not P4. Time the d25d4 `eW_sidecar.json` K / DEPTH as bound, with
   `--ca-write-fall` and `--plan-die`, on the pcsink_fix arrivals. If it fails, the ST4 recipe plus `--write-fall-plan --max-depth 16`
   becomes the KV record form (it already binds with 0 errors and verifies 0 / 2,000), and D25e2 carries its table.
3. QC-PLAN-R3: re-plan on the n46m form with main tools (2,972 of 2,993 ports fall), re-bind, re-time. Same pass mark.
4. HEAD: 28 crossings fall and the numbers do not move (R). No action.

### Lever 2. HEAD hd_tile: the die tree, in a form that keeps the tile root
**Evidence.**
- V (epyc10 `fable-fix-head-mesh/{tilehold,tilecomb}/gen/hd_tile/run_route.log`, OT_POSTCTS_GATE at global route):

| kit | window | TT setup_est / hold_est | FF setup_est / hold_est | note |
|---|---|---|---|---|
| tilehold | 78 to 114 | -271.4 / -189.6 | -158.4 / -168.4 | RSZ-0062, 156 setup ends left |
| tilecomb | 84 to 123 | -157.5 / -219.8 | -19.7 / -192.5 | hold ws -136.3 -> -106.6, 202 buffers, then `OT_HOLD_SETUP_GUARD stop: worst setup -178.68` |

  Pin-register clock mean 631 TT against the 450 bound on both. tilecomb2 (keepouts) restarted at 2_4 PDN at 17:50; no number.
- R (FABLE-FIX-HEAD-MESH-O 13:31): 67 of 70 negative setup ends are pairs inside clk / t7 / t8 / t10 / t12. Per-port mean offsets are
  within 9 ps of 0; the instance range is 90 to 114 ps per port (tolerance 45 to 57). So no constraint can encode it.
- R (HEAD-CROSSING 17:48): e5 result as in the headline; the sub-branch joins at the tile region root cut, so the other 38 taps lose the
  shared top and tile latency moves up to 320 ps in some tiles.
- R (HEAD-CROSSING 13:37, 13:59): reservation rects were centred on the cell's lower-left corner since r3; r8b re-derives 5 types.
  PG straps over the M5-M7 keepouts block 2,044 cells (5.4 %) unless cut. tilecomb2 run 1: PDN-0179 when the M1-M4 rects came before PDN.

**Root cause.** The five taps exchange data and the die tree delivers them from different sub-trees per tile instance. A window can only
move the damage from hold to setup; at 80 to 113 ps it exceeds what the tile's paths have.
**Fix (P).**
1. HEAD-CROSSING-1119: form e6 = the 5-tap matched sub-branch merged inside the tile DME tree (balanced merge with the other 38 taps,
   snake on), tile root unchanged. Pass marks: cluster worst <= 40 ps TT and FF on all 264 tiles; all-tap tile spread worst <= the e2
   value of 112; kit-contract on the r8 windows >= 0.
2. Parallel form (P, not measured): one die tap for the five, with the kit's own tree splitting to the five regions. CPPR then covers the
   pairs by construction. Check the sink count of the merged tap against the 1,200 cap and the insertion against the 631 ps already seen.
3. FABLE-FIX-HEAD-MESH-O: when e6 posts, cut the window on the five ports to about 50 ps (related pairs) and rerun the tile proof.
   Until then tilehold and tilecomb decide nothing more; the control (22 to 38) is the form that had TT -0.32 at placement.
4. Flow order for r9: M5-M7 keepouts before pdngen, M1-M4 rects in PRE_GLOBAL_PLACE.
5. hd_host_e, hd_lep0N and hd_mesh have no r8b kit yet (R 17:48). hd_lep0N is the last unsigned HEAD type; its r8b kit is the next read.

### Lever 3. S81 core taps: plan rows and tree offsets in one timing
**Evidence.**
- V (epyc10 `die-coretap-1119/runs/s81/c1119_cw6_sink/ca/sta_legacy.log`): TT intra setup 200.32, hold -508.55 (452,471 neg), skew
  522.21; FF hold -450.98, kit-contract -339.15 (need 446); `hold_pairs_measured 0`, missing views `core:dsdv_bk_g`, ... (36 or more).
- V (`s81_cw6_sink_offsets.json`): 6,256 offsets are the full early value per module (bk_sel c0 to c3 262.4, c4 607.7; attn 126.3; fE0
  225.6 / 283.0 / 303.2). `s81_cw6_sink.yaml` adds `sink_offsets` and nothing else.
- R (DIE-LEVEL): cw6_d8g has 3,614 of 6,255 core taps over 50 ps late against the signed need; attn_hcore plan early 0, need 126.
- R: on KV the same tool form gained 39 ps (-222.0 -> -182.6); there the declared insertions equal the signed ones.
- V: `runs/s81/sigsta/` (plan_signed.json, ROWS 0, APPLY 0) started at 17:51.

**Root cause (I).** The tree was moved to the signed need while the timed plan still declares the old early per core. The tap-level STA has
no core views, so it prices each core by its declared insertion; the 266 ps on both setup and hold is that difference, not delivery error.
**Fix (P).**
1. DIE-CORETAP-1119: finish sigsta (plan rows early_ps := signed max_clock_tree_path - 250 on the 40 modules) and time c1119_cw6_sink
   against that plan. Post the delivered-against-planned table per module. Pass mark: 90 % of ports within 25 ps and intra hold better
   than -242.4 / -218.8 in the same STA class.
2. If delivery overshoots as on KV's first tree (1.83 x + 85), iterate with feedback once; S81 is snake-all, so the KV leaf fix does not apply.
3. If the result holds, the rows and the tree go to S81-DIE-R3 as one clock event after D8i. rom_elem (1,787 taps) stays unsigned; keep
   its plan early.
4. The kit windows (S81-CW6-WINDOW-ROWS) were measured on cw6 taps; regenerate them from the adopted tree in the same event.

### Lever 4. S81: D8i on main tools, and the leaf write port
**Evidence.**
- R (S81-DIE-R3 17:51): C3 refused by PRE FIXEDCYC (60 GEOM fi_*_r2r1 lanes at fixed_cycles 5, latency rows at 4). C4 `db0bb7b1fcc0`
  prices them; bind r8 running on epyc8.
- V (wave): 46 S81 rows FAIL `KIT_TOPOLOGY_BIND_STALE` on event b4bb6a8b; they need the D8i bind.
- R (FABLE-FIX-S81-LEAF 13:43, 17:49): t28 with the face-bank fix `b482c7548f1` places (HPWL 1.003), CTS WNS -265, TNS -32,537; GRT at
  extra iteration 4 / 30 after 3 h. t27 GRT at 12 / 30.
- R (13:59): t31 worst CTS path -1,263: `u_vp.g_wr1.u_w sw_a_q -> wmw_q`, 2,160 ps = 5 gates + about 40 repeaters over 11 hops. It is
  the 0-cycle 5-writer write-port decode across the leaf. svc_rs: 0 core-to-core links, no row possible.

**Fix (P).**
1. S81-DIE-R3: the D8i tree carries main at or after `f5d3f6de3fc` (face bank, serdes boot detour, pre-route hold margin `ad516f62`,
   lepe LEF override `5eddbd1bfbd`). Without them t14 / t28 / t67, serdes t1 and the lepe kits repeat known stops.
2. FABLE-FIX-S81-LEAF: print the worst CTS path of t28 and t27. If it is the same `g_wr1` decode, add one register on sw_a / sw_m at
   the bank in the leaf RTL (+1 cycle on the write port, priced on its lanes) as a family row for the leaf types with `u_vp`. If not,
   read the t28 GRT congestion map before any row.
3. First D8i reads at CTS: col_h9_r0_p1 and col_h10_r1 (the two proof kits asked at 11:45 and 13:15 still have no post), iq_C t1.

### Lever 5. KV hgi_v1: the chain form
**Evidence (R, FABLE-FIX-KV-HG 13:34 to 13:39).** k7 on d25d4: post-CTS TT -172.5 on 12 ends (4 FSTART, 8 eN pad at -27); the kt class
is gone. GRT iteration 5: landing strip 13,000 to 15,000 -> 17 (W1 proven); total 41,887 (capped); x 200-400 y 600-800 15,490 (W3 at
x 340), x 0-200 y 400-800 13,280 (tail strip). V: no `reg_leaf_split` commit on main since 13:00.
**Root cause.** The t2 stage feeds three consumer channels from one site and W3 shares x 340 with it.
**Fix (P).** OPUS-FIX-KV-HG pushes `reg_leaf_split`. KV-D23-COMPOSE builds D25e2: three kept copies at (40, 285), (40, 618), (40, 950);
polyline `u_hst2_g` [[40, 1270.08], [40, 618]]; K6 = +1 on both i_ectl lanes with sites (40, 340) and (140, 680). Pass mark on k7 repeated:
GRT total under 5,000 at iteration 5, no tile over 2,000, CTS TT >= -42. D25e (bind running) does not carry this; hg / hgi stay off
the count until D25e2. kv3_pc waits on the E2 views in D25e; kv3_pv on the `e9ad080d925` rows.

### Lever 6. S81 bk_sel
**Evidence (V, main `e21f466924d`).** 22 core-to-core links, 7,847 bits, 0 stages, 16 over 405 um. The A2 station hooks exist in the RTL;
plan `verilog_defines` take bare names, so `OT_BKSEL_RC/RS/RO/RLN` bound at 0. `OT_BKSEL_A2P` sets RC 3, RS 3, RO 4, RLN 3.
**Fix (P).** One event: `OT_BKSEL_A2P` in the plan defines, the BK-PLACE core layout row, and dsdv_bksel_c re-hardened with the same macro
(XDX 5 with QRX 1); quarters unchanged. Check in the bind: every control <-> quarter and glue -> quarter link <= (D + 1) x 405 um, and the
control XDX priced on its lanes. The signed dsdv_bksel_c (eco3) stays counted until the new one signs. The 2 remaining S81 CA fails
(s_4S_C <-> bk_sel) should be re-planned after BK-PLACE, since the move changes that lag.

### Lever 7. QC
**Evidence (R).** OPUS-FIX-QC-COLLCORE 17:50: wall rows w2 on n46m, G0 = control; R-REACH-5 238 hops (worst 1,762 um) -> 3; 5 core clock
taps and 282 relay sites moved with their cores (missed by the first rows); a kit on the n46m bind is refused (reset tree differs), so a
private bind is running. QC-PLAN-R3 13:42: n46l / n46n failed PARAM_REGEN (bcf 3 -> 4), n46m green, N46P = f4a + e4 + e5. SONNET-FIX-QC
17:48: ring-group v2 failed (RSZ-0060 at GRT, CTS TT -54.08 against -54.76). V (wave): cbn_q11 x2 stop on OT_XSTN_STRETCH on N46C.
**Fix (P).**
1. OPUS-FIX-QC-COLLCORE: coll_core kit to GRT round 5. Pass mark sum under 5,000 and inside-core share under 30 %; then the worst 20 TT ends.
2. QC-PLAN-R3: N46P is the next event; the cbn_q11 b_d re-site is in f4a. Pass mark on the first cbn_q11 kit: stretched paths 0.
3. QC intra hold is -267.9 with 1,081 taps short of the planned early; it follows Lever 3's method once S81 shows the result.

## 2. The 13:15 levers: outcome

| 13:15 lever | outcome |
|---|---|
| 1 window setup cost | **Measured at GRT: fails** (-157 and -271). Related-pair and offset forms give no gain. QC window rows: no post. |
| 2 S81 CA depth 16 | **Superseded.** The cause was the write edge, not depth; depth 16 is still needed for 2 crossings. |
| 3 D8i one event | C3 refused, C4 binding. cw6 windows in C: not checked. Proof kits not launched. |
| 4 KV D25e | Sealed, bind running. P4 refused in fall form. pc pilot: no GRT read found. |
| 5 QC structure | Wall rows rebased and extended; f4 dropped for f4a as proposed; b_tw bits 0 to 28 solved by re-siting (e5). |
| 6 bk_sel | **Cause found** (define form), macro on main. |
| 7 HEAD via-stack keepouts | Rows ready, origin bug fixed; proof restarted after PDN-0179. |
| 8 `pass rr` | lepe proof5 at 16:37 still prints `pass all 3 margin 5.0` (private kit older than ad516f62). No routed result posted. |

## 3. Stop list (the 13:15 list stands, plus these)
- No further kit-side window form on hd_tile (all-pairs, related-pairs, offsets): all charge 80 to 113 ps. No r9 window raise.
- Do not adopt e5 as built. Do not join a tap sub-branch at a region root cut.
- Do not emit the M1-M4 reservation rects before PDN (PDN-0179); do not run a keepout proof without the strap cut.
- A crossing verdict whose STA output has no `write_fall_ports` is void on S81, KV and QC. Do not fold P4 into any KV event.
- Do not use `--depth-guard-ps 420` (caV3) as the fall fix; it leaves 7 crossings without a depth.
- Do not adopt the S81 sink-offset tree on the -508 read, and do not drop it on that read either; time it against the signed plan rows first.
- No `region.early` and no region DME on KV (stands).
- Do not relaunch hgi_v1 / hg kits on D25d or D25e; the route needs D25e2.
- Do not relaunch the 46 S81 BIND_STALE rows on D8h, or cbn_q11 on N46C.
- No plan define with a value for bk_sel (bare names only); no bk_sel__t2 kit before the macro, the BK-PLACE row and the new bksel_c.
- No reach rows for svc_rs (0 links). No retry of QC f4 (bcf 3 -> 4). Ring-group stays off.

## 4. Not checked
- caV1g gate STA; the d25d4 sidecar in fall form (nobody has run it); the QC re-plan.
- Whether the -266 ps on the S81 sink tree is fully the declared-early difference (I); the tap arrival files are keyed by tree node, and
  I did not map them to ports.
- D8i C4 bind result and whether C carries the cw6 window rows; D25e bind; N46P bind; the w2 private bind.
- tilecomb2 past PDN; any routed hd_tile number; the sink count of a merged five-tap.
- The KV pc_v1 pilot at GRT; t28 / t27 GRT TT; whether t28's worst path is the write-port decode.
- BK-PLACE row content and the bksel_c re-harden state.

# FABLE-CLOSURE-STRATEGY 2026-11-19 13:15 PST (1315): the window moves die hold into the type; the type proof shows what it costs

Reviewer: FABLE-CLOSURE-STRATEGY-13xx (Fable). Read-only: no job launched, killed or patched. Technical PD only; HBM parked.
Gate (R-MINIMAL): DRC 0, routed TT >= -42 ps, internal FF hold >= 0, bind + lane latency.
Marking: **V** = I opened the log or file this round. **R** = reported by the named lane. **I** = inferred. **P** = proposal.
State (V, failure_breakdown 13:11): types signed S81 44 / 394, QC 30 / 130, KV 6 / 56, HEAD 25 / 26. Three events landed since 11:45:
HEAD r7 12:10 and r8 12:51, KV D25d 12:40, S81 D8h 13:02. No kit on any of them has a timing number yet. Nothing below is a hold (r703).

## 0. Headline

1. **The hd_tile window works on the die contract and costs setup in the type (V).** Die: kit-contract fail pairs 45,083 -> 3,787 (R).
   Type proof kits on epyc10, placement RC: control (window 22 to 38) TT -0.32 and 11,722 hold cells; window 78 to 114: TT **-89.86**,
   21,232 hold cells; window 84 to 123 with the M1-M4 form: TT **-59.32**. Neither has routed. r8 put the same form on 18 more types
   with no type proof. Lever 1.
2. **S81 CA fails 114 on cw6 with 9 path-ambiguous cycles; KV failed 26 with 8 and passed 0 / 3,915 with `--max-depth 16` (V both).**
   Same class, one argument, no build. Lever 2.
3. **The measured S81 windows are 4 to 8 times smaller than the planned ones on lepe / lepw (R).** Median 21 to 37 against 162 to 208.
   The lepe kits paid 19 k to 27 k hold cells for the planned window. The rows belong in D8i, not D8j. Lever 3.
4. **QC has the same die-hold class and no window rows (V).** n46ct_e `kitwin.json`: 15,964 ports, median need 43, p90 92; 866 ports
   over 120 in 32 types, all in the cb fabric and su_l0. Nobody has derived rows from it. Lever 1.
5. **Region DME on KV regular taps made hold worse: -222 -> -327.6 (R).** My 11:45 Lever 4 step 3 was wrong for KV. Section 2.

## 1. Levers ranked by closure impact

| # | die | lever | types | owner |
|---|---|---|---|---|
| 1 | HEAD, KV, QC | price the window's setup cost on the type proof before the next window event; QC rows from kitwin | HEAD 26, KV 56, QC 133 | FABLE-FIX-HEAD-MESH-O, KV-PC-HGI-1119, DIE-LEVEL-CHECK-1119 + QC-PLAN-R3 |
| 2 | S81 | CA plan with `--max-depth 16` on cw6; then the die hold number | S81 die gate (all 394) | S81-CLOCK-WINDOW-1119 |
| 3 | S81 | D8i as one event: step C 198 types + cw6 windows + core-early + tap tables; D8h first reads | leaf 78, col about 150, slice C 12, lepe / lepw 4, svc 16 | S81-DIE-R3 |
| 4 | KV | D25e on the pcsink_fix tree: ST1 sidecar, window rows, cap for the 358 ports, pc clock-pin access check | KV 50 unsigned | KV-D23-COMPOSE, KV-CROSSING-1119, KV-PC-HGI-1119 |
| 5 | QC | coll_core wall proof kit; cbf_q00 f4 / f4a; the 29-bit tw_data broadcast | coll_core, cbf_q00 x3, cbn_q11 x2, sle / slw st_a | QC-PLAN-R3, QC-COLL-CORE-1118 |
| 6 | S81 | core-to-core legs inside a kept wrapper: bk_sel__t2 (16 links, to 1,346 um), svc_rs | bk_sel, svc_rs 6, 5 more blind types | no owner for bk_sel; FABLE-FIX-S81-LEAF traces |
| 7 | HEAD | via-stack access rows for the M1-M4 reservation form | hd_tile (264 instances), then 25 types | HEAD-CROSSING-1119, FABLE-FIX-HEAD-MESH-O |
| 8 | QC, S81, HEAD | first kit that prints `pass rr` with the 40 / 30 ps margin; routed result of the slw_hc1 fix run | every short type | HOLD-MARGIN-1119, WAVE-PILOT-FIX |

### Lever 1. The kit hold window: what it buys and what it costs
**Evidence.**
- R (DIE-LEVEL 12:19): HEAD r7, raw intra hold unchanged at -110.2 TT / -101.1 FF; kit-contract -76.1 -> -67.0; negative pairs
  45,083 -> 3,787 (need 82.0 against W 15). r8 raises 307 ports on 18 types and 14 per-type caps (mesh 83 -> 94, serdes 50 -> 94, spn 70 -> 98).
- R (HEAD-CROSSING 12:02): signed hd_tile re-timed with die arrivals: FF -110.2 to -140.7 against the signed -94.9.
- V (epyc10 `fable-fix-head-mesh/*/gen/hd_tile/pregrt_ff_hold.log`, `tt_setup_measure.log`; placement RC, before any setup repair):

| kit | window | TT setup wns / tns | hold before: cross-tap ends / ws | hold cells |
|---|---|---|---|---|
| tileproof (control, r6e rows) | 22 to 38 | -0.32 / -0.32 | 4,120 / -68.6 | 11,722 |
| tilehold (e3 rows) | 78 to 114 | -89.86 / -955 | 6,268 / -137.7 | 21,232 |
| tilecomb (r7 e2 rows + M1-M4) | 84 to 123 | -59.32 / -938 | 7,789 / -132.4 | pass running |

  tns over wns is about 11 to 16 ends: the setup loss sits on a few paths, not on the type. All three kits print
  `pass all 1 margin 5.0` (no `pass rr`) and `OT_HOLD_GATE structural limit -150.0 (... tap window 38.0)`: they are private kits with the
  SDC patched by hand, so the gate line still reads the old window.
- R (KV-CROSSING 12:52): KV rows from pcsink_fix: 4,267 ports raised, 358 need more than the 130 cap; kit-contract need max 145.6.
- V (QC `qc_n46e/chain/qc/n46ct_e/reg/kitwin.json`): 133 types, 15,964 ports, median 43, p90 92, max 283; over 120: 866 ports in 32
  types. Worst: cbn_q00 cldbcda913 283, cbn_q01 273, cbx_q10 cl94a12200_h 259 (median 133 to 184 on the cbx_q10 types), cbf_q00 182
  (median 163), sle_su_l0 200 (median 131). QC kit-contract is -213.9 at W 10. No QC window rows exist in lanes/handoff.

**Root cause.** The window is applied as an early capture on every cross-tap pair, so a cross-tap setup path loses the full window
(60 to 90 ps here) while the hold side gains it. On hd_tile the hold repair doubles (11.7 k -> 21.2 k cells on 111 k) and about a
dozen cross-tap setup ends go 17 to 48 ps under the gate. The die side is solved by the row; the type side is not measured after route.
**Fix (P).**
1. FABLE-FIX-HEAD-MESH-O: on tilecomb, print the setup ends under -42 with launch tap and capture tap. Then one of: (a) those
   pairs into `OT_TAP_PAIR_AFFINITY` (same tap, CRPR returns the window), or (b) the row keeps the low window on the ports whose
   die need is under it (the row is need + 10 per port; check that the 12 ends are not on ports raised by the cap rule).
   Pass mark, routed: TT >= -42 and internal FF hold >= 0. This decides HEAD; it is the one unsigned-critical HEAD item.
2. HEAD-CROSSING-1119: r8's 18 types take the same read at CTS on their first wave kit (TT against the signed value). hd_mesh
   was at -28.4 at CTS before any window (R 11-18); it is the type most likely to leave the gate.
3. DIE-LEVEL-CHECK-1119 derives QC rows from the n46ct_e kitwin with the HEAD script (need + 10, raise only, cap 130);
   QC-PLAN-R3 carries them in the event after f4. About 15,100 ports fit under the cap. The 866 over 120 are 32 cb / su types:
   list them by region pair first; they are a tree item (the cbx_q10 median of 133 to 184 is a whole-type offset, I), not a window item.
4. KV: Lever 4 step 3.
5. Not known: the routed cost on any type. Nothing here should be read as "window adopted = hold closed".

### Lever 2. S81 CA: depth 16
**Evidence (V, epyc10 `s81-clock-window/die/runs/s81/cw6/ca`).** `count_align_plan.json`: `fail 114`, `max_path_ambiguous_cycles 9`,
`old_ring_fail_margin 2247`. `ca_bind.log`: `114 crossings have no RTL K/DEPTH`, first names `xring__s_3S_C__s_4S_C__0`,
`sid_s_4S_C__s_3S_C__0`, `sid_s_7N_C__seqhost__9`, `unit__seqhost__svc_5__1`. STA_CA skipped; legacy summary: intra TT setup +466.5,
hold pairs measured 0 of 1,338,344 (missing core views). KV (R 12:50, same tool): 26 fails with 8 ambiguous cycles (L_hi 7.6 ns over
depth 8) -> 0 / 3,915 with `--max-depth 16`; re-parenting did not converge (26 -> 36 -> 32).
**Root cause (I).** 9 ambiguous cycles need a ring deeper than 8. The depth-16 ring is the RTL-proven form (DIE-S81-11).
**Fix (P).** S81-CLOCK-WINDOW-1119: rerun CA_PLAN on cw6 with the KV argument set (`--max-depth 16 --start-skew-clean`), no clock
rebuild. If fails remain, they are the slice C to slice C xring pairs and need a start-tree parent change, not depth. Then STA_CA
gives the first S81 landed number. The hold number stays unmeasured until the core views load (40 cores have offsets in
S81-CW6-CORE-EARLY.json; DIE-LEVEL-CHECK loads the signed views in the cw6_d8g run).

### Lever 3. S81: one D8i, and read D8h today
**Evidence.**
- R (S81-DIE-R3 13:02): D8h APPLIED, plan h3 8dfedade987b, 5 gen hosts, epyc7 dropped. D8i step C: 198 types change, 0 conflicts
  (551 relay rows / 117 types, geom 114 types, svc H8 16, SWR 6 stations, LEPE row B, CRP2 + WREP5). Step A bind r3 in elaboration.
- R (S81-CLOCK-WINDOW 13:01): cw6 passes reach (399.8 um). 21,610 ports: median 40, 82 % at or under 60, max 142. lepe / lepw LP
  21 to 37 / 51 to 58 (plan 162 to 208); slices 19 to 45; svc_rs 51 to 62 / 125 to 142. Rows for 395 types in S81-CW6-WINDOW-ROWS.json.
- R (S81-DIE-R3 12:45): "Not in C yet: the cw windows." They were handed over at 13:01.
- R (FABLE-FIX-S81-LEPE 12:11): DRT-0073 was an interior M5 pin under a blanket M1-M6 OBS; LEF override on main 5eddbd1bfbd, not yet
  through a GRT. Lepe TT gap is reach: data 1,278 = cells 621 + wire 381 on 4 logic cells + 13 buffers.
- R (FABLE-FIX-S81-LEAF 13:02): the 13 leaf global-place stops are a 3-column bank search; fix b482c7548f18, reaches kits with D8i tools.
**Root cause.** The S81 fixes now arrive in three places (plan rows, clock rows, tools); a type closes only when all three are on one tree.
**Fix (P).**
1. S81-DIE-R3: step C takes the cw6 window rows, the core-early file and the tap tables in the same bind. The windows shrink the
   lepe / slice hold population by construction; leaving them to D8j means one more round of 19 k to 75 k hold cells per kit.
   Re-measure on the D8i clock after the bind (the rows were measured on D8g taps; 1,976 added taps use the nearest tap, to 647 um).
2. First reads on D8h, at CTS: iq_C t1 (tap tables: is any tap still over 400 ps), leaf t16 / t27, col_h9_r1 route, phy__t1.
   col_h9_r0 / col_h10 will still read about -330 / -382 on D8h; that is expected and is not a D8h failure.
3. Two private proof kits on the step C plan as soon as its bind is green (r712): col_h9_r0_p1 and col_h10_r1 to CTS TT. 11:45 asked
   for them; no post.
4. Lepe RIP1 (ri only, aec264abc80) is its own event after D8i. The reset relay row B is unproven on a bus-fed reset pin; if the
   strict bind refuses it, the post-bind relay step is the fallback (R).

### Lever 4. KV: D25e on the tree that measured -182.6
**Evidence (R unless marked).** pcsink_fix: intra hold -222.0 -> -182.6 TT, -202.8 -> -174.2 FF; crossings 0 / 3,915 with depth 16
(4: 3,573, 8: 316, 16: 26). The P4 bind table is the wrong form for the tree (START-TREE-1, root hub_C, 3,595 ports); ST1 re-derive
running. D25e relay_depth: 285 rows / +330 stages on 15 pv types; the other 258 rows are already carried. Blind: 9 types (hubs, pc).
V (epyc10 pilot `gen.log`): the kv3_pc_v1 hold-window pilot is in gen and prints `PIN_FACE_BLOCKED ... tap clk_c6 ... inside u_kvpc2_f`
and `clk_c7 inside u_kvpc3_f`. That warning preceded DRT-0073 on the four S81 lane-core types.
**Fix (P).**
1. KV-D23-COMPOSE: D25e takes the ST1 sidecar only (not P4), on the pcsink_fix arrivals, with the window rows from the same arrivals.
2. KV-PC-HGI-1119: run the `abstract_detail` access check on the pc core views for clk_c4 to c7 before the pilot reaches GRT. If a
   pin has no access, the `lef_overrides` form of 5eddbd1bfbd is the fix and the pilot would otherwise spend its run to learn it.
3. The 358 ports over the cap: max need is 145.6, so a per-type cap of 160 on the types that hold them covers every one with a
   window and no tree work. KV intra setup is +530. Price it on the pc_v1 pilot together with the 130 form (hold cells, routed TT).
4. The count of real cross-tap register paths on pc_v1 (11:45 Lever 4 step 1) is still the missing number; the pilot gives it at CTS.
5. kv3_pv: 501 k to 519 k movable cells and no TT yet. Decide the pv split on the first CTS TT, as at 11:45.

### Lever 5. QC structure
**Evidence (R, QC-PLAN-R3 13:01; V in FABLE-PD-QC-1230).** coll_core: 75 to 90 % of overflow inside core bodies whose pin faces have
4.3 to 13 um channels; wall rows (14 core moves, 48 um channels) are in G0. cbn_q11: 521 keys moved off the shared anchors (f4).
cbf_q00: bins FIRM-sited, legs 633 to 637 -> 239 to 339 with +1 cycle (f4), or bins only (f4a). N4.6f failed its bind on copied reset
relay names; f3 keeps the type's own reset tree. u_bin_b_tw_data_i bits 0 to 28 span 1,012 um across four cores.
**Fix (P).**
1. QC-COLL-CORE-1118: the wall proof kit to GRT round 5; pass mark sum under 5,000 and inside-core share under 30 %. Then print the
   worst 20 TT ends (-998 at placement is a separate item with no path print).
2. QC-PLAN-R3: f4 changes the bc lane count 3 -> 4; that class broke the Morton balance before. If f4 fails PARAM_REGEN, take f4a and
   put the remaining 637 um leg on a 0-cycle station pair at the next event; do not retry f4 with pads.
3. The 29 broadcast bits need one added stage or a pd1 tail split; it has no row and no owner. It will be the wns of every
   sle / slw st_a kit after the e4 rows land (I).
4. Ring group row: v1 gave GRT -111.3 unrepaired against -158.4, tns worse, and the repair died (RSZ-0074). v2 (822e8ca0f1) has no
   result. Still opt-in.

### Lever 6. S81: over-reach inside kept wrappers
**Evidence (R, FABLE-FIX-S81-LEAF 12:49, 13:04).** bk_sel__t2, synthesized netlist: 7 cores, 22 core-to-core links, 7,847 bits, 0
register stages on all; 16 links over 405 um: u_c -> g_q[1].u_q 1,337 and 1,346 um, u_g.ln1 -> g_q[1].u_q 1,008, u_g.ln0 -> g_q[0].u_q
951, down to 560. Both ends sit inside the kept `u_core` wrapper, so no plan row reaches them. svc_rs t2 / t4 / t5 / t6 trace running;
svc_rs t1 / t3, svc_lo rs, pvso_entry and slice_station__t51 have no synthesized kit and stay blind.
**Root cause.** The as-built wrapper hides the hard cores from the bind, so the reach rule was never applied inside it.
**Fix (P).** One lane for bk_sel (none today): either move g_q[0] / g_q[1] next to u_c / u_g (move only), or add relay stages on the
7,847 bits in the bk_sel leaf RTL with the cycle priced on its lanes. A 1,346 um leg is about 3 added stages; the core move is
cheaper if the wrapper outline allows it. Until then every bk_sel__t2 kit ends in the same place.

### Lever 7. HEAD: the M1-M4 reservation needs pin access
**Evidence (R).** M1-M7 reservation: GRT overflow 621, 495 of 567 congested gcells inside a reserved rect. M1-M4: 0 overflow. Die check
(HEAD-CROSSING 12:50): all 3,480 hd_tile clock cell windows sit under solid M5-M7 type OBS; 0 of 264 tiles have a legal access.
**Fix (P).** HEAD-CROSSING-1119 generates per-cell M5-M7 via-stack keepouts (pin footprint + margin) from the e2 tree;
FABLE-FIX-HEAD-MESH-O re-runs the hd_tile GRT with them. Pass mark: overflow 0 again. The keepouts are a small part of the 1.9 % rect
area, but 70 rects stack in the x 300 to 400, y 500 to 600 box, so read that box first. Goes in r9 with the outcome of Lever 1.

### Lever 8. Pre-route hold margin
**Evidence (R, HOLD-MARGIN-1119 12:04).** Cause found: `run_kit` never exported `OT_PREGRT_HOLD_R2R_MARGIN`, so the rr pass was skipped.
Fix ad516f62; S81 family value 30 ps f3914d81; the -1,000 ps skip is in the same commit. Fix run on slw_hc1 launched 12:07 against
the control (-16.04, 143 ends). V: I found no result for it and no finished ECO sign-off on the 10 routed kits (my search timed
out; not a negative). R (WAVE-PILOT-FIX 12:28): wave-eco launched 0 because the 130 near-miss jobs were filtered.
**Fix (P).** HOLD-MARGIN-1119 posts the routed internal hold of the fix run. Every lane reading a new kit checks the log for
`pass rr`; a kit that prints only `pass all 1 margin 5.0` was generated before ad516f62 and will miss by the same 7 to 26 ps.

## 2. The 11:45 levers: outcome

| 11:45 lever | outcome |
|---|---|
| 1 D8h applied, D8i behind it | **Done 13:02** with epyc7 dropped. D8i step C composed. DRT-0073 has a cause and a LEF fix, unproven at GRT. |
| 2 hold margin 5 -> 30, ECO retry | **Fixed on main, unproven.** My stated cause was wrong: the 40 was not applied to the cross-tap term only, it was never exported. ECO class has produced no result. |
| 3 D8i depth rows | **Done to rows:** 551 / 117 types, G0 equal to control. The two proof kits were not launched. bk_sel answered: no plan row can fix it (Lever 6). QC stays blind at the fabric crossing stations (49 types). |
| 4 kit hold window; region DME on regular taps | **Window: done on HEAD (live), rows ready on KV and S81, not started on QC.** **Region DME: wrong** on KV (-327.6, 148 CA fails). The pc_v1 cross-tap count is still open. |
| 5 slice C: no hold repair under -1,000 | **Done on main.** The D8h tap-table read is pending. |
| 6 QC ring, single boundary ends, cbf_q00_s2 swap | **Stuck.** Ring v1 not proven; the slw_fw_v1 clock-arrival read has no post; the swap bind failed once on reset names and is on its fourth form. |
| 7 KV D25e in one event | **D25d live; D25e composing.** sys_c proof kit not started; pv proof has no TT. |
| 8 S81 clock of record, serdes H22 | **Clock done** (cw6, with the reach check ahead of the build as proposed). New: CA 114. H22 still in GRT hold repair at -7; serdes t1 boot-path detour fixed on main f5d3f6de3fc. |

## 3. Stop list (the 11:45 list stands, plus these)
- Do not read a die kit-contract number as hold closure of the type; hd_tile is -59 to -90 TT at placement under the window.
- Do not raise windows on further HEAD types (r9) before tilecomb has a routed TT and internal hold.
- Do not run region DME on KV regular taps again, and do not fold the P4 count_align table onto the hub_C start tree.
- Do not rebuild the S81 clock for the 114 CA fails before the depth-16 plan has run.
- Do not hold the cw6 window rows for D8j.
- Do not judge D8h by col_h9_r0 / col_h10 kits; their rows are in D8i.
- Do not send bk_sel__t2 back to the wave or write plan rows for it; the legs are inside u_core.
- Do not adopt the hd_tile M1-M4 rows without the via-stack keepouts.
- Do not retry cbf_q00 f4 with column pads if PARAM_REGEN fails; take f4a.
- Do not let the kv3_pc_v1 pilot reach GRT before the clk_c4 to c7 access check.
- Do not count a kit as carrying the 40 ps margin unless its log prints `pass rr`.

# FABLE-CLOSURE-STRATEGY 2026-11-19 11:45 PST (1145): the fixes exist and are not on a tree; routed kits fail on hold, not setup

Reviewer: FABLE-CLOSURE-STRATEGY-12xx (Fable). Read-only: no job launched, killed or patched. Technical PD only; HBM parked.
Gate (R-MINIMAL): DRC 0, routed TT >= -42 ps, internal FF hold >= 0, bind + lane latency.
Marking: **V** = I opened the log or file this round. **R** = reported by the named lane. **I** = inferred. **P** = proposal.
State (V, failure_breakdown 11:44): types signed S81 44 / 394, QC 29 / 130, KV 6 / 56, HEAD 25 / 26. Lanes were limited from about 09:56 to 11:40;
most posts below are from before 09:56 or from 11:42. Nothing below is a hold (r703).

## 0. Headline

1. **S81 D8h is bound and not applied (V).** `d8h_chain.out`: ELAB 0, BIND 0, LATCHECK 0, G0 new 0, type template 216 / 216, sealed 08:50,
   then `CHAIN_STOP bind_repl_epyc7` at 09:51. `tree_switch_s81.json` still names D8g. Every S81 wave number today is on a tree with none of
   the fixes: col_h9_r1 -278.6, leaf -44 to -874, slice C -1,307 to -4,306, phy__t1 -2,468 at CTS (V, 5 hosts). Lever 1.
2. **Routed QC kits pass setup and fail on internal hold by 7 to 26 ps (V).** 9 routed kits on epyc8 / epyc9: `hold_ff` -6.7 to -26.5 on 23 to
   143 ends is the only failed reason on 8 of them. The pre-route hold pass repairs to a 5 ps margin. Lever 2.
3. **The S81 col families fail on core-to-core legs the reach checker did not see (R).** 354 depth rows on 73 types, 216 of them on
   col_h9_r0 and 90 on col_h10; G0-clean at 11:42. This is the "one shared path per family" of 07:50. Lever 3.
4. **Die hold is floored by the regular tap spread, not the core taps (R, FABLE-PD-KV-0845; R, DIE-LEVEL 11:43).** KV with the unit repair:
   delivery 238 / 256 ports inside 25 ps, hold still -282 / -263 (droop class). QC with 28 early regions: -334.7 -> -267.9. Lever 4.
5. **Slice C spends 8 to 9 h in hold repair on kits that are 1,500 to 4,300 ps from setup (V).** Lever 5.

## 1. Levers ranked by closure impact

| # | die | lever | types | owner |
|---|---|---|---|---|
| 1 | S81 | apply D8h with epyc7 dropped; D8i composed on it now | leaf 78, slice C 11, lepe / lepw, col_h9_r1 60, seqhost; D8i +73 types, svc 16 | S81-DIE-R3 |
| 2 | QC, S81, HEAD | pre-route internal hold margin 5 -> 30 ps on low-utilisation types; ECO retry for the kits already routed | 8 QC types seen + slice_station; every short QC type next | FABLE-FLOW (flow), WAVE-FLOW-R2, SONNET-FIX-QC |
| 3 | S81 | D8i depth rows (354 + 6) for col_h9_r0, col_h10, leaf; close the two remaining trace gaps | col_h9_r0 p1 / p2 / p4 / p5, col_h10_r0 / r1 (about 150 col members), leaf 12 + 5; QC 48 blind | FABLE-FIX-S81-LEAF, S81-DIE-R3, CBC-RULES-1119 |
| 4 | KV, QC, HEAD | type-kit hold window from the real cross-tap path list; region DME on regular taps; no more core-tap offset passes | KV 50 unsigned (pc, pv, hg, hgi first), QC tile_nk_a0c, HEAD 264 tile regions | KV-PC-HGI-1119, KV-CROSSING-1119, QC-PLAN-R3, HEAD-CROSSING-1119 |
| 5 | S81 | slice C: no hold repair before setup structure; tap tables first (D8h), then the split | dsdv_slice C 10 kits read (12 types) | S81-DIE-R3, FABLE-FIX-S81-LEPE |
| 6 | QC | landing ring and single boundary ends between CTS and route; cbf_q00_s2 tile swap (N4.6f) | coll_ftc, fw, stm, st_b (ring types), cbf_q00_s2 | SONNET-FIX-QC, QC-PLAN-R3 |
| 7 | KV | D25e in one event: E2 pc views, pv +500 set, sys_c stations + dcal RTL, hgi_v1 raw branch | KV 50 unsigned | KV-D23-COMPOSE, FABLE-FIX-KV-PV, KV-SYSC-1119, FABLE-FIX-KV-HG |
| 8 | S81 | clock of record: all 6 local-tree stations under the reach bound before the build; serdes H22 | window rows for leaf 75 / slice C / lepe; serdes 11 | S81-CLOCK-WINDOW-1119, FABLE-FIX-S81-SERDES |

### Lever 1. S81: D8h on the tree, D8i behind it
**Evidence (V).** `d8h_chain.out` (intel2 s81-die-r3-hub): BIND_RC 0, LATCHECK_RC 0, `G0_ERRORS control(D8g) 2 d8h 2 new 0`,
`TYPE_TEMPLATE check: 216 position(s), 42 group(s), 216 equivalent, 0 FAILED`, SEALED `..._d8h_1117_work_bind_11190850`, `BIND_REPL epyc2 OK`,
`CHAIN_STOP bind_repl_epyc7`. No S81-DIE-R3 post after 09:51. Wave kits at CTS on D8g / D8f (V, `tt_setup_measure.log`, last 8 h):

| family | CTS TT | note |
|---|---|---|
| col_h9_r1 pv87d52780 | -278.6 | no trunk row on this tree; proof with the row was -41.49 at GRT (R 06:12) |
| leaf t2 / t12 / t26 / t43 / t24 / t71 / t11 / t44 / t25 | -837 / -499 / -492 / -479 / -310 / -195 / -172 / -125 / -44 | kv_leaf t5 -874 on two hosts |
| slice C: iq / c1x t4, t5, t7, t10 / lepe_nh / lepw / kv512 / c3x / c1x t8 | -1,308 / -1,412 to -1,526 / -1,533 / -1,529 / -1,556 / -1,686 / -4,306 | Lever 5 |
| phy__t1 | -2,468 | D8h proof kit never started (the chain stopped before publish) |

**Root cause.** The apply step replicates the sealed bind to every gen host and stops on the first host that fails. epyc7 is not a usable
gen host today. The HEAD r6e apply met the same host and went through with `DROPPED epyc7` (R 07:00).
**Fix (P).**
1. S81-DIE-R3: resume the chain from the replicate step with epyc7 out of the host list (the publish_apply form HEAD used). No re-bind:
   the sealed bind and plan h3 8dfedade987b are unchanged.
2. First reads on D8h, unchanged from 07:50: iq_C t1 CTS, leaf t16 / t27 CTS, col_h9_r1 route, phy__t1.
3. D8i on the D8h plan, one event: 354 depth rows + 6 station rows (Lever 3), svc H8 rows for 16 types with the 10 signed provider views
   (R 09:03), seqhost reach stations (R 07:19), col B + C merge, `clock.insertion_ps 306` on the lepe / lepw LP types. Its private bind
   can start on the sealed D8h copy now; it does not need the apply.
4. Lepe proof kits (R 09:13 to 09:56): both forms end at `DRT-0073 No access point for u_bound.u_u_ln0/ck[0] (dsfd_coll_lane_e_safe8_ntf)`.
   That is a core clock pin with no routable access, a pin or halo defect of the view, not timing. One owner line is missing for it;
   FABLE-FIX-S81-LEPE names the blocked layer at that pin before the D8h lepe kits reach DRT.

### Lever 2. Routed hold misses of 7 to 26 ps: margin before route, ECO after
**Evidence (V, `signoff/signoff.json` written in the last 8 h on epyc8 / epyc9 / intel1; `reasons` and `internal_hold`).**

| kit | failed reasons | internal hold ends |
|---|---|---|
| slw_st_b_v2 pvc2ec5bfb | hold_ff -6.73 | 23 |
| slice_station t8 (S81) | hold_ff -8.34 | 4 |
| slw_hc0 cl1bc59e1c | hold_ff -13.26 | 97 |
| slw_st_b_v1 pvffd43fdc | hold_ff -13.30 | 59 |
| sle_hc0 cl05696ed1 | hold_ff -15.10 | 28 |
| slw_hc1 cl3449ea95 | hold_ff -16.04 | 143 |
| sle_stm_v1 cl27746664 | hold_ff -18.52 | 75 |
| sle_stm_v3 | hold_ff -23.43 | 67 |
| slw_st_b_v1 pv6ace3e48 | hold_ff -26.46, drc 1 | 119 |
| slw_fw_v1 cl592e3d37 | setup_tt -65.57 (1 end, `u_bout_flt_wo/q`), hold_ff -12.29 | 31 |
| coll_ftc | setup_tt -217.80 (`u_cland_tl_st_wi_i/u_ring.dch[4].u_dsel/y[17]`) | 0 |

- V (slw_hc1, sle_stm_v1 `pregrt_ff_hold.log`): `OT_PREGRT_FF_HOLD pass all 1 margin 5.0 wns 5.000 endpoints 0`; class after: same_tap 0,
  cross_tap 0. So the kit leaves the pre-route pass with every internal end at +5 ps on placement RC, and the route moves 23 to 143 of
  them under 0. `config.mk` carries `OT_PREGRT_HOLD_R2R_MARGIN = 40` and `OT_HOLD_FAMILY_MARGIN_PS = 40`, but the pass prints 5.0.
- V: every kit in the table has an `eco_20261119_*` directory. The ECO retry class is running on them; none has finished.
- R (FABLE-FIX-HEAD-MESH-O): one ECO iteration on hd_ctl took 28,928 s.

**Root cause.** A 5 ps internal hold margin at placement RC is smaller than the placement-to-route delay shift (13 to 26 ps here). The
kits are at 5 to 24 % utilisation, so the padding area is free. The declared 40 ps margin does not reach the pass that decides (I: the
40 is applied to the cross-tap term only; the lepe log prints `margin 5.0 + cross-tap 40.0`).
**Fix (P).**
1. FABLE-FLOW: the same-tap / reg-to-reg margin of `OT_PREGRT_FF_HOLD` reads `OT_PREGRT_HOLD_R2R_MARGIN` (30 to 40 ps) on types under
   30 % utilisation. Expected cost: tens to hundreds of hold cells per kit (slw_st_b p3 closed with 202 added, R 11:09).
2. Wave owners: the 10 kits above stay in the ECO loop; do not relaunch them. Read the first ECO result on slw_st_b_v2 (23 ends) as the
   test of the class.
3. Not read: whether the routed violators are same-tap or cross-tap ends. `signoff/ff/ep_ff.tsv` has start and end kinds; one read on
   slw_hc1 decides which margin to raise.

### Lever 3. S81 depth rows: the col families' shared path
**Evidence (R, FABLE-FIX-S81-LEAF 09:01, 09:04, 11:42).** With the fixed trace call the D8g core-to-core recount measures 71,796 paths
where the CBC run measured 0. 73 types need 354 rows (+354 stages): col_h9_r0_p2 72, col_h9_r0_p5 72, col_h9_r0_p1 36, p4 36 (legs to
674 um), col_h10_r0_p1 36 (515 um), col_h10_r0_p4 30, col_h10_r1 24 (562 um), leaf 32 rows on 12 types. Plus 6 stations on 5 types
(kv_leaf t1, leaf t21, t27, t71, t60). G0 of D8g + both row files: 2 errors, the same 2 cut errors as the control.
- V (07:50 round): col_h9_r0 p1 / p4 / p5 read -331 / -334 / -335 and four col_h10_r1 kits -382.18. Equal wns across layouts fits a
  fixed over-reach leg between two cores (I). No kit with the rows exists.
- R: the 36-row station file of 09:01 was wrong for 31 types and is withdrawn; leaf t31 (-1,116) is unexplained.
- R: two blind classes remain: bk_sel (the bound module keeps the wrapper as one instance, so the plan cores are not visible) and
  svc_rs (2,518 non-wiring assigns between cores). QC flattened tiles: 48 types still blind.

**Fix (P).**
1. S81-DIE-R3: both row files into D8i; bind and lane latency for the +354 stages are the open check.
2. One private proof kit each on col_h9_r0_p1 and col_h10_r1 with the rows, to CTS TT (r712). A value near -330 after the rows means
   the leg is not the wns path and the family needs the endpoint read that 07:50 asked for.
3. FABLE-FIX-S81-LEAF: bk_sel and QC tile mapping on main, then CBC-RULES-1119 re-runs QC. Until then the QC "12 lanes +1" count is a floor.
4. Leaf: 13 types still stop in global placement (V, breakdown: `global_place error 13 (s81sl_leaf__t14, +12)`). The 07:50 face-bank item
   has no post. It is a pin-bank fit, not timing, and no depth row touches it.

### Lever 4. Die hold: the kit window, on three dies
**Evidence (R unless marked).**
- KV (FABLE-PD-KV-0845, computed from the tap arrival files): the "1.83 x planned + 85" was `die_trial` leaf() reading the leaf leg in um
  as ps (pcc 136.6, pcf 47.4). Regular-tap spread alone: pc median 117.5 / max 180.4, pv 122.8 / 185.7, hg 106.6 / 148.4. With exact
  core delivery the hold is about -170 to -186 TT. Core taps are worth 25 to 50 of the 222 ps.
- KV (DIE-LEVEL 11:43): `pcsink_fix` delivery 238 / 256 inside 25 ps; droop-class hold -282.0 / -262.9 (before -297.8 / -273.5);
  CA plan 26 / 3,915 fail with 35 ambiguous edges; nominal class not measured. k1 died.
- QC (DIE-LEVEL 09:04, 11:43): n46ct_e, 28 added early regions, record recipe: crossings 0 / 2,993 TT + FF, MC 0 / 300; intra hold
  -334.7 / -323.2 -> -267.9 / -263.4; kit-contract -93.0 -> -213.9 (W 10).
- HEAD: r6e e3 -92.6 / -104.5 stands; tile leaf spread p90 86 ps; no new run.
- V: KV-PC-HGI-1119 last post 07:56; the "count real cross-tap paths on kv3_pc_v1" step (rank 1 of 0845) has no post.

**Root cause.** The all-pairs number assumes a zero-delay path between every tap pair of a partition. The tree cannot deliver under
about 110 ps even for taps 150 um apart (KV). Kits were signed against W 36 (KV) and W 10 (QC). The gap is a kit hold contract,
not a tree defect; the per-port offset work moved 20 to 60 ps of it.
**Fix (P).**
1. KV-PC-HGI-1119 (or a successor lane, since it is silent): `kit_tap_related_pairs.tcl` on signed kv3_pc_v1: the count of real cross-tap
   register paths and their min data delay. That number sizes the window; nobody has it. 2 h, no build.
2. Then one pilot per die with the window as a kit row: kv3_pc_v1 at W about 200, qfd_tile_nk_a0c (QC, 720 taps), one HEAD tile type at
   W 96. Judge on added hold cells and routed TT. The S81 lepe kits paid 19 k to 27 k cells for a comparable window, so price it first.
3. In parallel, cut the need: region DME on all KV pc / pv / hg / hgi regions (DME pc parts median 77 against 119 on link_htree, R) and
   HEAD tile-region DME. QC: adopt the 28 early regions only together with the kit window, because they improve hold by 67 and cost
   121 on the kit contract.
4. KV crossings: `pcsink_fix` lost 26 crossings. Re-derive the A4 rows on the tree that is adopted, once, after step 3.
5. KV-D23-COMPOSE: E2 pc lib / lef rows in D25e so pc pairs leave BLOCKED(kits).

### Lever 5. S81 slice C: hold repair is running ahead of the structure
**Evidence (V, `pregrt_ff_hold.log` / `run_route.log` on epyc8).**

| kit | hold pass | result | setup |
|---|---|---|---|
| c1x_C t8 | 74,551 hold cells, 718,094 insts, 27,919 s | cross-tap -54.2 on 72 ends | -4,305.8 before and after |
| kv512_C t1 | 64,730 hold cells, 741,660 insts, 31,872 s | cross-tap -294.4 on 207 ends | -1,556.4 before and after |
| c3x_C t1 | before: cross-tap 41,575 ends at -354.9, same-tap 97 at -172.9 | pass running | -1,686 |

- V: `OT_TAP_CHECK` c1x_C t8: clk 650, clk_t21 565, clk_t28 465 against the rest at 276 to 316; kv512_C clk 819, t33 618, t28 616;
  c3x_C clk_t20 674. `OT_HOLD_GATE structural limit` -240 to -308 (tap window 140 to 208). Census: 520 k to 549 k non-tap cells at CTS,
  max-wire projection +136 k to +167 k, against a 400 k target.
- The diamond legaliser is the fallback on both finished passes (`DPL-0033`, then 0 overlaps).

**Root cause.** A few taps per kit carry 150 to 370 ps more insertion than the rest, so the window is 140 to 208 and the cross-tap hold
population is 40 k ends. The repair adds 65 k to 75 k cells to a kit already over the cell target, and setup is untouched because
its miss (zero-wire 668 to 724 ps, R 07:50) is depth plus the same tap tree.
**Fix (P).**
1. The D8h slice C tap tables (Lever 1) are the fix for the outlier taps; iq_C t1 on D8h is the first read.
2. FABLE-FLOW: `OT_PREGRT_FF_HOLD` is skipped when post-CTS TT is below about -1,000 ps; the kit continues to GRT for its congestion and
   reach data. That saves 8 to 9 h per C kit and changes no verdict.
3. If the D8h read still shows more than 500 k cells, the C types need the split that svc got (H8 form), not more rows. Owner to name: none today.

### Lever 6. QC: where the route loses setup
**Evidence (V).**
- CTS / GRT TT on 30 QC kits: 24 are at 0 to +71 at CTS. GRT: sle_fw_v2 -37.1 (3 ends) / -19.1 (2), sle_stm_v1 -28.8 (1) / -105.8,
  slw_hc1 -5.7 (4) / -15.4 (15), slw_st_b_v1 -7.6 (5) / -14.1 (2), slw_sc_v1 -12.6 (215) / -31.3 (1,232), slw_fw_v1 -118.7 / -112.1 /
  -85.1, slw_st_b_v2 -105.8 / -119.6 / -53.1, sle_stm_v2 -85.2, sle_stm_v3 -62.8, cbn_q01 -60.9.
- slw_fw_v1 cl592e3d37: GRT wns -118.66 = tns -118.66, one end; routed -65.57 on `u_bout_flt_wo/q`. `OT_TAP_RC sink insertion 188..322
  ps (partition skew 134)`, pinreg mean 292.4 against the 250 vclk.
- Routed worst setup ends on the kits of Lever 2 are landing-ring slots: `u_cland_*/u_ring.dch[k].sd_c[n]`, `u_ring.s_d`, and
  `u_cland_rstart_tx/q`. They are inside the gate there.
- Ring-group proof (epyc8 `sonnet-fix-qc-ring`): control CTS -54.76, GRT -126.52; `OT_CLAND_GROUP_ROW = 1` copy CTS -55.18, GRT not
  printed yet. The fix does not show at CTS; only the GRT line decides it.
- R (QC-PLAN-R3 09:03, 09:19): N4.6c applied 09:19. N4.6d bind failed: +5 stations on one Morton tree leg cannot be balanced by column
  pads. Structural cause: cbf_q00_s2 has u_t01 / u_t10 swapped against its family (bc_o01 launch 2.1 mm from the window, d6 path 1.7 mm).

**Root cause.** Two classes, both narrow. (a) Ring read mux far from its slot flops (row-wrap split, SONNET-FIX-QC). (b) Single
boundary ends that see the tap insertion spread once the clock is on global-route RC (I, from the one-end tns and the 134 ps skew;
the clock arrivals of that path are not read).
**Fix (P).**
1. SONNET-FIX-QC: post the GRT TT of the group-row copy against -126.52. If it holds, the row goes to every ring type, not only coll_ftc.
2. SONNET-FIX-QC: on slw_fw_v1, read launch and capture clock arrival of `u_bout_flt_wo/q` at GRT RC. If the loss is tap skew, the
   fix is the GRT-RC tap balance on boundary flops (`tap_balance_grt.tcl` is in the kit), not data-path sizing.
3. QC-PLAN-R3: N4.6f = tile swap in cbf_q00_s2 to the family arrangement (move, no re-shape). It removes the +5 stations and the
   -1,093 CTS of that type in one row. Do not retry the station form.
4. coll_core: CTS -575.8 (V). Its N4.6 tx station rows are in; the srr_cone region row waits on the DPL-0033 place_regions fix.

### Lever 7. KV: one D25e
**Evidence.** V, wave kits at CTS on the old tree: kv3_pc_v3 -1,486, hg_v1p6 -865, sys_c -845, hub_Eo -827, pv_v4 -541, pc -468,
hgi_v2 -319; kv3_io_cor +156, hroot +6.7. R: d25d4 is applied (KV-D23-COMPOSE 08:44). D25e-form rebind: the 4 pv reset-relay errors are
gone, 2 hgi_v1 raw Q errors remain (FABLE-FIX-KV-PV 11:43). pv proof kits placed: tail hops 870 um -> 382 (dense) / 412 (D25e form),
worst tap 10,234 -> 1,444 / 1,061 sinks; 519 k / 501 k movable cells; in CTS, no TT. kv3_sys_c: zero-wire 873.8 ps in the dcal
sequencer; 0-cycle RTL fix on main 107c4654a35e with a lockstep miter (KV-SYSC 08:17); its wave kit is dead before CTS.
**Fix (P).**
1. KV-D23-COMPOSE: D25e = E2 pc views + pv route-priced +500 set + sys_c station rows + the dcal core + the hgi_v1 raw-branch regen
   (FABLE-FIX-KV-HG named the two landing_remap defects). The 2 raw Q errors are the only bind blockers left.
2. kv3_sys_c proof kit on a private bound copy now (the pv proof kits used a stub bound top the same way); it does not wait for D25e.
3. kv3_pv at 500 k cells is over every size that closed. Read the first pv CTS TT before deciding on a pv split.

### Lever 8. S81 clock of record and serdes
**Evidence (R, S81-CLOCK-WINDOW 11:42; V on the run list cw4 / cw5 / cw6).** cw2 and cw3 failed on node 942 (994 um leg inside the
serdes PHY wall); fixed on main 64f7bc20f76 (detour box 600 -> 4,800). cw5 failed at the post-build guard: 3 of 21,734 tap edges over
405 um, all in station s_7N_x13 (local H-tree form, leaf drivers to 477 um). cw6 is running. Each attempt costs about 1 h of DME before
the guard speaks. No window rows exist; S81 die hold is unmeasured.
Serdes (R 07:42, 08:07): the one-hub star died in DRT twice (DRT-0255, about 200 legs through one hub). H22 two-level tree: 194 entries
under 14 sub-hubs, 31 stages per entry, built in CTS. V: the H22 log is in a repair table at wns about -7; no GRT line of its own that
I could separate from the H21 copy.
**Fix (P).**
1. S81-CLOCK-WINDOW-1119: run `OT_CLOCK_ACTUAL_REACH` on the station and region lists before the DME (it needs only sites and taps),
   and put all 6 REGTREE-1 stations under `--region-dme-actual-max 405`. One failure per hour-long build is the present loop.
2. FABLE-FIX-S81-SERDES: H22 row to D8i only on DRC 0; the 11 serdes types stay on H18 in D8h and will miss (R).

## 2. The 07:50 levers: outcome

| 07:50 lever | outcome |
|---|---|
| 1 col named-bus rows | **Stuck on the apply.** Rows are in D8h. The recount found the family paths (354 rows). `OT_MAXWIRE_POST_SKIP` is live (V: `post skipped` on col_h9_r1 / r2 kits). col_h9_r2: 4 kits at GRT -18.3 to -28.5 on 48 to 51 ends, inside the gate (V). |
| 2 per-port core-tap targets | **Built, and worth less than I ranked it.** Unit error found and repaired; delivery passes; hold moves 16 ps. The floor is the regular tap spread. The 25 ps delivery gate I proposed fails on port scatter alone (sd 20 to 31 ps) and should not be an adoption gate. |
| 3 D8h bound and applied | **Bound 08:50, not applied.** Reset-anchor re-record in the row writer: no post. The "tap rows without a bind" question is still open. |
| 4 measured per-port windows from cw3 | **Stuck.** cw3 and cw5 failed, cw6 running. |
| 5 route-keeping ECO as a standard step | **Wired** (V: eco directories on 10 routed kits). No result yet. |
| 6 QC CTS-to-GRT loss | **Partly answered.** Ring row-wrap on coll_ftc; one-end misses on fw; the routed failure is hold (Lever 2). My "+50 CTS repair target" is withdrawn: setup passes after route on 8 of 9 kits. cbf_q00_s2 has an owner and a cause. |
| 7 KV bind of record, pv +500 | **d25d4 applied.** pv proof kits in CTS. sys_c has a cause and an RTL fix. |
| 8 leaf and slice C first reads | **Wrong in part.** The two repeating leaf values are not one bus each: only 5 leaf types lack the station and t31 is unexplained. No D8h CTS exists. |

## 3. Stop list (the 07:50 list stands, plus these)
- Do not re-bind D8h for a host that cannot take the replica; drop the host.
- Do not relaunch a routed kit whose only failed reason is internal hold above -30 ps; it is in the ECO loop.
- Do not leave the pre-route internal hold margin at 5 ps on a kit under 30 % utilisation.
- Do not run more KV core-tap feedback passes (k2, k3), and do not use the 25 ps per-port delivery table as a gate.
- Do not adopt the QC 28 early regions without the kit window: hold +67, kit contract -121.
- Do not drive the all-pairs zero-delay hold number to 0 with tree offsets; count the real cross-tap paths first.
- Do not run pre-route hold repair on a slice C kit that is below -1,000 ps at CTS (74,551 cells and 7.8 h for no setup change).
- Do not add stations to a Morton fabric tree leg (QC bc_o01); move the tile.
- Do not apply the 36-row leaf station file of 09:01; the hub file now holds 5 types.
- Do not judge the ring group-row fix at CTS (-54.76 against -55.18).
- Do not start another S81 clock kit before the reach guard has run on its station list.
- Do not read the D8g / D8f leaf, col_h9_r1, col_h9_r0, col_h10 or slice C numbers as a test of any fix (repeats 07:50; still true at 11:45).

## 4. Not checked
- The col_h9_r1 GRT congestion strip at x 701 to 758 / y 1,214 to 1,218 (named in my brief): I did not open that kit's congestion
  report. Before any row: list the instances in the strip. If they are the i1 trunk station bank (D8h aims 1,100 bits at one centroid),
  the bank needs spreading along the trunk; that is a guess until the list is read.
- Which routed hold violators are same-tap or cross-tap (Lever 2); where the 40 ps config margin is dropped.
- The launch and capture clock of the slw_fw_v1 one-end miss; the tap-skew reading in Lever 6 is inferred.
- Any ECO result; the group-row GRT; cw6; H22 past CTS; pv proof TT; N46E (N4.6d-b) bind; the D8i bind with +354 stages.
- epyc7 kits (unreachable); epyc2 and epyc10 had no sign-off written in the last 8 h under the job root I read.
- The cost in cells of a 200 ps kit hold window on KV or QC: no measurement exists.
- N4.6f and the dsdv_slice split are proposals; neither has a plan file.

# FABLE-CLOSURE-STRATEGY 2026-11-19 07:50 PST (0750): the tree has to deliver what the plan declares; which 05:55 levers held

Reviewer: FABLE-CLOSURE-STRATEGY-07xx (Fable). Read-only: no job launched, killed or patched. Technical PD only; HBM parked.
Gate (R-MINIMAL): DRC 0, routed TT >= -42 ps, internal FF hold >= 0, bind + lane latency.
Marking: **V** = I opened the log or file this round. **R** = reported by the named lane. **I** = inferred. **P** = proposal.
State (V, failure_breakdown 07:10): signed any plan 459, current plan 404. Types signed: S81 44 / 394, QC 29 / 130, KV 6 / 56, HEAD 24 / 26
(hd_ctl signed off 07:00, R, not yet in the count). Nothing below is a hold (r703).

## 0. Headline

1. **A core-tap early row helps only on a tree that delivers it, port by port (V + R).** HEAD: the tree delivers, intra hold -176 -> -115 -> -93
   (V, `sta_ca.log` of l1119e1 / e3). KV and QC: the same class of row made hold worse on three runs (KV -222 -> -253 rows, -> -260 region.early;
   QC -335 -> -408), because the tree does not build to the row (QC: 1,081 of 1,461 taps arrive more than 25 ps late, R) or because one region
   holds two core types 122 ps apart (KV pcc 318 / pcf 196, R). Lever 2.
2. **The col families are the largest closable S81 block, and they fail on one narrow class each (V).** Wave kits at CTS: col_h9_r0 -331 / -334
   (905 to 911 ends), col_h10_r1 -382 (396 ends), col_h10_r0_p1 -432 (1,779 ends), col_h9_r1 -259 to -290. The one family with a named-bus row
   (col_h9_r1 trunk) went to -13.6 at CTS and -41.49 at GRT (V CTS, R GRT). Lever 1.
3. **Every S81 fix row still waits on one bind (R).** D8h failed its strict bind on a stale reset anchor (leaf t47 / t75), D8g2 was dropped;
   the third bind is running. Meanwhile 308 S81 rows launch on the D8f tree, which carries none of the fixes. Lever 3.
4. **The window is the hold cost, not the setup miss (R, S81-CLOCK-WINDOW step 1; V on the cell count).** At W 60 the cross-tap hold ends
   fall 3 to 5 times; TT moves 40 to 130 ps and no kit closes. The two lepe proof kits added 19,271 and 26,577 cells in the first hold pass. Lever 4.
5. **QC kits are positive at CTS and lose 20 to 115 ps at GRT (V).** Lever 6.

## 1. Levers ranked by closure impact

| # | die | lever | types | owner |
|---|---|---|---|---|
| 1 | S81 | one named-bus row per col family, from the col_h9_r1 pattern; route-keeping ECO for the last 10 ps | col_h9_r1 60, col_h9_r0, col_h10_r0 / r1 / r2, col_h9_r2 (216 col members, R) | S81-GEOM-OPUS, FABLE-FIX-S81-COLH9R1, S81-DIE-R3 |
| 2 | KV, QC, S81, HEAD | per-port core-tap targets built into the tree; a delivery table decides adoption; clock first, crossing rows after | 4 dies (die hold and crossings) | DIE-CORETAP-1119, KV-CROSSING-1119, QC-PLAN-R3, S81-CLOCK-WINDOW-1119, HEAD-CROSSING-1119 |
| 3 | S81 | D8h bound and applied; tap rows that need no bind; D8i right behind it | leaf 78 rows, slice C 11, lepe / lepw, col 60, seqhost | S81-DIE-R3, FABLE-FIX-S81-LEAF |
| 4 | S81 | measured `per_port_ps` from cw3 in the same event as the tap rows; no 44 ps fallback | leaf 75, slice C 12, lepe / lepw 8, kv_leaf 5 | S81-CLOCK-WINDOW-1119, S81-DIE-R3 |
| 5 | all | route-keeping ECO loop as the standard step for a routed kit within about 15 ps of the gate | hd_ctl done; hd_mesh; col_h9_r1 60; QC short types | FABLE-FIX-HEAD-MESH-O (tool), wave owners |
| 6 | QC | find the CTS-to-GRT loss on the short types; st_b form A back in with a re-keyed sidecar | st_a, st_b 12, fe / fw, coll_ftc, cbf s2 | SONNET-FIX-QC, QC-PLAN-R3, QC-COLL-CORE-1118 |
| 7 | KV | a bind of record (d25d4), then the pv cycle set priced on the route (+500), not straight pin-to-pin (+464) | KV 50 unsigned; pv 16 | KV-D23-COMPOSE, FABLE-FIX-KV-PV, FABLE-FIX-KV-HG |
| 8 | S81 | leaf and slice C: first CTS on the W+H 300 tables; read the two repeating leaf values once | leaf 75, slice C 12 | FABLE-FIX-S81-LEAF, S81-SLICE-C-TAPS |

### Lever 1. col families: one named-bus row each
**Evidence (V, kit `tt_setup_measure.log` / `tt_setup_repair.log` under `ot-jobs`, kits of the last 10 h; TT, placement RC, after the kit repair).**

| family (kits read) | CTS TT | ends before repair | cross-tap hold | window |
|---|---|---|---|---|
| col_h9_r1 wave (5) | -259 to -290 | 633 (05:55) | -76 to -123 / 462 to 633 | 40 |
| col_h9_r1 proof with trunk row (1) | **-13.6** | | -83 on 3,817 (1,491 port starts) | 40 |
| col_h9_r0 p1 / p4 / p5 (5) | -331 to -335 | 905 to 911 | -69 to -92 / 172 to 319 | 40 |
| col_h10_r1 (4, one layout) | -382 | 396 | -49 / 452 | 40 |
| col_h10_r0 p1 / p4 (3) | -295 to -432 | 1,779 (p1) | -68 to -159 / 112 to 271 | 40 |
| col_h10_r2 (1) | -77 | | -63 / 222 | 40 |
| col_h9_r2 (4) | -13.6 to -13.8 | | -44 to -85 / 132 to 202 | 40 |

- R (FABLE-FIX-S81-COLH9R1 06:12): proof kit pv36da905c GRT TT -41.49 on 48 ends, 0.5 ps inside the gate; it was -277.82 before the rows. The
  rows are 0 cycles, no RTL. FF hold: reg-to-reg +1.71; all 1,392 violating ends start at an input port (advisory).
- V: col_h9_r0 p1, p4 and p5 read -331, -334, -335 on three different partitions, and four col_h10_r1 kits read the same -382.18. That is one
  shared path per family, not placement noise (I). The repair removes most of the tns and none of the wns (col_h9_r0_p1: tns -74,758 -> -4,437,
  wns -350 -> -331), which is the signature of a few long ends that sizing cannot reach (I).
- R (S81-GEOM-OPUS 06:59): the col_h9_r1 pattern is generated for col_h10_r1, col_h10_r2, col_h9_r2; the B + C merge (21 col layouts instead of
  42) is proven to bind on a private D8h copy, for the event after D8h. The col_h10_r0_p4 proof kit is still the missing read.
- R (S81-FAILED-TRIAGE 06:07): 32 col_h9_r1 and 4 col_h10_r2 rows stopped at "hold after CTS" without a relaunch; 2 col_h10_r0_p4 and 3
  col_h10_r2 rows fail on GRT congestion.

**Root cause (I for the families without a row).** One long bus per family (in col_h9_r1 a trunk aimed at a 1-bit reset capture) sets the
wns; the 40 ps window and the tap tree are not the problem here.

**Fix (P).**
1. S81-GEOM-OPUS: before any new row, name the worst end of col_h9_r0 p1, col_h10_r1 and col_h10_r0_p1 from the existing `4_cts.odb.tt`
   (three STA reads, no build). If the end is the same trunk class, the col_h9_r1 row form applies; if not, it is a new named bus.
2. S81-DIE-R3: col_h9_r1 rows (`rows_h9r1_i1trunk_v1.json`) are in D8h; the col_h10 / col_h9_r0 rows and B + C go in D8i, composed now so
   they do not wait a full round after D8h binds.
3. FABLE-FIX-S81-COLH9R1: the proof kit's first routed number decides the 60. At 0.5 ps of margin some will land under the gate; plan the
   route-keeping ECO loop (Lever 5) for those, not a second plan row.
4. `OT_MAXWIRE_POST_SKIP` in the gen env of every col_h9 / col_h10 type (asked 06:14, R; not in a tree yet). The proof kit also stalled
   there and passed on the skipped re-run.

### Lever 2. Die clock: the tree must deliver the core-tap target, per port
**Evidence.**

| die | change | intra hold TT / FF | other effect | source |
|---|---|---|---|---|
| HEAD | region.early on the 4 lep0N core taps | -176.1 -> -115.1 / -105.4 | setup +548 -> +609 | V l1119e1 `sta_ca.log` |
| HEAD | + lep0N max 388, residual snake | -92.6 / -104.5 | kit-contract -72.9 (W 23, need 95.9); 171,707 of 571,124 pairs negative | V l1119e3 |
| KV | core rows (985 taps raised to the signed lib) | -222.0 -> -253.5 / -239.4 | kit-contract -142 -> -214 | R KV-CROSSING 06:16 |
| KV | region.early on 112 regions | -222.0 -> -259.7 (R); `sta_droop.log` now reads **-329.5 / -295.0** (V, written 15:05 UTC) | 32 crossings fail; kit-contract need 282 against W 10 | R + V early1 |
| QC | core rows on the M4 kit | -334.7 -> -407.6 / -347.0 | kit-contract -93 -> -251; setup +376 -> +303 | R DIE-LEVEL-CHECK 06:39 |

- V (`early1/kitwin.json`): with region.early the KV kit-port need on kv3_hg core ports is 120 to 233 ps (clk_c19 233, clk_c15 217, clk_c2 217).
  The same log lists TAP-OFFSET-GATE RESIGN lines on kv3_hg with excess up to 60 ps. The deeper tree moved the register taps too.
- R (KV-PC-HGI 07:04): pcc 318 / 320 ps and pcf 196 / 193 ps are measured on signed DBs and equal the declared values. Both types sit in one
  region. So the -222 is real, and no single early value for the region can serve both.
- R (DIE-LEVEL-CHECK 07:12): QC M4 kit, 1,081 of 1,461 core taps reach the core more than 25 ps later than the n46_ct rows ask; tile_nk_a0c
  (720 taps) median 114 ps short. 28 QC regions with hard-core taps had no region.early at all (QC-PLAN-R3 06:20).
- R (DIE-CORETAP 06:20): the QC M4 and S81 proto kits deliver no early at all (0 early taps in `tree.json`). S81 plan early is off from the
  signed latency by -357 to +335 ps across 40 modules (S81-CLOCK-WINDOW 06:33).
- V: every intra-hold line still ends `MEASURED-HOLD 0 measured ... BLOCKED(kits)`. All numbers above are model numbers.

**Root cause.** Three things were treated as one: the early value the plan declares, the arrival the tree builds, and the difference between
core types inside one region. HEAD worked because its four early taps are one core type in one region and the tree was rebuilt to them.
A declared value that the tree does not build only widens the gap in the STA (KV rows, QC rows). A region-wide early cannot split two
core types (KV pc). And every tree change moves the crossings that were planned on the old tree (KV 0 -> 32 fails).

**Fix (P).**
1. DIE-CORETAP-1119: give each core tap its own DME sink offset = signed insertion - common (`core_tap_retarget` per-port targets), so the
   merge balances the core pin and the register leaves to one arrival at the flops. This is the usual macro-pin insertion-delay form.
   First use: KV pc regions (pcc about 68 ps early, pcf about 54 ps late).
2. Adoption test, per die, before any core-tap row enters a plan event: the delivery table of the run (`core_tap_offsets.py`) shows
   |die early - need| <= 25 ps on 95 % of taps, and intra hold is not worse than the control. QC: n46ct_e (28 added regions, queued epyc10)
   is that test. KV: no row until a kit with per-port targets exists.
3. KV alternative if the per-port form is slow (P, not measured): pad the pcf clock leg inside the kv3_pc kit by about 122 ps, so both core
   types present 318 ps and one region early serves them. The pc types are unsigned, so no sign-off is lost. It costs clock power and OCV on
   that leg; measure it on one pc kit before choosing.
4. Order on every die: clock of record first, then the crossing run with the A4 arguments on that clock. The KV A4 rows are valid on
   l1119d_7yhr only. HEAD already showed the same thing (fresh CA on the early clock raised latency on 2 ports and was not carried, R).
5. HEAD-CROSSING-1119: the residue is the leaf spread inside each of 264 tile regions (p90 86 ps, taps at 45 against 48 stages, R).
   Tile-region DME with an equal stage count per tap is the structural row. Do not cover it with windows: W 23 against a need of 96 would
   put the signed types back through sign-off with 70 ps more hold padding.
6. S81-CLOCK-WINDOW-1119: cw3 (region DME, 392 regions) is still in DME (V, `kit.log` growing at 15:14 UTC). Its `core_early_s81.json`
   (40 modules) must go in with the tree, under the same adoption test, not ahead of it.

### Lever 3. S81: D8h, and rows that do not need a bind
**Evidence (R, S81-DIE-R3 07:02; WAVE-PILOT-FIX 06:14, 06:41).**
- D8g2: bind 0, LATCHECK 0, but 3 new G0 errors (gunit macros 0.012 um outside the core area under the newer kit_fit). Dropped; D8h carries the fix.
- D8h: G0 0 new; strict bind failed on RESET_ANCHOR for leaf t47 and t75. The leaf `whole_keys clock` rows re-picked the relays and kept
  the old `reset_tree_anchor`. Re-recorded on those 2 types; bind h3 started 07:0x.
- 277 to 304 S81 rows were held BIND-STALE every tick; since 06:41 308 of them launch on the D8f tree. V: on that tree the leaf kits read
  -44 to -1,117 at CTS (18 kits, median -495) and col_h9_r1 -259 to -290. They are any-plan count candidates only where the family
  already closes (slice_station +91 / +102, col_h9_r2 -13.6).
- The 05:55 question "do the tap rows apply through the reset key without a bind" has no answer: no kit was generated with the key.

**Root cause.** A tap row changes the clock tap table; the reset tree, the START pick and the anchor are derived from it; the bind compares
all of them. One stale derived field costs one bind round (about 3 h).

**Fix (P).**
1. FABLE-FIX-S81-LEAF: `reach_fix` / the `whole_keys clock` writer re-records `reset_tree_anchor` whenever it re-picks relays (S81-DIE-R3 asked).
   Add it to the private pre-bind check so the next table does not find it in the strict bind.
2. S81-DIE-R3: while h3 binds, generate leaf t16 once on the h3 tree with `reset.consumer_sites_um` (the open 05:55 item). If it generates,
   later tap-table revisions (slice C v2, lepe 122 / 174 / 126 taps, cw3 windows) go in without a bind.
3. D8i is composed now, on the h3 plan: seqhost reach row, col B + C, col_h10 / col_h9_r0 rows, `clock.insertion_ps 306` on the lepe / lepw LP
   types, measured windows (Lever 4), max-wire skip env.
4. First reads on D8h, in this order: iq_C t1 CTS (worst control, 20 of 45 taps over 100 ps), leaf t16 / t27 CTS, col_h9_r1 route.

### Lever 4. S81 window: what step 1 measured
**Evidence (R, S81-CLOCK-WINDOW 05:39, STA on each kit's own `4_cts.odb`; V for the cell counts in `pregrt_ff_hold.log`).**

| kit | TT kit window -> W 60 -> W 0 | cross-tap hold ends, kit -> W 60 -> W 0 |
|---|---|---|
| leaf t27keep | -230 -> -184 -> -124 | (DB already repaired) |
| leaf t69 | -222 -> -163 | 4,389 -> 1,659 -> 172 |
| lepe nh_mus_LP t1 (tap proof) | -786 -> -655 -> -595 | 12,300 -> 3,159 -> 68 |
| lepe mu_LP t2 (taps only) | -507 -> **-523** -> -463 | 7,913 -> 6,157 -> 159 |
| iq_C t1 | -1,308 -> -1,160 -> -1,100 | 33,470 -> 6,209 -> 2,307 |
| c1x_C t8 | -4,306 -> -4,248 -> -4,188 | 29,475 -> 13,369 -> 5,472 |

- V: first hold pass on the two lepe proof kits: mu_LP 14,617 ends -> 2,020, cells 334,962 -> 354,233 (+19,271), hold wns still -117.8;
  nh_mus_LP 16,837 -> 2,513, cells +26,577, wns still -165.2. The pass has not converged and the setup after it is not printed yet.
- V: leaf t60 wave kit: `structural limit -226 (tap window 126)`, hold -203.85 on 8,509 ends, tap means 276 to 478 ps after balance
  (spread 202, target 450).
- mu_LP is worse at W 60 than at the kit window because its worst capture port is an added tap on the 44 ps fallback (R).

**Reading.** The 05:55 claim was half right. The window owns most of the cross-tap hold and 40 to 130 ps of TT. It closes nothing by itself:
leaf t27 is -124 with no window at all, slice C stays at -1,100 to -4,200. Slice C at W 0 is far beyond its depth (668 to 724 ps zero-wire),
so its miss is the in-kit tap tree and reach (I).

**Fix (P).** cw3 -> `die_sta_related --kit-window-out` -> per-port rows for every tap including the added ones, applied in the same event as
the tap table they were measured with. A table and a window from different trees is the present state and the cause of the mu_LP result.

### Lever 5. Route-keeping ECO as a standard step
**Evidence (R, FABLE-FIX-HEAD-MESH-O 06:57, 07:00).** hd_ctl attempt 1 routed DB: one ECO-loop iteration (28,928 s) took TT to -34.86 and
internal reg-to-reg FF hold from -5.59 on 20 ends to 0; DRC 0; signed and exported. Attempt 4, a full re-run, ended at TT -45.97 with
reg-to-reg hold -7.94 on 16 ends. Of its 7,576 FF hold violators, 7,504 start at a port (advisory) and 16 are internal.
**Reading.** For a routed kit inside about 15 ps of the setup gate or with fewer than about 50 internal hold ends, the ECO on the routed
DB closes faster than a new attempt, and far faster than a plan row.
**Fix (P).** Wave owners: route-keeping `eco_loop` runs automatically on a routed DB with TT in -42 to -57 or internal hold ends <= 50.
Candidates now: hd_mesh (hold pass in DRT), col_h9_r1 (60 types at -41.49 GRT), the QC st_a / fw kits in DRT at GRT -2.5 to -37 (V).
Report internal hold from the reg-to-reg split, never from the full overlay number.

### Lever 6. QC: the CTS-to-GRT loss
**Evidence (V, same kits, `tt_setup_measure.log` at CTS and the `G2 setup_tt` line at global-route RC in `run_route.log`).**

| kit | CTS TT | GRT TT |
|---|---|---|
| sle_st_a_v2 pv88773f93 | +4.75 | -17.82 (1 end) |
| sle_st_a_v2 pvd2ec7769 / pv4242de79 | +4.71 | **-100.75 / -111.02** |
| sle_st_a_v1 (2 kits) | +10.81 | -22.02 (6 ends) / -2.51 (1 end) |
| sle_fw_v2 (2 kits) | +13.41 / +62.28 | -37.11 (3 ends) / -19.07 (2 ends) |
| coll_ftc | -54.76 | -126.52 |
| slw_st_b_v1 / sle_st_b_v2 / slw_st_a_v2 / cbf_q00_s2 / cbf_q01_s2 | -206 / -32 / -121 / -1,093 / -214 | not printed |

- 20 other QC kits (fe, fw, stm, hc, su, cbn, cbx) are at 0 to +71 at CTS, 3 at -1 to -5; sle_su_l1 -35 and sle_stm_v2 -45 are the
  exceptions. So most of QC is not failing at CTS; it is decided between CTS and route.
- V: the kit census projects 26,741 to 70,931 added cells from the max-wire repair (`maxwire_est`, OT_MAXWIRE_UM 100 or 120) on kits of
  105 k to 386 k cells.
- R (QC-PLAN-R3 06:50): N4.6a bind failed because the CA sidecar predates `landing_relay_tx_stages`; st_b form A (12 types) is out of N4.6b
  and returns as N4.6c with SONNET-FIX-QC's patched sidecar (06:59, not yet through a bind). coll_core attempt 7 GRT at 10.5 h, no TT.

**Root cause.** Not read. The kit repairs to about 0 on placement RC, and two st_a_v2 layouts with the same CTS number differ by 83 to 93 ps
at GRT, so it is a few routed nets, not a uniform RC shift (I).

**Fix (P).**
1. SONNET-FIX-QC: name the worst GRT end on sle_st_a_v2 pvd2ec7769 and on coll_ftc, and compare the same end on pv88773f93. One read.
2. If the ends are long nets that the max-wire repair or a GRT detour stretched, repair those nets; if they are ordinary paths, raise the
   CTS repair target for QC kits from 0 to about +50 on placement RC (the short types have the area: utilisation 5 to 24 %, V).
3. QC-PLAN-R3: N4.6c bind with the patched sidecar; st_b proof kit to GRT TT (base -106, wave kits -206 / -32).
4. cbf_q00_s2 at -1,093 with 2.13 M um2 of fixed area and 70 % utilisation is a separate case; it has no owner line today (new).

### Lever 7. KV: bind of record, then the route-priced cycle set
**Evidence (R).** KV launched nothing because the live D25c bind of record is empty (apply on G0 with a red bind); `bind_out` now points at
D24c (07:02). d25d4 and d25c2 are sealed, G0 0 errors, strict binds in elaboration since 14:57 UTC. Crossings 9 -> 0 of 3,915 with the A4
arguments (V earlier by DIE-LEVEL-CHECK). pv cycles: +843 -> +500 route-priced, or +464 from the pin-to-pin file; the +464 form adds 32 G0C
hops over 405 um (406 to 506 um) and 17 routed-reach warnings (FABLE-FIX-KV-PV 07:04). V this round: kv3_hg_v1p6 -865 and kv3_sys_c -845
at CTS (wave kits, old tree); kv3_pc RTL calendar in synth.
**Fix (P).**
1. KV-D23-COMPOSE: d25d4 as the bind of record the moment it is green; D25e = A4 crossing rows + E2 lib / lef rows + the pv cycle set.
2. FABLE-FIX-KV-PV: take the route-priced +500 set for D25e. It costs 36 cycles over the file and leaves no hop over 405 um; the straight
   pin-to-pin count is short exactly where the route goes around a core (12 lanes) or where the buffered class was priced at 550 (20 lanes).
   The two kv3_pv_v8 proof kits (D25e form and dense) decide if the dense form is ever needed.
3. kv3_sys_c (-845, 8,891 port-start hold ends) has no fix lane named in today's posts (new); kv3_hg_v1p6 is FABLE-FIX-KV-HG's.

### Lever 8. S81 leaf and slice C
**Evidence (V).** 18 leaf wave kits (D8f tree) at CTS: -44 (t25) to -1,117 (t31); cross-tap hold 3,320 to 11,451 ends at -140 to -343.
Two values repeat across types: about -840 (t2 -837, t6 -837, t74 -845, t38 -874) and about -1,115 (t31, t60). kv_leaf t5 -874 on two kits.
R: 10 leaf types fail global placement ("NS face bank cannot fit within 30 um pin retention"), 5 fail GRT-0116; leaf t27relay was worse
than t27keep; the fence trial failed DPL-0033. No leaf or slice C kit with a W+H 300 tap table has reached CTS.
**Fix (P).** FABLE-FIX-S81-LEAF: one endpoint read on t60 and on t2 names the two repeating classes; if each is one bus, it is a named-bus
row as on col_h9_r1. The tap tables are judged on the first D8h CTS (Lever 3). The 10 face-bank placement failures are a floorplan fit,
not timing: one row for the bank pitch covers them, and it has no owner post since 06:07.

## 2. The 05:55 levers: outcome

| 05:55 lever | outcome |
|---|---|
| 1 re-measure the window on a tree of record | **Measured, half held**: the window is most of the cross-tap hold and 40 to 130 ps of TT; it closes no kit. The tree (cw3) is still building. HEAD took 235 tighten-only rows in r6e and no floor raise. |
| 2 tap rows through the reset key, without a bind | **Not answered.** The rows went into D8h through a bind, which failed on the reset anchor. Tap span is unified at 300 (R). The 306 ps target is a row, not a kit. |
| 3 depth | **No new number.** hd_ctl closed by ECO, not by the recipe. LEC still 1 of 4. kv3_pc RTL in synth. |
| 4 reach by named bus; recount distance-only cycles | **Held.** Recount: S81 25 -> 0, QC 119 -> 12, HEAD 4 -> 0, KV pv 843 -> 492 / 464. col_h9_r1 row: -278 -> -41.49 at GRT. Whole-type relay mode removed. Regions: no H2 result posted. |
| 5 landed verdict on the form of record; core-tap offsets from signed latency | **Crossings held** (HEAD 427 / 427, KV 0 / 3,915). **Offset rows did not**: right values, wrong delivery; worse on KV and QC. |
| 6 col max-wire skip | **Held on one kit** (passed on the skipped re-run). Not in a tree. |
| 7 svc H8 | pvso shells 623,689 / 506,326 cells, both over 400 k (R). No kit. |

## 3. Stop list (the 05:55 list stands, plus these)
- Do not put a core-tap early row in a plan event before the delivery table of that die's tree passes (Lever 2, step 2).
- Do not use region-wide early on a region that holds core types with different insertion (KV pc: 318 and 196).
- Do not carry crossing rows across a clock change. KV A4 is valid on l1119d_7yhr only.
- Do not quote one KV early1 hold number: the post says -259.7, the droop log now says -329.5. Name the STA with the number.
- Do not raise HEAD windows to cover the tile leaf spread (W 23, need 96); fix the tile tree.
- Do not read the 308 D8f fallback launches as tests of any fix; do not triage their leaf, col_h9_r1, col_h9_r0 or col_h10 failures again.
- Do not write a clock row that re-picks relays without re-recording `reset_tree_anchor`.
- Do not mix a tap table with windows measured on another table, and do not leave added taps on the 44 ps fallback.
- Do not judge a QC kit at CTS; +5 at CTS has landed at -100 at GRT.
- Do not start a new attempt or a plan row for a routed kit within 15 ps of the gate; run the ECO loop on the routed DB.
- Do not report hold from the full overlay number; port-start ends are advisory, the reg-to-reg split is the gate.
- Do not take a pin-to-pin cycle count where the route goes around a core; price the routed leg (KV pv 32 hops over 405 um).
- Do not launch pvso kits at 506 k to 624 k cells before the H8 provider form.

## 4. Not checked
- The worst endpoint of any col_h9_r0, col_h10 or leaf kit: the "one shared path" reading is from equal wns across layouts only.
- Why QC loses slack between CTS and GRT; the max-wire cell counts are projections from the census line, not a measured cause.
- KV early1: which STA gives -259.7; I read only `sta_droop.log` (15:05 UTC) and `kitwin.json`.
- cw3, n46ct_e, n43cb, the d25d4 / d25c2 binds, the D8h h3 bind, the col_h9_r1 route: all still running at 07:45.
- The per-port DME offset form and the pcf pad are proposals; neither has a run.
- Setup after the lepe hold passes; depth after the ABC recipe; glue H2; coll_core GRT; hd_mesh hold pass.
- epyc7, epyc8 and epyc10 route logs (GRT lines read on intel1, epyc2, epyc9 only); col counts per family are lane-reported.

# FABLE-CLOSURE-STRATEGY 2026-11-19 05:55 PST (0555): the tap rows fix the tree, not the contract; which 03:30 levers held

Reviewer: FABLE-CLOSURE-STRATEGY-05xx (Fable). Read-only: no job launched, killed or patched. Technical PD only; HBM parked.
Gate (R-MINIMAL): DRC 0, routed TT >= -42 ps, internal FF hold >= 0, bind + lane latency.
Marking: **V** = I opened the log or file this round. **R** = reported by the named lane. **I** = inferred. **P** = proposal.
State (V, failure_breakdown 05:10): signed any plan 458, current plan 403. Types signed: S81 44 / 394, QC 28 / 130, KV 6 / 56, HEAD 24 / 26.
Nothing below is a hold (r703).

## 0. Headline

1. **The S81 families that fail are the ones whose kit SDC carries a 100 to 208 ps tap window; the col families carry 40 ps (V).** The window is
   `clock.tap_window.per_port_ps` in the plan, measured 11-05 on a die clock tree that no longer exists. It is written as an early source latency
   on each tap port, so a cross-tap path loses up to that much setup and needs that much hold padding. Leaf: 2,883 of 5,557 ports at 100 ps or more.
   The new tap rows do not touch it, and every added tap gets a 44 ps fallback that nobody measured. Lever 1.
2. **The tap region rule works on the tree and does not move TT by itself (V).** Two lepe proof kits: 0 of 52 and 0 of 70 taps at 100 ps or more
   in-tap skew (control family 15 of 39). TT on nh_mus_LP t1 went -926 to -786 only; the full-form mu_LP kit (-530) is no better than taps-only (-507). Lever 2.
3. **Slice C types cannot close on depth plus window alone (V + R).** Zero-wire depth 668 to 724 ps (R) plus a 134 to 208 ps window (V) is 833 ps
   or more before any wire. Levers 1 and 3 are both needed there.
4. **Whole-type automatic siting made three kits worse (R); single-bus topology fixes worked (R).** Lever 4.
5. **No die has a landed verdict on its clock of record (R).** HEAD's 6 fails and its 0-fail fix are both on the wrong start form; KV has 9 real
   fails; S81 and QC have no tree. The intra-hold numbers on HEAD and KV both start at a hard-core clock tap. Lever 5.

## 1. Levers ranked by closure impact

| # | die | lever | types | owner |
|---|---|---|---|---|
| 1 | S81 (HEAD, KV in reverse) | regenerate the die clock of record on the region taps, re-measure `per_port_ps`, target 60 ps per type; no blanket window raise on HEAD / KV | leaf 75, kv_leaf 5, slice C 12, lepe / lepw 8, bk_sel, gunit, part of serdes 8 and slice_station 43; HEAD 22, KV pc | S81-DIE-R3 (tree + table), FABLE-FIX-S81-LEPE (STA-only read), DIE-LEVEL-CHECK-1119 (measure), HEAD-CROSSING-1119 |
| 2 | S81, QC, KV | roll the region tap rows out through the reset key, without a bind; balance to the core-tap insertion, not to 250 | leaf 78 rows, slice C 11, lepe / lepw 4, QC 6 short types + coll_core, KV pv 16 | S81-DIE-R3, FABLE-FIX-S81-LEAF, S81-SLICE-C-TAPS, FABLE-FIX-S81-LEPE, QC-PLAN-R3, FABLE-FIX-KV-PV |
| 3 | all | depth: confirm the ABC recipe on the 17 types that really exceed 600 ps; keep_hierarchy where it is not enough; kv3_pc needs RTL | 17 measured (kv3_pc 4, slice C 7, lepe / lepw 4, glue, native59) + hd_ctl | KIT-SYNTH-TARGET-1119, CBC-RULES-1119 (zero-wire tool), KV-PC-HGI-1119, FABLE-FIX-HEAD-MESH-O |
| 4 | S81, QC, KV | reach by named bus only: relay stage or re-aim at a hand site; regions only after the snap proof; recount every distance-only cycle row pin to pin | seqhost, col_h9_r1 60, col_h10 / h9_r0 families, glue, coll_core, sle / slw st_b 12, KV pv 16, QC 52 slots | CBC-RULES-1119, FABLE-FIX-S81-SEQHOST, S81-GEOM-OPUS, FABLE-FIX-S81-GLUE, QC-COLL-CORE-1118, SONNET-FIX-QC, FABLE-FIX-KV-PV |
| 5 | KV, HEAD, S81, QC | landed verdict on the form of record; core-tap early offsets from the signed core latency | 4 dies | DIE-LEVEL-CHECK-1119, KV-D23-COMPOSE, HEAD-CROSSING-1119, S81-DIE-R3, QC-PLAN-R3 |
| 6 | S81 | col GRT: start col_h9_r1 / r2 kits with the post-GRT max-wire repair skipped | 120 | FABLE-FIX-S81-COLH9R1 |
| 7 | S81 | svc: H8 provider form, with the three open items below | 16 | S81-SVC-SPLIT-1119, S81-DIE-R3 |

### Lever 1. The tap window in the kit SDC
**Evidence (V).** Kit `constraint.sdc` and `config.mk` of 246 kit job folders under `ot-jobs` on epyc7, epyc8, epyc10, intel1, epyc2, joined with
`tt_setup_measure.log` and the `OT_PREGRT_FF_HOLD class before` line of the same kit. Per family: ports with a window of 100 ps or more, the
post-CTS TT (median), and the cross-tap hold class before repair (FF, median worst slack / endpoints).

| family (kits) | ports >= 100 ps | type max window | CTS TT | cross-tap hold |
|---|---|---|---|---|
| ot_s81sl_leaf (30) | 642 / 1,358 | 140 median, 208 max | -475 | -209 / 5,476 |
| dsdv_slice_iq_C (1) | 51 / 51 | 208 | -1,308 | -542 / 33,470 |
| dsdv_slice_c1x_C (7) | 261 / 293 | 156 | -4,306 | -316 / 29,475 |
| dsdv_slice_kv512_C (1) | 41 / 41 | 171 | -1,556 | -390 / 18,562 |
| lepe_nh_mus_C, lepw_mus_C | 91 / 91 | 170, 136 | -1,533, -1,529 | -230 / 16,618, -301 / 22,843 |
| lepe_mu_LP, lepe_nh_mus_LP | 37 / 44 | 208 | -798, -926 | -442 / 13,429, -462 / 9,719 |
| kv_leaf (3) | 9 / 125 | 122 | -874 | -405 / 7,111 |
| slice_station (15) | 112 / 734 | 130 median, 175 max | +97 | -85 / 432 |
| col_h9_r0 / r1 / r2, col_h10 (51) | 2 / 1,801 | 40 | -9 to -423 by family | -50 to -123 / 115 to 633 |

- The SDC (lepe_mu_LP proof4, V): `set_clock_latency -source -early -clock clk -208` on `clk clk_t2 clk_t3 clk_t6 clk_t7 clk_t14 clk_t15`, -139 to
  -204 on the other original taps, -44 on every added tap, `-late 0` on all. Comment: "MEASURED per port ... 44..208 ps; IO shift input -208 /
  output +44 ... FALLBACK". Hold gate line: `structural limit -308.0 (contract in_min -40, tap window 208)`.
- The plan (V, D8g tree `plan_h2_2249.json` `clock.tap_window`): leaf 75 types, 2,883 of 5,557 ports at 100 or more, median 100, max 208. bk_sel
  51 of 51 (median 185). gunit 50 of 74. c1x_C 268 of 312. lepe / lepw LP medians 163 to 208. serdes 85 of 402. slice_station 233 of 1,854.
  Every col family 40. Note in the plan: per-port values from TAPWIN-PORT-1105, proof `s81/r98`, on the ckclk3 tree.
- The lepe proof kits (V): after the region taps, tap means 233 to 306 and in-tap skew at most 67 ps, yet cross-tap hold is still -220 on 12,297
  ends (nh_mus_LP) and -199 on 7,886 (mu_LP). That is the window, not the tree.
- R (FABLE-FIX-S81-SEQHOST 05:10): all u_win ends outside the reach class sit at -20 to -122 "under a 160 ps adverse launch / capture tap skew".
- The clock-of-record kit for S81 (ECOv3, 43 levels) is on no host and has no `ot_clk` config (R, DIE-LEVEL-CHECK 04:57).

**Root cause.** The kit closes against a tap-to-tap arrival contract. On S81 that contract is two weeks old, from another tree and another tap
table, and on half the leaf ports it takes 100 to 208 ps of an 833 ps cycle from every cross-tap path (I for the per-path amount; V for the SDC
form and the hold class). The same contract forces 5,000 to 33,000 hold insertions per kit before GRT. The col families have 40 ps and are the
families that close.

**Fix (P).**
1. FABLE-FIX-S81-LEPE and FABLE-FIX-S81-LEAF, today, no place or route: STA only on the existing `4_cts.odb` of the nh_mus_LP t1 proof and of
   t27keep, same SDC with every early latency set to -60. The difference in TT and in cross-tap hold ends is the share the contract owns.
2. S81-DIE-R3: write the S81 tree as an `ot_clk` config (the kv_7yhr route), build it on D8h with the region tap tables, and run
   `die_sta_related` for `per_port_ps`. Design target: taps of one partition hang from one balanced leaf branch, window 60 ps or less per type.
   S81-DIE-R3 already names the limit: 50 taps per 600-um leaf driver (04:52). Protect the kit from cleanup.
3. Until the measurement exists, a tap table is not frozen against the 11-05 values or the 44 ps fallback: a kit that closes on 44 and meets
   150 at die level has to be rebuilt.
4. HEAD and KV, the reverse case. HEAD-CROSSING 05:10 proposes TAPWIN-FLOOR: 535 port rows, 23 per-type raises (hd_mesh 83 -> 100, hd_ctl 44 -> 90,
   hd_spn 70 -> 100, hd_serdes 50 -> 100). hd_mesh is at TT -32.9 and hd_ctl at -45 in their ECO passes; 17 and 46 ps more window puts both under
   the gate (I). Take the structural row instead (rebalance the lep0N leaf branch to the core-tap target, 186 ps) and raise only the lep0N ports.
   KV the same: need 178 against W 36 comes from pc_ES_2 `clk_c3 <-> clk_c4`, two core taps (Lever 5), not from the type.

### Lever 2. Region tap rows: what the proofs show, and how they reach kits
**Evidence (V, `4_1_cts.log` of the three lepe proof kits on epyc9).**

| kit | taps (>= 100 sinks) | skew >= 100 / >= 60 | tap insertion | TT after repair | control TT |
|---|---|---|---|---|---|
| lepe_mu_LP t2 taps-only (proof) | 83 (70) | 0 / 4 | 251 to 359 | -507 (R) | -798 |
| lepe_nh_mus_LP t1 taps-only | 61 (52) | 0 / 3 | 250 to 311 | -786 | -926 |
| lepe_mu_LP t2 full form (banks + taps + CRP2 + WREP5) | 83 (70) | 2 / 9 | 246 to 386 | -530 | -798 |

- The region rule is confirmed as the in-tap skew fix. It is not a closing row: nh_mus_LP still has 1,871 ends below 0 and the TT repair moved
  nothing (wns -785.86 before and after, 22 cells).
- The full form is not better than taps-only on the same type, and its taps are worse (2 over 100 ps, clk_t8 at 386 ps insertion). It carries the
  older banks table (R). Its endpoint classes have not been read.
- `OT_TAP_BALANCE` (V): the register taps are padded to a 250 ps target while the hard-core taps `clk_c0 / c3 / c6 / c9` sit at 306 and cannot
  move. The reported spread (73, 116) is mostly that gap.
- None of the W+H 300 tables (leaf 78 types, iq_C, kv512_C, c1x_C x9, lepe / lepw x3) has a kit. The leaf A/B has no CTS result (R).
- R: `reset.consumer_sites_um` (main b7b2095a5066) passed gen phys on leaf t16 with 239 added taps; no complete kit. Without the key, QC N4.5c
  failed its bind on `rst_n_t383` and KV pv class T shifted every reset reference (22 to 38 hops per type, up to 2,158 um).
- R: die M9 / M8 drop capacity 2.9 % worst; about 7 % with the leaf tables.

**Fix (P).**
1. FABLE-FIX-S81-LEPE (`tap_balance.tcl`): target = the largest core-tap insertion of the type when the type has core taps. No plan change.
2. S81-DIE-R3: one generation of leaf t16 with the key decides whether the 78 + 15 tap rows apply without a bind. If it generates, apply them on
   D8h with `clock.tap_span_um 300`; first CTS read on iq_C t1 (worst control: 20 of 45 taps over 100 ps, 378 ps).
3. FABLE-FIX-S81-LEPE: read the endpoint classes of proof4 before D8h takes the banks + CRP + WREP row; taps-only is the better kit today.
4. QC-PLAN-R3 (N4.6): key first, then taps for the 6 short types and coll_core (43 taps for 65,949 sinks). FABLE-FIX-KV-PV: class T on the key.

### Lever 3. Depth
**Evidence (R).** KIT-SYNTH-TARGET 04:55: recipe on main d460443cd51, default for all kits. Max levels hd_ctl 23 -> 14, kv3_pc 29 -> 24, kv_leaf t5
21 -> 17, leaf t57 15 -> 12; kv3_pc zero-wire TNS -22.9 ns -> -1.1 ns (150 -> 11 ends). LEC closed on 1 of 4. CBC-RULES 04:56 (old recipe): 17 of
53 measured types exceed 600 ps zero-wire: kv3_pc x4 907 to 979, glue 738, lepw_mus_C 724, lepe_nh_mus_C 710, c1x_C t8 705, iq_C 701, c3x_C 682,
kv512_C 670, c1x_C t6 668, lepe_mu_LP 651, native59 645, sle_stm_v1 629, lepw_mu_LP 612. All leaf types are under (463 to 502).
FABLE-FIX-S81-SEQHOST 05:10: keep_hierarchy is worth about 250 ps on u_win (-389 -> -122).
**Reading.** Leaf is not a depth family; its problem is Levers 1, 2 and 4. Slice C and lepe / lepw are depth plus window. kv3_pc is still 24 levels
after the recipe: it needs a pipeline stage in RTL.
**Fix (P).** KIT-SYNTH-TARGET-1119 re-runs the one-pass zero-wire tool with the new recipe on the 17 types and posts what is still over 600.
For those, `keep_hierarchy` on the bound sub-module with the state loop, then RTL. KV-PC-HGI-1119 owns the kv3_pc stage (4 types).
FABLE-FIX-HEAD-MESH-O: one hd_ctl kit on the new recipe beside the ECO; 23 -> 14 levels is more margin than the ECO can find at -45.

### Lever 4. Reach: what worked and what did not
**Worked (R).** col_h9_r1 trunk re-aim, CTS -278 -> -13.6, 623 ends -> 0 (GRT not read). Glue relay core, kit F +30.85 at CTS (control -24).
KV t2 split, 0 cycles, strip overflow 12,000 -> 4,560. coll_core tx stations on the direct path over M6 / M7, 3 lane-cycles saved.
**Did not (R).**
- PAD-CHAIN-SITE auto on sle_ctl: -97.9 -> -182.9, tns x 7.7, with 39,775 cells sited.
- Leaf t27relay (forms A + B proxy): -407 against t27keep -230.
- Glue timing-driven keys: kit E -176, kit D -49 against control -24.
- Regions: DPL-0033 on glue H and leaf t27fence. Cause found (box off the site grid); snap on main 133514c255cf; in-flow proof H2 not back.
  The leaf region also took the wrong flops (output registers whose loads are far cores).
- CBC ft span: (w+h)/2 on corner slots priced 98 um at 1,884; all 52 QC rows withdrawn (FABLE-PD-QC-0407).
**Root cause (I).** A fix that adds a stage or a copy on one named bus at a hand-checked site changes the topology and holds. A mode that
re-sites thousands of cells toward computed centroids fights the placer and the other sinks of the same registers.
**Fix (P).**
1. CBC-RULES-1119: pin-to-pin span; then recount the three distance-only sets before any is bound: KV pv class C (+843 cycles on 132 lanes,
   "all pure distance with no logic", R), S81 162 far branches, QC st_b form A (+2). Core-free buffered legs close to about 550 um (03:30).
2. FABLE-FIX-S81-SEQHOST row (+2 stations 0S, +1 0N, mu_c / mu_rc kept at the core): take it in D8h; the residue (-122) is Lever 1.
3. FABLE-FIX-S81-GLUE: H2 result first. Then regions in this order: coll_core `srr` (QC-COLL-CORE-1118), seqhost `mu_c* / mu_rc*`, leaf vp
   with the fan-in walk and without pin-register flops.
4. SONNET-FIX-QC: PAD-CHAIN-SITE auto off; site only the chains of the failing bus (st_a_st_b_o, 428 bits without a register within 50 um, R).
5. S81-GEOM-OPUS: the col_h9_r1 pattern (trunk aimed at a 1-bit reset capture) on col_h10_r1, col_h10_r2, col_h9_r2 is generated (R); the
   col_h10_r0_p4 proof kit to GRT TT is still the missing read. V: 14 of 17 col_h9_r1 wave kits print the same CTS line (-290.47, 633 ends),
   so one proof covers them.

### Lever 5. Die level
**Evidence (R, DIE-LEVEL-CHECK and HEAD-CROSSING).**
- KV D25c on kv_7yhr: GRT overflow 0; landed 9 fails of 3,915 (4 on hg_ES_7 -> pc_ES_7, +73.8 TT / +1.0 FF against a need of 100); start skew
  15 of 159; setup +490. Intra hold -222 (pc_ES_2 `clk_c3 <-> clk_c4`); kit-contract hold -142.
- HEAD NF15f: the 6 landed fails and the 0-fail fix were both computed on the generic data-start-tree form; the plan of record is START-TREE-1
  (427 ports, 1,846 regions). Neither number is a verdict. Intra hold -176: lep0N leaves arrive 186 ps after the early core tap `clk_c1`.
- S81: generic tree only; default CA left 66 crossings without K / DEPTH. QC: M4 kit found on epyc2, abstracts are s4q9m4, not N4.3.
- R (FABLE-FIX-KV-PV): pc core clock insertion about 318 ps against the plan's 250.
**Root cause (I).** Both intra-hold numbers start at a hard-core clock tap whose real insertion differs from the early offset the die tree was
balanced to. V on S81: lepe core taps at 306 against a 250 target.
**Fix (P).**
1. DIE-LEVEL-CHECK-1119: per die, list every core tap with plan `early_ps`, signed `core_latency`, and the die-tree arrival; rows where they
   differ by more than 30 ps go to the die owner as core-tap offset rows. This is a table from existing files, not a run.
2. KV-D23-COMPOSE: the hg_ES_7 -> pc_ES_7 window (+26 TT / +99 FF) and the 5 single crossings, in D25e.
3. HEAD-CROSSING-1119: `head_current_ca.py` on the l1119c_t2p proof once the NF15f regions map and ring spec are named.
4. S81-DIE-R3 / QC-PLAN-R3: tree of record as in Lever 1; QC re-cuts the M4 tree for partitions N4.x moved.

### Lever 6. col GRT
R (FABLE-FIX-S81-COLH9R1 03:29, V by that lane on 3 kits): the post-GRT max-wire `repair_design` goes flat for 1,800 s at 10 to 11 thousand of 86
thousand nets, the script re-runs GRT once, and the second pass adds 1 to 2 h. 23 col_h9_r2 and 31 col_h9_r1 kits ended there.
**Fix (P).** Gen env for col_h9_r1 / r2 starts with that repair skipped (the form the script already has). The net it hangs on is not found;
one read of the repair log on a stalled kit would name it.

### Lever 7. svc
R (S81-SVC-SPLIT 04:37): flat H16 is 5.1 to 5.3 M cells; with the 62 cores black-boxed 597 k; the cores need 1.196 M um2 against 1.138 M free;
die spare 103.7 um. H8 provider form: parent soft 382 k (lo) / 229 k (hi).
**Open technical items (P).** (a) 382 k is close to the 400 k practical limit: count svc_lo after the new ABC recipe before the rebind.
(b) `idx_hslice_fp` changed after its signed DB (pin registers): re-sign running. (c) pvso_entry t1 / t2 keep 64 H16 heads: census first.
(d) The kits instantiate `ot_s81_svc_idx_hslice_fp` while the signed H16 core is `ot_hdc_v41x_idx_hslice`: resolve the name in the H8 bind.

## 2. The 03:30 levers: outcome

| 03:30 lever | outcome |
|---|---|
| 1 tap by compact region, no spill | **Held for the tree** (0 taps over 100 ps on 2 proofs, V). **Did not close TT**; the leaf A/B never reached CTS. The window (Lever 1 here) was missed. |
| 2 ABC delay target | **Held** on 4 types synth-only; kv3_pc still 24 levels; LEC 1 of 4; svc never measured. |
| 3 reach estimator | Scans now return on all hosts (R). **Not useful yet**: "legs > 405" in 26 of 26 QC and 59 of 61 S81 kits; no core-span or logic column in the digest. The CBC span it fed was wrong. |
| 4 die proof on the composed plan | **Half**: KV done, HEAD on the wrong form, S81 / QC without a tree. Token cost read on KV / HEAD only. |
| 5 region for scattered soft logic | **Did not pan out yet**: DPL-0033 twice, wrong flop set on leaf, anonymous cells; snap unproven in flow. |
| 6 col_h9_r2 FAIL_route | Cause found (Lever 6 here); fix not applied. |
| r713 centroid aim as a whole-type mode | **Worse** on sle_ctl and on leaf t27relay. |

## 3. Stop list (the 03:30 list stands, plus these)
- Do not expect a tap row to close an S81 type while its SDC carries 100 to 208 ps windows.
- Do not freeze a region tap table against the 11-05 `per_port_ps` or the 44 ps fallback.
- Do not raise windows by a floor rule on HEAD (TAPWIN-FLOOR, 23 per-type raises) or on KV for types within 50 ps of the setup gate.
- Do not quote HEAD landed 6 or landed 0; both are on the generic start form.
- Do not take the lepe banks + CRP2 + WREP5 row into D8h on the proof4 number; it is not better than taps-only.
- Do not run PAD-CHAIN-SITE auto or the timing-driven placement keys on a whole type.
- Do not use place_regions before glue H2 passes; do not fence output registers whose loads are far cores.
- Do not bind KV pv class C (+843) or any other distance-only cycle set before the pin-to-pin recount.
- Do not spend more kits on flat H16 svc, and do not open a svc depth lane before the H8 count.
- Do not launch col_h9_r1 / r2 kits with the post-GRT max-wire repair on.
- Do not treat leaf as a depth family (463 to 502 ps zero-wire).
- Do not pad register taps to 250 ps where the type's core taps sit at 306.

## 4. Not checked
- The setup share of the window per path: no STA run by me; Lever 1 step 1 measures it. Whether same-tap pairs get full credit is read from the
  hold class only (same_tap -22 to -25).
- epyc9 wave kits (my scan failed there), HEAD and most KV windows beyond the family table; QC cb* kits show 4 to 12 ports each with an early
  latency of 447 to 538 ps, which I did not trace.
- Endpoint classes of any lepe or leaf proof kit; GRT TT of col_h9_r1, seqhost kit2 / kit3, glue F, t27keep (none had printed).
- The ABC recipe under place and route; LEC on hd_ctl, kv3_pc, kv_leaf.
- The H8 svc numbers, the reset key in a complete kit, the snap in flow: all lane-reported.

# FABLE-CLOSURE-STRATEGY 2026-11-19 03:30 PST (0330): what the tap rows and the +cycle rows will not fix

Reviewer: FABLE-CLOSURE-STRATEGY-04xx (Fable). Read-only: no job launched, killed or patched. Technical PD only; HBM parked.
Gate (R-MINIMAL): DRC 0, routed TT >= -42 ps, internal FF hold >= 0, bind + lane latency.
Marking: **V** = I opened the log or file this round. **R** = reported by the named lane. **I** = inferred. **P** = proposal.
Not re-proposed (owned since 02:00, evidence read): col_h9_r1 trunk (CTS -278 -> -14), glue relay core, tt_ctlm resynth + fence, lepe taps / CRP / WREP,
leaf fold + cap-1,000 rows + CFX, seqhost u_win, hd_mesh ECO, QC N4.4 / N4.5, KV hgi t2 split, col templates, the pinned-tree tool lag.
Rule set r713 as in `tools/die_plan/cbc_rules.py`. Nothing below is a hold (r703); every item is an estimator, a recipe change or a row.

## 0. Headline

1. **The leaf in-tap skew is a few far, small sink clusters per tap, and the cap-1,000 rows do not remove it (V).** Non-leaf taps follow the size of
   the tap's sink region; leaf taps read 100 ps or more even when small and compact. Lever 1.
2. **The cap pass itself is a cause (V).** Taps sitting exactly at the cap are 2 to 6 times more often over 100 ps than larger, uncapped taps. Lever 1.
3. **Kit synthesis is flat and ABC gets no delay target (V command line, R mechanism).** Depth fixed in RTL comes back relaxed. 63 of 95 scanned types
   have cones over 13 cells and only seqhost, glue and tt_ctlm have an owner for it. Lever 2.
4. **The placed-leg reach estimator returns nothing on 3 of 4 hosts and over-flags where it works (V).** Its digest line "legs>405 in 0" is a failed
   scan, not a clean kit; col_h9_r2 has about 3,400 legs over 405 um and passes 30 of 30. Cycle rows sized from distance alone are too many. Lever 3.
5. **About 1,000 lane-cycles of new rows (KV pv, KV hg, QC ft, S81 far copies) have no token run and no die-level STA / GRT on the plan that
   carries them (R, V by absence).** Lever 4.

## 1. Levers ranked by closure impact

| # | die | lever | types | owner |
|---|---|---|---|---|
| 1 | S81, KV | tap assignment by compact sink region, no cap spill; CTS-only A/B on two leaf DBs | leaf 75, kv_leaf 5, iq_C, kv512_C, c1x_C 43, lepe / lepw, KV hg 8, pv 16 | WAVE-FLOW-R2 (clock_taps.tcl), FABLE-FIX-S81-LEAF (A/B), CBC-RULES-1119 (rule constant) |
| 2 | all | synthesis recipe: delay target in the ABC script, or keep_hierarchy per bound sub-module | 63 types with cones over 13 cells (svc_hi / svc_lo, kv3_pc 4, iq_C, kv_leaf, kv512_C, kv3_hg 8, serdes) | WAVE-FLOW-R2 (recipe), FABLE-FIX-S81-SEQHOST (measure); svc depth NEEDS-LANE |
| 3 | all | reach estimator: retry failed scans, drop strap legs, classify a leg by macro span and logic, then size cycle rows | every type with a +cycle row | PRECHECK-1119, CBC-RULES-1119 |
| 4 | KV, QC, S81 | token run + die crossing STA / GRT on the composed plan before the bind is published | KV 56, QC 130, S81 394 | KV-D23-COMPOSE, QC-PLAN-R3, S81-DIE-R3 (one worker each); token run NEEDS-LANE |
| 5 | S81, QC | region for every scattered soft block (0 cycles) before its +1 cycle form | leaf 75 (vp glue), coll_core, lepe, glue-like partitions | FABLE-FIX-S81-GLUE (tool), FABLE-FIX-S81-LEAF, QC-PLAN-R3 |
| 6 | S81 | col_h9_r2 FAIL_route and the 162 far branches left over 405 um | 60 + col families | WAVE-FLOW-R2, S81-GEOM-OPUS |

### Lever 1. In-tap skew: far small clusters, and the cap spill
**Evidence (V).** `OT_TAP_INSERTION` joined with the TritonCTS lines of the same `4_1_cts.log` (sink region `CTS-0025/26`, buffers in path `CTS-0013`),
taps of >= 100 sinks, every route kit under `ot-jobs` on epyc8 (61 kits, 2,461 taps) and epyc10 (37 kits, 1,015 taps). Share of taps with skew >= 100 ps:

| | non-leaf, epyc8 / epyc10 | leaf + kv_leaf, epyc8 / epyc10 |
|---|---|---|
| sink region W+H < 150 um | 2 % / 6 % | 55 % / 54 % |
| 150 to 300 | 4 % / 9 % | 48 % / 35 % |
| 300 to 450 | 29 % / 25 % | 73 % / 74 % |
| 450 to 600 | 80 % / 40 % | 92 % / 88 % |
| >= 600 | 75 % / none | 100 % / 100 % |
| 100 to 500 sinks | 2 % / 8 % | 63 % / 52 % |
| 1,000 to 1,500 sinks | 6 % / 13 % | 75 % / 70 % |
| buffers in path >= 8 | 79 % / 33 % | 92 % / 89 % |

- Sink count hardly matters outside leaf. Region size does: W+H under 300 um keeps a tap under 100 ps in 91 to 98 % of cases.
- Taps at the cap (1,500 to 1,651 sinks, all families) are over 100 ps in 45 % (epyc8, 126 taps) and 71 % (epyc10, 49 taps). Larger uncapped taps
  (1,651 to 5,000): 20 % and 12 %. `clock_taps.tcl` line 477 moves the cheapest sinks of an over-full tap to the next-nearest tap with room.
- Leaf, per sink (`fable-fix-s81-leaf/t27d8e` and `t69d8e/leafclk_cts.tsv`, 26 taps): spread inside one clock leaf net is 1 ps. The spread is between
  leaf nets of one tap: median 117 ps (t27) and 92 ps (t69). No register class or flop master is early or late (class medians within 15 ps).
  The latest cluster holds 2 to 8 sinks in 19 of 26 taps, and cluster arrival follows distance from the tap's sink centroid (correlation >= +0.5 in
  15 of 26 taps, up to +0.97). `tap_balance.tcl` then pads the tap to that latest cluster, which leaves the bulk early (clk_t14: 159 ps).
- Worst taps: leaf t21 clk_t12, 1,500 sinks (1,942 before the cap pass), insertion 756 ps against the 450 target, skew 345; leaf t16 clk_t9, 1,499
  sinks, 685 / 257. Kit config: `OT_TAP_PITCH_UM = 400`, `OT_TAP_MAX_SINKS = 1500`, pair radius 200; CTS is one buffer type (BUFx24) with default clustering.
- Families outside the tap lanes with the same reading: dsdv_slice_iq_C 20 of 45 taps over 100 ps (insertion to 863; the 02:00 "iqf taps clean"
  line is withdrawn), kv512_C 18 of 40 (819), c1x_C 8 of 46 (650), lepe_nh_mus_C 15 of 39, kv_leaf 25 of 29 (1,020). KV from the kit scan (R):
  kv3_hg family 102 to 207 ps on 8 types, pv_v1 288 with 14 taps over.
- Not fatal alone: col_h9_r1 has 61 of 494 taps over 100 ps and its proof kit reads -13.6.

**Root cause.** Two terms. (a) Region: a tap that serves sinks over more than about 300 um of W+H gets 6 to 14 buffer levels and unequal branches.
(b) Stragglers: scattered soft logic, the cap spill and the group / pair passes hang a few sinks 200 to 300 um from the tap's bulk; the tree
reaches them late and the pad follows them. (I) for which pass produces each straggler: not traced sink by sink.

**What the dispatched rows do.** The 78 leaf rows use cap 1,000 and `tap_radius_um` 200 (`S81-LEAF-TAP-ROWS-cap1000.json`, V); 24 types keep taps
at exactly 1,000, the spill form. `cbc_rules.TAP_RADIUS_UM = 200` allows W+H up to 800. They will shorten the deepest trees; they do not address (b),
and leaf taps of 100 to 500 sinks already fail in over half the cases.

**Fix (P).**
1. FABLE-FIX-S81-LEAF: CTS-only A/B from the existing `3_place.odb` of leaf t21 and t16 (about 30 min each, no GRT), read `OT_TAP_INSERTION`:
   A nearest-tap only (cap pass off); B = A + `-sink_clustering_size 20 -sink_clustering_max_diameter 50 -balance_levels`; C = A + pad to the
   95th-percentile sink, not the latest. Accept: 90 % of taps under 60 ps and no tap insertion over the target.
2. WAVE-FLOW-R2: whichever form wins becomes the kit default; the cap becomes a reason to ask for a tap (WARN with the site), never a move to a farther tap.
3. CBC-RULES-1119 / PRECHECK-1119: the tap rule is "sink region W+H <= 300 um", checked on placed sinks; drop radius 200. tap_resolve.py and
   reach_fix.py take the same criterion. Die owners price the added M9 drops (about 150 um pitch on leaf free area, roughly twice the rows posted).
4. The t27stb kit (GRT pre-pass) stays as it is; it balances subtrees and may cover (b). Read it before choosing between A, B and C if it lands first.

### Lever 2. Flat synthesis with no delay target
**Evidence.** V: `1_2_yosys.log` of leaf t27keep: `abc -script /OpenROAD-flow-scripts/flow/scripts/abc_speed.script ...`, `SYNTH_HIERARCHICAL = 0`.
R (FABLE-FIX-S81-SEQHOST 03:20): the script maps with `&nf` and never references the period, so area recovery relaxes every cone toward the deepest
cone of the type; a 32-bit lookahead incrementer came back as a 16-stage OR chain (640 of 833 ps) and a 14-buffer serial chain.
R (PRECHECK depth scan, mapped cells, 95 types): 63 have cones over 13: svc_hi_dsdv_svc_rs t2 37 (69k ends), svc_lo t7 34 (83k), kv3_pc x4 26 to 29,
hd_ctl 23, iq_C 21, kv_leaf 20 to 21, kv512_C 18, serdes 17 to 18, kv3_hg family 15 to 18, glue 16.
**Root cause.** The mapper has no timing budget and one flat netlist; hand netlists (glue, tt_ctlm) and RTL rewrites (seqhost) each work around it.
**Fix (P).** WAVE-FLOW-R2: a kit-owned ABC script that uses the target (`&nf` then `buffer -c`, `upsize {D}`, `dnsize {D}`), target = 600 ps zero-wire
(the r713 depth rule), selected by one kit key. Proof is synthesis only: zero-wire STA (the seqhost frame) on svc_hi t2, kv3_pc and iq_C, old
script against new, count of ends over 600 ps and cell count. Until it lands: `(* keep_hierarchy *)` on each bound sub-module with a state loop
(seqhost kit3 is the test). svc_hi / svc_lo depth has no lane: NEEDS-LANE, and it shares a cause with the open over-cell-count class
(svc_lo_dsdv_svc_rs_w__t1, 450 min unanswered): buffer chains.

### Lever 3. Reach estimator: blind on three hosts, strap legs, distance without wire class
**Evidence (V).** `~/.local/state/precheck-kit-scan/*.placed.json`: epyc7 about 50 of 50 kits have a result; epyc8 0 of 73, epyc9 0 of 49, epyc10 1 of 68
hold `{"rc": 1}`. `kit_scan.py` writes the failure once and never retries (`if not sp.exists()`). The hourly digest then prints "legs>405 in 0".
- Where it works, slice_station's top legs are all `port:strap_ca_*` (static straps, 1.2 to 2.0 mm), and kv3_hub_Ei's is a strap at 2,254 um.
- col_h9_r2: 3,413 and 3,424 legs over 405 um (`u_y_xa/xb.o -> u_bs / u_t` core pins, 491 to 550 um, 1,132 + 1,064 + 370 bits). The family passes
  30 of 30 at TT -24 or better. col_h9_r1 has the same legs and failed only on the 652 to 729 um leg that crosses the ROM columns (718 ps unbuffered, R).
- Real, undeclared legs it does show: kv3_hg x8 `hst_t2.ti_b -> head_e` 1,582 bits at 600 to 691 um and `ectl columns -> hst0_g` 1,559 bits at 835;
  kv3_hgi x7 546 to 601; kv3_pv x9 `u_pvgN_pN -> u_pv_u_gN_j` 2,052 bits x 4 groups at 569 to 596; QC sle / slw_su_l1 `u_ist_x_su_c -> u_lane` 599 bits
  at 488 to 564; lepe `rid -> bout` 1,041 bits at 1,257.
**Root cause.** A buffered register-to-pin leg with no logic closes to about 550 um; a leg over a hard core cannot be buffered and fails near 400.
The estimator and the CBC rows price both the same.
**Fix (P).** PRECHECK-1119: retry `rc != 0`, exclude false-path and strap ports, and print per leg the span over hard cores and the zero-wire logic
delay. CBC-RULES-1119 and the die owners: a +cycle row is taken for a leg over 405 um only if it spans more than about 200 um of core or carries
logic; otherwise it is left to repair or gets a re-site. Applies now to: the 162 S81 far branches (03:17), QC ft re-station (+1 to +4 on 119
lanes, upper bound), KV pv class C (+843 cycles on 132 lanes, max +10) and class D (+12 on 64 columns).

### Lever 4. Cycle rows without a token run or a die-level proof
**Evidence.** R: KV pv C +843 cycles / 132 lanes, D +12 on all 64 command columns, pe2 to +11; KV hg section B +6 on 56 lanes; QC ft +1 to +4 on 119
lanes, slw_fw +3 on 5; S81 bs0 +1 on 2 buses. V by absence: no post since 11-18 16:00 reports a die GRT or crossing STA; the last are S81 D7w,
QC N3, KV HG1A, each 3 to 5 events old. Token cost per die is still not computed.
**Fix (P).** Each die owner runs its existing die GRT0 + crossing STA chain on the composed plan in parallel with the strict bind (KV: 25 min, R),
and one lane runs the token sim on the KV D25e and QC N4.5 cycle rows before publish. Advisory for count, but it is the only check of lane latency
at die level, which is a blocking gate. HEAD's three die items (M8 grant lock on 14 types, hold on real views, stale reservations) are unchanged.

### Lever 5. A region for scattered soft logic before a cycle
**Evidence.** V: leaf t69 placed scan, 3,766 legs over 405 um: `cst_hi -> lane macro` 1,193 to 830 um, `driver_xwd_c -> xwd_q` 241 to 765,
`vq -> u_ist_leafup` 278 at 619, `driver_hw_d -> u_vn` 256 at 594. Kit `PLACE_DENSITY = 0.25` on partitions PRECHECK measures at 0.4 to 2 % used.
R: t27keep's remaining class is vp glue with 600 to 800 um legs (336 + 122 ends) and "no region"; glue `u_record` stays 300 x 400 um without a fence;
the tt_ctlm fence holds 99.2 % of cells; coll_core `bin / lpad / srr` scattered over 700 to 1,100 um.
**Root cause.** In a nearly empty partition global placement has no reason to keep a block compact; its registers land hundreds of um apart.
**Fix (P).** FABLE-FIX-S81-GLUE turns its fence recipe into a generator rule: each bound sub-module above a cell threshold gets a region at about
55 % utilisation at the centroid of its core pins and face registers (0 cycles). FABLE-FIX-S81-LEAF runs it on t27 for the vp controller before
CFX / form B are bound; QC-PLAN-R3 on coll_core `srr` beside its ring SRAMs. Cycles are then added only for legs the region leaves over.

### Lever 6. col_h9_r2 route and the far branches (carried over, no new evidence)
R: the 02:00 item (21 of 63 kits FAIL_route in the post-GRT max-wire repair) has no cause posted; WAVE-PILOT-FIX notes only that
`OT_MAXWIRE_POST_SKIP` is not set. coll_core GRT ran 7 h 50 min in extra iterations with the clock NDR dropped (R). Both need one read of
`5_1_grt.tmp.log`; neither is a timing verdict.

## 2. Stop list (the 02:00 list stands, plus these)
- Do not expect the cap-1,000 rows to remove leaf skew, and do not enforce a cap by moving sinks to a farther tap.
- Do not quote "legs>405 in 0" from the kit scan on epyc8, epyc9 or epyc10, and do not count `strap_ca` legs as reach.
- No +cycle row from distance alone: col_h9_r2 passes with 3,400 legs at 491 to 550 um.
- No RTL tree-balancing as a depth fix without `keep_hierarchy` or the recipe change; the mapper undoes it.
- No per-type hand netlist for depth after glue and tt_ctlm; fix the recipe.
- No +1 cycle on a block whose registers have no region yet (leaf vp, coll_core).
- No middle-channel (x 310 / 340) trunk in KV hg (R: overflow moves, 43,904 against 45,119).
- No utilisation threshold as a flag (R: 572 of 610 types flagged).
- No tap table solved before the core or bank moves of the same event (FABLE-PD-S81-0253).

## 3. Not checked
- Which pass creates each leaf straggler; KV and QC taps on epyc7 / epyc9 (the tap join ran on epyc8 and epyc10 only).
- Whether variants A to C close the leaf TT; the share of leaf TT that is clock is still unmeasured, and t27stb has no result.
- The `&nf` behaviour itself (read from the seqhost post, not from the script: it lives in the flow image).
- Why the placed scan returns rc 1 on three hosts.
- col_h9_r2 FAIL_route, HEAD die items, any KV hg channel capacity number.

# FABLE-CLOSURE-STRATEGY 2026-11-19 02:00 PST (0200): cross-family causes, reach rule, die readiness

Reviewer: FABLE-CLOSURE-STRATEGY-01xx (Fable). Read-only: no job was launched, killed, deleted or patched. Technical PD only; HBM parked.
Gate (R-MINIMAL): DRC 0, routed TT >= -42 ps, internal FF hold >= 0.
Marking: **V** = log opened this round (01:15 to 01:55). **R** = reported by the named lane. **I** = inferred. **P** = proposal.
Signed (V, failure_breakdown 01:12): S81 43/394, HEAD 24/26, QC 27/130, KV 6/56. No change since 15:30 on 11-18.
Method (V): three scans of every wave kit with `run_route.log` written in the last 15 h on epyc8, epyc10, intel1, epyc2, epyc9, epyc7. KV wave kits are not under the scanned path (2 KV kits only), so KV is R.
"TT" below is the last `OT_TT_SETUP_REPAIR` line of `run_route.log`. That mixes placement-RC and GRT-RC reads, so use it for pass/fail counts and family ranking, not as a number of record.
Tonight's owned items (leaf fold, col_h9_r1 trunk, RLYBR, glue, lepe, serdes, QC pad chains, KV pv/hgi, HEAD ECOs, type reduction) are not re-proposed. Section 3 says which of them the scans agree with.

## 0. Headline

1. **Clock skew inside one tap is the best predictor of closure, and nothing in the flow removes it (V).** Sink-weighted skew inside a tap (`OT_TAP_INSERTION skew_ps`, taps of >= 100 sinks, 171 kits with a TT number):

   | skew inside a tap | kits | TT >= -42 | median TT |
   |---|---|---|---|
   | < 60 ps | 111 | 58 | -15 |
   | 60 to 100 ps | 37 | 5 | -290 |
   | 100 to 150 ps | 19 | 0 | -538 |
   | >= 150 ps | 4 | 0 | -732 |

   The tap balance pads each tap by its latest sink, so a tap with a few late sinks leaves its other sinks early. The GRT-RC pass that balances subtrees (`tapbal_grt.tcl` + `subtree_balance.tcl`) is opt-in and off in every kit I opened. Lever 1.
2. **Six S81 families are in that class and five have no clock diagnosis: leaf, kv_leaf, lepw LP, seqhost, bk_sel (about 85 types with lepe).** seqhost and lepw LP have the lepe signature (one tap with 25,794 and 13,284 sinks). Lever 2.
3. **The reach rule works as it stands at 405 um, where the placed hop obeys it (V).** Col kits whose largest placed relay hop (`OT_RELAY_POLY`) is <= 405 um: 30 of 30 at TT >= -42 (all col_h9_r2, largest hop 340). Col kits with a hop over 405: 13 of 62. The plan check cannot see this: PRECHECK REACH flags 6 of 395 S81 types. Section 2.
4. **col_h9_r2 (60 types) is clean on timing and dies in GRT (V).** 21 of 63 live kits are FAIL_route. One kit that got through reads GRT TT setup_est -21.51, hold_est +2.20. Lever 3.
5. **No die is ready to freeze on its own rule.** The last die GRT + crossing STA are on plans 2 to 4 events old (S81 D7w, QC N3, KV HG1A). Section 4.

## 1. Levers ranked by closure impact

| # | die | lever | types | owner |
|---|---|---|---|---|
| 1 | S81 (all) | balance inside the tap: proof kit with the GRT tap pre-pass on, or pad on the bulk of the sinks | leaf 75, kv_leaf 5 | FABLE-FIX-S81-LEAF (proof), WAVE-FLOW-R2 (default) |
| 2 | S81, KV, QC | re-solve taps on placed registers, criterion = insertion, for the over-loaded families | seqhost 1, lepw LP, bk_sel 1, kv_leaf 5, KV pv 17, kv3_sys_SD 2 | FABLE-FIX-S81-LEPE (solver), S81-DIE-R3, KV-D23-COMPOSE |
| 3 | S81 | col_h9_r2 GRT: post-GRT max-wire repair stalls, the retry is killed | 60 | WAVE-FLOW-R2 |
| 4 | S81 | relay generator (S81-RLYBR-1) on every col family in one D8h listing, judged on the placed hop | about 156 col | S81-GEOM-OPUS, S81-DIE-R3 |
| 5 | S81 | slice_station START reader hop rows | up to 46 (12 of 23 kits fail) | NEEDS-LANE |
| 6 | QC | tt_ctlm: depth rewrite with the glue tool | 1, plus the glue tool reuse | FABLE-FIX-S81-GLUE |
| 7 | all | placed-hop scan as the reach estimator (section 2) | all reach families | PRECHECK-1119 |

### Lever 1. Skew inside a tap (S81 leaf 75, kv_leaf 5)
**Evidence (V).**
- epyc10 `ot_s81sl_leaf__t16` attempt_8, no tap over the 1,500 cap. Raw CTS (`OT_TAP_BALANCE it0`): clk_t28 mean 223 ps, range 207 to 440, 535 sinks; clk_t22 mean 104, range 97 to 111. After balancing (target 450): clk_t22 450 (444 to 457), clk_t28 261 (245 to 478), clk_t36 316 (298 to 482), clk_t26 355 (342 to 497). Tap means span 261 to 477 (spread 216). TT -1,102.83.
- `ot_s81sl_leaf__t50` attempt_8, no tap over cap: tap means 336 to 639 (spread 303), clk_t42 `skew_ps` 180, clk_t9 214. TT -986.68.
- Family medians of the sink-weighted skew: lepe_nh LP 165, kv_leaf 150, bk_sel 144, lepw LP 141, leaf 130 (18 kits, largest tap skew 367, 0 of 17 pass), seqhost 115. For comparison: col_h9_r2 56 (29 of 29 pass), slice_station 31, QC st_a 18 to 27.
- Tap-mean spread gives the same split on 188 kits: < 80 ps 56 of 80 pass; 80 to 150 13 of 52; 150 to 250 3 of 40; >= 250 2 of 16.
- `gen_phys.py` (rt 0fe81af067d5): `TAP_GRT_PRE_DEFAULT = False`. `config.mk` of leaf t16, col_h9_r2, seqhost, QC sle_hc0 x3 and HEAD hd_turn_a has no `OT_TAP_GRT_PRE`; no `OT_STB` line exists in any log of the leaf kits.

**Root cause.** TritonCTS leaves 130 to 230 ps between sinks of one tap on these types. `tap_balance.tcl` adds delay at the tap root only, up to the latest sink, so the bulk of such a tap stays 100 to 190 ps early against its neighbours. Which sinks are the late ones is not read (I: sinks re-assigned by the cap rebalance to a tap 200 um away, or sinks behind leaf repeaters).

**What this does not show.** It is a correlation. The leaf fold (FABLE-FIX-S81-LEAF) is proven on its own and its proof went -527 to -230 with the clock untouched. The share of the remaining -230 that is clock is not measured.

**Fix.**
1. FABLE-FIX-S81-LEAF, on the t27keep DB: split the remaining ends by launch-clock minus capture-clock arrival. If the 336 `driver_dodd_q` ends carry more than 100 ps of it, the 600 to 800 um relay form is the wrong fix for them.
2. One private kit of leaf t16 or t50 (clean test: no over-cap tap) generated with `OT_GEN_TAP_GRT_PRE=1` (type key `clock.tap_grt_pre`), to GRT TT. Raise `OT_STB_ROUNDS` from 8: serdes H12 was still converging at round 8 (span 399 to 214, R 11-17).
3. If the late sinks are a small named set, the cheaper form is in `tap_balance.tcl`: pad to the median and re-hang the late sinks on their own chain.

### Lever 2. Over-loaded taps (seqhost, lepw LP, bk_sel, kv_leaf, KV pv)
**Evidence (V unless marked).**
- seqhost__t1 (epyc7 attempt_21): 29 taps, 46,198 sinks, one tap 25,794; spread 302; TT -538.36, GRT -570.57 on 12,107 ends, worst `u_win.mu_c[126]`. S81-TAIL filed it as data or depth; the tap table says clock first.
- dsdv_slice_lepw_mu_LP__t2 (epyc7 attempt_24): 21 taps, 52,142 sinks, one tap 13,284; spread 315; TT -1,890.29. Same form as the lepe LP pair, not in that lane's scope.
- kv_leaf t3 / t4: one tap 8,317 / 11,095; spread 276 / 309; TT -320.47 / -280.89.
- bk_sel__t2: 8 taps for 8,600 sinks on a 4,329 x 1,227 um outline (PRECHECK TAP-EDGE: 0% of the height); spread 451; TT -5,299.75.
- R: KV pv / pv_v8 one tap 10,339 / 10,234, TT -2,024 / -1,703; kv3_sys_SD x2 have 87% of free area over 200 um from any tap (PRECHECK).

**Sink count is not the criterion.** QC sle_hc0 has a tap with 13,082 sinks and reads +6.81 (spread 70). Leaf t16 has no tap over 1,500 and reads spread 216. What matters is the tap's raw insertion against the target, which is set by extent (FABLE-DIE-QC row 6 found the same on cbn_q00).

**Fix.** FABLE-FIX-S81-LEPE generalises its solver (taps from the placed register inventory of the latest `3_place.odb`, existing taps keep name and xy) into one tool with the rule "raw tap insertion <= target and sinks within 200 um", and runs it on seqhost, lepw LP, kv_leaf and bk_sel for D8h. KV-D23-COMPOSE runs the same tool for the pv family and sys_SD in D25d and drops the stale sink bins. Die owners confirm the spine can take the added M9 drops before the rows go in.

### Lever 3. col_h9_r2 GRT (60 types)
**Evidence (V).** 63 live kits: 21 FAIL_route, 30 of 30 with a TT number at -23.71 or better, hold FF estimate -68 to -85 before repair. Nine kits show one sequence: `OT_GRT_REPAIR_NO_PROGRESS ... flat 1,815 to 1,853 s inside the post-GRT repair_design (nets_done 10,000 to 14,000, remaining 70,602 to 75,694)`, stage stopped (rc 137 or 143); the retry with max-wire skipped ends `make Error 247` in GRT extra iteration 3/30 after 38 min (clce45cab5 pvf9c773d5, peak 15.7 GB). `col_h9_r2__t1__cl774acf45__pvea45273b` reached 6_report: GRT TT setup_est -21.51, hold_est +2.20.

**Root cause.** Not read. (I) `repair_design -max_wire_length 100` visits about 86,000 nets and its progress line goes flat past the 1,800 s watchdog; Error 247 on the retry is a kill, either the host memory guard or the same watchdog. The other 12 FAIL_route kits are not classified.

**Fix.** WAVE-FLOW-R2: read `5_1_grt.tmp.log` of one of the nine for what the repair is doing when the line goes flat, and name the killer of the retry. Then either restrict the max-wire pass to nets over the limit, or make the watchdog count buffers, not log lines. No unchanged relaunch of the 21.

### Lever 4. Relay generator on every col family
**Evidence (V).** Largest placed hop and pass count per family: col_h9_r1 729 um (49 of 49 kits over 405; 9 of 38 pass), col_h10_r1 867 (0 of 2), col_h10_r0_p1 746, col_h10_r0_p4 672 (0 of 4), col_h9_r0_p5 593 (1 of 6), p6 485 (3 of 5), p1 478 (0 of 1), col_h10_r2 446 (0 of 6), col_h9_r2 340 (30 of 30).
**Fix.** S81-GEOM-OPUS's all-col c4f listing is the right vehicle. Acceptance per family is the kit line: no `OT_RELAY_POLY` hop over 405 on the proof kit. Hand rows (col_h9_r1 trunk, bs0) fold into the generator output.

### Lever 5. slice_station START reader hop
**Evidence (V).** 12 of 23 kits fail (-139.85 to -874.87) with small tns (1,451 to 50,348), taps clean (skew 31, spread 56). The three worst ends I could read are one class: `u_cland_reader_start_ft18_i_0/g_x[0].u_r/q` (t43, 31 ends, -587.65), `..._ft0_i_0/g_x[4]` (t31, 90 ends at GRT, -344.07), `..._ft4_i_0/g_x[7]` (t48, 12 ends, -163.54). The 11 passing kits read -9.55 to +192.83.
**Fix.** One lane reads the START source of those three paths and checks them against the 8 START rows of D8f. If the rows miss ft0 / ft4 / ft18, the rule is the KV F2 one: the reader-start stage takes the nearest tap of the same depth (`start_stage_raw_resite.py`, 0 cycles).

### Lever 6. tt_ctlm
**Evidence (V).** epyc7 attempt_7: TT -266.85, GRT -279.37 on 4,845 ends, worst `u_core.u_8648/Q`; taps clean (largest 1,200, skew 31). (I) A flat generated netlist with a depth class, as glue was.
**Fix.** FABLE-FIX-S81-GLUE reads its cone depth histogram and runs `depth_opt.py` on it if the generator is the same.

## 2. Would "register both sides, hop <= 300 um" close the reach families?

**The rule is already right at 405 um. What is missing is where it is checked.**
- Both sides of every boundary are registered today (face registers, pin registers, landings). No change needed.
- Plan-declared hops obey 405 (6 of 395 S81 types flagged). Every reach failure found tonight is a leg the plan does not declare:
  1. a relay with sinks in two directions (bs0 918 to 972 um, col_h10_r0 t2 -> t3 at 1,035);
  2. a trunk aimed at a minority sink (col_h9_r1, 2,135 um tour; 156 col types + 61 dsdv_slice flagged MISAIM);
  3. a second source into a station (col_h10_r0 bn3, 1,448 um);
  4. the last leg into a hard-core pin on the far face (t3_payload 718 ps, QC rom_qr 1.1 mm, KV ectl 2,540 um);
  5. pad chains placed by GPL (QC: 0% sited outside sle_ctl and st_a; 651 um last hop on sle_ctl);
  6. reset relay to core reset pins (lepe 700 to 1,000 um, phy 19.9k bits, KV writer-start 2.1 mm).
- Do not lower the limit to 300: col_h9_r2 passes 30 of 30 with a 340 um hop, and more stations cost face-bank room (the leaf NS bank already fails at stride 2). Use 300 only for a leg that ends on a hard-core pin with library setup over 100 ps or starts at an SRAM / ROM output (bs0 setup 154 ps; st_b SRAM clk-to-q 255 ps + 276 ps wire).

**P: the rule as one check.** After placement, list every register-to-register, register-to-core-pin and reset-relay-to-sink leg over the limit (the wave already prints `OT_RELAY_POLY`; the placed scan QC-COLL-CORE used gives the rest). Fix in this order: re-aim, branch copy, join at the nearest station, site the pad chain (all 0 cycles), then one relay stage (+1 cycle).

**Lane-latency cost known so far (R).**

| die | rows | cycles |
|---|---|---|
| S81 | trunk aim, branch copies, join, tap rows | 0 |
| S81 | bs0 branch relay, 42 p3..p6 types | +1 on 2 buses |
| QC | pad-chain siting, st_b origin | 0 |
| QC | slw_fw flt_wo, 5 types | +3 on 5 lanes (4 -> 7, W2 5 -> 8) |
| QC | st_a rows (in N4.3) | 12 lanes changed |
| QC | glue relay core (kit F), coll_core stations | +1 on 2 program rows; coll_core not sized |
| KV | hg section B, 7 types | +6 on 56 lanes |
| KV | hgi K6 | +1 on 2 lanes |
| HEAD | none open | 0 |

Token cost per die is **not computed**: no lane ran the token sim on these rows. S81 is nearly free (one +1). KV hg +6 on 56 lanes is the only large item and needs the sim before D25d binds.

**What the rule does not close.** The clock class (levers 1 and 2, about 85 S81 types + KV pv 17), depth in state loops (glue, tt_ctlm, leaf vp 28 levels on 92 um, st_b multiplier 22 levels) and col_h9_r2 GRT.

## 3. Tonight's findings against the scans

| finding | scan |
|---|---|
| col_h9_r1 trunk aim | agrees: 49 of 49 kits have a placed hop over 405 (max 729) |
| col_h10_r1 / r2 same pattern (not measured by the lane) | agrees: 867 and 446 um, 0 of 8 pass |
| leaf fold | not re-checked; lever 1 adds a clock term the fold does not cover |
| leaf TAP-CAP 11 types | 13 of 25 leaf kits have a tap over 1,650, but leaf kits with no such tap fail the same way |
| lepe tap tables | agrees; lepw LP, seqhost, kv_leaf and bk_sel show the same signature |
| seqhost "pin-register / data" (S81-TAIL) | refuted as first cause: one tap holds 56% of the sinks |
| KV pv 10k-sink taps | not checked (KV kits outside the scan) |
| QC st_a | agrees on N4 kits (-318 to -445); no N4.3 kit has a number yet |

## 4. Die-level readiness for freeze (GRT0 + crossing STA rule)

| die | last die GRT | last crossing STA | changed since | open at die level |
|---|---|---|---|---|
| S81 | D7w, 11-17: overflow 0, M4-M7 use 2.7 to 4.4% (R) | D7w: 993 of 993 pass, worst +217.6 TT (R) | D8c to D8g: 9 rigid moves, 3 flips, bs0 +1 cycle | re-run both on D8g; nothing else known |
| QC | N3: overflow 0 (R) | N3: 2,993 crossings, 0 fail, 105 / 112 ps (R) | N4 to N4.3 changed lane transport on all 133 types | re-run crossing STA on N4.3 |
| KV | HG1A, 11-16: overflow 0 (R) | 3,915 of 3,915, worst +177.7 (R) | D21 to D24c: hub_C split; D25 adds kst depth 2 and +6 on 56 lanes | re-run both after D25d |
| HEAD | NF15f: overflow 0, use 0.37% (R) | tree2: intra +572, seam +656 (R) | r5 touches hd_mesh rows only | M8 grant lock: 4,321 die tracks on type tracks in 14 types; hold on real views 0 of 585,476 pairs measured; reservations stale (hd_tile 856 clock sites over placed logic) |

Reading: die routing is not the constraint on any die (overflow 0 everywhere measured). S81, QC and KV need a re-run of their existing proof chain on the current plan (KV: 25 min, R). It can start now and need not wait for type closure. HEAD is the only die with real die-level work left, and it is the three items in its row, not its two unsigned types.

## 5. Stop list (the 22:40 list stands, plus these)
- Do not judge taps by sink count alone (sle_hc0 passes with 13,082 on one tap; leaf fails with none over 1,500).
- No landing or pin-register rows for seqhost before its taps are re-solved.
- No lowering of the hop limit to 300 die-wide.
- No more hand relay rows per col family; use the generator and accept on the placed hop.
- Do not read col_h9_r2 FAIL_route as a timing verdict, and no unchanged relaunch of those kits.
- No +1 register stage for the depth classes in state loops (glue, tt_ctlm); rewrite depth.
- PRECHECK REACH on plan hops is not evidence that a family is inside reach.

## 6. Not checked
- Which sinks are late inside a leaf tap, and how much of the leaf TT is clock.
- The killer behind `make Error 247`, and the 12 other col_h9_r2 FAIL_route kits.
- KV kits (not under the scanned path), iqf (-336.95, taps clean, no end read), cbx_q10, su_c x3 and cbf_q01_s2 worst ends.
- Token cost of any cycle row.
- Whether `tapbal_grt.tcl` converges on a leaf (it has only run on cores and one serdes pilot).

# FABLE-CLOSURE-STRATEGY 2026-11-18 22:40 PST (2240): first D8e numbers, D25c structure, next levers

Reviewer: FABLE-CLOSURE-STRATEGY (run on Opus, Fable limited). Read-only: no job was launched, killed, deleted or patched. Technical PD only; HBM parked. No new holds or gates (r703).
Gate (R-MINIMAL): DRC 0, routed TT >= -42 ps, internal reg-to-reg FF hold >= 0.
Marking: **V** = log or report opened this round (21:15 to 22:37). **R** = reported by the named lane. **I** = inferred. **P** = proposal.
Corners: every number below is **TT**. "PC-TT" means the `OT_TT_SETUP_REPAIR` result after tap balance on placement RC. "GRT-TT" means the `OT_POSTCTS_GATE TT (global_routing)` line or the TT sign-off frame of `OT_GRT_FRAMES`. Path detail comes from `4_cts_post_hook.rpt`. I quote no `4_cts_final.rpt` or `5_global_route.rpt` number. The endpoint names in lever 4 and lever 8 come from the `tt_setup_repair.log` final row.

Signed (V, failure_breakdown 21:17): S81 43/394, HEAD 24/26, QC 27/130, KV 6/56. No change since 15:30.
Method (V): one scan of every route job on epyc8, epyc10, intel1, epyc2, epyc9 and epyc7 with `run_route.log` written in the last 3 h (261 jobs; last `OT_TT_SETUP_REPAIR`, GRT gate, `OT_GRT_FRAMES` and `OT_HOLD_GUARD_GRT` lines). `kit_wave_state.json` (21:03). Two `4_cts_post_hook.rpt` reads. Posts since 19:35 from 13 lanes.

## 0. Headline

1. **No D8e, N4.1q/N4.2 or D24c kit has a GRT number yet (V).** The first D8e numbers are PC-TT only, from 164 S81 rows in place/route. Two QC N4.1q kits are at GRT: coll_ft x2 have GRT-TT +19.03 and +27.08 (PASS), with hold FF est -124.17 / -162.52 before repair. D24c applied at 21:04 and has no kit past gen.
2. **D8e sorts S81 into three groups (V, PC-TT):**
   - Near (D8f also touches these): col_h9_r2 has 7 kits at -13.57 to -13.63 and one at +0.02 (pv7a260fc0). It was -96.71 GRT-TT before.
   - Clean slice_station: t24 x2 at +152.85 / +155.20, t50 at +165.24 (was -42.69), t29 cl2e5c855a at +44.48.
   - Broken in families that D8f and D8g do not touch:
     - leaf t25: -775.90, tns -2,166,466, 7,817 violators.
     - col_h9_r1: -277.82, tns -69,621, 641 violators.
     - col_h10_r0_p4 x3: -309.66 (was -473.83).
3. **The col_h9_r1 class is clock latency plus one unbuffered leg (V, post_hook TT).** The path is `u_lpl_9_r.u_y_q.g_chunk[1].r[23]` -> `u_t3_payload/i[47]` (sstn_payload536), with launch clock 452.22 ps against capture `ck` 151.21 ps. That is 301 ps of skew against setup. The data leg is one INVx4 into 98.86 fF, then 717.76 ps of wire delay. Slack is -297.57. Repair stalls at -278.0 after 4,092 iterations.
4. **The 1935 lever 2 was a corner error, now withdrawn.** The -44.50 ROM -> bn0 path was FF (from `5_global_route.rpt`). At TT on GRT RC all ROM -> bn ends pass (+27 to +84; R, S81-GEOM-OPUS 20:48). The real p3..p6 class is the y_xa/xb relay legs, which D8g c4c fixes.
5. **KV D25c is D25b with two notes renamed (R).** It still lacks F2 (K1), the W3 polyline move (K5) and hgi_v8 (K8). The 8 hg types sit at PC-TT -852 to -898 on D23H, and repair adds 0 ps. Their section B rows are in no event.
6. **Serdes (R, FABLE-FIX-S81-SERDES 22:36):**
   - H19 (k-means roots) routed with DRC 0, and `6_final` + spef are written. The make stopped at `6_report` on a flow guard (partition IR deferral refuses `PRE_FINAL_REPORT_TCL`); it is not a design fault.
   - H20 (star) failed detailed route with DRT-0255 after 99.5k iteration-0 violations.
   - **P:** pick k-means as the serdes form for the D8g host=type trunk rows now. Run `signoff.py` (TT/FF) on the H19 `6_final` without waiting for H21.

## 1. Outcome of the 1935 levers

| 1935 # | Lever | Outcome (22:37) |
|---|---|---|
| 1 | D8f clean landing | Not landed. Bind r3 died at 19:57 because ot-auto-retire deleted the S81-DIE-R3 gitshim. r4 elab passed at 20:59 and is in strict bind; apply about 22:45. The D8e reads asked for (leaf, col_h9_r1) are in this section: both are broken. |
| 2 | ROM -> bank late capture | WITHDRAWN (FF corner; see 0.4). Replaced by D8g c4c relay_sites, now handed to S81-DIE-R3. |
| 3 | GRT hold guard stop at met | f2c9d5f37f3 is in rt. New kits print `installed (single-mode GRT hold repair progress/time bound)`, but no kit has shown the stop yet. Old kits still chunk at 0 violators: sle_hc0 cl38badc56 chunk 4 (+1.15), cl4baa7c9c chunk 4 (+6.84), sle_hc0 cl05696ed1 chunk 3, slw_st_b_v2 chunk 3, slice_station t41 chunk 6 at ws +20.47 (+1.21). |
| 4 | QC st_a rows + coll_core lane | Rows requested at 19:26 (FABLE-FIX-QC-STA) and not in N4.2. The 8 N4 st_a kits are still -159.90 to -288.18 PC-TT. A coll_core lane exists (QC-COLL-CORE-1118): NEED-STATION, 106 groups. No N4.3 yet. |
| 5 | Sign-off from the bundle | rt fd8cedab is live, but nothing has signed since, so it is untested. |
| 6 | KV W1 + hgi reads | D24c applied at 21:04. The F2 rule is on main aae3f7b5ec6. D25b went RED at PRE (SCHEMA); D25c is building. See lever 5. |
| 7 | S81 tail | S81-TAIL classified the tail types: glue is an RTL OR chain; pvso_entry t1/t2 need macro-path rows (31+31); leaf t56 is an RTL reset width. seqhost and dsdv_slice still have no cause. |
| 8 | HEAD hd_mesh | The 16 DRC come from 2 stale reserved clock rows plus 2 tap-site slivers (R, 20:51 / 21:01). r5 deletes them; the mesh_pa2 route-keeping ECO is running. mesh_w1 is dropped. |
| 9 | p2 throat | In D8g c4c (MX flip, frame hops <= 405, ft0 22x51). The DRT-0352 probe is being retried. |

## 2. Levers ranked by closure impact

| # | die | lever | unblocks | owner |
|---|---|---|---|---|
| 1 | S81 | leaf: name the `u_lf4_u_vs/sw_fi` class (7,817 ends) and write rows for D8h | leaf family about 77 | S81-LEAF-D8E-1118 (read), S81-DIE-R3 (rows) |
| 2 | S81 | col_h9_r1: t3_payload `ck` lead (about 300 ps) + relay site on the `u_lpl_9_r.u_y_q` -> t3 leg | col_h9_r1 60 | S81-GEOM-OPUS (rows), S81-DIE-R3 (D8h) |
| 3 | S81 | D8g c4c bind with the bs0 branch relay cycle row in the same delta | col_h9_r0_p2..p6 54 | S81-DIE-R3 |
| 4 | S81 | col_h10_r0: frame_int_o0 face hop (worst `u_ist_frame_int_o0_0/q[1156]`, 905 ends), using the c4c p2 frame-hop form | col_h10_r0 p1..p6 | S81-GEOM-OPUS |
| 5 | KV | D25c lacks F2, the K5 polyline, K8 hgi_v8 and the hg section B rows: put them in D25d, not volume on D25c | hgi 11, hg 8 | KV-D23-COMPOSE, FABLE-FIX-KV-HG |
| 6 | QC | N4.3 = st_a rows (72 paths, 0 conflicts on live) + coll_core bound record-bus stations | st_a about 11, coll_core 1 | QC-PLAN-R3, QC-COLL-CORE-1118 |
| 7 | S81 | serdes form = k-means (H19 DRC 0); sign off H19 now; host=type trunk rows in D8g/D8h | serdes 11 | FABLE-FIX-S81-SERDES, S81-DIE-R3 |
| 8 | S81 | phy__t1 reset recovery: -2,467.98 PC-TT, worst end `u_bin_dfi_i0/eq` RESETN, 2,101 ends | phy 1+ | NEEDS-LANE |

### Lever 1. leaf `sw_fi` (S81, about 77 types)
**Evidence.**
- V: epyc10 `ot_s81sl_leaf__t25__cl431c660f` (D8e), `tt_setup_repair.log`. PC-TT went -1,113.81 -> -775.90, tns -2,495,882 -> -2,166,466, with +1,990 cells. The repair stalls at -765.907 for its last 100 iterations. The final row has 7,817 violators, worst end `u_bound.u_u_lf4_u_vs/sw_fi`. Placement density is 0.25.
- R: the other leaf kits (t24, t40, t44) are still running. Of the 3 leaf kits that reached place in 6 h, t54 failed on the NS face bank (the `face_flop_ns_types row_stride 2` row, S81-DIE-R3 19:51).

**Root cause.** Not read. A -766 ps wns with a stalled repair and 7.8k ends looks like a structural class, not a tail (I). It is not XR (S81-DIE-R3 19:51).

**Fix.**
1. S81-LEAF-D8E-1118: open `4_cts_post_hook.rpt` on this kit, or the first leaf kit that has one, and name the start of the `sw_fi` path. Say whether it is distance (station/relay row), clock (core pin lead) or logic depth (RTL).
2. S81-DIE-R3: one class row for D8h. Also revert or widen `row_stride 2` for the t54 face bank.

### Lever 2. col_h9_r1 (S81, 60 types)
**Evidence (V, epyc2 `col_h9_r1__t1__cl49d7a23e__pv36da905c`, D8e, `4_cts_post_hook.rpt`, TT).**
- Worst path: `u_lpl_9_r.u_y_q.g_chunk[1].r[23]` (clock 452.22) -> INVx4 (fanout 1, 98.86 fF) -> `u_t3_payload/i[47]` (`ot_s81_sstn_payload536`). Arrival 1,374.60; `ck` at 151.21 ps; required 1,077.03; slack -297.57.
- `r[2]` -> `i[26]` gives -290.15; the next end is -284.63.
- The repair ends at -278.008, 641 violators, worst end `t3_payload/i[47]`.

**Root cause (I).** Two terms:
- (a) The hard core's `ck` is 301 ps earlier than the launching relay flops, so the capture clock is early against setup.
- (b) The last relay leg is one unbuffered wire of 718 ps (about 600 um by the 98.86 fF).

This is the same class S81-GEOM-OPUS named for p3..p6 (y_xa/xb last relay into sstn t1/t2, -64/-35/-23), but far larger here because of term (a).

**Fix.**
1. S81-GEOM-OPUS: `clock.core_pin_lead_ps` on `u_t3_payload` (the D8f key). Size it from the measured skew, less the hold room on the other t3 inputs.
2. A relay_site that puts `u_lpl_9_r.u_y_q` within 405 um of t3 (0 cycles, c4c form).
3. Both go in the delta after D8g (D8h) and cover all 60 col_h9_r1 types.

### Lever 3. D8g c4c (S81, 54 types)
**Evidence (R, S81-GEOM-OPUS 22:35).**
- c4c (ad60aa762ac9) on D8f c4 changes p2 (12 types) and p3..p6 (42 types).
- G0 shows 2 errors against 2 in the control, 0 new. Strict bind on c3 gave 0 errors and LATCHECK 873/873.
- bs0.i_x0/i_x1 are single-cycle (TT setup -154 / hold +179 against `ck[0]`). Their relay -> bs0 legs are 918 to 972 um (FABLE-PD-STRUCT-2053 S1).

**Fix.** S81-DIE-R3 binds c4c together with the bs0 branch relay cycle row (xa_1_bs0_0 / xb_1_bs0_0, 283 + 266 bits, bs3 form) and the S81-FAILS rows (station t51 native_w/_e paths, eng t1 engram closure). The S81-TAIL pvso_entry 31+31 renames (`lanes/handoff/S81-TAIL-1118-pvso-macro-rows.json`) belong in the same delta.

Without the bs0 row, all 42 p3..p6 types fail on bs0 at GRT (I, from S1). The 12-type cf lattice WARN is advisory; take c4d (origin 604.8 + track_offset) only if the bind complains.

### Lever 4. col_h10_r0 (S81)
**Evidence (V, PC-TT).**
- p4 pv5b623e07 / pvc9270d09 / pvd11cc58b (D8e): -524.98 -> -309.66, tns -453,854 -> -25,037, +4,744 cells. 905 violators, worst end `u_ist_frame_int_o0_0/q[1156]` D.
- The d8t p4 kit was -473.83.

**Root cause (I).** This is the frame_int_o0 face-bank hop that c4c fixed on p2 (446 -> <= 405 um). col_h10_r0 has no such row.

**Fix.** S81-GEOM-OPUS: measure the frame_int_o0 hops on the h10_r0 plan and site regs as on p2. Put this in D8h.

### Lever 5. KV D25c against FABLE-PD-STRUCT-2053 K1-K9

D25c = D25b with the two SCHEMA annotation keys folded into the note (R, KV-D23-COMPOSE 22:34). The gate is on epyc8. Per item:

| K | 2053 risk | In D25c? | Read |
|---|---|---|---|
| K1 | F2 writer-start stages 6/7 reset tap | **NO** | The rule has been on main since aae3f7b5ec6 (21:04, `start_stage_raw_resite.py`, plan-rule form: 342 START stages on hgi_v3..v7, median 764 um, worst 2,611 um). D25b/c are built on tools d6a5a52. hgi_v4..v7 keep PC-TT -571.30 / -595.44 / -802.28 / -890.39 (V, D23H). Run the resite after the W1 tree re-solve and use `--check` on the bind. |
| K2 | kt stations | PARTLY | The 16 sited rows per type (304) are kept, so the 2053 line-siting risk is gone. But no generator places the kst cells at those sites (`kit_istations` maps `core:` rows to S81 classes only), so the cells are GPL-placed. The k3 proof used plan sites, so the proof does not carry over. |
| K3 | second band rect copy | YES | Both copies, the core and the tap are shifted by the same amount. |
| K4 | 16.4 um E gap, about 595 of 1,560 q wires | n/a | Read GRT overflow at x 61..78, y 1097..1218 on the first hgi_v1 kit. |
| K5 | W3 polyline on the ft2 stations | **NO** | It is still [[340, 950.4], [340, 618]], 16 to 25 um from the ft2 stations. The 2053 fix was x about 312 with the tail ending at y about 660. This is what fails next on hgi_v1 after W1 (k4: new overflow of 12,000 at x 0..400, y 400..600). |
| K6 | W5 two-hop pad (580 + 670 um) | as is | 0 cycles at (45, 560). Expect a small negative at GRT; the fallback is a second pad stage (+1 cycle). |
| K7 | W2 with W1 untested | as is | The proof kit decides. |
| K8 | hgi_v8 core at y 924.48 | **NO** | FABLE-FIX-KV-HG gave the row at 21:04 ([25.92, 924.48] -> [25.92, 1097.28]). hgi_v8 PC-TT is -294.85 (V, D23H). |
| K9 | 5 unsigned cores (e0, ectlk q0..q3) | rule taken | No hg/hgi kit counts until these sign. |

**Also absent: hg section B (V + 2053).**
- 8 hg types on D23H: hg_v1p2..p6 and hg_v3 at PC-TT -851.75 to -897.59. Repair adds 0 ps (wns unchanged in -> out); tns -169k to -286k. kv3_hg is at -235.00.
- These are the ectl q0 eN -> `u_bout_o_ectl_Q_N_eN` legs (-837, 2,540 um), tN, ring dsel and astk ep -> er rows. No event carries them.

**P (no hold).** Let D25c apply if green; it is W1/W2/W3/W5 on hgi_v1 only. Do not read hgi_v4..v8 or hg kits on D25c as a result. Compose D25d now on D25c: F2 resite after the W1 re-solve, K5 polyline at x 312 / tail 660, K8 hgi_v8 +172.8, and the hg section B rows (FABLE-FIX-KV-HG has them in `lanes/handoff/FABLE-FIX-KV-HG-rows-d24.json` section B).

### Lever 6. QC N4.3
**Evidence.**
- V, N4 kits, PC-TT: sle_st_a_v1 -166.94 / -208.31; sle_st_a_v2 -198.80 / -214.34 / -186.80; slw_st_a_v1 -272.62 / -288.18; slw_st_a_v2 -159.90 / -167.95.
- V: coll_core -575.77, tns -656,572. cbx_q10 -730.88 (repair made wns worse). sle_ctl x3 -85.79 to -109.28. cbf_q01_s2 -214.21.
- R (QC-COLL-CORE-1118 19:31): coll_core is NEED-STATION. Bound record buses: qdata -> bout_rec_tx_s0 427 bits at 851 um; dsel -> bin_rec_rx_s2_i 331 bits at 1,298 um; bin_rec_rx -> coll.srr about 297 bits at 1,500 um.
- R (FABLE-FIX-QC-STA 19:26): 72 st_a row paths resolve on live N4.1q with 0 conflicts, and N4.2 touches none of them.

**Fix.** QC-PLAN-R3 composes N4.3 on N4.2 now with the st_a rows + asbuilt edits (and the R8 re-derive), plus the coll_core station rows when QC-COLL-CORE posts them. Do not wait for a routed st_a kit.

### Lever 7. serdes form
H19 k-means: routed, DRC 0, `6_final` written (R). H20 star: DRT-0255. H21 (star + boot fix) is in GRT.

**P.** FABLE-FIX-S81-SERDES runs main `signoff.py` TT/FF on the H19 `6_final` now, and takes k-means for the serdes die_trunk host=type rows that S81-DIE-R3 carries in D8g/D8h. The 6_report stop is a flow guard: WAVE-FLOW-R2 lets `final_report.tcl` accept `pad_abut_strip.tcl` as a pre-final hook, or skips the IR deferral for that hook.

### Lever 8. Smaller, one lane each
- **phy__t1** (intel1, -2,467.98 PC-TT, tns -456,368, 2,101 ends, worst end `u_bin_dfi_i0/eq$_DFF_PN0_/RESETN`): a reset recovery class. Reset is not staged to the dfi bank. NEEDS-LANE.
- **slice_station t43** (-587.65, 31 ends, `cland_reader_start_ft18_i` g_x[0]) and **t29 clc7772371** (-345.20, 32 ends, `cland_fstart_ft3_o`): START-hop ends. Confirm that D8f's 8 START rows cover ft18 and ft3. If not, S81-DIE-R3 adds them to D8h.
- **HEAD:** hd_ctl -184.99 PC-TT on 1 end (tns equals wns): one routed setup ECO, owner HEAD types lane. hd_mesh via r5 + mesh_pa2. These two take HEAD to 26/26.
- **hold guard** (WAVE-FLOW-R2): show one `OT_HOLD_GUARD_GRT` stop line on a post-f2c9 kit. Until then, the 22 old kits keep chunking.

## 3. Stop list
- Do not read setup from `5_global_route.rpt` (FF) or `4_cts_final.rpt` (pre-tap-balance). The 1935 lever 2 was wrong for this reason.
- No late-capture rows for col_h9_r0 ROM -> bn (all pass at TT).
- Do not expect D8f or D8g to move leaf, col_h9_r1 or col_h10_r0 (they touch none of them). Read their D8e kits now and do not wait for D8f GRT.
- No p3..p6 D8g kit counts as proof before the bs0 row is in and S1/S2 are read at TT on GRT.
- Do not treat D25c as carrying F2, K5 or K8, and do not launch hgi_v4..v8 or hg volume to prove it. No hg/hgi kit counts before e0 and ectlk q0..q3 sign.
- No unchanged relaunch of leaf t54 (face bank), leaf t56 (RTL rst_n), pvso_entry t1/t2 (macro paths), gunit t1 (module closure) or eng t1 (engram closure).
- No more H20 star route attempts; H21 is the last star read.
- No pc rows from HG6-era kits.
- No hold chunks after 0 violators (rule exists; prove it fires).

# FABLE-CLOSURE-STRATEGY 2026-11-18 19:35 PST (1935): what fails next on D8e / N4.x / D24

Reviewer: FABLE-CLOSURE-STRATEGY-1935. Read-only: no job launched, killed, deleted or patched. Technical PD only. HBM parked.
Gate (R-MINIMAL): DRC 0, routed TT >= -42 ps, internal reg-to-reg FF hold >= 0. No new holds or gates (r703).
Marking: **V** = file or log opened this round (19:10 to 19:35). **R** = reported by the named lane. **I** = inferred from V data. **P** = proposal.
Numbers: GRT or routed only, plus `OT_TT_SETUP_REPAIR` lines (they run after tap balance, on placement RC). No `4_cts_final.rpt` number is used.

Signed (V, failure_breakdown 19:10): S81 43/394, HEAD 24/26, QC 27/130, KV 6/56. No change since 15:30.
Method (V): posts since 15:30 of 18 lanes; `kit_wave_state.json` (19:08); one scan of every route job with a log written in the last 40 min on the six build hosts (127 jobs); two kit reads (col_h9_r0_p6 on epyc10, kv3_hgi_v7 on epyc7).

## 0. Headline

1. **No D8e or N4.1q kit has a GRT or routed number yet (V).** D8e (df7446e48ba9): 331 rows RUNNING. 49 have been in kit gen since 17:49 to 17:55; 282 were launched at 19:08. N4.1q (b146b2d2b02a): 32 rows, all launched at 19:07. First D8e GRT lines: about 22:00 (I). Everything below is read from older-plan kits whose rows D8e / D8f / N4.x do not change, and from the private proof kits.
2. **122 of the 282 new D8e kits are in families that D8f replaces at about 20:50 (V counts):** col_h9_r2 60, col_h10_r1 12, col_h9_r0_p3..p6 42, slice_station START types 8. They will be in gen or placement when D8f applies. The D8e reads that count are leaf (77) and col_h9_r1 (60).
3. **col_h9_r0_p6 at GRT is -104.89 TT after repair, and its GRT report names a ROM-to-bank end (V).** `u_u_e0_u_w` (falling edge) -> `u_u_bn0`, -44.50 in `5_global_route.rpt`. This is the col_h9_r2 class (e11 -> bn11). D8f gives the 45 ps late capture to `u_r2.u_bn1[12]` only, and the p3..p6 halo buffers nothing. 42 types fail next on D8f.
4. **The GRT hold guard is the largest avoidable cost on every die (V).** 22 live kits have 0 violators and still add chunks at +0.2 to +2.7 ps each (slw_sc_v1 x2: chunk 6 after 14.5 h in GRT). On S81 col kits the port bus is still in the repair and chunk 1 made hold worse. Both 1530 fixes are not done.
5. **QC st_a has no row in N4.1q or N4.2 (R + V).** Eight wave st_a kits sit at -108 to -214 TT at GRT. The proven form (k5) is a handoff file.
6. **KV: 13 hgi kits are in GRT on D23H at -208 to -890 (V), 2.5 to 24.5 h each.** W1 is in D25, not in D24c. hgi_v4..v7 and pc are two classes with no named cause.

## 1. Levers ranked by closure impact

| # | die | lever | unblocks | owner |
|---|---|---|---|---|
| 1 | S81 | D8f lands clean: tree on all six gen hosts before apply, supersede in the same tick; read leaf and col_h9_r1 first on D8e | 122 kits re-gen once, not twice; leaf 77, col_h9_r1 60 | S81-DIE-R3, WAVE-FLOW-R2, S81-LEAF-D8E-1118 |
| 2 | S81 | ROM -> bank late capture for the col_h9_r0 banks; relay for `u_y_cc` -> `u_s0.lc` | col_h9_r0_p3..p6 42 | S81-GEOM-OPUS |
| 3 | all | GRT hold guard: stop at met; S81 col input ports out of the repair | about 22 live kits now, 2 to 12 h each; every D8e col kit | WAVE-FLOW-R2 (tool), S81-DIE-R3 (S81 setting) |
| 4 | QC | st_a rows (k5 form) into the next QC event; coll_core gets a lane | st_a 11; coll_core 1 | QC-PLAN-R3, FABLE-FIX-QC-STA; NEEDS-LANE coll_core |
| 5 | QC, S81, HEAD | Sign-off and late ECO from the admission bundle, not the kit copy; post-route insert result on hc0 | every routed near miss (hc0 x2, st_b x4, slw_fe, station t50 / t41, col_h9_r2 pilot) | WAVE-FLOW-R2, FABLE-FIX-ROUTE-LOSS, QC-TYPES-R3 |
| 6 | KV | W1 into the next bound event without a D24c wait; one read each for hgi_v4..v7 and pc | hg / hgi 17, pc 4 | KV-D23-COMPOSE, FABLE-FIX-KV-HG; NEEDS-LANE pc |
| 7 | S81 | Tail types with tns below -30,000 and no row | about 8 types | NEEDS-LANE, one per type |
| 8 | HEAD | mesh_pa ECO: hold pads against 14 ps of TT room; the 16 DRC are pin-edge shorts | hd_mesh 1 | FABLE-FIX-HEAD-MESH |
| 9 | S81 | col_h9_r0_p2 bank-leaf GRT stop: open the lpad_xo_i0 throat; judge GRT on the 2D report | col_h9_r0_p2 12 | S81-GEOM-OPUS, WAVE-FLOW-R2 |

### Lever 1. D8e reads and the D8f switch

**Evidence (V, `kit_wave_state.json` 19:08).**
- df7446e48ba9: RUNNING 331. By host: epyc8 229, epyc10 54, intel1 18, epyc2 16, epyc9 14. 49 rows at stage gen with start 17:49 to 17:55; 282 with start 19:08.
- Old block e291d6a8e740 (d8t): 22 RUNNING, 30 ENQUEUED; ed968f4cc6e6: 11 ENQUEUED. The autopilot was cancelling these at 19:15 (`CANCELLED class SUPERSEDED`).
- epyc8 at 19:20: 668 GB available, load 76. Memory is not the limit now.
- R (FLEET-OPS-R 19:13): D8e replicas verified on epyc7 and epyc9; S81 gen hosts are now six.
- R (FAIL-ROUTE-1115 19:08): leaf t56 failed at kit_rtl bind; svc_hi_dsdv_svc_rs__t4 failed on the cell cap at place.
- R (FABLE-FIX-S81-SERDES 17:58): all 17 serdes attempts stop at `OT_BOOT_RELEASE expected3 kept stages, found 0`; fix 2551bd7f342 is not confirmed on a wave kit.

**Root cause.** The wave launched the full S81 set on D8e 100 min before D8f. The event key is the same for both; only the plan block differs.

**Fix (no hold).**
1. S81-DIE-R3: replicate the D8f tree to all six gen hosts before the apply, so the relaunch does not land on epyc8 alone (229 of 331 rows are there).
2. WAVE-FLOW-R2: on the D8f apply, cancel the rows whose block changed in the same tick as the probe (17:46 took one extra tick).
3. S81-LEAF-D8E-1118: the first D8e numbers to post are leaf t17 / t24 / t31 / t51 at GRT (XR rows) and one col_h9_r1 kit at GRT (frame stations). These two families are 137 types and D8f does not touch them.
4. S81-DIE-R3: the D8e tree tools are b3e667d1865. The cell-cap stop was deleted on main 54d289d964a; svc_hi_dsdv_svc_rs__t4 shows the kit still carries it. State whether kit tools come from the tree or from rt/current, and put 54d289d964a, 2551bd7f342 and 01c4b1e891d in the D8f tools.
5. FABLE-FIX-S81-SERDES: the first D8e serdes attempt must print `OT_BOOT_RELEASE placed3`. If it prints `found 0`, 11 types fail again for the 17:58 cause.

**Lost read.** The col_h9_r2 pilot pvf8d9f9e5 (GRT -96.71, in detailed route at 15:30) was cancelled as superseded at 19:15 with kit logs idle 10.2 h (V, autopilot log). The GRT-against-routed question for S81 col kits is still open; the first D8f col_h9_r2 kit answers it.

### Lever 2. col_h9_r0_p3..p6: the ROM -> bank end

**Evidence (V, epyc10 `ot-jobs/col_h9_r0_p6__t1__pv9da72aa7-route-civil-redfish-579642-1795043355/work`, old plan; D8e and D8f add only the halo to this family).**
- `OT_TT_SETUP_REPAIR` at GRT: wns -143.87 -> -104.89, tns -9,618 -> -2,823. `OT_POSTCTS_GATE TT (global_routing)` setup_est -104.89. The kit is in detailed route.
- `5_global_route.rpt`, worst setup path: `u_bound.u_u_e0_u_w` (falling edge-triggered) -> `u_bound.u_u_bn0`, data arrival 1,090.53, slack -44.50. I did not confirm the corner of this report, so the TT end at -104.89 may be another path of the same bank.
- Sibling pv8241ebb8 (epyc8): -437.44 -> -330.33 on placement RC, max-wire pass +64,891 cells.
- R (S81-GEOM-OPUS 17:37): p3 `u_y_cc` -> `u_s0.lc` -440, 867 ps of unbuffered wire in a boxed pocket.

**Root cause (I).** Same structure as col_h9_r2: a ROM launched on the falling edge feeds a qbank core pin. The data has half a cycle less the ROM clock-to-q. D8f moves and late-clocks bn11 / bn12 in `u_r2` only.

**Fix (S81-GEOM-OPUS, next delta after D8f).**
1. Read the TT worst 20 ends on pv9da72aa7 at GRT (`tt_setup_repair_grt.log`) and name the banks. If they are ROM -> bn ends, add `clock.core_pin_lead_ps` rows for those banks (same key as D8f, value from the measured shortfall, bounded by hold on the other bank inputs).
2. One relay or buffer site for `u_y_cc` -> `u_s0.lc` (FABLE-PD-STRUCT-1840 B6 fix 4).
3. The first D8f col_h9_r2 kit tells what 45 ps buys at GRT. Size the r0 rows from that number, not from the estimate.

### Lever 3. GRT hold guard

**Evidence (V, scan; last `OT_HOLD_GUARD_GRT` line per kit).**
- Kits with 0 violators still adding chunks: slw_sc_v1 x2 chunk 6 at ws 24.9 (+1.4 / +1.9), 14.5 and 14.8 h after launch; slw_sc_v3 chunk 4 (+2.70); sle_sc_v3 chunk 4 (+0.56); sle_sc_v2 chunk 3 (+0.38); coll_s chunk 7 (+0.19); sle_st_b x4 chunk 2 (+0.24 to +0.44); hc0 x2 (+0.17, +0.22); slw_fe_v1 (+0.18); hd_host_e chunk 8 (+0.91); hd_spn chunk 4; kv3_io_cor chunk 4; glue; slice_station t14 / t41. 22 kits.
- R (FABLE-FIX-QC-STA 18:37): on k5 chunks 3 and 4 gained +0.80 and +0.46 ps for 2,370 s and 2,320 s; the chase to 40 costs about 2.5 h per kit after hold is met.
- S81 col, port bus still in the repair: p6 pv9da72aa7 `OT_GRT_PORT_HOLD ... INCLUDED`; start ws -63.46 / 953 ends; chunk 1 ws -90.74 (-27.27) / 1,367 ends, +202 buffers, 2,056 s. col_h10_r0_p4: port_in 1,374 at -59.17.
- S81-COL-FLOW-1118 has no post since 15:30.

**Root cause.** The stall rule only stops at ws >= 30 (or 40), so a met design keeps buying fractions of a ps. R-MINIMAL needs >= 0, and the post-route insert pads the real tail.

**Fix.**
1. WAVE-FLOW-R2: in the guard, end the repair after the first chunk that leaves 0 violators at the kit margin (the 1530 `OT_HOLD_STALL_MIN_WS` fix, withdrawn request 1320 lever 2 fix 1). One condition; no gate.
2. S81-DIE-R3 (the COL-FLOW lane is silent): `OT_GRT_PORT_HOLD_INCLUDE=0` for S81 col kits in the D8f gen env, the QC form. The signed col pilot carries 340 port ends and passes.

### Lever 4. QC: st_a rows, and the wide kits

**Evidence.**
- V (scan, N4 wave kits at GRT, `OT_TT_SETUP_REPAIR`): sle_st_a_v1 -166.94 / -208.31; sle_st_a_v2 -198.80 / -214.34; slw_st_a_v1 -108.52 / -118.87; slw_st_a_v2 -159.90 / -167.95. tns -5,948 to -12,525.
- R (FABLE-FIX-QC-STA 17:54): k3 (copies at the row pins) -155.38 at the GRT gate after +26,384 max-wire cells: dead. k5 (copies at 0.6 of source -> pin) +10.78 on placement RC, hold +7.82 at GRT; its TT GRT gate had not printed at 18:37. Rows: `lanes/handoff/FABLE-FIX-QC-STA-rows-n41.json`.
- V (wave state): the 32 N4.1q launches hold no st_a item. R (QC-PLAN-R3): N4.2 is seam 110 / per-type 160, su_l1 chains, wep. No post puts the st_a rows in either event (I).
- V: coll_core -692.43 -> -575.77, tns -656,572; no lane post names it. cbf_q01_s2 -214.21 (port_in 605 at -159.66). sle_st_b_v2 pvcd986c42 GRT gate TT -106.24, in route; its sibling classes are at -4 to -17.
- V: cbx_q10 -730.88 and sle_stm_v3 -175.65 / tns -62,756 are N4 kits; N4.1q carries their rows (sidx straps, 3 stations). Re-read on N4.1q.

**Fix.**
1. QC-PLAN-R3: take the k5-form st_a rows into the event after N4.2 as soon as k5 prints a TT GRT gate >= -42. Do not wait for its route.
2. FABLE-FIX-QC-STA: post the k5 `OT_POSTCTS_GATE TT (global_routing)` line.
3. NEEDS-LANE: coll_core (read the worst 20 ends at GRT; tns -656,572 is a structure, not a tail).
4. QC-TYPES-R3: sle_st_b_v2 pvcd986c42 at -106 against siblings at -4 to -17 is a class difference; read its worst end before a relaunch.

### Lever 5. Sign-off and ECO tools from the bundle; post-route insert

**Evidence.**
- R (FABLE-FIX-ROUTE-LOSS 17:37): the wave signs with the kit-frozen `signoff.py`. Same hc0 routed DB: kit copy TT -29.85, FF -21.57 on 152 ends; main copy TT -18.81, FF -12.99 on 34 ends (nominal clock pin cap, r708). col_h9_r2 pvea45273b failed TT by 2.75 ps this way.
- R (QC-TYPES-R3 17:55): hc0 cl38badc56, 34 HB4 at the capture pins inserted, route running; cl4baa7c9c 72 HB4 planned at the -45 limit. No sign-off result yet.
- R (FABLE-FLOW-1750 C): the staging fault is gone for new kits; hd_host_n ran a real late ECO and failed in it (TT 53.26, FF -129.41, DRC 3).
- V (scan, GRT gate TT / hold): sle_hc0 cl05696ed1 +5.96 / +9.08; slw_hc0 cl4f54b7a3 -1.46 / +2.82; slw_hc1 cl144ee7b3 -17.33 / +11.40; sle_st_b_v1 x2 -10.31 / -4.24; slw_st_b_v1 -16.79; slw_fe_v1 cl95cd1d0c +15.81; slice_station t14 +44.12, t7 +6.17, t50 -42.69, t41 -65.86 on one end; hd_spn +11.29. All in or near detailed route. These are the next sign-offs on every die.

**Root cause.** Kits generated before ad8672055e are judged with pre-r708 caps, and their late ECO prices room with the old tool.

**Fix.**
1. WAVE-FLOW-R2: the sign-off stage and the late ECO take `signoff.py` and `eco_loop` from the admission bundle (the `SIGNOFF_BUNDLE` list the ECO already prints), not from the kit.
2. QC-TYPES-R3: when the hc0 D-pin form returns, post TT and internal FF from the main `signoff.py`. If TT lost more than 10 ps, the branch pad on the `wd` driver is the form to build.
3. S81: slice_station kits without a START hop are the nearest S81 count after the pilots (four at GRT TT -43 or better). t41 is one end: one routed setup ECO.

### Lever 6. KV

**Evidence.**
- V (scan, epyc7 and epyc10, D23H, `OT_TT_SETUP_REPAIR` at GRT): hgi -208.16; hgi_v1 -267.91 / -309.01 (tns -54,659 / -123,836; 18.4 h); hgi_v2 -311.03 / -319.37 (24.5 h; hold start -591.08 on 1,302 ends); hgi_v3 -222.35; hgi_v8 -294.85; hgi_v4 -571.30, v5 -595.44, v6 -802.28, v7 -890.39 with tns only -12,231 to -23,568.
- V: pc cl254f2e73 -468.20 (tns -221,370) and -814.67 (31.6 h, hold chunk 4 at -207.92 on 1,173 ends); pc cl5a95b461 -729.16; pc_v3 -1,486.48 (tns -412,788).
- R (FABLE-FIX-KV-HG 17:38): k5 +0.46 after the pad re-site; west band 28,820 at iteration 5 (-35 %), not clear without W1; W1 needs a bound event. R (KV-D23-COMPOSE 17:56): D24c = pvfin fork nets; D25 = W1, W2 + W3 + W5, kt.
- V (kv3_hgi_v7 `run_route.log`): `cross-tap guard not applied (no tap window lines in the kit SDC)`; port_in 815 at -80.00; no GRT report yet.

**Reading (I).** v4..v7 have a wns 2 to 3 times worse than v1 / v2 with a fifth of the tns: a few ends on one long path, not the west-band class. Nobody has named it.

**Fix.**
1. KV-D23-COMPOSE: compose D25 on the D24c plan now and bind it as soon as D24c is green; D24c hgi kits cannot sign (no W1).
2. FABLE-FIX-KV-HG: read the worst 20 TT ends of hgi_v7 and hgi_v4 from `tt_setup_repair.log` on epyc7 (read-only, 10 min) and say whether D25 covers them.
3. NEEDS-LANE: kv3_pc (4 kits, tns -205,000 to -413,000, no post since 15:30).
4. KV-HUBPV-1118: hub_C at 709k cells is above the largest closed run (517k); the D24 split is its only path.

### Lever 7. S81 tail types

**Evidence (V, scan, old plan; `OT_TT_SETUP_REPAIR` or GRT gate).** dsdv_slice_lepe_mu_LP__t2 -797.59 / tns -706,385; dsdv_slice_lepe_nh_mus_LP__t1 -925.61 / tns -834,432; seqhost__t1 -538.36 / tns -2,077,477; col_h10_r0_p4 -473.83 / tns -32,900; tt_ctlm GRT TT -285.9 (pin-register mean 294 against 250); glue GRT TT -130.39, in route 9.3 h.

**Root cause.** Not read. D8e relaunched dsdv_slice, eng, gunit, iqf, svc and col_h10_r0 rows; no D8e or D8f item names any of them.

**Fix.** One lane per type (owner rule 11-14): read the worst 20 ends at GRT, write a class row for the event after D8f. col_h10_r0 (p1..p6) first: it is a family.

### Lever 8. HEAD hd_mesh

**Evidence (R, FABLE-FIX-HEAD-MESH 17:38 / 18:47).** mesh_pa routed: TT -27.61 on 3 ends (pass), FF internal -22.59 on 39 ends, DRC 16 (12 shorts, 4 spacing; M4 / M6 at the north-edge pins x 395 to 397 and 510 to 512, y 1226.7; M6 / M7 at x 27 and 70, y 199). GRT over-reads routed tap insertion by 34 ps TT. V (19:20, `mesh_pa_eco1.log`): ECO pass dir ready (`prd pass dir ready .../eco1/i1t`), no result.

**Risk (I).** TT room is 14.4 ps; the S81 r2 pilot lost 13 ps in one ECO. The shorts sit on boundary pins, so a reroute may return them.

**Fix (FABLE-FIX-HEAD-MESH).** If the ECO returns DRC > 0 at the same four spots, move those pin sites one track in the plan pins (structural), not a second ECO. If TT falls below -42, pad the 39 ends at capture pins with the sign-off-priced insert only.

### Lever 9 (added 19:50, COORD input). col_h9_r0_p2 bank-leaf proof kit: GRT-0116

**Evidence (V, epyc2 `s81-geom-opus-bank/gate_bl2/kits/col_h9_r0_p2__t1__cl0045af7b__pv622a6f97/gen/.../run_route.log` and `congestion*.rpt`).**
- Layer table at the stop: total 77,186 = M8 43,074 + M6 29,732 + M4 3,624 + M5 454 + M7 301. Usage is low: M8 6.46 %, M6 18.33 %, all layers 14.47 %. M2 and M3 have 0 and 1.
- The 2D overflow did converge. Report sizes by iteration: 5 -> 720 gcells (overflow 1,444), 10, 15, 20 shrinking, 25 -> 416 bytes, 30 -> 5 gcells (7), final `congestion.rpt` -> 2 gcells (4 tracks).
- The two final gcells: `Vertical congestion, capacity:0`, bbox (1162.23, 671.46) and (1170.21, 671.46), nets `u_lpad_xo_i0.q[45 / 176 / 214 / 250]`.
- At iteration 5, 1,183 of the 1,444 sat in x 1100 to 1200, y 600 to 700: `u_lpad_xo_i0.q` bits and their buffer nets, vertical, capacity 0 to 9. Neighbours (plan sites): `u_cf` (1131, 604), `u_t1_payload` (1123, 475), `u_n5` (1166, 734). Second spot: the north edge y 1250, ft0 output stations (`ft0_o_s*`), 67; `ft_track_use.json` flags ft0 `u_station 3.05, over_target`.
- `OT_PGCAP region adjustments (adj 1.0 ...) by layer M7 331 M5 664 M6 588`; resource reduction M6 38.6 %, M7 36.0 %, M5 33.8 %, M8 29.0 %. `GRT-0297 Disabling NDR for 8 congested nets` (clock nets).

**Root cause (I; the layer-assignment reading is not checked against the router source).**
1. The stop itself is 4 tracks in two zero-capacity gcells: the `u_lpad_xo_i0` q bus leaves its landing pad through a vertical throat at x 1162 to 1171, y 671 that the pad / `u_cf` obstruction and the PG-cap regions close completely.
2. The 77,186 is per-layer overflow after layer assignment, on the two upper horizontal layers only. M6 and M8 carry regional capacity cuts (PG-cap M6 at adj 1.0 in 588 regions; M8 grant runs) while M2 / M4 are 76 to 80 % free. The 2D router balanced the sum; the assignment put horizontal demand on M6 / M8 where they have none. This is a capacity-model effect, not a lack of tracks: 63,485 gcells over 90 % at 14 % total usage cannot be real demand.

**Fix form (S81-GEOM-OPUS; rows for the delta after D8f, 12 types).**
1. Structural: open the throat. Shift the `u_lpad_xo_i0` pad (or `u_cf`) so its q pins face a channel with vertical tracks, or give the first hop of the 251-plus q bits a relay row on the open side (same form as the D8f u_vq re-site). Check with one number: capacity > 0 in the gcells at x 1160 to 1172, y 671.
2. ft0 north edge: spread the ft0 output stations (station use 3.05 against a 0.5 target) over two rows.
3. Flow, WAVE-FLOW-R2: the kit should judge GRT on the 2D report (4 tracks here) and carry on to detailed route when the 2D overflow is under a few tens, as the QC kits do (`GRT congestion allowed`). The kept `5_1_grt-failed.odb` can go to detailed route as it is; that is the cheapest proof of whether the M6 / M8 figure is real.
4. S81-GEOM-OPUS: check why PG-cap blocks M6 at adj 1.0 in 588 regions on this type; a partial adjustment restores the upper horizontal layer.

Unblocks col_h9_r0_p2 12. Not checked: the bank-leaf row itself (what gate_bl2 changed against the wave kit), and whether the wave p2 kits stop the same way.

## 2. The 1530 levers: outcome

| 1530 # | outcome | note |
|---|---|---|
| 1 D8e | **APPLIED 17:37 (R)**; 331 rows running (V); no GRT number yet | p3..p6 "relay row" and slice_station magnitudes withdrawn or unconfirmed (pre-hook report, FABLE-PD-STRUCT-1840 C). |
| 2 post-route insert | **PARTIAL** | Tools on main; hc0 insert routing (R). Stall stop not put back: 22 kits still chase (V). |
| 3 S81 port hold | **NOT DONE** | Still INCLUDED; chunk 1 made p6 worse by 27 ps (V). Owner lane silent. |
| 4 col_h9_r2 | **IN D8f** | Bank move, grid-snapped, plus 45 ps late capture (R). Owed routed read lost at 19:15 (V). |
| 5 col_h10_r1 | **IN D8f** | Site at 0.41 (R). Second class withdrawn (report artifact). |
| 6 KV | **HALF** | Hop fixed, k5 +0.46 (R). West band needs W1 in D25. Five cores running (R). |
| 7 HEAD | **ROUTED, NOT SIGNED** | TT passes; FF -22.59 / 39; DRC 16; ECO running. Halo fix da13a203f90 in rt/current (R). |
| 8 QC st_a | **HALF** | k3 dead at GRT -155.38; k5 hold met, TT gate pending (R). N4.1q applied 18:18 without st_a rows. |

## 3. Stop list

1. S81: reading the 122 D8e kits of col_h9_r2, col_h10_r1, col_h9_r0_p3..p6 and the 8 START slice_station types as results; D8f replaces them.
2. S81: expecting the p3..p6 halo to move -105 at GRT; it buffers nothing.
3. All dies: hold chunks after 0 violators (0.2 to 2.7 ps per 2,000 s chunk).
4. S81: input ports in the col GRT hold repair.
5. QC: more st_a wave kits on a plan without the k5-form rows (eight are at -108 to -214 now); the pin-sited st_a form.
6. KV: hgi / hg kits on D23H or D24c as sign-off candidates; more hours for hgi_v1 (18.4 h) and hgi_v2 (24.5 h) in GRT; pc cl254f2e73 at 31.6 h.
7. All dies: judging a routed kit with its kit-frozen `signoff.py` when the kit predates ad8672055e.
8. HEAD: a second blind ECO on mesh_pa if the same four pin-edge shorts return.
9. Any verdict from `4_cts_final.rpt` (unchanged from 1840).
10. S81: reading 77,186 on the p2 proof kit as missing tracks; the 2D overflow is 4. No outline or channel growth for it before the failed DB has been through detailed route.

## 4. Not checked

- The D8e plan content for tail types and col_h10_r0 (I read posts, not the plan diff).
- The corner of the p6 `5_global_route.rpt` path; the TT worst-end list.
- Whether N4.2 plan_n42_c holds st_a rows (inferred from posts only).
- k5 TT GRT gate, hc0 ECO sign-off, mesh_pa ECO result: not printed at 19:30.
- Whether wave kit tools come from the tree or rt/current.

# FABLE-CLOSURE-STRATEGY 2026-11-18 15:30 PST (1530): delta on 13:20

Reviewer: FABLE-CLOSURE-STRATEGY-1530. Read-only: no jobs launched, nothing killed, deleted or patched. Technical PD only. HBM parked.
Gate (R-MINIMAL): DRC 0, routed TT >= -42 ps, internal reg-to-reg FF hold >= 0.
Marking: **V** = I opened the file or log this round (15:10 to 15:30 PST). **R** = reported by the named lane, not opened. **P** = my proposal or estimate. **I** = inferred from V data.

Signed (V, failure_breakdown 15:10): S81 43/394, HEAD 24/26, QC 27/130, KV 6/56.
Method (V): the ten lanes' posts since 13:20; one scan of every live `ot-jobs/*-route-*/work` dir on the six build hosts (280 jobs: S81 203, QC 57, KV 13, HEAD 7), reading stage, last TT setup line, hold-guard lines and last error; then the logs named in section 2.

## 0. Headline

1. **Four of five live S81 kits cannot close on the d8t plan (V).** Of 146 S81 kits with a post-CTS or GRT TT number, 116 are below -100 ps, 11 are in -100 to -42, and 19 are at -42 or better. Leaf 47 of 48 below -100 (median -598); col_h9_r1 15 of 20 (median -278); col_h9_r0_p1..p6 22 of 22 (-148 to -375); slice_station 8 of 14 (-352 to -1,039); col_h10_r1 8 of 9. D8e is the only event that changes this. At 15:04 its chain had refreshed the tools (`TOOLS_SHA` b3e667d1865) and was building the publish pack; `g0.log` ends `G0 FAIL: 2 errors` (I did not identify the two lines).
2. **The post-route repair path has been dead since 11-17, and that, not GRT margin, is the route-loss lever (R, FABLE-FIX-ROUTE-LOSS 14:18 / 14:37).** STAGE-CAP deleted `5_2_route.odb` before the late ECO read it: 16 of 26 late ECOs ended `pass dir not staged`, 0 kits signed off after an ECO. Fixed on main 8f3d167975 and cd66ba221f. On hc0 the bulk hold moves -0.9 ps through route; the 152 failing ends are a 0.3 % tail caused by clock leaf arrival (+17 ps), not signal RC.
3. **My 1320 fix (stall stop only at ws >= 30) was the wrong lever; withdraw it (V + R).** Live QC kits now chase at +2.2 to +2.8 ps per chunk under the buffer cap (`slw_sc_v1` x3 at ws 15.9 / 17.4 / 22.7, `sle_sc_v3` 24.0, each chunk ending `RSZ-0060`). ROUTE-LOSS measured that 85 of the 152 ends still fail with every end at +20, and 46,487 ends sit below +30.
4. **S81 col kits spend their GRT hold repair on input ports (V).** `OT_GRT_PORT_HOLD_INCLUDE=1`: 1,170 violating ends, all `port_in` (pre-GRT class line: port_in 1,169, same_tap 0, cross_tap 0; worst path `frame_int_i0[1046]` -> `u_bin_frame_int_i0/q[1046]` -87.02). Chunk 1: 440 buffers in 1,917 s for +15.6 ps, then `RSZ-0060`. 26 live S81 kits end the guard on the cap. The signed col pilot carries 340 port ends at -61 and passes.
5. **col_h9_r2 at GRT reads -87 to -109 on 12 of 27 kits, not -47 (V).** Same kit: -23.71 on placement RC, -148.05 / tns -47,636 on GRT RC, -108.74 / tns -3,505 after 3,820 repair cells. The max-wire pass added 1,978 cells against an estimate of 47,471 (`OT_MAXWIRE_PASS post skipped: no-progress stop`). The +13 ps bank move does not cover this.
6. **KV west rows cost setup (V).** k4 (k3 + W2 + W3) post-CTS TT -138.19 / tns -231 against +0.43 on k3. k3 GRT is flat: west-band overflow 44,172 at iteration 5, 41,052 at iteration 10, now at extra iteration 13 of 30 after 5 h.

## 1. Levers ranked by closure impact

| # | die | lever | unblocks | owner |
|---|---|---|---|---|
| 1 | S81 | D8e apply; read the four first kits; open rows for the families D8e does not touch | leaf 77, col_h9_r1 60, col halo 216, serdes 11 | S81-DIE-R3 |
| 2 | QC, HEAD, S81 | Post-route insert (sign-off-priced) on every routed DB; relaunch the late ECO on kits that died `pass dir not staged` | about 11 routed kits now; every QC kit after | FABLE-FIX-ROUTE-LOSS, QC-TYPES-R3, HEAD-TYPES-OPUS, S81-COL-FLOW-1118 |
| 3 | S81 | Take input ports out of the GRT hold repair on col kits, or pad them by a fixed count | 32 min per chunk on every live col kit; 440 buffers per chunk | S81-COL-FLOW-1118, WAVE-FLOW-R2 |
| 4 | S81 | col_h9_r2: stronger form than the +13 ps move; settle GRT against routed TT | col_h9_r2 60 | S81-GEOM-OPUS, S81-COL-FLOW-1118 |
| 5 | S81 | col_h10_r1: d1 site at 0.40, not the midpoint; second class (lpl chunk strobe) has no row | col_h10_r1 12 | S81-GEOM-OPUS |
| 6 | KV | k4 srl hop before W2 / W3 go into an event; ECTLK quarter re-harden started now | hg / hgi 17, pv 16 | FABLE-FIX-KV-HG, KV-KT-E0 |
| 7 | HEAD | mesh_pa: tap-balance buffer off the clock-entry OBS; routed TT and hold by ECO, new sign-off files | hd_mesh 1 | FABLE-FIX-HEAD-MESH |
| 8 | QC | st_a: buffer core-pin nets before GRT; N4.1 pack | st_a 11, cbx_q10 4, stm 1 | FABLE-FIX-QC-STA, QC-PLAN-R3 |

### Lever 1. D8e apply, and what it leaves

**Evidence (V).** Scan buckets in headline 1. epyc8 `s81-die-r3-e8/d8e`: `TOOLS_SHA` b3e667d1865 written 15:03, `pub/finalpack` created 15:04, `r6/g0_status.log` `G0_RC=1`, `pre.out` PASS with findings 0. R (S81-DIE-R3 14:32): BIND_RC 0, LATCHECK 873 / 873.

**Root cause.** The wave keeps 203 S81 route jobs alive on d8t. XR (leaf), frame stations (col_h9_r1) and halos (col) exist only in D8e.

**Fix (S81-DIE-R3).**
1. Apply. The four first reads from 1320 stand (leaf with XR, col_h9_r1 GRT residual, col_h9_r0_p6 at 3_5 and M5 shorts, serdes__t13 star lines).
2. D8e does not carry a row for these, and each is wide (V numbers; the paths are from `4_cts_final.rpt` in the flow frame, so the class is I):
   - col_h9_r0_p3 / p4 / p5 / p6, 15 kits at -330 to -339 after repair (p6: tns -59,983 -> -5,157 with 3,861 cells). Flow-frame worst: `u_d14_u_cf_rs_r122_s1` -> `u_d14_u_cf_rs_r122` -283.8 (cf reset relay hop) and `u_bout_ret_o0` -> `ret_o0[3]` -336.6. Owner S81-GEOM-OPUS: read the sign-off-frame worst end on p6 pv0012ba28 (epyc10) and write the relay row; the halo alone does not move -330.
   - slice_station t22 -1,039, t36 -858, t25 -839, t52 -611, t43 -588, t31 -574, t27 -454, t44 -352. No post since 13:20 names a cause. NEEDS-LANE: one read per type, then a class row.
3. XR-MID (58 far types) stays the delta after this event.

### Lever 2. Post-route insert, not GRT margin

**Evidence.**
- R (ROUTE-LOSS 14:18, hc0 cl38badc56, same DB before and after detail route, 49,310 internal ends): route minus GRT hold slack median -0.9 ps, p05 -2.6. The 152 failing ends lose 13.9 ps mean, of which clock +17.2 (capture clock 18 ps later routed than estimated) and data +3. Routed TT setup room at the 152 capture pins is >= 144.9 ps.
- R (14:37): no post-route repair ran on any kit since 11-17; the old FF-only pass read TT room at the FF corner (hc1 TT -59.5 -> -141).
- V (epyc9 `fable-fix-route-loss/hc0/kit/signoff_rl1/{tt,ff}/sta.log`, new `signoff.py`): `STD_WNS_MAX -18.81`; FF `STD_MIN_NONPORT n 34 wns -12.99`; `EP_DUMP ff 34`, `EP_DUMP tt 60711`. The wave job read -29.85 and -21.57 on 152 ends on the same design; the posts do not say why the private copy reads 11 ps and 118 ends better. ROUTE-LOSS should state it before the numbers are compared. No `eco_loop` output yet at 15:25.
- V (scan): 15 live QC kits end a hold chunk on `RSZ-0060`; chunk gains after the first are 2.2 to 2.8 ps.
- V (scan): QC is healthy before route. 24 of 36 QC kits with a TT number are at 0 or better post-CTS.

**Root cause.** The tail is per-leaf clock arrival error (-14 to +47 ps routed minus GRT), which no uniform GRT margin covers at an affordable cell count (hc0 is at 102 % of the cell cap).

**Fix.**
1. QC-TYPES-R3: put `OT_HOLD_STALL_MIN_WS` back so the guard stops once hold is met (about 10 ps). 1320 lever 2 fix 1 is withdrawn.
2. Owners named by ROUTE-LOSS: one late-ECO relaunch on each routed DB that ended `pass dir not staged` (hc0 x2, hd_ctl, col_h9_r2 pvea45273b, slice_station t24 / t26 / t47 / t49, hd_spn_wshim_rx x2, slw_fe_v1 x3), with `signoff.py` >= cd66ba221f and `eco_loop` >= 8f3d167975 copied into the kit.
3. FABLE-FIX-ROUTE-LOSS: finish the hc0 proof (34 ends padded at capture pins, TT re-read). This is the QC count lever: st_a, sc, fe and hc all arrive at route with setup met.
4. TT side, P: the hc0 routed TT failures are not the GRT worst ends (`asm_d[0][*]` loses 59 to 75 ps: one start point fans to all of them). A fan-out start point of this kind needs a copy per sink group; ROUTE-LOSS to name the count from `ep_tt.tsv`.

### Lever 3. S81 col kits: input ports in the GRT hold repair

**Evidence (V, epyc10 `ot-jobs/col_h9_r2__t1__clce45cab5__pva119e808-route-*/work/run_route.log`).**
- `OT_PREGRT_FF_HOLD class after port_in 1169 ws -57.61 same_tap 0 cross_tap 0`.
- `OT_GRT_PORT_HOLD input-port starts INCLUDED in the GRT hold repair (OT_GRT_PORT_HOLD_INCLUDE=1)`.
- `OT_HOLD_GUARD_GRT start: hold ws -89.09 tns -52242.6 viol 1170`; chunk 1 `-73.52 (+15.57) ... +440 buffers (cap 439), 1917 s`; `[ERROR RSZ-0060]`.
- `5_global_route.rpt` min path: `frame_int_i0[1046]` -> `u_bin_frame_int_i0/q[1046]` -87.02.
- Other col_h9_r2 kits: chunk 3 -46.96, chunk 4 -45.15 (+1.76). col_h9_r0_p6 starts at -63.46 with 953 ends.
- 1320 (V): the signed col pilot has `STD_MIN_NONPORT n 0` with 340 port ends at -61.39.

**Root cause.** The port bus is a 1,169-bit input register bank with one common shortfall. An iterative repair capped at 0.25 % of instances per chunk treats it as 1,170 separate problems, takes 32 min per chunk, and never reaches its target.

**Fix (S81-COL-FLOW-1118 with WAVE-FLOW-R2; no gate).** Either `OT_GRT_PORT_HOLD_INCLUDE=0` on S81 col kits (the QC form, `grt_nonport_hold.tcl`), or, if the die seam needs `OT_HOLD_IN_MIN`, one deterministic pad: the same delay cell on each `u_bin_*` D pin, count taken from the measured shortfall, placed in the pre-GRT script. The owner of the INCLUDE=1 setting should say which.

### Lever 4. col_h9_r2: +13 ps is too thin

**Evidence.**
- R (S81-COL-FLOW-1118 13:29): pilot cl774acf45 pv11b6518d routed TT -46.87 with DRC 2; after one ECO DRC 0, TT -59.45. The ECO cost about 13 ps.
- R (S81-GEOM-OPUS 14:24): the -59.45 path is ROM `u_e11_u_w` pval (falling-edge launch, 610 ps clk-to-q) -> `u_bn11` e_r0 over 259 um. H9R2-BANK-1 moves bn11 / bn12 to 151 to 160 um; estimate +13 ps, no kit yet.
- V (1320): the sibling pilot signed at TT -38.29.
- V (this round): kit pva119e808 numbers in headline 5. Scan: 12 of 27 col_h9_r2 kits below -100 at GRT, 5 in -100 to -42; the 10 at -13.6 to -23.7 are still at CTS on placement RC. epyc2 cl774acf45 pvf8d9f9e5: GRT -96.71, in detailed route (79,225 violations at iteration 0).

**Why +13 is too thin (I).** -46.87 + 13 = -34 leaves 8 ps, and the kit still needs the ECO that cost 13. -59.45 + 13 = -46 fails. The family lands at -38 to -59 routed, so a robust close needs 30 ps or more.

**Stronger form (P; S81-GEOM-OPUS).** The launch is a ROM at half cycle, so the wire is the small term and the capture clock is the large one. Keep the bank move and add a late capture clock on the bn11 / bn12 clock entry by the measured rule FABLE-FIX-QC-STA put on main 4815c737fdb (`cland_fclk_target`: raise the macro clock delay to what the worst D pin lacks; on QC it took 1,574 ends from -177.4 to +11.2 with 8 cells). Target 45 ps, bounded by e_r0 -> e_r1 setup inside the core and by hold on the other bn inputs.

**Owed read (S81-COL-FLOW-1118).** Routed TT of pvf8d9f9e5 against its GRT -96.71. If the route lands near -47, the S81 GRT estimate is about 50 ps pessimistic (the opposite sign to QC) and the 3,820 repair cells per kit are waste; if it lands near -97, the wave kits are worse than the pilot and need the max-wire pass that was skipped.

### Lever 5. col_h10_r1: two classes

**Evidence.**
- R (S81-GEOM-OPUS 14:24): H10R1-D1-1 puts `u_d1_11_Y.q` at the midpoint, 693 um per cycle.
- V (1320): the path has 792 ps of data with 1,274 um and 355 ps of wire delay (0.28 ps / um), wns -138.57, launch clock 339 against capture 307.
- V (this round, epyc8 pv6a7ae122 and intel1 cld01bb4ae): wns -384.96 / tns -46,245 and -351.22 / tns -52,776. Flow-frame worst: `u_u_lpl_32_r.g_chunk[13].rq` -> `.wr` -207.6 and `.g_chunk[22].wr` -> `u_y_q.g_chunk[22].r[5]` -225.1.

**Why the midpoint is thin (P).** Midpoint saves 581 um x 0.28 = 162 ps: +24 on placement RC, before a 25 to 45 ps route loss. The legs are not equal: leg 1 carries the landing-pad macro launch and 32 ps of adverse skew, leg 2 is flop to flop.

**Fix (S81-GEOM-OPUS).** Site d1 at 0.40 of the pad -> station path (about 555 um from the pad): +62 on leg 1, and leg 2 at 833 um is about 235 ps of wire. Second class: the `g_chunk[*].rq -> wr -> r[*]` strobe on 2 of 9 kits has no row; one `wr` copy per chunk sited at the chunk (P).

### Lever 6. KV

**Evidence.**
- R (KV-D23-COMPOSE 13:30): D23h2 applied with fixes 1 and 3.
- V (epyc9 `fable-fix-kv-hg3`): k4 `OT_TT_SETUP_REPAIR cells 56 added; wns -145.52 -> -138.19 tns -309.75 -> -231.21`; flow-frame worst `u_srl_152` -> `u_srl_153` -114.8; HPWL 8.53e9 against 9.17e9 on k3; GRT at extra iteration 2, no congestion report yet. k3 `congestion-10.rpt`: overflow 44,582, west band 41,052 in 17,050 gcells (25,686 of it at y 1000 to 1200).
- V (scan): wave kits hgi_v1 -267.9 / -309.0, hgi_v2 -311.0, pc -729 to -1,486 post-CTS.
- R (KV-KT-E0 14:41): the score tag depth is a literal 13 in the four ECTLK quarter cores; depth 2 needs HXK 15, so `qkd_ectlk_q0..q3` re-harden as well as e0.

**Fix.**
1. FABLE-FIX-KV-HG: W2 moved the lane-pad station and stretched one srl hop. Add a relay site for `u_srl_153`, re-read k4 at CTS, then read its `congestion-5.rpt` against 44,172. W2 / W3 go into an event only with both numbers.
2. FABLE-FIX-KV-HG: stop k3 in GRT. It is on the base trajectory and has given its setup evidence.
3. KV-KT-E0: start the four HXK-15 quarter hardens in parallel with the lock-step proof (precedent `kv_qkh_safe32`). Five cores are now the KV long pole.

### Lever 7. HEAD hd_mesh

**Evidence.** V (epyc9 `mesh_pa/hd_mesh/run_route.log`, 15:10): 8,534 violations after iteration 1, second iteration started. R: mesh_w1 died in iteration 2 on `DRT-0255` at `clk_t41_tb0_tree`; buffer `clk_t41_tb0_d3` abuts the M1-M7 reserved OBS beside the clock entry. mesh_pa has its d3 at (279.882, 522.990) on the same OBS edge. V (scan): the two wave hd_mesh kits are at GRT TT -74.45 with the hold guard on the cap; `sle_hc2` died on the same `DRT-0255` code.

**Root cause (I).** `tap_balance.tcl` places balance buffers without a keep-out from the clock-entry obstruction, so a pin can sit on the route-box corner with no access.

**Fix (FABLE-FIX-HEAD-MESH).**
1. Flow: a one-site placement keep-out around the clock-entry OBS for tap-balance buffers. The 0.9 um nudge is the same fix by hand.
2. mesh_pa lands at about -58 to -78 routed (P, GRT -32.92 less 25 to 45). Use the routed setup ECO on the `u_lb` credits path (4 ends, 49 ps intra-tap skew on clk_t27) and the sign-off-priced hold insert; swap `signoff.py` and `eco_loop` first, the kit copies predate both fixes.

### Lever 8. QC st_a and the N4.1 pack

R (FABLE-FIX-QC-STA 14:49): k5 `sle_st_a_v1` post-CTS TT +10.78 with 0 negative ends (N3-era -580.7 on 2,898). k6 `slw_st_a_v2` -133.7 on 2 ends: one INVx8 drives 668 um into a core pin, expected +95 after the GRT max-wire pass. V: k5 / k6 lines confirmed in their `run_route.log`.

**Risk (I).** On S81 the same pass ended `no-progress stop` with 4 % of its estimated buffers (lever 4). If k6 logs the same line, the 2 ends stay at -133.

**Fix.** FABLE-FIX-QC-STA: buffer nets over 100 um into hard-core pins at placement, not only at GRT. QC-PLAN-R3: fold the 72 N4.1 rows with the N4.1p rebind (cbx_q10 sidx pins, stm_v3 stations).

Serdes: no new measurement. H19 post-CTS -108 is the boot-release end that H21 fixes (R); H19 gives routed rck pair skew and hold cell count only.

## 2. Evidence I opened this round

| item | file | result |
|---|---|---|
| fleet scan | 6 hosts, `ot-jobs/*-route-*/work/run_route.log` | 280 jobs; S81 TT buckets 19 / 11 / 116; 48 kits end hold on `RSZ-0060` (S81 26, QC 15, HEAD 5, KV 2) |
| D8e r6 | epyc8 `s81-die-r3-e8/d8e/{TOOLS_SHA,pub,r6/g0.log,r6/pre.out}` | tools b3e667d1865, pack building, G0 2 errors, PRE PASS |
| col_h9_r2 | epyc10 `...clce45cab5__pva119e808.../work/{run_route.log,tt_setup_repair*.log,config.mk}` | -23.71 CTS, -148.05 -> -108.74 GRT; port hold 1,170 ends; max-wire +1,978 of 47,471 |
| col_h9_r0_p6 | epyc10 `...pv0012ba28.../work` | -437.44 -> -330.33 CTS; GRT before -143.87 |
| col_h10_r1 wide | epyc8 `...cl95b37463__pv6a7ae122.../work` | -413.72 -> -384.96, lpl chunk strobe |
| hc0 re-sign | epyc9 `fable-fix-route-loss/hc0/kit/signoff_rl1` | TT -18.81; FF internal -12.99 / 34 ends |
| KV k3 / k4 | epyc9 `fable-fix-kv-hg3/{k3,k4}/gen/kv3_hgi_v1__cl141fc26e` | k3 west 41,052 at iteration 10; k4 CTS -138.19 |
| mesh_pa | epyc9 `fable-fix-head-mesh/mesh_pa/hd_mesh/run_route.log` | DRT iteration 2, 8,534 violations |
| st_a | intel2 `fable-fix-qc-sta/kit/{k3,k5,k6}` | -153.75, +10.78, -133.68 post-CTS |

Not opened: intel1 slice_station t22 (path read returned nothing), serdes H19 / H21 kits, any sign-off-frame path report for the S81 wide classes.

## 3. The 1320 levers: status

| 1320 # | status | note |
|---|---|---|
| 1 D8e r6 | **IN PROGRESS** | Bind 0, LAT pass, tools refreshed with the five commits (R + V). Not applied at 15:25. |
| 2 GRT margin | **WITHDRAWN (fix 1)**; fixes 2 to 4 replaced by the post-route insert | ROUTE-LOSS measured the cause as clock leaf arrival. |
| 3 col_h9_r1 | **DONE** | Launches stopped on d8t, AC test stopped (R). Rows wait for lever 1. |
| 4 KV | **HALF** | D23h2 applied (R). West rows cost setup on k4 (V). kt needs five cores (R). |
| 5 col_h10_r1 | **HALF** | d1 row written at the midpoint (R); thin; second class open (V). |
| 6 QC rows | **IN PROGRESS** | N4.1p bind running (R); st_a +10.78 at CTS (V). |
| 7 Serdes | **NO CHANGE** | H21 has no routed number. |

## 4. Stop list

1. QC: the hold chase to +30 at GRT (2.2 to 2.8 ps per chunk, still fails routed). Stop at met; pad after route.
2. S81: hold chunks on input ports in col kits.
3. S81: counting on +13 ps for col_h9_r2, or a second ECO pass on its pilot (each ECO costs about 13 ps of TT).
4. S81: new leaf, col_h9_r0_p*, col_h10_r1 or slice_station launches on d8t without a changed row; 116 of 146 are below -100.
5. KV: more GRT iterations on k3; folding W2 / W3 before the srl hop is fixed.
6. HEAD: the two wave hd_mesh kits at GRT TT -74.45; any hd_mesh route without the keep-out or the nudge.
7. All dies: a hold ECO from a kit copy older than cd66ba221f (it prices TT room at the FF corner).
8. All dies: relying on the GRT max-wire pass to buffer core-pin nets until its `no-progress stop` is explained.


# FABLE-CLOSURE-STRATEGY 2026-11-18 13:20 PST (1320): delta on 09:30

Reviewer: FABLE-CLOSURE-STRATEGY-1320. Read-only: no jobs launched, nothing killed, deleted or patched. Technical PD only. HBM parked.
Gate (R-MINIMAL): DRC 0, routed TT >= -42 ps, internal reg-to-reg FF hold >= 0.
Marking: **V** = I opened the file or log this round (13:10 to 13:20 PST). **R** = reported by the named lane, not opened. **P** = my proposal or estimate. **I** = inferred from V data.

Signed (V, failure_breakdown 13:10): S81 43/394, HEAD 24/26, QC 26/130, KV 6/56.
Method (V): the eight lanes' posts since 09:30; one scan of the 239 live `ot-jobs/*-route-*/work` dirs on the six build hosts; then the sign-off STA logs, CTS reports and congestion reports named in section 2.

## 0. Headline

1. **The first routed QC N3 kit fails internal FF hold, and every QC kit in flight stops its hold repair at the same point (V).** sle_hc0__cl929603c0__cl38badc56: detailed route 0 violations, routed TT -29.85, but routed FF internal hold -21.57 on 152 ends (TT corner -16.58 on 13). The GRT hold repair had stopped at +6.56 against an asked margin of 40 (`margin chase stalled, stop`). The route cost 28 ps of hold and 43 ps of TT setup (GRT estimate +12.81).
2. **D8e r6 is the one event that carries four S81 fixes (about 290 types), and its tools need three commits that were made after the plan was composed (R + I).** XR HI rows (77 leaf / kv_leaf), col_h9_r1 frame stations (60), 5 um halos (216 col types), serdes star + boot path (11). A 5 um halo without `macro_halo_carve` stops every kit at 3_5 (DPL-0004), as it did on QC st_a today.
3. **col_h9_r1 is being rebuilt unchanged (V).** Five more kits ended `GRT-0116` between 10:10 and 11:05, and at least 9 new kits are in place / CTS with all 354 `frame_int` station sites still at y 1226.88. The allow-congestion test is not a cheap path: 3.7 h in, it has not reached detailed route.
4. **KV hgi_v1 closes setup, and its next blocker is already visible (V).** Kit k3 at GRT iteration 5: overflow 44,172 in 17,057 gcells, all in the west band x 0 to 200, y 400 to 1200, on the `u_hst2_t1.u_reg.ti_b` and `cland_ft2_i` buses. The base kits had the same band (0930). The 172 hold ends at -102 are all `port_in`, so they do not block.
5. **col_h10_r1 (12 types) is held by a single-bit path, not by a family problem (V).** wns -138.57 with tns -252: `u_lpad_frame_int_i1.q[819]` -> 9 wire buffers -> `u_d1_11_Y.q`, 792 ps of data. Setup repair gains 0.
6. **S81 routed FF hold is not a problem (V).** The negative FF numbers on today's S81 exports are port-start paths: col_h9_r2 pilot `STD_MIN_NONPORT n 0` (340 port ends at -61.39), slice_station t28 n 0. The col pilot is signed at TT -38.29. This closes 0930 stop-list item 8.

## 1. Levers ranked by types unblocked

| # | die | lever | unblocks | owner |
|---|---|---|---|---|
| 1 | S81 | D8e r6 apply with tools at or after de34662bfb5, bd76ec2856c, dc9b82ef5b5 | leaf 77, col_h9_r1 60, col halo 216, serdes 11 | S81-DIE-R3 |
| 2 | QC (HEAD next) | Hold and setup repair at GRT must cover the measured route loss (hold 28 ps, TT 31 to 43 ps) | about 90 QC rows in flight; hd_mesh | QC-TYPES-R3, FABLE-FIX-HEAD-MESH |
| 3 | S81 | col_h9_r1: stop unchanged rebuilds; frame rows come with lever 1 | col_h9_r1 60 | S81-COL-FLOW-1118, S81-DIE-R3 |
| 4 | KV | D23h2 apply (relay keys + reset tail); west-band rows for hg / hgi in D24; e0 re-harden for the kt stages | hg / hgi 17, then pv 16 | KV-D23-COMPOSE, FABLE-FIX-KV-HG, KV-KT-E0 |
| 5 | S81 | col_h10_r1 / r2: site the `u_d1_*_Y` single-bit flops at their landing-pad bit | col_h10_r1 12, r2 12 (r2 not read) | S81-GEOM-OPUS |
| 6 | QC | Structural rows: cbx_q10 strap pins, stm_v3 so_e pins, hc1 wep copies, st_a tail hops over 380 um | cbx_q10 4, stm 1 to 3, hc1 1, st_a 11 | QC-PLAN-R3, QC-TYPES-R3, FABLE-FIX-QC-STA |
| 7 | S81 | Serdes: H21 to sign-off as evidence; countable kits from D8e with the star row | serdes 11 | FABLE-FIX-S81-SERDES |

### Lever 1. D8e r6: one event, four fixes, three tool commits

**Evidence.**
- R (S81-DIE-R3 12:39): r5 was red on one class, 77 `LF_CS_DEPTH hi` errors. XR adds one per-lane HI stage in `ot_s81sl_vp`, so the bound depth is plan + 1 on the 77 types that had no XR. r6 plan df7446e48ba9 appends one HI reg per lane (11,214 rows). Prechecks with tree tools 8efd33fb: 0 errors.
- V: epyc8 `s81-die-r3-e8/d8e/r6`: `elab.log` 1.0 MB and still written at 13:14, `bind.log` empty. No result yet.
- R (S81-GEOM-OPUS 12:33): the plan carries the col_h9_r1 `frame_int_o0 / i0` stations 27 to 42 um inside the north edge, and `halo_um 5` on 1,368 sstn / cfifo cores in 216 col types. The halo needs main 8958d3e8a4e.
- R (FABLE-FIX-QC-STA 12:57): on QC st_a a 4.32 um halo put 1,344 endcaps and 152 tapcells inside the blockage ring, and both kits stopped at 3_5 with `DPL-0004 (1496)`. Fix on main de34662bfb5 (`macro_halo_carve.tcl`), proven on k4.
- R (FABLE-FIX-S81-SERDES 12:35, 12:43): star key on main bd76ec2856c; boot path export on main dc9b82ef5b5.

**Root cause of the risk (I).** The prechecks ran with tree tools 8efd33fb. Nothing in the posts says that the r6 tree carries 8958d3e8a4e or de34662bfb5. A 5 um halo is wider than the 2.05 um row cut, so 216 col types would repeat the st_a stop.

**Fix (S81-DIE-R3).**
1. Before the apply, check that the D8e tools hold all of: 8958d3e8a4e (HALO-1), de34662bfb5 (halo carve), bd76ec2856c (star), dc9b82ef5b5 (boot path), 922c27887ac (TT setup repair). If the tree is older, refresh the tools; do not drop the halo rows.
2. First kits to read after the apply, one each:
   - a leaf with XR: `OT_VPW_BANK placed N` (about 1,219 = XR at the bank) and post-CTS TT;
   - col_h9_r1: GRT residual in x 660 to 780, y 1200 to 1227;
   - col_h9_r0_p6 with halo: passes 3_5, then M5 shorts at the cf macro west end (was 21 of 25);
   - serdes__t13: `OT_RCK_STAR` lines and the boot recovery endpoint.
3. XR-MID (58 far types) stays the delta after this event.

### Lever 2. Repair at GRT must cover the route loss

**Evidence (V, epyc9 `ot-jobs/sle_hc0__cl929603c0__cl38badc56-route-*/work`).**
- `run_route.log`: `OT_HOLD_GUARD_GRT start: hold ws -24.53 viol 140, margin 40`; chunk 1 +4.69 (1,110 buffers, 3,269 s); chunk 2 +6.15 (306 buffers); chunk 3 +6.56 (202 buffers); `hold met (ws >= 0), margin chase stalled, stop`.
- Same log: `OT_TT_SETUP_REPAIR ... wns -84.95 -> 12.81` at GRT.
- `signoff/tt/sta.log`: `STD_WNS_MAX -29.85` (105 ends), `STD_MIN_NONPORT n 13 wns -16.58`.
- `signoff/ff/sta.log`: `STD_MIN_NONPORT n 152 wns -21.57 core_n 152`.
- Worst hold path: `u_u_xl0_0.wd[394]` (tap clk_t90, source latency -9.6, insertion 171 ps) -> INV -> buffer -> OA21 -> `u_u_xl0_0.g_t[1].g_e[24].m[10]` (tap clk_t104, source latency +20.6, insertion 250 ps), plus 25 ps uncertainty. The kit has `OT_TAP_PAIR_AFFINITY = 1`, and the pair is still cut.
- Sister kit cl4baa7c9c: GRT hold +6.63, sign-off STA still running (SDC-level FF min -45.53; the non-port line is not out).
- R: hc1 routed -59.5 from a GRT estimate of -28.6 (31 ps). Every finished QC kit ends its GRT hold repair at +5.0 to +8.2 (FABLE-PD-QC-1240).
- R (QC-TYPES-R3 12:49): main b5bdd3347e1 cuts the first hold chunk to 200 buffers. The 10 ps pad is not applied.

**Root cause.** The guard treats "ws >= 0 and gain under 1 ps per chunk" as done, and the chunk cap shrinks (1,110 -> 306 -> 202), so the gain per chunk falls below 1 ps although only 1,618 buffers were spent. The repair therefore ends 34 ps short of its own margin, and the route takes 28 ps. With a 200-buffer first chunk the stop comes earlier.

**Fix.**
1. QC-TYPES-R3, `hold_guard_grt.tcl`: apply the stall stop only once ws >= 30 ps (the measured loss), and keep the chunk cap at 1,000 or more until then. Do not apply the 10 ps pad. This is the check the 12:40 review asked for, and it came out negative.
2. QC-TYPES-R3, the two routed hc0 kits: post-route hold ECO on the 152 ends, with the TT corner loaded so setup is seen. Buffer the `wd` branch, not the `m` D pin: the same endpoint is the TT-critical `wep` enable path (I: that is why the hc1 ECO cost 82 ps of setup).
3. Structural, P: the `wd -> m` bank pairs need the HEAD rule (`OT_TAP_PAIR_MACRO` form: the register array follows the tap of its `wd` flops). On hd_mesh it cut internal hold ends 11,163 -> 5,251 and hold buffers about 35,000 -> 9,629 (R).
4. TT side: a kit whose GRT TT estimate is under 0 will land outside -42 after a 31 to 43 ps loss. FABLE-FIX-HEAD-MESH: mesh_pa is at GRT TT -32.92 (V), so expect about -65 to -75 routed (P). Keep mesh_w1 alive and prepare a routed TT repair on the mesh_pa DB now.

### Lever 3. col_h9_r1

**Evidence (V).**
- `GRT-0116` again on epyc9 pv2f96c04f, pv4593e8e5, pv5ffbfb8b and epyc10 pvd9381c1d, pvee46d7b8 (logs last written 10:10 to 11:05).
- epyc8 pv15cef3f7 (launched after 09:30, in CTS): `istations.tcl` has 354 sites at y 1226.88. TT -277.6 before repair.
- Allow-congestion test (epyc7 `lanes/s81-col-flow-1118-grtac`): GRT 6,300 s, `GRT-0115`; then `OT_MAXWIRE` at 100 um added 79,494 cells (257,455 -> 336,949) in 5,642 s; hold repair is flat at -64.39 with 183 ends at `u_bn6/e_r0[1]`. Not in detailed route at 13:15.
- S81-COL-FLOW-1118 has not posted since 09:30.

**Fix.** S81-COL-FLOW-1118: no further col_h9_r1 builds on the d8t plan; the frame rows arrive with lever 1. Read the test's DRT only if it gets there; do not copy the hook to other kits. One read is owed: whether `OT_MAXWIRE` adds 30 % cells on a normal col_h9_r2 kit too, or only after congested routing (hc0 at 120 um: +2,510 cells in 118 s).

### Lever 4. KV

**Evidence.**
- R: k3 (hgi_v1 with relay keys, reset tail, 28 x 2 parent kt stages) TT +0.43 after CTS; tap spread 96 ps.
- V, k3 `run_route.log`: `OT_PREGRT_FF_HOLD class after port_in 172 ws -101.93 same_tap 0 cross_tap 0`; `cross-tap guard not applied (no tap window lines in the kit SDC)`.
- V, k3 `congestion-5.rpt`: 17,057 of the 20,000 listed gcells lie in x 0 to 200, y 400 to 1200 (H 8,614, V 8,443), overflow 44,172; peak column x 80 to 140. Top nets: `u_hst2_t1.u_reg.ti_b[*]`, `cland_ft2_i[*]`. 2,759 pins sit on the west face. GRT was at extra iteration 9 of 30.
- R (KV-D23-COMPOSE 13:00): D23f applied without the keys; D23h2 (keys + reset rsync / rtail) sealed and green; fix #2 needs e0 RTL + re-harden + calendar +2 (NEEDS-LANE KV-KT-E0).

**Root cause (I).** The hst2_t1 bus and the ft2 landing bus share a 200 um band behind the west face, and the relay stations are FIRM on source-to-sink lines inside it. Both directions overflow equally, so it is local density, not one bundle.

**Fix.**
1. KV-D23-COMPOSE: apply D23h2 now. It closes setup on 17 types apart from the kt class.
2. FABLE-FIX-KV-HG: post the k3 GRT end (residual and box). If it ends with `GRT-0116` or a residual over about 500, write D24 rows that move the hst2_t1 relay line out of x 80 to 140 and stagger it against the ft2 landing rows (P, 0 cycles).
3. KV-KT-E0: start the e0 source change today; it is the long pole (re-harden at the frozen 216 x 216 outline).

### Lever 5. col_h10_r1 / r2

**Evidence (V, epyc9 pv86f5e3b9 `4_cts_final.rpt`).** wns -138.57, tns -251.99, so 2 to 4 ends. Path: `u_lpad_frame_int_i1.q[819]` (tap clk_t12, CLK 339 ps) -> INV -> 9 buffers -> `u_d1_11_Y.q` D at 1,220.5 (tap clk_t22, CLK 307 ps). `OT_TT_SETUP_REPAIR cells 8 added; wns -145.99 -> -145.99`. The first report path (reset recovery, `u_d11_11_Y_r119`) is met at +240.8. Tap spread 79 ps.

**Root cause (I).** `u_d1_11_Y` is a single-bit delay flop with no site row. Global placement puts it at its loads, about 1 mm from the landing-pad bit (P from 355 ps of wire delay).

**Fix (S81-GEOM-OPUS).** A relay-site row that puts each `u_d1_*_Y` flop within 100 um of its landing-pad bit, or one station on that bit. Read the same report on one col_h10_r2 kit (-128.1 at 0930) before writing its row.

### Lever 6. QC structural rows

- cbx_q10 x4 (R): QC-PLAN-R3 cancelled the four kits at 13:09 after a strict-bind failure. The strap-pin move (sidx pins to their stations, 1,450 um -> local) must be in the next plan change, or the relaunch repeats -1 ns.
- sle_stm_v3 (R): so_e pin band to the stream core. Unowned in the posts since 12:40.
- sle_hc1 (R): 8 `wep` copies are in RTL and wait for the next source pin. This is also the endpoint class of lever 2.
- st_a (V, intel2 `fable-fix-qc-sta/kit/{k3,k4}`): `OT_TAIL_SITE copies 156 of 156 sited ... max_hop 524.4 um ... over_380 66` (k4: 148 of 148, 507.1 um, 66 over). 66 hops over the 380 um rule will show at CTS. If they are negative, add one K stage on those groups (FABLE-FIX-QC-STA). N4 st_a kits generated between 10:03 and the tools refresh with de34662bfb5 stop at 3_5.

### Lever 7. Serdes

R: matched-leg star trunk gives rck p1..p99 40 ps before balance (single tree 172) and span 65.2 with 689 pads. The boot-release stop was a private chain placed 544 um off its line; path-local seating moves it from -134.8 to +398.2. V: H20 post-CTS TT -147.83 (the boot endpoint, expected); H21 (both fixes) has no CTS line yet. Not shown yet: routed pair skew and hold cell count. No action beyond lever 1.

## 2. Evidence I opened this round

| item | file | result |
|---|---|---|
| hc0 routed | epyc9 `ot-jobs/sle_hc0__cl929603c0__cl38badc56-route-*/work/{run_route.log,signoff/tt/sta.log,signoff/ff/sta.log}` | DRT 0; TT -29.85; FF internal -21.57 / 152 ends; GRT hold +6.56, GRT TT +12.81 |
| S81 routed hold | epyc9 `fable-fix-s81-col/p774/s2/so_out/ff/sta.log`; epyc2 `autopilot/closed/s81/slice_station__t28__3c913dbdfb/kit/signoff` | non-port n 0 on both; port-start 340 / 191 ends |
| col_h9_r1 rebuild | epyc8 `ot-jobs/col_h9_r1__t1__cl49d7a23e__pv15cef3f7-route-*/work/istations.tcl` | 354 sites at y 1226.88 |
| col_h9_r1 AC test | epyc7 `lanes/s81-col-flow-1118-grtac/.../run_route.log` | GRT-0115, +79,494 cells, hold flat at -64.39 |
| col_h10_r1 | epyc9 `ot-jobs/col_h10_r1__t1__cl95b37463__pv86f5e3b9-route-*/work/run/reports/.../4_cts_final.rpt` | -138.57, one-bit path to `u_d1_11_Y` |
| KV k3 | epyc9 `fable-fix-kv-hg3/k3/gen/kv3_hgi_v1__cl141fc26e/{run_route.log,run/reports/.../congestion-5.rpt}` | hold ends all port_in; west band overflow 44,172 |
| D8e r6 | epyc8 `s81-die-r3-e8/d8e/r6` | elaboration running, bind.log empty at 13:14 |
| mesh_pa | epyc9 `fable-fix-head-mesh/mesh_pa/hd_mesh/run_route.log` | GRT gate TT -32.92, FF hold_est -3.21 (all paths), no DRT line yet |
| st_a k3 / k4 | intel2 `fable-fix-qc-sta/kit/{k3,k4}/gen/*/run_route.log` | tail copies all sited, 66 hops over 380 um |

## 3. The 0930 levers: status

| 0930 # | status | note |
|---|---|---|
| 1 col_h9_r1 | **NOT DONE** | Rows written and in the r6 plan (R). Unchanged kits still launch and fail (V). AC test not at DRT (V). |
| 2 tt_setup_repair | **DONE on main**, patch pass open on epyc7 | 922c27887ac; epyc8 patched (R). |
| 3 D8e + XR | **NOT DONE** | r5 red on 77 `LF_CS_DEPTH`; r6 in elaboration (V). About 50 leaf kits are again in CTS on the d8t form (V). |
| 4 col r0 | **IN PROGRESS** | p6 shorts named: 21 of 25 on the cf macro OBS, fix = halo (R). Bank proof kit in GRT (R). |
| 5 col_h9_r2 | **DONE** | Pilot signed, TT -38.29, internal hold clean (V). The nominal-cap question is closed: wave kits carry NOMCAP r708 in `config.mk` (V). |
| 6 KV | **HALF** | Setup closed on the proof kit (R). Keys not applied yet; west-band congestion open (V). |
| 7 QC | **HALF** | N4 applied as n4_s1, 57 launches since 13:00 (R). First routed kit fails hold (V). |
| 8 HEAD | **IN PROGRESS** | mesh_pa GRT overflow 0, TT -32.92 (V); in detailed route. |

## 4. Stop list (the 09:30 and 12:40 lists stand, plus these)

1. QC: no 10 ps hold pad, and no stall stop below ws 30 at GRT. Do not judge a QC kit as closed on `hold_ws` +5 to +8.
2. QC: no post-route hold ECO that buffers the `m` D pin of the xl banks, and none with only the FF corner loaded.
3. S81: no D8e apply with halo rows on tools older than de34662bfb5. Do not answer a 3_5 `DPL-0004` on col kits one by one.
4. S81: no col_h9_r1 build on the d8t plan, and no roll-out of the allow-congestion hook to that family.
5. S81: no hold work on S81 kits because of a negative FF number in an export line; read `STD_MIN_NONPORT` first.
6. S81 col_h10_r1: no setup repair passes, tap changes or family rows. It is one bit.
7. KV: no hold padding for the 172 k3 ends (port_in). No more GRT iterations on hg / hgi as the answer to the west band.
8. HEAD: do not stop mesh_w1 on the mesh_pa GRT number. Wait for the routed TT.
9. Serdes: no relaunch of H19 or H20 for the boot endpoint; H21 carries the fix.

## 5. Not checked

- The other 151 hc0 hold ends by class: only the worst path was read. The routed TT -29.85 path was not read.
- The sign-off of the sister hc0 kit, hd_ctl (6_final), mesh_pa in DRT, H21 past place.
- Whether the D8e r6 tree tools already carry the three commits (lever 1 is a check to make, not a found defect).
- k3 GRT at its last iteration; the 3,000 gcells outside the west band; hg (non-i) and pc kits.
- col_h10_r2, slice_station (several kits near TT 0 at GRT), dsdv_slice place stops, hd_lep0N (in CTS).
- The distance in lever 5 is from wire delay, not from coordinates.
- The `OT_MAXWIRE` cell count on a normal col kit.
- The live scan read stage and error lines only; its TT pattern did not match most kits, so no fleet-wide TT table this round.

---

# FABLE-CLOSURE-STRATEGY 2026-11-18 09:30 PST (0930): delta on 07:10

Reviewer: FABLE-CLOSURE-STRATEGY-0930. Read-only: no jobs launched, nothing killed, deleted or patched. Technical PD only. HBM parked.
Gate (R-MINIMAL): DRC 0, routed TT >= -42 ps, internal reg-to-reg FF hold >= 0. r708: nominal clock pin cap at sign-off.
Marking: **V** = I opened the file or log this round (09:10 to 09:25 PST hub time). **R** = reported by the named lane, not opened. **P** = my proposal or estimate.

Signed (V, failure_breakdown 09:10): S81 42/394, HEAD 24/26, QC 26/130, KV 6/56. Count 393 (R).
Method (V): one scan of every live `ot-jobs/*-route-*/work` dir on intel1, epyc2, epyc7, epyc8, epyc9, epyc10 (176 live route jobs): last stage log, tap spread, post-CTS TT, hold gate, pre-GRT hold pass, GRT congestion report, DRT violations.

## 0. Headline

1. **col_h9_r1 (60 types) cannot pass global route as built: every kit ends on the same hot spot (V).** 9 kits on epyc7 have a final congestion report with a residual of 179 to 288 after 30 extra iterations, and the 7 whose job log I opened end `GRT-0116`; 26 more in GRT show 344 to 775 at iterations 10 to 20. Every one has its overflow in one box, x 660 to 780, y 1200 to 1227 (the die top is 1226.88). Timing on these kits is clean: TT +0.2 to +0.6 (worst -6.0), pre-GRT hold 0 ends, 142k cells. This family is the nearest block of sign-offs on S81 and it is blocked by one station row.
2. **`tt_setup_repair.tcl` has a Tcl error in every runtime tree since 04:19, so new kits lose TT setup repair at CTS and at GRT (V).** Line 134 carries a trailing `# comment` after the closing brace of an `if`. When `OT_TT_SETUP_GUIDE` is unset the `if` raises `wrong # args: extra words after "else" clause`, the step returns rc 1 and the flow keeps the unrepaired DB. 121 live kit copies carry the line (S81 79, QC 26, HEAD 13, KV 3); 27 kits have already logged the fallback.
3. **30 leaf kits are in route on the d8t form with no XR stage and TT -79 to -919 (V).** They cannot sign. Each spends 10k to 71k hold cells and up to 2.7 h in the pre-GRT hold pass.
4. **KV has timing numbers now, and they are all structural (V).** 21 KV kits are in GRT at TT -268 to -1,486. Only io_cor (+156) and hroot (-3) can sign from this wave.
5. **QC: the vclk fix works.** sle_hc0 x2 are the first N3 kits through GRT, now in detailed route (V).

## 1. Levers ranked by types unblocked

| # | die | lever | unblocks | owner |
|---|---|---|---|---|
| 1 | S81 | col_h9_r1: `frame_int_o0` station line off the north die edge; meanwhile re-route with allow-congestion | col_h9_r1 60 | S81-COL-FLOW-1118 (re-route), S81-GEOM-OPUS (row), S81-DIE-R3 (delta) |
| 2 | all | Fix `tt_setup_repair.tcl` line 134 and patch the live kit copies | 121 live kits; every kit generated from now (N4, D8e, D23) | WAVE-FLOW-R2 (main + test), S81-COL-FLOW-1118 (kit copies, as for the reset fix) |
| 3 | S81 | D8e apply, then XR mid-wire proof on t3 / t16, then the 58-type key | leaf 74 + kv_leaf 5 | S81-DIE-R3, S81-GEOM-OPUS |
| 4 | S81 | col r0: bank-leaf + relay_sites rows; DRC names on col_h9_r0_p6 | col_h9_r0 60 + col_h10_r0 12 | S81-GEOM-OPUS, S81-COL-FLOW-1118 |
| 5 | S81 | col_h9_r2 to sign-off (pilot ECO + first in-flow route); class table for col_h10_r1 / r2 | col_h9_r2 60; col_h10_r1 / r2 24 | S81-COL-FLOW-1118 |
| 6 | KV | Relay chain keys on hg / hgi after the p2 CTS number; D23g apply; D24 rows for kp and reset | hg / hgi 17, pc 6, pv 16 | FABLE-FIX-KV-HG, KV-HG-OPUS, KV-D23-COMPOSE |
| 7 | QC | N4 apply (st_a stations); class tables for stm_v3 and st_b_v2; first routed sc / hc0 read | st_a 11; sc / hc / fw / fe about 30; 21 provisional | QC-PLAN-R3, QC-N-OPUS, QC-TYPES-R3 |
| 8 | HEAD | hd_mesh: TT setup repair on mesh_pa; SDC sha on mesh_w1; patched script on lep_p3 | hd_mesh, hd_lep0N | FABLE-FIX-HEAD-MESH, HEAD-TYPES-OPUS |

### Lever 1. col_h9_r1: one bus, three stations on the die edge

**Evidence (V).**
- epyc7 `.../3fa87b84b18/items/col_h9_r1__t1__cl49d7a23e__pv87d52780/attempt_2/gen/<type>`: `5_1_grt.log` total congestion 11,632 (M6 5,822, M8 5,227, both horizontal) at 12.9 % usage, 30 of 30 extra iterations, `GRT-0116`. `congestion.rpt`: 239 gcells, overflow 288, all in x 660 to 780, y 1200 to 1240.
- Nets in those gcells: `frame_int_o0_is0_q` 1,165 hits, `frame_int_o0_is1_q` 1,041, `u_ist_frame_int_o0_1` 987, `_2` 822, `_0` 533, `u_u_lpl_11_w.q` 420, clk_t22 leaves about 60.
- `istations.tcl` sites the three stations of `frame_int_o0` (1,168 bits) on one line at y 1227, which is the die edge: station 0 x 979 to 1159, station 1 x 667 to 847, station 2 x 355 to 535. The pins are on the north face at x 6 to 260 (M5 / M7). `OT_ISTATIONS placed 11029 flops FIRM`.
- Same box on all kits I binned: cl49d7a23e 179 / 288 final (9 kits, epyc7), 379 to 775 in flight (20 kits, epyc9 / epyc10); clf32cde8d 344 to 397 (6 kits, epyc10).
- Cost of one attempt: place about 20 min, pre-GRT hold pass 0.9 to 1.1 h (6,239 to 7,395 cells), GRT about 1.3 h.

**Root cause (I).** The bus runs 900 um west along the top row band with all three station blocks pinned to the edge. Each block is 1,168 flops in 180 um, so it stacks about 7 rows deep. At station 1 the incoming bundle from station 0 and the outgoing bundle to station 2 overlap above the block, with only the half-plane south of the edge to use. Horizontal demand is twice the bus where the supply is one edge strip. Not checked: whether a macro or halo south of x 660 to 780 narrows the strip further at station 1.

**Fix.**
1. Now (S81-COL-FLOW-1118): re-run route from the existing `4_cts.odb` of the col_h9_r1 kits with the allow-congestion hook. The hook exists (`OT_GRT_ALLOW_CONGESTION=1` read by `gen_phys.py` line 6385 at gen time; it writes `grt_allow_cong.tcl`, which QC kits already carry). P: for the kits on disk, copy that file and its hook block into the kit instead of a regen. Take one kit first and read DRT at iteration 3: 179 gcells of overflow 1 at 0.57 um is within what detailed route usually absorbs, but the block sits on PG pair rows (P).
2. Structural, 0 cycles (S81-GEOM-OPUS, row via S81-DIE-R3 in the delta after D8e): site the `frame_int_o0` stations at y = 1227 - 45 um or deeper, and step stations 0 / 1 / 2 by 10 um in y so in and out bundles do not share tracks. Widen each block from 180 to about 254 um so the bit pitch equals the pin pitch. Class rule for `kit_istations.py`: a station line parallel to a face sits at least one bus width (bits x track pitch / 4 H layers, about 30 um here) inside it.
3. Check the same rule on `frame_int_o1` (stations at y 0 for stages 2 and 3, x 528 to 1038): 28 site groups, so a narrower bus; col_h9_r2 shows residual 15 to 16 at (700, 0) (V).

### Lever 2. TT setup repair is lost in every new kit

**Evidence (V).**
- `rt/current/tools/die_plan/tt_setup_repair.tcl` (rt c860f199a9c6), line 134: `if {$ot_tt_rc eq "grt" && [info exists ::env(OT_TT_SETUP_GUIDE)] && ...} { write_guides ... }     # after any re-route, ...`. All 28 rt trees from 528751c159c8 (04:19) on carry it; 5144e086700c (11-17 23:45) and older do not.
- epyc8 `slice_station__t18` `tt_setup_repair.log`: `Error: tt_setup_repair.tcl, 135 wrong # args: extra words after "else" clause in "if" command`; run_route.log: `OT_TT_SETUP_REPAIR FALLBACK step rc 1: 4_cts.odb unchanged`.
- GRT stage too: hd_spn_wshim_tx `FALLBACK grt step rc 1 ... 5_1_grt.odb is the UNREPAIRED DB`.
- Kits that logged the fallback: slice_station 14, leaf 3, HEAD 10 (hd_ctl, hd_host_n, hd_host_w, hd_mesh x2, hd_spn, hd_st_str x2, hd_turn_a, hd_spn_wshim_tx). The wave hd_mesh kit sits at TT -92.64 unrepaired.
- What the step is worth where the old script ran: col_h9_r1 -9.00 -> +0.64; mesh_w2 -54.94 -> -1.45; leaf t61 -191 -> -80; leaf t2 -379 -> -274.
- Spread: 121 live work dirs hold the bad copy (epyc2 73, epyc9 16, epyc10 12, epyc8 11, intel1 5, epyc7 4). The 08:09 job-start flow refresh replaces old kit copies by rt/current, so it carries the error into older kits at their next stage job.

**Root cause.** A comment after a closing brace on the same line is an argument in Tcl. The `if` only raises when its condition is false, which is every run without a guide file, so both rc bases fail.

**Fix.**
1. WAVE-FLOW-R2: move the comment to its own line on main. Add a test that sources the script body with `OT_TT_SETUP_GUIDE` unset for both `placement` and `grt` (a Tcl parse of the `if` word count is enough).
2. S81-COL-FLOW-1118 pattern: copy + mv of the fixed file into every live work dir and every per-item gen dir (`items/<item>/gen/<item>/`), all 7 hosts. Not `sed -i`.
3. Kits that already passed CTS with the fallback keep an unrepaired DB. For types within 60 ps of the gate, re-run the step on `4_cts.odb` before judging them (slice_station t48 -163 and hd_mesh are outside that; read after repair).

### Lever 3. Leaf: D8e, then XR mid-wire

**Evidence (V).**
- 21 leaf kits in GRT: TT -79.5 (t61), -97 (t62), -192 (t57), -250 (t28, t40), -274 (t2), -298 to -395 (t59, t70, t22, t5, t47, t46), -457 to -529 (t21, t42, t54), -639 to -919 (t60, t67, t23, t52, t72, t54__cl501e5681).
- t52: `OT_VPW_BANK placed 317 FFs` = no XR in the netlist (0855 rule: 317 no XR, about 1,219 XR at the bank).
- Hold on the same kits: gate WNS -150 to -253 on 4k to 20k ends; pre-GRT pass adds 9.7k to 71k cells (t22 71,211, t28 68,813, t72 64,149 on 386,687) in 0.1 to 2.7 h; t22 / t28 / t61 / t70 still end with open ends.
- Tap spread 129 to 389 ps (t52: 287 to 601, core clock `clk_c1` 601 against target 450).
- R: D8e r4 crashed on the t40 taps; r5 on plan a30d6c6f (t40 back on rd2) was moving to epyc2. I found no r5 bind log on epyc2 or epyc8 at 09:20 (V). XR-MID-1 is on main (c4f44b2c1d2), rows for 58 types, unbuilt.

**Root cause.** As 0855 fix 2: the VS-to-bank wire is in one cycle. Second class (I): the hold cell count follows the tap spread, and the spread follows core clock pins whose pin + internal insertion is above the tap target.

**Fix.**
1. S81-DIE-R3: r5 bind, apply D8e. Run `reset_anchor.resolve_plan` and `taps.grid_explicit_sites` first (13 s, already done on a30d6c6f, R).
2. S81-GEOM-OPUS: t3 and t16 proof kits on the D8e tree with `budgets.vpw_xr_mid_types` + `OT_S81_VPW_BANK=1`. Read `OT_VPW_BANK placed N`, post-CTS TT and the tap spread. Then the 58-type row file as one delta.
3. P, after the first XR kit: if the spread stays above 150 ps, set the tap target per type to the slowest core clock pin (pin + internal) instead of 450, so the taps are delayed up to it; the hold cells then fall with the spread.

### Lever 4. col r0 (72 types)

**Evidence.**
- V: 38 of 72 rows are place FAIL in the stage table: 47 S81 rows on `RESET v5 refuses empty explicit buffer set`, 8 on `OT_HOOK_COVERAGE relay_mid`. R (S81-COL-FLOW-1118 08:22 to 09:05): both fixed on main (235d4be8301, 096be78133f) and in the kit copies, including the per-item gen dirs; retry keys in.
- V: the only r0 kits past CTS: p1 TT -46.8 (10,530 hold cells, 7,290 s), p5 -11.9, p6 -1.2 at CTS but **-88.89 after GRT** (the GRT setup repair made it -133.97 and was restored). p6 is in detailed route at iteration 25+, flat at 32 to 39 violations since iteration 17 (29 M5 shorts, 2 M4 spacing).
- R (S81-GEOM-OPUS): r0 has macro-to-macro paths up to 1,740 um with 0 stages; RELAYSITE-1 row proven at placement (127 / 128 FIRM).

**Fix.** S81-GEOM-OPUS: bank-leaf rows + relay_sites on both cl0045af7b and cl9f71e63d into the delta after D8e; route the bank proof kit to sign-off. S81-COL-FLOW-1118: on p6 name the 29 M5 shorts (nets and whether they sit on PG M5 stripes) before any ECO; the TT -88.89 means this kit is a DRC probe only.

### Lever 5. col_h9_r2 and col_h10

**Evidence (V).**
- col_h9_r2 pvea45273b: TT +0.1, pre-GRT hold 0 ends (3,738 cells), GRT residual 1, `hold_ws 25.19 margin 25 OK`. Cleanest S81 kit in flight.
- Pilot pv11b6518d ECO started 09:07 on epyc7 (`s81-col-flow-1118-pilot/eco_1118`); R: DRC 2, TT -46.9, FF hold -62 on 345 ends under r708.
- col_h10_r1 (7 kits): TT -87.6 to -146.0 at CTS, setup repair gains 0; GRT iteration 5 overflow 56k around x 800 to 1100, y 200 to 300. col_h10_r2: TT -128.1.
- `failure_breakdown` TOOLS-LAG still lists the s81 tree as missing fixes; in-flow hold repair runs on range clock pin caps (I).

**Root cause (I).** The 345 hold ends at -62 on a kit that had 5 ends at -5 in flow are the range-cap / nominal-cap difference, not a design change.

**Fix.** S81-COL-FLOW-1118: let pvea45273b route and re-sign under r708; if hold fails the same way, the class fix is nominal clock pin caps in the in-flow hold passes (r708 into the kit libs), not an ECO per type. col_h10_r1 / r2: one class table of the TT ends at `4_cts.odb` (start, end, wire um) before any row.

### Lever 6. KV

**Evidence (V).** TT after the pre-GRT pass: hg -502 (kv3_hg), -805 to -864 (hg_v1, v1p2 to v1p5); hgi -268 to -340 (v1 x2, v2, v3), -705 (v4), -792 (v7); pc -468, -815, -1,069, -1,360, -1,486 (pc_v3); hroot -3.2; io_cor +156.2. GRT overflow in flight: hg 42k to 52k, hgi_v1 40k to 44k around x 0 to 200, y 1000 to 1100, pc_v1 17k to 20k. Hold pass: pc_v3 18,678 cells in 15,353 s. Proof kit p2 (relay chain keys): last log `2_1_floorplan` at 09:20, no CTS number yet. R: D23 / D23b failed on one hub_Wo EMIT; D23e / f / g gates due about 10:40.

**Root cause (R, FABLE-FIX-KV-HG).** Unregistered 1.0 to 3.2 mm wires in every failing class; the hst / ftg relay flops were not placed (0 of 9,450).

**Fix.** FABLE-FIX-KV-HG: p2 CTS ends table. KV-HG-OPUS: if hst and lpad classes clear, item_env keys on the 17 hg / hgi types and relaunch. KV-D23-COMPOSE: apply g > f > e. D24 rows for what p2 leaves (kp core to core -239, reset to core -309) and for pc. Route io_cor and hroot to sign-off now; hroot needs TT setup repair to work (lever 2: 3 KV kits carry the bad script).

### Lever 7. QC

**Evidence (V).**
- sle_hc0 x2 passed GRT (`hold_ws 6.56 / 6.63`, TT +18.4 / +11.9 before GRT, 408,738 / 394,442 cells), in detailed route.
- In GRT: sle_sc_v1 TT +9.2; slw_sc_v1 x3 -17.4 to +11.6; slw_fw_v1 x2 +2.2 / +54.1; slw_fe_v1 +55.4 (28,001 hold cells).
- Outside the gate before route: sle_st_a_v1 -654, slw_st_a_v2 -462, slw_st_a_v1 x2 -235 / -242, sle_stm_v3 -203, sle_st_b_v2 -67.7.
- The pre-GRT pass in these kits still pads port_in (517 to 2,742 ends left at -49 to -165); ee7566bd8b7 reaches only kits generated after 08:04.
- 26 QC kit copies carry the bad setup-repair script.

**Fix.** QC-PLAN-R3: N4 apply (st_a stations). QC-N-OPUS: k2 routed. QC-TYPES-R3: read routed TT and internal hold on sle_hc0 first; class tables for stm_v3 and st_b_v2 (no row exists for either). N4 kits must be generated after the lever 2 fix.

### Lever 8. HEAD

**Evidence (V).**
- mesh_w1: `5_1_grt.log` ended 09:12 with `HOLD-SDC-MISMATCH stage repair_timing: golden SDC /work/constraint.sdc sha 9de86b68 != kit OT_SIGNOFF_SDC_SHA ae5020a4`, after the 35,109-cell hold pass. A GRT-only relaunch started 09:16.
- mesh_pa: CTS done, taps 401 to 462, hold gate -131.42 on 9,462 ends. The kit has no `tt_setup_repair.tcl`, so TT -28.36 (R) is unrepaired; the same step took mesh_w2 from -54.94 to -1.45.
- lep_p3: in CTS; its kit copy has the bad script.

**Fix.** FABLE-FIX-HEAD-MESH: run the fixed setup-repair step on the mesh_pa `4_cts.odb` before the hold pass result is used (hold padding on an unrepaired DB fixes the wrong slack). HEAD-TYPES-OPUS: if the 09:16 GRT run stops on the same sha, set `OT_SIGNOFF_SDC_SHA` to the kit SDC that the hold pass used; patch lep_p3 by copy + mv before its CTS ends.

## 2. Stop list (the 07:10 and 08:55 lists stand, plus these)

1. No unchanged relaunch of col_h9_r1 from kit_rtl. It ends at the same box after about 2.7 h. No more GRT iterations either: 30 were flat.
2. No triage of a near-gate TT number from a kit whose log says `OT_TT_SETUP_REPAIR FALLBACK`. Repair first.
3. No reading, ECO or hold work on the 30 leaf route kits of the d8t form (`OT_VPW_BANK placed 317`).
4. No ECO on col_h9_r0_p6: TT -88.89 after GRT. Use it for the M5 short names only.
5. KV: no hold padding or ECO on a kit with TT under -250; no hg / hgi keys on wave rows before the p2 CTS number.
6. hd_mesh: no sign-off attempt on mesh_pa without setup repair; no second padding round (07:10 item stands).
7. QC: no port_in hold cells; no N4 kit gen before the setup-repair fix is in rt/current.
8. Do not raise the per-type hold margin to clear the col pilot's 345 ends before the nominal-cap question is answered.

## 3. The 0710 levers: status

| 0710 # | status | note |
|---|---|---|
| 1 D8e bind | **NOT DONE** | r3 error fixed by tools (R). r4 crashed 08:37 on 8 t40 added taps (R, 0855). r5 on a30d6c6f not finished; no bind log found at 09:20 (V). t40 taps re-sited, gate queued (R). XR-MID-1 on main, unbuilt. |
| 2 RESET v5 empty set | **DONE** | main 235d4be8301 + kit copies and per-item gen dirs patched by 09:05 (R). 47 rows still show the old FAIL until the retry tick (V). |
| 3 col_h9_r2 ECO, bank proof | **IN PROGRESS** | ECO dir created 09:07 (V). Bank proof kit: relay_sites proven at placement, route restarted after the reset fix (R). |
| 4 QC N4 / measured hold | **HALF** | vclk fix proven: sle_hc0 x2 through GRT (V). N4 publish / apply still running (R). n41d bind 0 errors, k2 kit running (R). |
| 5 hd_mesh | **MECHANISM FOUND** | R: -141.74 = declared tap window 76 + uncertainty 25 + guard 45 on zero-logic cross-tap pairs. mesh_pa cuts internal ends 11,163 -> 5,251 (R). mesh_w1 lost its GRT to an SDC sha check (V). |
| 6 KV first evidence | **DONE, premise corrected** | KV kits do reach CTS in the sealed ot-jobs dirs; 21 TT numbers above (V). D23 / D23b failed; e / f / g binding (R). hub_C node move not checked. |
| 7 serdes H18 | **SUPERSEDED** | 0855: H18 is recipe evidence. H19 (16 rck roots, north taps on the strip) is at floorplan (V). H18 in GRT: TT -159.87 after CTS, 415k non-tap cells (V). |
| 8 mergex | **DONE** | mm6 signed under r708: TT +161.22, FF +16.18 (R). mm15r stopped. |
| r708 in the die trees | **OPEN** | TOOLS-LAG 09:10 still lists r708 missing on qwen_kvsys and s81_head, and 93 fixes missing on s81 (V). |

## 4. Not checked

- Whether detailed route absorbs the col_h9_r1 residual with allow-congestion; what lies south of x 660 to 780 at the north edge.
- D8e r5 bind result; any XR kit.
- The path classes of col_h10_r1 / r2, QC stm_v3 / st_b_v2, slice_station t18 / t46 / t6 (-917 / -577 / -419, all with the setup-repair fallback).
- Routed numbers of any QC N3 kit, of mesh_pa, lep_p3, H19 and the col pilot ECO.
- KV p2 beyond floorplan; PV CLAND on v2 / v6; D23e / f / g.
- Why the pre-GRT hold pass takes 0.9 to 4.3 h (single thread, R) on col, leaf and kv3_pc.
- Die STA on the real clock (S81, HEAD): unchanged.

---

# FABLE-CLOSURE-STRATEGY 2026-11-18 07:10 PST (0710): delta on 05:10

Reviewer: CLOSURE-STRATEGY-0710 (Opus; Fable is at its weekly limit). Read-only: no jobs launched, nothing killed or deleted. Technical PD only. HBM parked.
Gate (R-MINIMAL): DRC 0, routed TT >= -42 ps, internal reg-to-reg FF hold >= 0, die bind + LATCHECK. r708: clock pin cap is nominal at sign-off.
Marking: **V** = I opened the file or log this round (07:10 to 07:40 PST). **R** = reported by the named lane, not opened. **P** = my proposal or estimate.

Signed (V, failure_breakdown 07:10): S81 42/394, HEAD 24/26, QC 25/130, KV 6/56. S81 kit rows: 316 running, **27 other flow error** (back up from 0 at 06:25), 5 cancelled, 3 kit input missing.

## 0. Headline

1. **D8e has not been bound. Its 05:41 rebind ended at about 06:13 with 80 errors, and nobody has posted about it (V).** epyc8 `s81-die-r3-e8/d8e/r3/bind.log` reports `errors 80`. One is an EMIT error: `relay_depth col_h10_r0_p1__t1__cl574cc59d__pv3d0d4d97: 3 row(s) matched no internal sink ['u_r0_u_y_cc_1_0.o','u_r0_u_y_cc_3_0.o','u_r0_u_y_x2_3_0.o']`. The other 79 are leaf / kv_leaf `LF_CS_DEPTH ... no bound module file`. `leaf_cs_depth.py` reads `s81p_<type>.sv`, and the failed emit never wrote those files, so the 79 are a cascade. G0 RC 1 with 2 errors (the D8d control errors). The bind ran on tools `74354c18`, which do not contain b8f543dd448: S81-GEOM-OPUS pushed that fix (relay_depth compared by sv_id, `u_r0.u_x == u_r0_u_x`) at 05:5x for exactly this error. Nothing has been written in r3 since 06:32, no bind is running on epyc8, and S81-DIE-R3 has not posted since 05:41. The 07:40 apply ETA will not hold. Everything on S81 that depends on the plan is waiting on this bind: XR, reset relays, leaf stride, the serdes rck pin, the face-clear rows and the 15 setup stops.
2. **27 S81 col kits fail at `3_4_place_resized` on one reset-tool assert (V).** `reset_chain_spread.tcl` line 87 in the d8t tree, `tools/die_plan` (header `PRIVATE CANDIDATE v5`; the file is not on main): `RESET v5 refuses empty explicit buffer set`. Split: col_h9_r2 clce45cab5 11, col_h9_r1 cl49d7a23e 10, col_h9_r2 clb8d86cd5 3, col_h9_r2 clc9ad8f7e 2, col_h10_r1 cl95b37463 1. Each one fails 15 min into resize.
3. **The routed col pilot is still on disk, and nobody has taken it (V).** On epyc10, both `/srv/opentallas-scratch{,2}/.../3fa87b84b18/items/col_h9_r2__t1__cl774acf45__pv11b6518d/attempt_2` hold `6_final.odb` (01:03 PST) and `signoff/signoff.json` (TT -46.87, DRC 2, hold 5 ends at -5.07, per 0510). Because of the DRC 2 the r708 sweep skipped it. The wave has relaunched the type from scratch (attempt 5, in gen on d8t).
4. **hd_mesh: tap balance worked (399 to 462, spread 63 ps, was 128), but hold demand barely moved (V).** mesh_w2 `pregrt_ff_hold.log`: RSZ sees 22,446 hold endpoints, WNS -141.74, TNS -447,851. OT_HOLD_GATE: 15,380 ends, 1,036 forwarded ring inputs on 2 clocks, contract in_min -90, structural limit -183. Repair has run since 06:05. The 0510 premise ("the 128 ps tap spread is the hold demand") was only partly right.
5. **Serdes H18 rck tree closes at placement (V).** epyc9 H18 `4_1_cts.log`: `OT_STB_SPAN io_pma_rck[0] sinks 26277 min 1948.4 max 2058.0 span 109.5 limit 110.0 PASS`, using 1,012 delay inverter pairs. It is now in GRT (`5_1_grt.tmp.log` 07:19).
6. **KV still has no CTS number (V).** I found no `4_1_cts.log` under `runs/qwen_kvsys` on epyc7 / epyc9 in the last 15 h. The last HG6 PV kits stopped at `3_5_place_dp` (02:4x to 03:1x) and were then superseded. The 10 retry rows launched at 07:06 on D22 are at kit_rtl (V, wave state).
7. **QC: the measured-hold fix is in code but not yet proven on a kit (R + V).** QC-FLOW-1118 e1ce3e0b234 (05:53): per-clock means, IO vclk bound to the pooled mean, `::nka_blk` made global. Wave state: sle_sc_v3 a3 at place, cbx_q10 a4 at place, sle_sc_v1 a2 enqueued. No stage pass yet.

## 1. Levers ranked by closure impact

| # | die | lever | unblocks | owner |
|---|---|---|---|---|
| 1 | S81 | Rebind D8e (plan d396b7d6) on tools >= b8f543dd448, then LATCHECK / G0 / apply | leaf 75 + kv_leaf 5, serdes 11 rows, face-clear rows, 15 setup stops | S81-DIE-R3 (no post since 05:41) |
| 2 | S81 | `reset_chain_spread.tcl` v5: an empty BUF set is a no-op, not an error | 27 col kits (5 type groups) | S81-COL-FLOW-1118, S81-TYPES-R3 |
| 3 | S81 | ECO the routed col_h9_r2 pv11b6518d (2 DRC + 5 hold ends + TT 4.87 ps), r708 re-sign; route the bank-leaf proof kit | col 215 (family proof) | S81-TYPES-R3 + CAPSKEW-ECO; S81-GEOM-OPUS |
| 4 | QC | N4 apply (N4D derived-R8 pass 2) -> N4.1 kit k2 to routed sign-off; read the 6 measured-hold relaunches at GRT | st_a 11; sc/su/fe/fw up to 29; cbx | QC-PLAN-R3, QC-N-OPUS, QC-TYPES-R3 |
| 5 | HEAD | hd_mesh: read mesh_w2 after repair (TT, cell count); if TT < -42, take a launch/capture class table of the hold ends before any padding | hd_mesh | HEAD-TYPES-OPUS |
| 6 | KV | First hg/hgi CTS read on D22; D23 -> D23b apply; CLAND facegrow read on pv_v2/v4/v6 at 3_3 | pv 16, pc 6; first evidence for hg/hgi 19 | KV-HG-OPUS, KV-D23-COMPOSE, KV-D22-ROWS |
| 7 | S81 | Serdes H18 to routed + r708; pad-clock trunk rows in the D8e rebind | serdes 11 | S81-CORES-OPUS, S81-DIE-R3 |
| 8 | S81 | mergex_mm3b: r583 internal hold ECO on the routed DB (FF -3.45, 62 ends) | svc 16 (last core) | S81-CORES-OPUS |

### Lever 1. S81 D8e bind

**Evidence (V).** As in headline 1. `r3/pre.out` reads PLAN-GATE-PRE PASS, findings 0 (06:32), with 50 inherited station/relay sites over hard cores. `bind.log` is 42 lines long: 1 EMIT error, 29 LF_CS_DEPTH lines shown (80 in the count), 10 RESET_ANCHOR info lines. `TOOLS_SHA` = 74354c18d2f9.

**Root cause.** bind.py on 74354c18 matches `relay_depth` rows by dotted instance name. Bound r0 col instances are flattened (`u_r0_u_y_cc_1_0`), so the 3 u_r0 rows match no sink. Emit stops, no bound module is written, and leaf_cs_depth then fails every XR leaf type. P: there is one real error, not 80.

**Fix.**
1. S81-DIE-R3: re-run the D8e bind on the same plan d396b7d6 with tools at or after b8f543dd448 (on main). The alternative is to drop the u_r0 `*.o` rows. Do not strip the XR rows.
2. After the bind, check that LF_CS_DEPTH reads 0 on all 80 leaf / kv_leaf types. If it does not, it is a second class (plan stage vs bound RTL stage depth), and leaf_cs_depth names the class per type.
3. In the same rebind: the pad-clock trunk rows for the moved `io_pma_rck` pin (lever 7), plus S81-GEOM-OPUS `rows_face_clear_d8e.json` (de8ad49d0f1b: t40 fc6, t29 fc5, 0 cycles). Both are row-only and were proven on D8e (R). If adding them would restart the bind proof, they go in as the first delta after apply instead.

### Lever 2. Col reset-chain spread v5 assert

**Evidence (V).** epyc2 kit `col_h10_r1__t1__cl95b37463__pve28d14fa/attempt_5`, `3_4_place_resized.log`: PLACE-HPWL 1.002, NOCONVERGE OK, then the assert. `config.mk` sets `OT_RESET_CHAIN_SPREAD = 1` (reset_replicate copy-depth chains). The script walks from each chain root through BUF/INV cells and collects only the BUF cells that GPL inserted. It errors when it finds none (line 87). Also in the same log: OT_PLACE_WIRE_RATIO 14 violations, worst 28.07, all on the `u_bound.u_d11_11_Y_r*_s0` reset copy stages (21 um direct, 589 um built). This is the chain that the spread step exists to fix.

**Root cause.** The v5 candidate assumes that GPL buffered every reset root. On these col types the copy-depth roots have low fanout, so GPL inserted no BUF, and the "nothing to prune" case becomes a hard error.

**Fix.** An empty `rc_bufs` logs `RESET v5 no GPL buffers: nothing to prune` and goes on to the spread. Keep the CLOCK-net error and the INV preservation. Put the fix in the tree tools / rt, and land the candidate on main with a test for the empty case (test_reset_chain_spread.py exists in the tree). Then relaunch the 27 rows. P: after the spread, the u_d11 wire-ratio paths are what the TT gate should be read on.

### Lever 3. Col family proof by ECO

**Evidence (V).** As in headline 3. The kit DB includes `5_1_grt.odb`, `6_final.{odb,def,spef,v}`, the LEF and the typ lib. R (S81-GEOM-OPUS 07:10): bank-leaf gate_bl1 / bl2 PASS (bind 0, LATCHECK 873/873, G0 0 new). The proof kit col_h9_r0_p2 cl0045af7b (r0 worst 1,740 um family + ROM move) is at kit gen on epyc8. The rt4 probe on the attempt_5 floorplan is reading the u_y_rt_4a_0 / 4b_0 sources so that FIRM relay_sites can be placed (0 cycles).

**Fix.**
1. S81-TYPES-R3 (+ CAPSKEW-ECO form): on the existing attempt_2 routed DB, name and fix the 2 DRCs (detail-route ECO). Then run the capture-skew / hold-pad ECO on the 5 hold ends and the worst TT ends (core to core `u_u_e*_u_w -> u_u_bn*`), and re-sign under r708. That is about 5 ps of TT and 5 ends of hold. No rebuild is needed.
2. S81-GEOM-OPUS: take the bank-leaf proof kit to routed sign-off; put the rt4 FIRM relay_sites rows on both cl0045af7b and cl9f71e63d.
3. P: a signed r2 plus a signed r0_p2 proves both col sub-families on d8t rows. The other 50+ placed col kits then need the same ECO, not new rows.

### Lever 4. QC N4 / N4.1 and the measured-hold relaunches

**Evidence (R).** N4: the N4C LANE_ASBUILT error (delivered 10 vs 7) was fixed by setting `lanes[].fixed_cycles 3` on sl_W0/W2/W4_fw__x_fw_st_a. The N4D pass-1 bind is clean apart from the expected 30 R8_STALE. Derived-R8 pass 2 has run since 06:48; publish + apply around 07:45 (QC-PLAN-R3 06:56). N4.1: n41b has 15 errors: R8_STRAP_PAD 12 on sle_ctl__cl503337ff (26 > 25) and __cl67434795 (16 > 15), TYPE_SPLIT 2 and EMIT 1. The x_fe_o +1 station moves R8 by one cycle at ctl. n41d (r8_strap_pad_max 26 / 16) is running (QC-N-OPUS 06:3x). V: the measured-hold relaunches are in place / gen; sle_ctl__cla4f6f12f FAILs kit_rtl with `captured reset identity` on N3.

**Fix.**
1. QC-PLAN-R3: apply N4 as composed.
2. QC-N-OPUS: rebase n41d onto the N4 tree. Raising the ctl strap pad limit is a real +1 R8 on two ctl types: check the receiver latency in LATCHECK rather than only raising the limit. Then take kit k2 to routed sign-off under r708.
3. QC-TYPES-R3: read `OT_VCLK_MEASURED_CLOCK` and the hold_ws line in `5_1_grt.log` of sle_sc_v3 / slw_fw_v3 / sle_sc_v1 / sle_su_l1 / slw_fe_v2 when they reach GRT. Three of them were at CTS wns 0.00 / -5.29 / -33.43, so they are the next sign-off candidates on QC.

### Lever 5. hd_mesh hold after tap balance

**Evidence (V).** As in headline 4. CTS took 20 min; the repair log stops at iteration 0. R (HEAD-TYPES-OPUS 06:30): TT at CTS -1.45 (7 cells), cross_tap 10,130 of 15,372 ends.

**Root cause (P).** With 63 ps of tap spread, -141.74 cannot come from tap skew alone. The remaining about 80 ps is either the forwarded ring input class (1,036 inputs on 2 clocks, contract in_min -90) or same-clock short paths in `u_core.u_la.u_ln.u.u_ep.xpn_f` (the worst endpoint). Padding 15 k ends is the cost profile of mesh_w1, which lost TT -49.56 -> -68.34 on 37,912 cells.

**Fix.** HEAD-TYPES-OPUS: let the repair finish and read routed TT and the inserted cell count. If TT >= -42 and hold >= 0, sign and export. If not, before any new form: take the hold ends from `4_cts.odb` (launch tap, capture tap/clock, path depth), bin them, and fix the largest bin at its source. For the ring class that means a capture-side offset on the forwarded ring clock. For xpn_f it means 1 to 2 min-delay cells at the D pin in RTL synth constraints. Do not pad. Keep mesh_w1 alive until mesh_w2 has a routed number.

### Lever 6. KV first timing evidence

**Evidence.** V: no KV CTS log (headline 6). R: D23 strict bind since 06:20 (plan add04d1e8a2d: tail split `kv3_pv.*`, 68 pc taps, efault, hub_Wo 11 cores). D23b = D23 + 59 PV raw-stage band rows, already binding. D23c = D23b + reach rows + lite+narrow rings on all 5 hubs (hub_C 357,873 -> 238,112 cells, proven formally and in lock-step). Its bind waits on the reach code landing on main. hub_Wi host split: gate clean, shell 299,999 cells. hub_C clock-node move BLOCKED: the e9 die clock tree source (`kv-clk-r2/runs/e9`) was deleted, so the reserved-rect collision on pvfin_hi stays at 1.

**Fix.**
1. KV-D22-ROWS: as soon as one of the 10 retry rows (hg_v3, hgi, hgi_v5, hgi_v6) reaches CTS, read the OT_TAP_BALANCE and wns lines. This is the first KV evidence and it decides D24.
2. KV-D23-COMPOSE: apply D23, then D23b, each as soon as it is green. Read OT_CLAND for the two writer-face START windows on pv_v2/v4/v6 (the first run with facegrow 58211f43d07). If they fail, the fix is in the facegrow law (tools), not in plan rows.
3. hub_C node move: rebuild the e9 die clock kit (the inputs are gone) before any node re-site. e9 is an x-mirrored DME template, so check the mirror instances in the same run. Do not hand-edit the rect.

### Lever 7. Serdes H18 and the die trunk

**Evidence.** V: headline 5. R: H18 rail check 6,726 rows, 0 bad. H17 under r708: TT -69.66, FF -17.09, not signed. The die trunk (about 1,115 um, 3 hops <= 405 um, M8/M9) still has no plan field.

**Fix.** S81-CORES-OPUS: route H18, then run in-flow sign-off + the r708 re-sign. If TT is within about 30 ps, use the sd9he ECO form on the routed DB. S81-DIE-R3: put the trunk in as explicit die clock rows in the D8e rebind (lever 1.3). Compare the measured rck insertion at the sinks (1,948 to 2,058 ps from the pin) with the die trunk arrival budget before export.

### Lever 8. mergex

**Evidence (R).** mm3b r708: NOT SIGNED, TT +161.72, FF -3.45, 62 internal violators. mm6 in detailed route (iter0 20 k violations). mm3r at CTS hold margin (HM 30, 36,994 ends). mm15r in GRT.

**Fix.** S81-CORES-OPUS: the r583 internal hold ECO on the mm3b routed DB has 161 ps of TT slack to spend on 62 ends, so it should close. Run it now in parallel with mm3r / mm6, and stop mm15r.

## 2. Stop list (the 05:10 list stands, except where struck below, plus these)

1. Do not treat D8e as "binding / applying ~07:40". The bind failed at about 06:13. No publish from r3, and no partial apply that leaves out the leaf XR rows.
2. Do not read the d8t leaf / kv_leaf / iqf kits relaunched at 06:04 as evidence. They have no XR and will stop again at -260 to -734 ps post-CTS TT. Do not re-triage them.
3. Do not relaunch the 27 RESET v5 col rows before the empty-set fix: each one refails in 15 min.
4. Do not treat a fresh attempt 5 as the only path for col_h9_r2 pv11b6518d. The routed DB exists. Do not delete or clean epyc10 attempt_2.
5. hd_mesh: no second pre-GRT hold padding round, and no new mesh form before mesh_w2 has a routed number.
6. mergex: stop mm15r (the 15 ps form; hslice showed there is no room).
7. KV: no hand edit of the hub_C clock rect; no D24 ring decision before one KV CTS number.
8. QC: no N4.1 rows into N4. Do not raise the ctl R8 strap pad limit without a LATCHECK of the receivers.
9. Serdes: still no `serdes_shore_delta.py` rerun on D8e.

## 3. The 0510 levers: done, stale or wrong

| 0510 # | status | note |
|---|---|---|
| 1 col ROM rows | **DONE** (rows) / **STALE** (ECO) | 1,140 rows stripped 05:41 (R, S81-DIE-R3). 149 one-ROM moves gate PASS, `read_loop_place.py` on main 4ce3ad6120c (R). The col_h9_r2 ECO was not started (V); now lever 3. |
| 2 leaf D8e + interior class | **BLOCKED** / **partly answered** | D8e bind failed (lever 1). Interior windows: t40 and t29 are the face-window class, closed by 0-cycle face-clear rows fc6 / fc5 (R). fc2 / vp1-3 not applied: the t25__cl55642d17 ft0 reg cannot be re-sited, so it is still open. t24 / t68 not imaged. |
| 3 QC measured hold | **DONE in code** | e1ce3e0b234 + the nka_blk global (R). Kit proof pending (lever 4). |
| 4 KV D23 | **IN PROGRESS** / **STALE** | D23 / D23b binding. "Read hg/hgi at CTS now" could not happen: no KV kit has reached CTS (V). |
| 5 QC N4 / N4.1 | **SLIPPED** | Apply 05:30 -> about 07:45 (LANE_ASBUILT fixed_cycles, then R8 pass 2). The N4.1 k1 kit failed kit-rtl on the 34-error bind; n41d is pending. |
| 6 serdes | **ADVANCED** | H18 rck span PASS, in GRT (V). The die trunk field is still open. |
| 7 HEAD | **PREMISE WRONG** (hd_mesh) / **ADVANCED** (lep0N) | Taps were balanced to a 63 ps spread, yet hold is still -141.74 on 15 k ends (V), so tap spread was not the main hold source. hd_lep0N: RTL fix 0dcc215 is building as lep_p3 on epyc9 (moved from epyc10 when the docker create stalled, R). |
| 8 svc mergex | **STALE** | mm3b r708 NOT SIGNED -3.45. mm15r still running against the 0510 stop (R). |
| 0510 headline 4 (QC kits hidden as `_LAYOUT_RENDER`) | **DONE** | The classifier now files it as FLOW (R, QC-FLOW-1118). |

Also: r708 was approved for all four dies at 06:02 (COORD). The 07:10 TOOLS-LAG still lists r708 as missing on the s81, s81_head and qwen_kvsys trees (it is not named for qwen_compute: 141 more not shown). So in-flow hold repair on those kits still runs against range clock-pin caps while sign-off uses nominal ones (V, breakdown). P: expect small hold over-fix and small setup loss until the trees carry ad8672055e3. Re-sign remains the rescue path.

## 4. Not checked

- Whether LF_CS_DEPTH clears once emit succeeds (lever 1, P).
- The routed col_h9_r2 DRC names; the bank-leaf proof kit beyond gen.
- mesh_w2 repair outcome; lep_p3 beyond synth start.
- N4D pass 2, n41d, D23 / D23b bind results.
- Any measured-hold relaunch at GRT; H18 GRT overflow.
- dsdv_slice (20), slice_station t6, bk_sel / eng / gunit / iqf / seqhost: wave rows only.
- Die STA on the real clock (S81, HEAD): unchanged, 0 measured hold pairs (R).

---

# FABLE-CLOSURE-STRATEGY 2026-11-18 05:10 PST (0510): delta on 03:20

Reviewer: FABLE-CLOSURE-STRATEGY-0510 (Fable). Read-only: no jobs launched, nothing killed or deleted. Technical PD only. HBM parked.
Gate (R-MINIMAL): DRC 0, routed TT >= -42 ps, internal reg-to-reg FF hold >= 0, die bind + LATCHECK. r708: clock pin cap nominal at sign-off.
Marking: **V** = I opened the file or log this round (05:10 to 05:50 PST). **R** = reported by the named lane, not opened. **P** = my proposal or estimate.

Signed types by family (V, plan cache 05:10): S81 42/394 (slice_station 41/46, col_h9_r2 1/60, everything else 0: leaf 75, col 215, dsdv_slice 20, svc 16, serdes 11, kv_leaf 5, bk_sel, eng, gunit, iqf, seqhost). HEAD 24/26 (open: hd_mesh, hd_lep0N). QC 24/130 (hc 7/18, fe 4/9, su 4/9, stm 2/11, fw 1/11; 0 of st_b 12, st_a 11, sc 9, cbn/cbf/cbx 18, ctl 7). KV 6/56 (0 of pv 16, hgi 11, hg 8, pc 6, hub 5).

## 0. Headline

1. **The D8e plan now in bind carries 1,140 relay rows that break the col config sequencer (V).** epyc8 `s81-colgen-1/ev/d8e_rd.json` (sha1 c24b3f8b72b8, the plan S81-DIE-R3 took at 05:08): 2,058 `relay_depth` rows; 480 `u_c*_*.addr_in` + 480 `ce_in` + 180 `u_s*.q*` = 1,140 rows on 168 col types, identical to `d8d_rd.json`. FABLE-FIX-S81-BANKLEAF measured at 04:56 (R, verilator on `ot_s81_cfg7_seq`): one stage on one ROM of the fixed-latency read loop captures the wrong word; bind and LATCHECK accept it. The S81-DIE-R3 post does not mention the alert (V, 0 matches). These rows span 420 to 640 um, just over the 405 um reach.
2. **Col is 215 of the 352 unsigned S81 types and its one routed member is ECO-sized (V).** epyc10 `col_h9_r2__t1__cl774acf45__pv11b6518d/attempt_2` sign-off: DRC 2, TT -46.87 / 131 ends, internal FF hold 5 ends at -5.07, 102 unconstrained. The worst TT path is core to core (`u_u_e*_u_w` -> `u_u_bn*`), the bank-leaf class. No relay rows are in that kit.
3. **`5_global_route.rpt` is not a TT number (V).** Leaf t11 reads -5.30 there and -288.97 at the TT gate of the same DB; t15 -17.59 / -350.29; kv_leaf t4 -4.71 / -259.65. The GRT repair session is FF-only (`tt_setup_repair.tcl` header); the TT repair on t11 moved -353.00 -> -288.97 with 404 cells. This answers the 03:20 open item: the 14 strip stops are real at TT.
4. **QC kits with clean GRT die on the measured-hold bind when pin registers sit on more than one clock (V).** `vclk_measured_hold.tcl` line 131 errors unless `ncl == 1`. Five kits: N3 sle_sc_v3 (04:4x today, CTS wns -59.25, GRT overflow 0, `clocks 3`), N1B slw_fw_v3 (CTS 0.00, `clocks 4`), sle_sc_v1__cl7479a5ec (-5.29), sle_su_l1__cl5ea486db (-33.43), slw_fe_v2__cle312294d (-88.40). The wave row for sle_sc_v3 reads `_LAYOUT_RENDER ... local_density`, so the class is hidden. No QC lane post names it.
5. **S81 leaf GRT overflow has a second class that row stride 2 does not address (V).** t25__cl431c660f (fixed by the pilot) is the south face. t24: 566 congested gcells in one window x 850-950, y 300-450, M6 6,368 + M8 11,182 of 18,328. t68: 524 gcells at x 500-550, y 200-250, M6 5,616 + M8 6,253. t25__cl55642d17: 5,122 gcells at x 200-300, y 350-450, M6 69,907 + M8 21,090. All interior, all on the horizontal layers M6 and M8 only.
6. **KV has no CTS number on the current plan family (V).** 27 KV-HG6 kits have `3_5_place_dp` as their last log (1.3 to 4.8 h old) and none has a `4_1_cts` log. D22 applied at 05:0x with the tail split on 1 of 16 PV types (R, KV-D23-REACH: `re.fullmatch("^kv3_pv")`).
7. Closed since 03:20 (R): hd_serdes sd9he signed (TT -27.16, hold 0); svc hslice signed twice (mm3r at 30 ps with r692; mm4 by r708 re-sign, TT +184.88); lep_pair vE28 signed and in HEAD r2; t25 stride-2 pilot GRT 1,022 -> 0.

## 1. Levers ranked by closure impact

| # | die | lever | unblocks | owner |
|---|---|---|---|---|
| 1 | S81 | Take the 1,140 ROM-loop rows out of D8e before publish; close those hops by core placement; ECO the routed col_h9_r2 as the family pilot | col 215 | S81-DIE-R3, FABLE-FIX-S81-BANKLEAF, S81-COLGEN-1 |
| 2 | S81 | D8e leaf rows (XR, core reset relays, face stride): judge the first kits at the TT gate; open a lane item for the interior M6/M8 window class | leaf 75, kv_leaf 5 | FABLE-FIX-S81-STRIP, S81-DIE-R3 |
| 3 | QC | Measured-hold bind per clock root instead of an error at `ncl != 1` | sc 9, su 5, fe 5, fw 10 as an upper bound; 5 kits proven | WAVE-FLOW-R2, QC-TYPES-R3 |
| 4 | KV | D23 with `kv3_pv.*`, bands sized by `band_capacity`, reset hops; read hg/hgi at CTS now | pv 16; first evidence for hg/hgi 19 | FABLE-FIX-KV-HG |
| 5 | QC | N4 then N4.1 on one measured st_a kit; cbn/cbf/cbx place errors | st_a 11; cb 18 | QC-PLAN-R3, FABLE-FIX-QC-N, QC-TYPES-R3 |
| 6 | S81 | Serdes: H18 is the first rail-clean kit; the die pad-clock trunk to the moved `io_pma_rck` pin has no plan field | serdes 11 | FABLE-FIX-S81-SERDES2, S81-DIE-R3 |
| 7 | HEAD | hd_mesh: balance the 5 short taps before hold padding; first hd_lep0N build on r2 | 2 types, then the die | FABLE-DIE-HEAD, FABLE-FIX-HEAD-LEP0N |
| 8 | S81 | svc mergex at 30 ps + r692 (the hslice recipe); r708 re-sign of mergex_mm3b | 1 core, then svc 16 | FABLE-FIX-S81-SVC2, NOMCAP-1118 |

### Lever 1. S81 col: remove the ROM-loop relay rows, close col_h9_r2 by ECO

**Evidence (V).** `d8e_rd.json` rows by class: ROM `addr_in` 480 and `ce_in` 480 (168 types, 420 to 640 um), `u_s*.q*` 180 (144 types, 420 to 692 um), `u_t*.c*` 288, `u_n*.fi` 180, `u_n*.a` 96, `u_e*.xb_data` 72, y_cc / y_x links 126 (920 to 1,244 um). The die bind on this plan is running on epyc8 (`bind.py elab ... --strict`). Routed col_h9_r2 numbers as in headline 2; its `config.mk` has `OT_HOLD_FF_MARGIN = 0` and the SDC hold uncertainty is 25 ps.

**Root cause.** The relay generator treats every hop over 405 um as a schedulable link. The cfg7 sequencer loop is not a link: its read latency is fixed in RTL. The frame tracer models the sequencer as a 0-edge pass-through, so the only signal is `RELAY_DEPTH_UNSCHEDULED`, which D8e plans to name in the ack record and pass.

**Fix.**
1. S81-DIE-R3: do not publish D8e with the 1,140 rows. Filter `inst ~ u_c<b>_<k>` with port `addr_in` / `ce_in` and `inst ~ u_s<n>` with port `q<k>` out of `relay_depth` and rebind as the delta; the other 918 rows stay only where the tracer can schedule them (R: BANKLEAF is adding that).
2. FABLE-FIX-S81-BANKLEAF: the ROM hops are 15 to 235 um over reach, so move the ROM cores toward the sequencer (0 cycles), as already started. Deliver as one col row set for all 168 types.
3. S81-TYPES-R3 + CAPSKEW-ECO: col_h9_r2 pv11b6518d is 4.87 ps and 5 hold ends from the gate. Name the 2 DRCs and the 102 unconstrained ends, then run the capture-skew / hold-pad ECO on the routed DB (the sd9he form: 15 flops, 113 pads). A signed r2 proves the family without relay rows; 50 placed col kits are waiting on the same answer.
4. P: the macro-to-macro worst path means the r2 TT miss is set by core pin timing plus distance, so core placement also closes TT; do not add a cycle there before the placement rows are measured.

### Lever 2. S81 leaf: D8e rows, TT-gate reads, interior congestion class

**Evidence (V).** TT gate estimate against the FF-session report, same DB:

| type | CTS wns | TT gate | `5_global_route.rpt` |
|---|---|---|---|
| t11 | -304.64 | -288.97 | -5.30 |
| t15 | -401.81 | -350.29 | -17.59 |
| t30 | -283.77 | -315.26 | -29.06 |
| t44 | -160.55 | -288.41 | -11.32 |
| t54 | -575.04 | -470.52 | -30.37 |
| t55 | -384.19 | -449.57 | -30.27 |
| kv_leaf t4 | -273.55 | -259.65 | -4.71 |
| kv_leaf t5 | -403.50 | -297.36 | -34.49 |
| t50 | -684.45 | -445.36 | -94.32 |
| t27 | -610.56 | -515.04 | -202.02 |
| t38 | -488.12 | -462.95 | -248.26 |
| t16 | -734.41 | -733.84 | -384.76 |
| t53 | -1,085.45 | -891.61 | -666.38 |

All these kits: `VERILOG_DEFINES = -DSYNTHESIS` (no XR), plan before D8e. GRT overflow rows: t24 18,328, t25__cl55642d17 99,680 (still running), t68 15,143, t40__clf8bbdae1 10,497, t4 2,283, t41 1,620, t25__cl431c660f 1,022, t29 547, t35 4 (GRT-0232). Seven more leaf kits stop at place on `OT_VPW_BANK distance exceeds 100um` (t1 t10 t13 t14 t75 class); kv_leaf t1 and t3 on PLACE-HPWL 1.48 x and 1.32 x.

**Root cause.** Unchanged from 03:20 for timing (VS core clk-to-`x_wa` 383 ps, reset relay far from the core pin). For the interior class: one window of 50 to 150 um carrying only horizontal-layer overflow is a bundle crossing one channel, not pin access. P: the FIRM bank placement pulls the write bus of one VPW bank through a single gap between hard cores. Not shown; the stage DBs were cleaned.

**Fix.**
1. S81-DIE-R3: D8e keeps XR 16/16, the 1,967 reset relay sites and `face_flop_ns_types` stride 2 (R, all in). These do not depend on the col rows; if the col delta costs a rebind, publish the leaf rows first.
2. FABLE-FIX-S81-STRIP: read the first XR kits at `postcts_gate_tt.json` and `tt_setup_repair_grt.log` only. Expected (P): the `wdo_q` class gains one cycle of 833 ps against misses of 260 to 734, so t16 and t53 (-734, -892) may keep a residue; take their class table first.
3. FABLE-FIX-S81-STRIP: keep `5_1_grt.odb` on t24, t68, t25__cl55642d17 and t40 and image the window. If it is a core gap, the fix is a bank or core move in the type rows, not stride.
4. The `OT_VPW_BANK distance exceeds 100um` stop is a placement check on a path that XR re-times; with XR in, it should be measured again before any site work.

### Lever 3. QC measured-hold bind with forwarded clocks

**Evidence (V).** epyc9 `s29q103S4Q9N3/items/sle_sc_v3/attempt_2`, `5_1_grt.log` line 727 after `OT_HOLD_BUDGET added 0 ... hold_ws -21.86 ... OK`: `OT_VCLK_MEASURED_HOLD: pin-register mean unavailable (samples 8205 missing 0 clocks 3)`. `vclk_measured_hold.tcl`: `ot_vmh_pinreg_mean` maps a clock to its root only when `fwd_roots` is non-empty and `ot_cf_root` exists; the bind then requires exactly one clock name. The col sign-off record shows the working form: `samples 1496 missing 0 clocks 1 forwarded_excluded 8`.

**Root cause.** In these QC kits the pin registers are clocked by forwarded cland clocks that are not in the kit's forwarded-root table, so they count as separate clocks and the step aborts. All samples have arrivals (`missing 0`); only the clock count fails.

**Fix (WAVE-FLOW-R2 with QC-TYPES-R3).** Bind the IO virtual clock from the pin registers of the primary clock and exclude forwarded-clock registers, as sign-off already does (`forwarded_excluded`), or fill `fwd_roots` from the plan cland rows at gen. Then relaunch the five kits from GRT; three of them are at CTS wns 0.00, -5.29 and -33.43. The same error stopped HEAD sd9c on 11-16 (R), so the fix is die-agnostic.

### Lever 4. KV D23

**Evidence.** V: 4 PV kits stop at `OT_CLAND no legal nonoverlapping row/site in reserved band` (pv_v2 and pv_v4 `u_cland_raw_fs_o_pvw...`, pv_v6 `..._valid_d1_0`, pv_v2n `u_cland_fstart_ft26_o`); hub_C 773,818 and hub_Wo 406,241 cells; no KV kit past placement. R: D22 gate of record passed (strict bind 0 errors, R8 recheck 0, LATCHECK 2,404 / 2,404); not in D22: rider (29 routed hops over 405 um), reset relay rule, `u_d` pipes, pc taps, hub splits; hub_Wi shell 299,999 cells with 14 hard `qkd_hr` masters; hub_C split gate A failed 16 EMIT (reset_net on ring rows, `landing_ring_wreg`), gate B running, 1 collision with a reserved die clock rect open.

**Fix (FABLE-FIX-KV-HG).**
1. D23 in one event: `types ["kv3_pv.*"]`, writer-start and raw-reset bands grown from `band_capacity.py measure` on all 16 PV types, rider, reset hops, hub_Wi rows. hub_C follows when gate B and the clock-rect collision are clean; do not hold D23 for it.
2. hg / hgi / pc / hroot / io_cor (25 kits placed on HG6) are not touched by the PV rows; under r710 they survive the apply. Their first CTS tap-balance and wns lines are the first KV evidence; read them before composing D24.
3. D24 (lighter rings) should be decided from the 186,960 ring cells in the hub_Wi shell and a measured ring kit, not before.

### Lever 5. QC N4 / N4.1 and the cb types

**Evidence (R unless marked).** N4 chain running (group A stations, coll_core 43 taps, clk_t115 split, relay_sites for 11 st_a types). N4.1 by FABLE-FIX-QC-N: u_btab bank moves tested (0 halo hits, lane latency equal), rs_s per-row copies, nb_od / nb_oc station (+1 on x_fe_o), cland forwarded-clock insertion target 485 instead of 419 ps for three masters with setup over 80 ps; one kit to routed sign-off, first CTS in about 3 h. V: cbx_q10__cl94a12200 stops at `global_place.tcl ... can't read "nka_blk": no such variable`; cbf_q01_s2 and cbn_q11__cl5cc92dfe at `GRTM mode edge_outline`; st_b refused at 486,894 to 501,829 cells; tt_ctlm TT gate -258.47.

**Fix.**
1. QC-PLAN-R3: apply N4 as composed. FABLE-FIX-QC-N: no N4.1 rows before the single kit is read at CTS.
2. QC-TYPES-R3: the `nka_blk` Tcl error is an unset variable in the generated `global_place.tcl` (V: the error line; P: a gen branch for the nk_a hard-core form that this type does not take). Fix in gen; P: it stops every cb type built with that core form, so check cbn / cbf kits for the same line.
3. The +66 ps forwarded-clock target is a contract change on the sender; check the three cland masters in the signed fe / hc kits before it becomes a gen default.
4. tt_ctlm still needs the RTL stage (flat `u_core`, 253 ps wire + 700 ps logic, R).

### Lever 6. S81 serdes

**Evidence (R, SERDES2 / DIE-R3).** H18 (H17 recipe + `OT_S81_LPL_CHUNK`, PHY row cut): rail check 6,726 rows 0 bad (H17: 2,046 of 6,664 bad), in placement at 04:41. H17 with nominal clock cap: TT -69.66, internal hold -15.88 / 20 ends. D8e: u_cmem read register at 0 cycles, TAP-GROUP-CAP-1 back (cap 1,700; t13 clk_t42 split in 4), `io_pma_rck` pin moved x 332.704 -> 1,448.032 on 5 shore types (insertion 1,695 against 2,217 ps). Open: the die pad-clock trunk (about 1,115 um, 3 hops) has no plan schema field, and `serdes_shore_delta.py` would move the pin back.

**Fix.**
1. S81-DIE-R3: add the trunk as explicit die clock rows (three stations <= 405 um on M8/M9) in the clock event, and make `serdes_shore_delta.py` read the pin from the plan. Without it the type closes against a pin the die cannot feed.
2. FABLE-FIX-S81-SERDES2: sign H18 under r708 if routed TT >= -42; otherwise the sd9he ECO form (capture skew + hold pads) on the routed DB. The six non-shore types wait for the H18 result, not for a new H form.

### Lever 7. HEAD

**Evidence (R, FABLE-DIE-HEAD 04:18).** hd_mesh mesh_w1 with the credit counter on one tap: TT at CTS -0.96 (was -50.56). Hold before repair: cross-tap 10,190 ends at -185.30, same-tap 1,408 at -84.24; five taps short of the 450 ps target (clk_t45 322, clk_t54 330, clk 332, clk_t42 360, clk_t43 384). The earlier attempt lost TT -49.56 -> -68.34 after 37,912 hold cells. V: no hd_lep0N kit directory exists on epyc9 / epyc10 / intel1 under event `..._r2` at 05:45; hd_tile on NF15f a4 reads TT gate -354.59 (it is signed from nf15c_tp2_land1).

**Fix.**
1. FABLE-DIE-HEAD: the 128 ps tap spread is the hold demand. Fix the five short taps (delay cells at the tap root, or the tap group rule) and re-run CTS before pre-GRT padding; padding 10 k ends by 185 ps repeats the 37,912-cell run.
2. FABLE-FIX-HEAD-LEP0N: first r2 synth, band and CTS read; nothing technical can be said before it.
3. M8 grant: 1,723 die-track conflicts on signed types (hd_tile 1,069) stay a die clock leg move (R). It blocks die assembly, not the type count.

### Lever 8. S81 svc mergex

**Evidence (R).** hslice: 15 ps finished at FF r2r -0.00 (not signed), 30 ps + r692 signed (+12.14 routed), 50 ps failed on utilisation. mergex mm6 in GRT, mm3r and mm15r in CTS hold repair; mergex_mm3b routed r2r -6.93, r708 re-sign running (hslice_mm3b re-sign: FF -2.85, not signed).

**Fix.** FABLE-FIX-S81-SVC2: mergex_mm3r is the form of record; stop mm15r (hslice proved 15 ps leaves no room). If the mm3b re-sign lands within 3 ps as hslice_mm3b did, close it with the r583 internal hold ECO instead of waiting for the rebuild.

## 2. Die floorplan or type-internal, per die

| die | unsigned families | where the blocker sits | one die-level change |
|---|---|---|---|
| S81 | leaf 75 + kv_leaf 5 | Type structure, fixed by die-plan rows (XR stage, reset relay sites, face stride). A second, type-internal class: interior M6/M8 windows on 4 types | D8e |
| S81 | col 215 | Type-internal and close (routed -46.87, 5 hold ends). Held by plan rows: relay hops over 405 um and bank-leaf core distance | D8e col delta without the ROM-loop rows, with core moves |
| S81 | serdes 11 | Type-internal (rck tree, PG rails) plus one die item: pad-clock trunk to the moved pin | D8e rows + die clock rows |
| S81 | svc 16, dsdv_slice 20, slice_station 5, singles 5 | Type-internal (mergex core hold; kit preflight / `edge_outline`; slice_station t6 TT gate -229). Not opened this round beyond the wave rows | none |
| HEAD | hd_mesh | Type-internal (tap balance, cross-tap hold) | none |
| HEAD | hd_lep0N | Die plan (bands, pair views, tap offsets): delivered in r2, unbuilt | r2, already applied |
| QC | sc, su, fe, fw (29 unsigned) | Flow: measured-hold bind; no floorplan cause found | none; lever 3 |
| QC | st_a 11 | Die plan rows inside the type (stations, tail copies, bank sites) | N4 + N4.1 |
| QC | st_b 12, hc 11 | Type size (350 to 502 k cells) and routed hold; not floorplan | none |
| QC | cbn / cbf / cbx 18, ctl 7, tt_ctlm | Generator and RTL (place Tcl error, `edge_outline`, missing stage) | none |
| KV | pv 16, pc 6 | Die plan rows (tail split, bands, taps) | D23 |
| KV | hub 5 | Partition size: split on signed ring and host masters | D23 (Wi), later hub_C |
| KV | hg 8, hgi 11, others 4 | Unknown: no CTS number exists | none known |

No die has a die-floorplan routing problem: die GRT overflow is 0 on S81 (M4 to M7 use under 5 %), QC (worst cut 0.237) and HEAD combo (0.37 %) (R, FABLE-DIE-* 11-17). The die-level open items are clock structure (S81 K table from B6gsh, 93,626 unreserved clock cell sites, 21 legs over 405 um; HEAD M8 grant) and they gate die STA, not type sign-off.

Answer: S81 yes, one event. D8e plus a corrected col delta reaches 306 of the 352 unsigned types (leaf 80, col 215, serdes 11). KV yes for 22 of 50 (D23: pv, pc), unknown for hg / hgi. QC no: N4 covers 11 of 106; the widest single change is the flow fix of lever 3. HEAD no: one type each.

## 3. Stop list (the 03:20 list stands, plus these)

1. Do not publish D8e with `relay_depth` rows on `u_c*_*.addr_in / ce_in` or `u_s*.q*`. Do not record `RELAY_DEPTH_UNSCHEDULED` as an accepted finding for those rows.
2. Do not read `5_global_route.rpt` / `6_finish.rpt` wns as the TT result; it is the FF session. TT is `postcts_gate_tt.json`, `tt_setup_repair*.log` and sign-off.
3. No relaunch of pre-D8e leaf kits; no SETUP_TRIAGE threshold change (the 8 kits that look closed at GRT are at -260 to -470 TT).
4. No row stride as the answer to t24 / t68 / t25__cl55642d17 / t40; no S81-wide stride default (fires on 387 of 395 types, R).
5. QC: no relaunch of sc / su / fe / fw kits with forwarded-clock pin registers before the bind fix; no N4.1 plan rows before its one kit is measured.
6. KV: no judgement of PV on HG6 or D22 kits (split covers 1 type); no D24 compose before one KV CTS number; no hold of D23 for hub_C.
7. hd_mesh: no hold padding against a 128 ps tap spread.
8. svc: no 15 ps and no 50 ps margin builds.
9. Serdes: no `serdes_shore_delta.py` rerun on D8e; no export of H17 (rail defect).

## 4. Not checked

- The D8e bind output itself (still running); whether S81-DIE-R3 acted on the BANKLEAF alert after 05:08.
- The BANKLEAF verilator result, the 515 bank-leaf paths and the core-move rows (R).
- What the interior congestion windows contain (no stage DB; the cause in lever 2 is a proposal).
- Whether the five QC kits pass sign-off once the bind is fixed; how many of the 29 sc / su / fe / fw types carry forwarded-clock pin registers.
- Any KV timing. Any hd_lep0N r2 result. H18 beyond the 04:41 post. mergex results.
- dsdv_slice (20), svc shell types and bk_sel / eng / gunit / iqf / seqhost: wave rows only.
- QC N4 bind result; the cland +66 ps effect on port hold.
- Die STA on the real clock for S81 and HEAD (0 measured hold pairs, R).

---

# FABLE-CLOSURE-STRATEGY 2026-11-18 03:20 PST (0320): delta on 23:20

Reviewer: FABLE-CLOSURE-STRATEGY-0320 (Fable). Read-only: no jobs launched, nothing killed or deleted. Technical PD only. HBM parked.
Gate (R-MINIMAL): DRC 0, routed TT >= -42 ps, internal reg-to-reg FF hold >= 0, die bind + LATCHECK.
Marking: **V** = I opened the log or file this round (03:14 to 03:40 PST). **R** = reported by the named lane, not opened. **P** = my proposal or estimate.
All lanes were stopped 00:30 to 03:10; most "running" items below are builds that kept going with no reader.

## 0. Headline

1. **S81 strip leaves: 14 of the first 21 route verdicts are a pre-route setup stop of -244 to -734 ps, and it is structure, not settings (V).** Worst classes in the kits: VS core `x_wa` -> `u_vp_g_wr1_u_w.wdo_q` (t16 -715 / 1,025 ends; t50 -684 at CTS), and reset into hard-core `rst_n` pins (`u_vsw/rst_n` -298 to -425 on t15 t26 t38 t50). The XR stage that was decided for this family on 11-17 is not in any of these kits (t50: 0 `ot_s81sl_xr` instances, `VERILOG_DEFINES = -DSYNTHESIS`). The other 7 verdicts are GRT congestion (t25 class).
2. **The GRT optimism is a serdes rck-tree problem on both dies, not a fleet problem (V).** hd_serdes, three forms routed overnight: sd9h GRT TT -0.24 -> routed -45.34; sd9pa -10.89 -> -49.62; sd9pb2 -0.89 -> -92.27. Over 85 other kits with both a `grt_policy.json` and a later `signoff.json` (epyc7/9/10), TT moves mostly within +-25 ps and FF hold within +-10 ps; the bad outliers are QC sle_fe_v3 (+39 -> -29), S81 col_h9_r2 (-19 -> -47) and QC slw_hc1 (-14 -> -41).
3. **hd_serdes sd9h is 3.3 ps from the gate (V):** DRC 0, TT -45.34 / 119 ends, FF hold -31.02 / 169 ends. sd9pa: DRC 0, TT -49.62 / 8 ends. Both are ECO-sized on setup.
4. **lep_pair vE28 is 12 flops from sign-off (V):** DRC 0, TT -0.66, internal FF hold -9.7 on 12 ends (the other 2,739 hold ends start at ports). No ECO has been started on it. It is the only thing hd_lep0N waits for.
5. **KV D22s failed its strict bind at 23:58 (V); this is the third D22 plan.** `R8_STRAP_PAD kv3_pc_v1__cl7f648944 slg.vreq: pad 18 > strap capacity 15`, `TYPE_SPLIT` 12 instances -> 7 variants, `EMIT clock landing`; R8 recheck 64 unequal groups, 2 inversions. Rider gate3: 30 `R8_STALE`, LATCHECK 2,404 / 2,404. Meanwhile the wave ran PV kits on KV-HG6 with no tail copies (pv_v6: 0 `ot_dp_dly_keep`), and 4 of them tripped the CLAND band breaker.
6. **The svc hold misses are not ECO-sized (R, SVC2 03:14).** hslice_mm4 ECO failed (1,092 negative ends, incremental route failed); mergex_mm3b refused (1,567 ends); hslice_mm7 at 50 ps died at CTS (53,294 hold buffers, utilisation over 100 %). My 23:20 lever 4 item 1 was wrong for these two cores. V: hslice_mm6 is in detailed route (471 violations in the current iteration), mergex_mm6 in CTS hold repair at 30.9 k buffers.

## 1. Levers ranked by closure impact

| # | die | lever | unblocks | owner |
|---|---|---|---|---|
| 1 | S81 | Strip leaf: XR stage on the VS -> VPW write, registered reset at the core `rst_n` pins, in one plan/RTL event | 14 stopped strip types now; the same class sits in all 75 leaves | FABLE-FIX-S81-STRIP, S81-DIE-R3 |
| 2 | HEAD | lep_pair vE28 hold ECO (12 ends) -> sign -> view pack -> hd_lep0N | hd_lep0N, then the HEAD die | FABLE-FIX-HEAD-LEP0N, HEAD-PLAN-R4 |
| 3 | HEAD, S81 | Serdes rck: close sd9h / sd9pa by post-route clock ECO; size rck pads on extracted arrivals; never decide these types at GRT | hd_serdes; 11 S81 serdes types | FABLE-FIX-HEAD-SD9F, FABLE-FIX-S81-SERDES2, CAPSKEW-ECO |
| 4 | KV | D22: fix the `slg.vreq` pad (18 > 15) before a fourth bind; regenerate the rider R8 table from that bind; PV bands by `band_capacity`; hold PV kits | PV 16, pc 6, the die event | FABLE-FIX-KV-HG, KV-R3 |
| 5 | S81 | Strip south-face pin-row congestion (t25 class, 7 types) and col relay reach, as generator rules | 7 strip types; col 216 | FABLE-FIX-S81-STRIP, S81-TYPES-R3 |
| 6 | QC | N4 with flt_bank stations + sited tail copies; own tt_ctlm | st_a 11 types; tt_ctlm types | QC-PLAN-R3, TAIL-REPL |
| 7 | S81 | svc hslice / mergex: sign mm6 if it passes; if not, cut the hold demand at its source instead of adding buffers | 2 cores, then the svc shell | FABLE-FIX-S81-SVC2 |
| 8 | KV | Hub types over the size OpenROAD closes: split hub_C and hub_Wi on signed ring cores; waive hub_Wo | 3 hub types | KV-HUBWO-SPLIT rows, FABLE-FIX-KV-HG |

### Lever 1. S81 strip leaf: the stops are two structural paths

**Evidence (V).**
- `kit_wave_stages.tsv`, current plan, strip route rows: 14 `FAIL_POSTCTS SETUP_TRIAGE` (iqf__t1 -537, kv_leaf t4 -260, t11 -289, t15 -350, t16 -734, t26 -483, t27 -515, t30 -315, t38 -463, t44 -288, t50 -445, t54 -471, t55 -450; last one t55 at 02:55), 7 GRT congestion (t25 t29 t35 t4 t40 t41 t68), t51 DPL-0033.
- epyc8 `.../items/ot_s81sl_leaf__t50/attempt_7`, `4_cts_final.rpt`: wns -684.45, tns -336,321. Path `u_bound.u_u_vs/clk` -> `x_wa[0]` leaves the core at 401.7 ps, then 38 cells (31 buffers, 7 gates) in three long hops (401 -> 911, 951 -> 1,288, 1,351 -> 1,576) to `wdo_q[0][82]`, arrival 1,603 against 919 required.
- Same kit: `OT_VPW_BANK placed 317 FFs FIRM, nearest-bank max 11.328um`. So the bank placement works and does not close the path: the capture flops sit at the bank, the source core and the arbiter logic do not.
- Same kit: asynchronous group, `u_lpad_leafdn_i0.q[0]` -> 22 buffers -> recovery at a `_DFF_PN0_`, -41.42.
- `tt_setup_repair_grt.log` last line per kit: t16 -714.4 `wdo_q`; t15 -297.8, t26 -329.4, t38 -420.2, t50 -424.7 all `u_*vsw/rst_n`; kv_leaf t4 -243.4 `u_vp_g_ln_7_u_l/rst_n`; t55 -291.1 `g_u_lf4_u_vp_cf.native_memory`. t16 then crashes: `[ERROR RSZ-0074] Failed to build tree from global routes`.
- All these kits: `OT_HOLD_FF_MARGIN = 0` (plan 30c40fae, before the D8d key).

**Root cause.** The VS core spends 383 ps clk-to-`x_wa` inside the core (R, 11-16 review; V 401.7 at the pin). The five-writer arbiter then has about 430 ps for 400 to 1,000 um of wire plus 7 gates. No placement can close that. The reset class is the same shape: a relay flop far from the core pin it drives. The repair cannot help either path and spends its time (and crashes) trying.

**Fix.**
1. S81-DIE-R3 + FABLE-FIX-S81-STRIP: put the XR form (r432 `ot_s81sl_xr`, +1 cycle on `x_w` and `x_wd` together, pre-approved) into the next S81 event for every leaf type, with bank placement kept. I did not find XR in D8d (P: it is not there; the 03:13 D8d result does not name it). If D8d is already bound, make it D8e, not a per-type patch.
2. Reset: one `ot_dp_rrelay` stage sited within 50 um of each hard-core `rst_n` pin (vsw, vp_g_ln), from the existing relay-site rows; the 64-cycle reset hold makes the cycle free.
3. FABLE-FIX-S81-STRIP: class table of the 14 kits from `4_cts_final.rpt` (not from the gate estimate) before anything is relaunched. t15 shows kit GRT -17.6 against an estimate of -350 (R); find what the estimate adds, but that question does not change t16 / t50, which are real at CTS.
4. WAVE-FLOW-R2: `tt_setup_repair.tcl` must catch RSZ-0074 and keep the pre-repair DB; today the crash hides the real number.

### Lever 2. HEAD: sign lep_pair vE28 by ECO

**Evidence (V).** epyc9 `head-lep0n-opus/lep_ve28/kit/ot_s81hd_lep_pair_kit/signoff/signoff.json` (23:27): NOT SIGNED, DRC 0, antenna and PG PASS, `setup_tt -0.66 / 1`, `hold_ff -177.0 / 2751` of which `std_min_start.port 2739`, `nonport_n 12`, `nonport_wns -9.7`. TT insertion 517 to 528 ps; pair skew min 87.3. No ECO directory exists in the kit. hd_lep0N p2 (diagnostic, old windows) is at CTS wns -379.62, tns -97,009: not a verdict.

**Fix.**
1. FABLE-FIX-HEAD-LEP0N: `hold_eco_internal_run.py` (r583) with the top-layer route fix b6e97307 on the routed vE28 DB now; hei3 closed 7 -> 0 pads in three rounds the same way. Sign, export.
2. HEAD-PLAN-R4: one pack = vE28 views (`bb.v` KCRED 28) + plan_grown2 bands + related-pair windows; take the four pair tap offsets from the signed core's `clock_contract.json` (insertion about 527, not the 450 target).
3. M8 grant (R): track-level lock 4,321 -> 3,178; hd_tile (signed) 1,069. Types do not re-sign; if the shape test shows real overlap the die clock legs move. Still open with FABLE-DIE-HEAD.
4. hd_mesh `mesh_w1` (related windows) is in CTS (V 03:20); read its cross-tap hold class against 11,732 ends / -125.74.

### Lever 3. Serdes rck trees: decide on extraction, close by clock ECO

**Evidence.**
- S81 H17 (R census; V the eight census files exist, epyc9 `fable-fix-s81-serdes2/drtx/census/`): GRT -27.17 / +0.12, routed -117.47 / -55.85; data nets median -14 ps; rck sinks spread 1,848 to 2,051 routed; lpl_r.rc -> o 144 ps, lpl_2_w.wc -> b 179 ps.
- HEAD hd_serdes (V, epyc10 `fable-fix-head-sd9h/<form>/hd_serdes/{grt_policy.json,signoff_fable/signoff.json}`):

| form | GRT TT / ends | routed TT / ends | GRT FF hold | routed FF hold / ends | DRC |
|---|---|---|---|---|---|
| sd9h (PW16 + PW8) | -0.24 / 1 | -45.34 / 119 | -24.34 | -31.02 / 169 | 0 |
| sd9pa (PPCYC) | -10.89 / 1 | -49.62 / 8 | -17.77 | -33.68 / 432 | 0 |
| sd9pb2 (SPCYC) | -0.89 / 2 | -92.27 / 228 | -35.12 | -46.66 / 107 | 0 |
| sd9pc2 (both) | +0.67 / 0 | none: `DRT-0255` | -21.12 | none | - |

- sd9h vclk reference latency 488.8 at GRT, 446.4 routed: the tree is 42 ps faster under extraction, as on H17 (74 to 94).
- Fleet (V, 85 kit pairs): the effect is small elsewhere. HEAD types (insertion 478 to 521) move TT by -9 to +11 typically; S81 slice_station (280 to 350) by -44 to +90; QC by -68 to +61.

**Root cause.** The rck balance pads are sized on placement RC and confirmed on GRT RC. A 2 ns, 63-stage tree turns a few percent of clock RC error into 50 to 180 ps between branches (R, SERDES2). Ordinary CTS trees of 300 to 520 ps do not show it.

**Fix.**
1. FABLE-FIX-HEAD-SD9F: sd9h needs 3.3 ps on 119 ends; sd9pa needs 7.6 ps on 8 ends. Run `capskew_eco_run.py` on both routed DBs, then the internal hold ECO. The 100-pad hold limit will refuse 169 / 432 ends: split by rck branch and run two rounds rather than raise the limit blind. First to pass signs. sd9pb2 is out.
2. I withdraw my 23:20 line "stop PPCYC/SPCYC once sd9h shows TT >= -42 at GRT". No rck-tree type is decided at GRT.
3. CAPSKEW-ECO + WAVE-FLOW-R2: for kits with `OT_S81_RCK_BALANCE` (S81 serdes 11, hd_serdes), make the flow: route -> extract -> rck pad re-size on SPEF sink arrivals -> incremental route -> hold ECO. The GRT policy stays as a triage only.
4. FABLE-FIX-S81-SERDES2 / S81-DIE-R3 (R, agreed): cmem read register, centre-root trunk, t42 four-tap split in the S81 event; pilot t13 only after that.
5. sd9pc2: `DRT-0255` is the M6 pair-row class; hd_serdes kits need the `pg_row_guides.tcl` hook (r598) that S81 serdes has. Do not rerun unchanged.
6. Triage margin elsewhere (P): a type with GRT TT between -42 and +30 is not safe; plan the CAPSKEW ECO for it rather than a rebuild (col_h9_r2, slw_hc1, sle_fe_v3 are this case).

### Lever 4. KV D22

**Evidence (V).** epyc7 `kv-hg-opus/d22s/gate/gate.out` (07:58Z): PRE PASS, G0 PASS (0 errors, 2,403 warnings), `RC_BIND 1` with 3 errors as in headline 5, `RC_R8CHECK 1`, LATCHECK not run (no `*_bound_top.sv`). `kv-pv-rider/gate3/gate.out`: `BIND_ERRORS 30 {'R8_STALE': 30}` (`pvw_0__u_T0Q0_45_r0.b as-built 2 bound 9, table ... bound 5`), LATCHECK PASS. Wave 01:37 to 01:48: `OT_CLAND no legal nonoverlapping row/site in reserved band` for `u_cland_fstart_ft0_o` (pv_v6), `ft26_o` (pv_v2, pv_v2n), `u_cland_raw_fs_o_pvw...` (pv_v4, literal-local-reset). Sited proof epyc9 `kv-hg-opus-site/proof/kv3_pv_v12`: placed; `OT_TAIL_SITE copies 7009 of 7040 sited ... max_hop 441.3 um over_380 1205 core_crossing 0 in_halo 0`; no timing number yet.

**Root cause.** The pc `slg.vreq` pad needs depth 18 and the R8 strap carries 15, so instances of one type bind differently and the emit inventory changes. The rider's R8 table was built from an older bind. The PV writer-start bands are sized for the pre-split flop count.

**Fix (FABLE-FIX-KV-HG).**
1. One plan station on `slg.vreq` for pc_EN / pc_ES so no pad exceeds 15 (or a 5-bit strap for that bus only). Then the bind; G0 cannot see this class, so do not compose again before it.
2. Rebuild the rider R8 table from the passing bind; R8_STALE is a stale input, not a design error.
3. Run `band_capacity.py measure` (r681, all dies) on the 16 PV types and grow the writer-start and raw-reset bands in the same plan (HEAD needed 11 rects).
4. Hold all `^kv3_pv` items on KV-HG6: they have no tail copies, so their timing is the unsplit -1,197 class and 4 already fail the band.
5. Sited proof: read CTS reg-to-core on pv_v12. The 1,205 copies over 380 um need one more stage (K+1) in D22; decide that from the CTS number, not before.

### Lever 5. S81 generator rules: face pin row and relay reach

**Evidence.** Strip (R, STRIP 03:4x; V the 7 GRT rows): t25 has 595 `leafdn_i0` input regs in 12 full rows at y 4.32 to 7.29 on 598 pins in 124 um; 101 congested gcells at x 360 to 480, y 0 to 7; M6 568 + M8 347. Pilot `t25_ns2` (row stride 2) is running. Col (R, S81-TYPES-R3 23:21): poly relay hops 446 to 746 um in every col family (limit 405); col_h9_r0_p2 stops on 2 unfitted groups (252 / 206 um). 22 direct wires of 412 to 640 um (R, COORD brief; I found no generator post). Col after the marker fix (V): 10 rows running, none past place yet, 87 old place FAIL rows; col_h9_r2 reached sign-off with DRC 2, TT -46.87, hold_ff -62.46, `unconstrained` FAIL.

**Fix.**
1. FABLE-FIX-S81-STRIP: if `t25_ns2` gives GRT 0, make the stride a generator default from pins/um on the face window (no per-type plan rows), and apply to the 6 other types in one relaunch. t29 is the landing-ring variant (`cland_strip_rows`).
2. S81-TYPES-R3: gate `OT_RELAY_POLY` max hop over 405 um at generation, and insert stations so every poly hop is <= 405 um (+1 cycle each). The 22 direct wires get the same rule. Otherwise all 216 col types pass place and stop at CTS.
3. col_h9_r2: name the 2 DRCs and the unconstrained endpoints first; the 4.9 ps of TT is a CAPSKEW case.

### Lever 6. QC N4

**Evidence.** (R, TAIL-REPL 23:19; V the keep kit exists on epyc9) st_a split + keep + sited: CTS wns -901.4 -> -580.7, tns -160,939 -> -123,092; `rs_n_c_p` gone; new worst `u_r2.flt_bank_o -> u_r0.flt_bank_i` (819 to 1,000 um, R). (R, QC-PLAN-R3 03:15) N4: flt_bank 2 + 2 stations need `claude/qc-intra-stations-1118` (proof bind running, READY about 05:00); coll_core 43 taps + t115 split composing; tt_ctlm stage unowned.

**Fix.**
1. QC-PLAN-R3: N4 carries tail split + keep + sites, flt_bank stations and the tap rows in one event, as planned. Before the apply, place ONE st_a kit to CTS from the N4 bind and read wns; the acceptance is better than -250 with no path over 380 um unregistered.
2. COORD: tt_ctlm (31 cells in `u_core`, about 253 ps wire + 700 ps logic, R) needs an RTL stage and has no lane; without it those types fail N4 as they failed N3.
3. Routed QC rows already inside TT (V: sle_st_b_v1 +7.0 and -32.3, slw_st_b_v1 -25.4 and +9.5, slw_stm_v3 -4.8, slw_hc1 -41.1): their open item is internal hold; give them the r692 hold repair and the r583 ECO, not a rebuild.

### Lever 7. S81 svc hslice / mergex

**Evidence.** Headline 6. mergex_mm6 CTS hold repair: 36,993 endpoints under margin (R), 30.9 k buffers at +10.6 % area and still running (V).

**Root cause (P).** Tens of thousands of short paths cannot be a skew accident; the cores are built with a 30 ps margin on top of the 25 ps hold uncertainty in the SDC, so the repair is asked for 55 ps on every zero-logic stage.

**Fix (FABLE-FIX-S81-SVC2).**
1. Read hslice_mm6 at route end; sign it if DRC 0 and internal hold >= 0.
2. If mm6 fails: do not go to 50 ps (mm7 proved it does not fit). Check whether sign-off measures internal hold with the 25 ps uncertainty; if it does, build at margin 0 to 10 with r692 (worst + 1 ps floor, bounded re-repair), which removes most of the 30 k buffers and the route pressure that broke the mm4 ECO.
3. Count the endpoints per launch-capture clock-leaf pair in mm4; if a few leaf pairs carry most of the 1,092, a leaf-level clock pad is the ECO, not 1,092 data pads.

### Lever 8. KV hub types

**Evidence (V, wave).** kv3_hub_Wo 406,241 cells, kv3_hub_C 773,818: `OT_NATIVE_CELL_CAP SPLIT-NEEDED`. kv3_hub_Wi: `FAIL_PREFLOOR kit_preflight PROVISIONAL[qkd_hr_core_order, _peer, _prompt, qkd_hr_ingest_eng :routed]` and 1.155 M cells (R).

**Fix.** Waive hub_Wo (1.5 % over; QC signed 351 k and r696 waived 500 k). hub_C and hub_Wi are in the range where every past run failed (0.53 to 1.31 M): split on signed ring masters plus dly cores as KV-HUBWO-SPLIT measured for hub_Wo (rows exist for D23; 419,971 -> 199,876 synth cells). hub_Wi also needs its four qkd_hr cores signed, not routed-provisional. These belong in D23, not in D22.

## 2. Evidence I opened this round

| item | file | result |
|---|---|---|
| failure_breakdown 03:14 | intel2 | S81 42/394, HEAD 23/26, QC 24/130, KV 6/56 (unchanged since 23:10) |
| strip route verdicts | intel2 `autopilot/kit_wave_stages.tsv`; epyc8 / epyc10 / intel1 / epyc2 kits `FAIL_POSTCTS`, `tt_setup_repair_grt.log`, t50 `4_cts_final.rpt`, `config.mk`, `1_synth_odb.v` | lever 1 |
| hd_serdes four forms | epyc10 `fable-fix-head-sd9h/*/hd_serdes/{grt_policy.json,signoff_fable/signoff.json,run_route.log}` | lever 3 table |
| GRT vs routed, 85 kit pairs | epyc7 / epyc9 / epyc10 wave kits, `grt_policy.json` + later `signoff.json` | headline 2 |
| lep_pair vE28 | epyc9 `head-lep0n-opus/lep_ve28/kit/.../signoff/signoff.json` | lever 2 |
| hd_lep0N p2, hd_mesh mesh_w1 | epyc9 `4_cts_final.rpt`; `4_1_cts.tmp.log` | -379.62 at CTS; in CTS |
| KV D22s, rider | epyc7 `kv-hg-opus/d22s/gate/gate.out`, `kv-pv-rider/gate3/gate.out` | lever 4 |
| KV PV kit | epyc7 KV-HG6 `kv3_pv_v6/attempt_5` bound RTL | 0 keep copies |
| KV sited proof | epyc9 `kv-hg-opus-site/proof/kv3_pv_v12/run_place.log` | OT_TAIL_SITE line; placed |
| svc reruns | epyc10 `fable-fix-s81-svc2/svc/build/{hslice_mm6,mergex_mm6}` | DRT; CTS hold repair |
| H17 census | epyc9 `fable-fix-s81-serdes2/drtx/census/` | 8 files present, not re-aggregated |
| VPW marker | intel2 `tree_switch_s81.json` | key gone; last VPW fail 00:32 |

## 3. Stop list (the 23:20 list stands, plus these)

1. S81 strip: no relaunch of the 14 SETUP_TRIAGE types on a plan without the XR stage and the core-pin reset relay. No gate-threshold change for them.
2. Serdes (both dies): no go / no-go from `grt_policy.json`. No new H-form or sd9 route before the clock ECO on the routed DBs in hand.
3. hd_serdes: no sd9pb2 follow-up (-92). No unchanged sd9pc2 route.
4. lep_pair vE28: no rebuild; ECO the routed DB. No hd_lep0N judgement from p2.
5. KV: no fourth D22 compose before the `slg.vreq` pad is 15 or less. No PV kit on KV-HG6. No cell waiver for hub_C or hub_Wi.
6. svc: no hslice or mergex run above 30 ps margin; no post-route data-pad ECO on a DB with more than about 100 negative ends.
7. Col: no mass launch before the 405 um hop rule is in the generator; the first col past place must be read at CTS.

## 4. Not checked

- Whether D8d (plan e291d6a8) carries the XR form or a reset relay at the core pins; lever 1 item 1 assumes not.
- The cause of the t15 estimate gap (-17.6 kit GRT against -350 gate estimate); the endpoint classes of 9 of the 14 strip kits (only last repair lines read).
- Whether sign-off internal hold includes the 25 ps SDC uncertainty (lever 7 rests on it).
- The 2 DRCs and the unconstrained endpoints of col_h9_r2. Any col kit past place. The col direct-wire generator (no post found).
- `t25_ns2` result. hslice_mm6 / mergex_mm6 final results.
- KV: the CLAND band logs themselves (wave lines only); pv_v12 timing after place; band fill numbers for PV.
- QC: every N3 route result beyond the six rows in the GRT/routed table; the N3 clock-chain proof; the intra-station proof bind.
- HEAD: hd_host_e route FAIL (GRT-0116 at 01:48 on NF15f) was not opened; the M8 per-instance shape test; die hold on real views (0 measured pairs on HEAD and S81).
- The H17 census numbers are FABLE-FIX-S81-SERDES2's; I confirmed the files, not the aggregation.

---

# FABLE-CLOSURE-STRATEGY 2026-11-17 23:20 PST (2320): delta on 21:20

Reviewer: FABLE-CLOSURE-STRATEGY-2320 (Fable). Read-only: no jobs launched, nothing killed or deleted. Technical PD only. HBM parked.
Gate (R-MINIMAL): DRC 0, routed TT >= -42 ps, internal reg-to-reg FF hold >= 0, die bind + LATCHECK.
Marking: **V** = I opened the log or file this round (23:08 to 23:16 PST). **R** = reported by the named lane, not opened. **P** = my proposal or estimate.
Signed (failure_breakdown 23:10): S81 42/394, HEAD 23/26, QC 24/130, KV 6/56. No type signed on S81, QC or KV in the last 4 h (wave stages).

## 0. Headline

1. **S81 col still dies at GPL because the D7w tree-switch marker re-adds the key every tick (V).** `lanes/handoff/tree_switch_s81.json` still holds `OT_S81_VPW_BANK: "1"` at 23:10. Wave stages, last 4 h: 58 col rows FAIL `OT_VPW_BANK needs exactly two real VP SRAM macros, got 0`. The item_env move (6b15cc83) is correct but is overwritten in memory. Until the marker is edited, no col type (216, the largest family on any die) can show a real result.
2. **The S81 die GRT is now real and clean on the clock of record; the landed check still has no result (V).** epyc10 `s81-die-r3-proto/s81/d7w_eco`: ECOv3 clock, taps 21,687, missing 0, overflow 0 / 0 / 0 (M4 2.73 %, M5 4.04, M6 4.42, M7 2.15, M8 0.92, M9 0.79). Then `CHAIN_FAIL CA_CHAIN`: `count_align_plan.py: error: unrecognized arguments: --strap-window --min-lat-cycles 1` (the D7w tree tools predate the r4 recipe). The retry with newer tools (`ca_r4_noparts`) stops at `partition START origins require actual src_part/dst_part on every crossing`. `ca_r4/phase_ocv.log` is empty.
3. **No sited tail-copy result exists yet on either die (V).** KV: the keep + anchor proof (epyc9 scratch3 `kv-hg-opus-site/proof/kv3_pv_v12`) sources `tail_copy_anchor.tcl` at `face_flops.tcl:975`, 7,040 rows in `tail_copies.tsv`, but is still in 3_1 GPL (overflow 0.39); no `OT_TAIL_SITE` line yet. QC: `tail-repl-qc-kit/splitk` stops at 1_synth; nobody has placed a sited st_a.
4. **The tail split pushes KV PV over the cell limit (V).** Wave row kv3_pv_v3: `REFUSED: SPLIT-NEEDED: cells 467307 > 400000`. The split adds 19 to 27 k flops per PV type. S81 kv_leaf__t2 is refused the same way (estimate 462,435).
5. **hd_serdes: the structural fix is building (V).** epyc10 `fable-fix-head-sd9h`: `KP4_PW_BENCH PASS`; sd9h `config.mk` carries `ENC_PW16` + `SYN_PW8`, sd9pa carries `ENC_PPCYC`; both are in 3_1 GPL. sd9pb2 and sd9pc2 have a kit and no log yet.
6. **KV D22 is on its third plan (V).** try 2 (`d22gate/gate.out`): PRE FAIL, bind FAIL `pvw_0 column 5 ... flags [(88, 31), (88, 32)]`. Composer plan d22s 957d81e49c52: PRE PASS, G0 0 errors; first bind stopped on a manifest path, second bind started 06:52Z and has not reported.

## 1. Levers ranked by closure impact

| # | die | lever | unblocks | owner |
|---|---|---|---|---|
| 1 | S81 | Remove `OT_S81_VPW_BANK` from the tree-switch marker; land r676 (skip, nearest bank, FT snap); then read the next col stop classes | col 216 types; leaf t1 t7 t10 t13 t31 t45 t53 t74 t75 | S81-DIE-R3 (marker), FIX-S81-VPW, S81-TYPES-R3 |
| 2 | QC, KV | Sited tail copies, proven at CTS on st_a and pv_v12; PV cell waiver | QC st_a 11 types; KV PV 16 types | TAIL-REPL, FABLE-FIX-KV-HG |
| 3 | HEAD | hd_serdes PW16/PW8; lep_pair vE28 then hd_lep0N with related-pair windows; die clock off the granted M8 tracks | last 3 HEAD types = the die | FABLE-FIX-HEAD-SD9F, FABLE-FIX-HEAD-LEP0N, FABLE-DIE-HEAD, HEAD-PLAN-R4 |
| 4 | all | Close small routed hold misses with the post-route internal hold ECO, not with rebuilds | S81 svc hslice + mergex (then the svc shell, 2 svc families), hd_mesh, QC L2 | CAPSKEW-ECO, FABLE-FIX-S81-SVC2 |
| 5 | KV | D22s bind, with rider + siting folded in; pc 68 taps in D23 | PV 16, pc 6, hroot/pv_v2 band 5 | FABLE-FIX-KV-HG, KV-R3 |
| 6 | S81 | Serdes: H17 routed TT / hold read, then t13 + 10 on D8d | 11 serdes types | FABLE-FIX-S81-SERDES2 |
| 7 | S81 | Die landed check on ECOv3 with the r4 recipe; K refresh + clock site reservation as one clock event | die clock verdict; hold windows of every seam type | S81-DIE-R3, FABLE-DIE-S81 |
| 8 | S81 | Leaf and svc place/kit stops: HPWL (t37, kv_leaf t3), landing collectors missing, svc kit_rtl closure, relay_mid coverage | about 25 types | FABLE-FIX-S81-STRIP, S81-TYPES-R3, FABLE-FIX-S81-SVC2 |

QC N4 content (lever 7 of 21:20) is decided and TAKEN by QC-PLAN-R3 (R, 22:51); no new technical finding. QC has produced no N3 kit, so r650, the halo fix and the 40 ps margin are all still unmeasured.

### Lever 1. S81 col: the marker, then the next classes

**Evidence (V).**
- `tree_switch_s81.json`: `OT_S81_VPW_BANK": "1"` present at 23:10.
- Wave stages, last 4 h, S81 place FAIL 81: 58 `VPW_BANK ... got 0` (col), 9 `distance exceeds 100um` (leaf t1 t10 t13 t31 t45 t74 t75), 2 FT off-grid (t7 `82.9376 176.8544`, t53clb `9.3393 1032.3389`).
- Behind it, already visible on col: `OT_HOOK_COVERAGE relay_mid: 2 of 15 stations on the old fallback; unfitted group:even_hop_um u_bound.u_u_r0_u_y_rt_4a_0:252 u_bound.u_u_r0_u_y_rt_4b_0:206` on 4 col_h9_r0_p2 rows (22:45).

**Root cause.** A type-scoped opt-in sits in a die-scoped marker that `apply_tree_switches` re-applies each tick (R, FIX-S81-VPW 23:10; consistent with what I read). The relay_mid stop is a real design class: two relay groups in u_r0 have hops of 252 and 206 um that the even-hop fitter cannot place.

**Fix.**
1. S81-DIE-R3: re-write the marker without the key (`apply_reviewed_tree_marker`). Release hold `s81-col-vpw-1117` only after one regenerated col spec shows no key.
2. FIX-S81-VPW: r676 (`claude/fix-s81-vpw-ftsnap` @0d4134418d4, gate 67/67) reaches kits only through the S81 tools refresh, which r685 unblocks. Then relaunch t7, t10, t45, t53, t74, t75. Do not wait for the B4 plan row; the gen snap covers t7 and t53.
3. S81-TYPES-R3: for col_h9_r0_p2, add one relay station to each of `y_rt_4a` and `y_rt_4b` (252 -> 2 x 126, 206 -> 2 x 103; +1 cycle, pre-approved) or place the two groups by explicit sites. Do not disable the coverage check.
4. First col kit past GPL: confirm `OT_HOLD_FF_MARGIN = 25` in `config.mk` and read the CTS hold class line before 200 more launch.

### Lever 2. Sited tail copies (QC st_a, KV PV)

**Evidence.** Headline 3 and 4 (V). Unsited result stands: -901.39 -> -912.09 (V, 21:20). Yosys folds unkept copies: 3,155 of 7,040 flops on pv_v12, 35 of 140 on st_a (R). Keep module `ot_dp_dly_keep` READY @6fc8c4a3 with `types.<t>.sites` anchor rows (R).

**Fix.**
1. TAIL-REPL: place `splitk` to CTS now with the bind `sites` rows loaded FIRM by the r650 anchor path. This is the only QC proof and it is not running. Acceptance: `rs_n_c_p` wire under 150 ps, CTS wns better than -250.
2. FABLE-FIX-KV-HG: on the pv_v12 proof read the `OT_TAIL_SITE` line first (`copies N of 7040 sited`, `over_380`, `core_crossing`, `in_halo`). Any `core_crossing` > 0 is the same defect as the 29 detour hops: the anchor must use the routed path around kv3_pv_pair (M1 to M7 OBS). Then reg-to-core against -1,197.
3. COORD/KV: PV types cross 400 k only because of the pad flops (pv_v3 467,307). Waive as in r682; a partition split of a PV column is not wanted. If GPL then stalls for size, cut K: tail copies only on pads with spread over 380 um.
4. The 1,822 short chains on pv_v12 and the pad < K buses need plan stages regardless (R, CHAIN 22:28); they belong in D22s/D23, not in the split.

### Lever 3. HEAD: three types

**Evidence.**
- hd_serdes (R, SD9F 23:20; V on the build state): one stage holds an 8-level XOR rank; sd9f -105.6, sd9g3 -184.09 TT and hold -44.59 on the same family. PPCYC removes one level only.
- lep_pair vE28 (V, epyc9 `lep_ve28/kit/.../run_finish.log`, `postcts_gate_TT.log`): at 6_report (RCX 124,229 nets, IR 1.32 %); GRT-stage gate `pinreg mean 555.05 bound 450.00 ... setup_est 11.75 hold_est -203.93 PASS`. No sign-off file yet.
- hd_lep0N p2 diagnostic (V): 3_3 GPL iteration 210, overflow 0.42, past the band stage.
- Die (V, epyc10 `fable-die-head/base/head/nf15f_t2/CHAIN.log`): combo GRT TT/FF 0 / 0 / 0 at 0.37 %; TT intra +572.03, seam +656.04; seam contract +9.08 (W 90, need 80.92); intra kit-contract -76.07 (W 22, need 98.07, 44,945 pairs). Hold measured on 0 of 585,476 pairs.
- M8 lock (V `m8/lock.log`, R for the totals): tree2 clock legs sit on granted type tracks, e.g. hd_turn_a 150, hd_turn_b 175; 4,321 in 14 types.

**Fix.**
1. FABLE-FIX-HEAD-SD9F: sd9h (PW16 + PW8) is the build of record. At GRT read `tt_setup_repair_grt.log`; expect 5 to 6 levels in the window stage. Stop PPCYC/SPCYC forms once sd9h shows TT >= -42 at GRT; they cost a cycle and fix less.
2. FABLE-FIX-HEAD-LEP0N: the vE28 core has 555 ps mean insertion against a 450 bound. Take the four pair tap offsets from its `clock_contract.json` when it signs, not from the 450 target. Its -204 hold estimate is port-side; close internal hold with r583 as on hei3.
3. HEAD-PLAN-R4: one pack = plan_grown2 + vE28 views with `bb.v` default KCRED 28 + related-pair `per_port_ps` for hd_lep0N and hd_mesh (file in `lanes/handoff/`). The routed window need of lep0N is 163 ps whole-set; the 63 ps figure was placement RC and must not size anything.
4. FABLE-DIE-HEAD: t2g (die clock with granted tracks as M8 obstructions). Types do not re-sign.

### Lever 4. Small routed hold misses: ECO the routed DB

**Evidence.**
- (R, SVC2 22:5x; V that mm6, mm7 are at CTS and mergex_mm6 at floorplan at 23:11) hslice mm4, HM 30, guards off: +2.83 before route, -3.27 routed, -6.15 at sign-off, TT +175.5, DRC 0. mergex mm3b -6.93, TT +97.83.
- Precedent (R): lep_pair hei3 closed 7 -> 2 -> 1 -> 0 pads with r583; sd9f ECO2 kept DRC 0 with 0 cells moved; QC L2 hold closes with the post-route ECO (6 signed).

**Root cause.** Pre-route margin does not predict the routed result on these cores (loss 6 to 9 ps on hslice, 20 to 40 ps on QC). Each margin step costs a full rebuild.

**Fix.**
1. FABLE-FIX-S81-SVC2 (P): run `hold_eco_internal_run.py` (r583) on the routed hslice_mm4 and mergex_mm3b DBs now. Both have large TT room, so a handful of pads closes them. Keep mm6/mm7 running as the second form; sign whichever passes first.
2. CAPSKEW-ECO: make that ECO the default last step of every kit that ends DRC 0, TT >= -42, internal hold between -50 and 0. This is the flow form of what three lanes do by hand.
3. Still open from 21:20: the chunk cap (2,000 buffers x 3) that stopped hslice at 11.7 k endpoints; `OT_HOLD_CHUNK_BUF_PCT=0` is under test in mm6.

### Lever 5. KV D22s and D23

**Evidence (V).** Headline 6. Rider gate (epyc7 `kv-pv-rider/gate2`): G0 PASS twice, LATCHECK `no *_bound_top.sv (the bind did not finish emitting)`; gate3 started 07:00Z. Wave: KV has 8 kit_rtl and 5 gen RUNNING, 0 at place or route.

**Fix (FABLE-FIX-KV-HG).**
1. Gate d22s on strict bind before anything else; the two try-2 errors were both invisible to G0.
2. Fold the rider (29 detour hops, 11 keepout stations) into the same plan if its bind passes this hour; else a separate event. No PV kit before keep + siting + rider.
3. D23 pc: 32 added taps, 68 total, max load 1,200 on measured sinks (R, KV-R3). Add the three forwarded pc clocks over 1,200 (3,347 / 1,303 / 1,271) to the same event. Drop tap_spill.

### Lever 6. S81 serdes

**Evidence (V).** epyc9 H17 `6_report.tmp.log`: RCX `411739 nets finished` at 22:18; unit 476135 still alive at 23:13 in final STA; no numbers yet. 204 `STA-1652 ... pin cland_fwd_fclk_out_ft{0,1,2}_o:N not found` SPEF warnings (98 / 60 / 33, plus 13 on `cland_up`).

**Fix (FABLE-FIX-S81-SERDES2).**
1. When STA ends: routed TT and internal FF hold by class; that read decides whether TAP-GROUP-CAP-1 (6,502 flops on clk_t42) returns.
2. Check the four forwarded-clock nets for missing parasitics before trusting their arrival (P: the SPEF refers to nodes the netlist no longer has after the pad strip).
3. t13 + 10 build on D8d with r678 once h-form PASS is posted.

### Lever 7. S81 die clock event

**Evidence (V).** Headline 2. `sta_droop.log` (legacy margins, not the gate form): TT intra +173.41 (0 negative), seam -0.46 (6 negative), skew 409 / 623; kit contract needs 341 intra / 548 seam against W 40; 0 measured hold pairs.

**Fix (S81-DIE-R3).**
1. Run the landed check with the tools and inputs of the r4j run: `fable-die-s81/reach_codex/run_current_r4_ca_phase.sh` end to end on the d7w_eco proof. Do not pass its arguments to the D7w tree tools, and do not drop `--start-partition-origins`; give the crossings their `src_part/dst_part`.
2. Name the 6 negative seam pairs in the legacy read and show them in the nominal form.
3. D8d (plan e291d6a8) proceeds to bind/G0; the route does not need more cut moves. Then one clock event: in-place K refresh + `clock.reserved_sites_um` after a census of the 42 signed DBs.

### Lever 8. S81 leaf and svc stops

**Evidence (V, wave stages).**
- PLACE-HPWL: t37 `7.8347e6 = 1.40 x 5.5789e6`; kv_leaf__t3 `1.0557e7 = 1.32 x` (new).
- svc: 11 rows (svc_hi pvso_entry t1 t2, rs t1, svc_lo rs_w t1 ...) FAIL kit_rtl `RuntimeError: closure failed for .../items/<item>/`.
- t56: `native module must declare exactly one memory array`. gunit__t1 KIT_PREFLIGHT 5 issues; serdes__t14 4 issues.
- (R, S81-FIX-OPUS 22:22) t22 died at GPL: `OT_CLAND no mapped cells under u_cland_collect_rst_rl_188`, because `build_rebase.sh` drops `--clock-landing` for non-col types.

**Fix.**
1. FABLE-FIX-S81-STRIP: t37 and kv_leaf t3 are one class (timing-driven repair grows area by 78 % on t37 and the placer re-spreads). Image the attempt_8 3_3 DB; if the growth is in the re-slotted ft bundles, cap the TD repair (r496 0.25/0.30) for the family. No ratio change.
2. S81-TYPES-R3: `--clock-landing` for every type with landing rows, then t22 (the GRT calibration over the M5 cores is still unmeasured).
3. FABLE-FIX-S81-SVC2: the svc kit_rtl closure failures are the old soft svc types; they end only with the shell rows (4 of 6 cores signed). Keep them held rather than relaunched.

## 2. Evidence I opened this round

| item | file | result |
|---|---|---|
| failure_breakdown 23:10 | intel2 | S81 42/394, HEAD 23/26, QC 24/130, KV 6/56 |
| wave stages, last 4 h | intel2 `autopilot/kit_wave_stages.tsv` | S81 place FAIL 81 (58 VPW got 0, 9 VPW distance, 4 relay_mid coverage, 2 FT off-grid, 2 HPWL); S81 route RUNNING 41, QC 8, HEAD 10; KV 0 at place/route; SPLIT-NEEDED kv3_pv_v3 467,307 and S81 kv_leaf__t2 462,435 |
| VPW marker | intel2 `lanes/handoff/tree_switch_s81.json` | key still present 23:10 |
| S81 die proto | epyc10 `s81-die-r3-proto/s81/d7w_eco/{CHAIN.log,grt_st_TT/combo_TT.log,ca/ca_plan.log,ca_r4_noparts/ca_plan.log,sta_droop.log}` | GRT 0 overflow; CA_PLAN rc 2 (unrecognized arguments), retry ValueError; legacy STA numbers above |
| svc reruns | epyc10 `fable-fix-s81-svc2/svc/build/{hslice_mm6,hslice_mm7,mergex_mm6}` | 4_1_cts, 4_1_cts, 2_1_floorplan; no exit files |
| hd_serdes | epyc10 `fable-fix-head-sd9h/{bench_b.log,sd9h_gen,sd9pa_gen}` | bench PASS; defines as stated; both in 3_1 GPL |
| HEAD die | epyc10 `fable-die-head/base/head/nf15f_t2/{CHAIN.log,m8/lock.log}` | numbers in lever 3 |
| lep_pair vE28, hd_lep0N p2 | epyc9 `head-lep0n-opus/lep_ve28/kit/...`, `fable-fix-head-lep0n/p2/hd_lep0N/run_cts.log` | 6_report; GPL it 210 |
| H17 | epyc9 `fable-fix-s81-serdes2/H17/.../6_report.tmp.log` | RCX done, STA running, 204 SPEF warnings |
| KV sited proof | epyc9 scratch3 `kv-hg-opus-site/proof/kv3_pv_v12/{face_flops.tcl,tail_copies.tsv,run_place.log}` | anchor sourced; 3_1 GPL; no OT_TAIL_SITE yet |
| QC keep proof | epyc9 `/srv/opentallas-scratch/claude/tail-repl-qc-kit/splitk` | last log 1_synth; no place |
| KV D22 | epyc7 `kv-hg-opus/{d22gate,d22s/gate,d22s/gate_try1}/gate.out`, `kv-pv-rider/gate2/gate.out` | as headline 6 |

## 3. Stop list (the 21:20 list stands, plus these)

1. S81 col: no relaunch while `tree_switch_s81.json` carries the key. 58 fails in 4 h prove each one is wasted.
2. S81 die: do not read `STA_DROOP` (legacy margins) or `STA_LEGACY` as the landed verdict, and do not pass r4 CA arguments to the D7w tree tools.
3. S81 serdes: do not re-add TAP-GROUP-CAP-1 before the H17 routed timing. No new H17 route.
4. S81 svc: no further 30 ps margin rebuild of hslice (mm4 at HM 30, guards off, is -6.15 at sign-off). No relaunch of the soft svc types that fail kit_rtl closure.
5. S81 t37 / kv_leaf t3: no HPWL ratio change (branch 4eeee568 withdrawn; the real log is still 1.38 x). No t22 rebuild without `--clock-landing`.
6. HEAD: no CAPSKEW on sd9g3 (deficit 184 against about 130 per flop). Do not judge the die on `run_grt.sh` (signal-only runner over real views; the combo GRT is 0 / 0 / 0). Do not size lep0N windows from the 63 ps placement span.
7. QC: no partition split of st_a, st_b or hc (st_a is 54 k cells on the current event; 8 types waived by r682). No tt_ctlm region-only fix.
8. KV: no PV kit before keep + siting + rider. No pc judgement on tap_spill. No partition split of a PV column for the cell limit. Do not read the unsited pv_v12 run.
9. Tail split anywhere: no kit without the keep module; unkept copies fold back in synthesis.

## 4. Not checked

- H17 routed TT and hold (STA still running). The cause of the STA-1652 warnings (P).
- Any S81 route result of the 41 running rows; none finished in the window.
- hd_mesh route state and its numbers (R only). The t2g result. hd_lep0N CTS.
- sd9h past GPL; whether PW16/PW8 reach -42.
- KV d22s bind, rider gate3, the `OT_TAIL_SITE` line, the kv3_hg_v1 pilot.
- QC: N3 gate (blocked on a host disk, out of scope), the N3 clock-chain proof (queued), every N3 kit read.
- Whether r583 was already tried on hslice_mm4 or mergex_mm3b (lever 4 item 1 is P).
- The col_h9_r0_p3 place stop (`unclassified`, last GPL line only) and the gunit__t1 / serdes__t14 preflight issues.
- The relay_mid hop arithmetic in lever 1 item 3 is from the error text only; I did not open the plan rows.

---

# FABLE-CLOSURE-STRATEGY 2026-11-17 21:20 PST (2120): delta on 19:20

Reviewer: CLOSURE-STRATEGY-2120 (Opus, standing in for Fable, out of quota until 11-24). Read-only: no jobs launched, nothing killed or deleted. Technical PD only. HBM parked.
Gate (R-MINIMAL): DRC 0, routed TT >= -42 ps, internal reg-to-reg FF hold >= 0, die bind + LATCHECK.
Marking: **V** = I opened the log or file this round. **R** = reported by the named lane, not opened. **P** = my proposal or estimate.

## 0. Headline

1. **Splitting the pad tails does not help unless the copies are also sited (V).** QC st_a proof `sle_st_a_v1__cl67389ecd` (epyc9 `/srv/opentallas-scratch/claude/tail-repl-qc-kit/{base,split}`, `4_cts_final.rpt`): wns -901.39 -> -912.09, tns -160,939 -> -159,509. The new copy `u_pd2_x_hc1_i_0_u_r0_5` drives one load, `u_u_r0/rs_n_c_p[0]`, but still has 1,585 ps of wire at 5,017 ps slew. The KV pv_v12 split kit (epyc7 `fable-fix-kv-hg-chain/tailsplit/kit_split/kv3_pv_v12`, still in GPL) has no anchor or relay-site knob for the `u_pd*_c*` copies in `config.mk`, and its GPL already added 153,615 buffers on 40,945 nets. It will show the same result. This is now the largest lever: about 27 QC and KV types depend on it.
2. **S81 has no die GRT result, although both proto arms "RAN exit 0" (V).** On epyc10, in `s81-die-r3-proto/s81/{d7w,d8c}`, the kit built, then all three GRT arms died in under 1 s at `mk_combo_kv.py: ModuleNotFoundError: No module named 'die_sta'`, because `OT_DIE_PLAN_TOOLS` is unset. TTA_TT and TTA_FF have no `arr_*.txt`, and CHAIN_DONE still ran. The s_4N_L1 congestion question is unanswered.
3. **HEAD hd_lep0N p2 is dead at global place since 20:19 PST, and no lane has posted it (V).** `fable-fix-head-lep0n/p2/hd_lep0N/run_cts.log` stops with `OT_CLAND no mapped cells found under u_core.u.g_plw.g_s\[0\][/.].*`. The cells do exist in `1_synth_odb.v` (`\u_core.u.g_plw.g_s[0].u_st.q[0]$_DFF_PN0_`), so the CTS read HEAD-LEP0N-OPUS is waiting for will never come.
4. **H17 serdes reached DRC 0, fill and fillcell, then stopped at `6_report` (V):** `[ERROR ODB-0420] tmg_conn::detachTilePins: tilepin inside iterm` (final_report.tcl:13). The r644 in-pin segment ends inside the pin shape, and RCX/tmg_conn refuses it.
5. **Other technical place-stop classes in the last 12 h (V, `kit_wave_state.json`):**
   - S81 `OT_VPW_BANK distance exceeds 100um` on leaf t10, t45 and t74 (+1), up to attempt a9;
   - S81 `explicit FT site is not on a row/site` on t7 and t53;
   - `PLACE-HPWL` divergence on hd_tile (2.26x) and S81 leaf t37 (1.40x);
   - QC GPL-0305 on slw_st_b_v1__cle6023ec2;
   - `SPLIT-NEEDED` over 400 k cells on 7 QC types (hc0, hc2, st_b, 453 k to 487 k) and on kv3_hub_Wo (528 k).

## 1. Levers ranked by closure impact

| # | die | lever | unblocks | owner |
|---|---|---|---|---|
| 1 | QC, KV | Site the split tail copies at their consumer pins | QC st_a 11 types (44 hard rows); KV PV 16 types; PC bin-to-core | KV-HG-OPUS (r657 code), TAIL-REPL (st_a proof) |
| 2 | S81 | Get a real die GRT (fix the proto env), then D8d = re-sited stations + lattice snap + reset write-back + ist_rows | die route verdict; 8 G0 geometry ERRORs; col_h9_r1; t1/t15 serdes reset | S81-DIE-R3 |
| 3 | HEAD | hd_lep0N CLAND stage-row stop; lep_pair vE28 contract; related-pair windows | hd_lep0N, then hd_mesh and the last 3 HEAD types | HEAD-LEP0N-OPUS, HEAD-PLAN-R4 |
| 4 | all | Hold repair must reach the asked margin: no area-guard cut below the target, repair last, in the gate RC frame | S81 svc smc/hslice, S81 col family (236 items), QC N3 at 40 ps | CAPSKEW-ECO, S81-TYPES-R3 |
| 5 | S81 | Pad abut segment ends at the pin edge, not inside it (ODB-0420) | H17 sign-off, then 11 serdes types | S81-SERDES-GEN, S81-FIX-OPUS |
| 6 | S81 | Leaf place stops: VPW_BANK distance, FT site off row, CLAND band | about 8 to 10 leaf types | S81-TYPES-R3 |
| 7 | QC | N4 content: st_a flt_bank 2 stations, clk_t115 split, tt_ctlm pipe stage, coll_core offsets measured before apply, plus the >400 k splits | st_a, cbn_q00, tt_ctlm, coll family, 7 split types | QC-PLAN-R3, QC-N-OPUS, QC-TYPES-R3 |
| 8 | KV | D22 = 612 stations + facegrow + tap spill + tail split **with siting** | PV family, kv3_hroot/pv_v2/v2n band (5), pc pilot4 caps | KV-HG-OPUS, KV-R3 |

### Lever 1. Site the split tail copies (QC st_a, KV PV)

**Evidence (V).**
- In the st_a split kit, every `rs_n_c_p` end keeps its wire and slew: base 1,589 ps / 5,030 ps, split 1,585 ps / 5,017 ps.
- The bind and LEC are correct: 35 of 803 pads were split, giving 140 copies and +123 flops (R, TAIL-REPL 20:33).
- KV pv_v12: the split bind gives 7,044 copies and +19,382 flops (R). The kit has `PRE_DETAIL_PLACE_TCL = face_flops_release.tcl` only, with no anchor for the copies (V).

**Root cause.** r657 `land_pad_tail_split` changes the netlist only. GPL places each copy flop at the timing/wirelength optimum of its fan-in, which is the shared D-K trunk near the clock tap region (clk_t386 in st_a). The copy-to-pin hop stays at the full spread.

**Fix.**
1. KV-HG-OPUS: bind writes a sites record for every copy, at most 20 um from its consumer-core pin centroid (for QC st_a, the soft-leaf centroid from TAIL-REPL's 617dd4d9). The shared trunk stage goes at the pin-spread centroid.
2. The kit loads that record FIRM at 3_3, using the same anchor path as r650 `core_input_anchor.tcl`, so that both dies use one mechanism. A two-pass `type_relay_sites.py` regeneration is the slower fallback.
3. K from the r657 formula keeps each hop at or under `hop_um` 380.

**Acceptance.** On the st_a proof DB, `rs_n_c_p` wire under 150 ps and CTS wns better than -250. Then the same test on pv_v12 (before: reg-to-core -1,197).
4. TAIL-REPL runs the st_a proof as soon as the anchor exists. Do not wait for N4.

### Lever 2. S81 die GRT and D8d

**Evidence.**
- Lever-2 proto chain (V): `CHAIN.log` shows KIT 0, three GRT arms, each `mk.log` with `ModuleNotFoundError die_sta`, TTA 1 FileNotFoundError, CA_CHAIN 1, STA_DROOP 1, then `CHAIN_DONE`. `ot-run` reports exit 0. The same applies to d8c.
- D8c (R, FABLE-PD-S81-2100):
  - moved macros cover 2,296 ft station bits in 8 slots;
  - t1 `rst_rl_170` is gone and t15 `rst_rl_244` is 690 um away;
  - `ist_rows.py` and `cut_census.py` are not in the tree;
  - the 12 moved origins are off the 8.64 um lattice.

**Fix.**
1. S81-DIE-R3: in `proto_die.sh`, export `OT_DIE_PLAN_TOOLS=<tree>/tools/die_plan`. Make the chain exit non-zero when any GRT arm has no `arr_*.txt`. Rerun the D7w arm now; it is the applied plan and needs no D8.
2. Read three things from that run:
   - total overflow;
   - the gcell map over s_4N_L1 (y 19.77 to 21.0 mm), and over s_5S_L0, where the new worst cut segment (0.577) sits;
   - routed clock skew on related pairs.
3. D8d:
   - choose each core's dy so that it clears both the cut line and the station rows of that slot, as a multiple of 8.64 um;
   - otherwise re-site the 8 slots' stations with the generator;
   - build with r666 + gen4 (bind, then `local_reset_writeback.py`, then G0);
   - carry r652 `ist_rows` and r645 `cut_census`;
   - expect G0 with 0 geometry ERRORs, bind rc 0 and LATCHECK 873/873.
4. Run the D8d die GRT A/B against D7w before D8d applies. If the D7w die GRT shows s_4N_L1 below 100 % with no overflow, D8 is not needed for the route, and only the station and reset fixes matter.

### Lever 3. HEAD hd_lep0N

**Evidence (V).**
- p2 failed at 3_3 with the `OT_CLAND` error above. `landing_placement.tcl` lines 323 to 325 hold three `stage:plw_s0..s2` rows. The error is raised when `hit` stays 0 (line 2492).
- The cell names exist in the netlist, so either the escaped regex does not match the ODB names, or every flop was already in `cland_done` from an earlier entry (P: in that case the `continue` leaves `hit` at 0). Both are tool defects on a placement hint, not a plan fault.
- lep_pair vE28 (epyc9 `head-lep0n-opus/lep_ve28`) is in 5_1 GRT hold repair: `OT_HOLD_MM` SS setup -8.44 / FF hold -177.03 at margin 10. Insertion is 586 ps against a 450 target (R).
- tree2 die GRT is at extra iteration 11/50 with a 75 % derate on M4 to M7, so it is congested. Result not yet available.
- tree2 placement-RC clock STA: 195 lep0N taps span 62.9 ps TT (R, 20:22); the kit SDC gives each port a 89 to 96 ps window.

**Fix.**
1. HEAD-LEP0N-OPUS: in `landing_placement.tcl`, count already-placed members as a hit, or test the regex on the 3_2 ODB with `get_cells`. Relaunch p2 from 3_2, not from synth.
2. Replace the stale rp21x per-port windows with related-pair windows from tree2 (`die_sta_related --kit-window-related`). That is the only cure for the cross-tap hold class; more margin is not.
3. HEAD-PLAN-R4: re-derive the four pair-clock tap offsets from the vE28 `clock_contract.json` (about 586 ps) when it signs.
4. When tree2 GRT ends, post the overflow and the gcells for x 880 to 1160 and 1230 to 1472.
5. hd_tile PLACE-HPWL (2.26x) is the same divergence class as S81 t37 and QC cle6023ec2 (lever 6, item 3).

### Lever 4. Hold repair that reaches its target

**Evidence.**
- (R, S81-FIX-OPUS 20:30) smc mm3b r2r FF -10.62 and hslice -5.92. The ORFS hold guard cut HM from 30 to 19 (a projected +8.9 util points over the 8-point limit), then MET-FIRST repaired at HM 0 and stopped.
- (V, 19:2x) The same order problem exists on QC: on slw_sc_v2 the GRT hold repair ends at +0.15, then TT setup repair runs after it.
- (R) Col item_env `OT_HOLD_FF_MARGIN_PS` 10 replaces the die key (25) and the family floor (`_fam = None if _hm`).

**Fix.**
1. CAPSKEW-ECO:
   - when the area guard trips, lower the margin no further than the gate target (0 plus the 20 to 40 ps routed loss already measured), and log it;
   - never fall back to HM 0;
   - run the final hold pass after the setup repair, in the gate RC frame.
2. The mm4 runs (guards off) are the A/B for this. If they sign, make guards-off the svc default.
3. S81-TYPES-R3: the 10 -> 25 change on all col item_env rows. Confirm `OT_HOLD_FF_MARGIN = 25` in the first col `config.mk`.

### Lever 5. Serdes: ODB-0420 at finish

**Evidence (V).** H17 `6_report.log:27` shows ODB-0420 after `5_3_fillcell` and `6_1_fill` passed. Route was DRC 0 at iteration 5, with 1,089 pad nets carrying the r644 segment (R).

**Root cause.** The hook draws a wire whose endpoint lies inside the macro iterm's pin shape. tmg_conn, which RCX and `estimate_parasitics` use, rejects a tile pin inside an iterm.

**Fix (S81-SERDES-GEN).**
- Preferred: end the segment exactly on the pin boundary (the pin-edge point on the access layer), so tmg_conn sees a normal connection.
- Alternative: the strip-before-RCX hook in test, but it must not leave these nets "unrouted" for RCX.
- Prove it on the H17 `6_1_fill.odb` copy; do not route again.
- Then run t13 from the D6z generator (running, epyc10 unit 306723) with the fix, and the TAP-CAP-CENSUS on the first CTS of each of the 11 types.

### Lever 6. S81 leaf place stops

**Evidence (V).** In `autopilot/kit_wave/s81_ot_s81sl_leaf__t10_*/a9` the error is `OT_VPW_BANK distance exceeds100um at u_bound.u_u_lf4_u_vp_g_wr1_u_w.wa0[0]`. The same error appears on t45 and t74 at attempts a4 to a9. Leaf t7 and t53 stop on an FT site off a row (`ft3,1,0 82.9376 176.8544`).

**Root cause (P).**
- OT_S81_VPW_BANK (r-strip, opt-in) clusters the VPW flops beside "both real SRAMs" and fails hard when the bank is over 100 um away. In lf4 sub-leaves the SRAM it chooses is not in the same sub-leaf.
- The FT site x is not snapped to the 0.054 um site grid (82.9376 is off-grid).

**Fix (S81-TYPES-R3).**
1. VPW_BANK chooses the SRAM of the same `u_u_lfN` instance. Under R-MINIMAL, a bank over 100 um gives a WARN and the flops are left to GPL.
2. The generator snaps the FT station xy to the row/site grid.
3. The PLACE-HPWL stops (t37 1.40x, hd_tile 2.26x, QC cle6023ec2 GPL-0305) get one retry of the converged DB without region guides and with the r496 td 0.25/0.30 GPL setting, not another unchanged relaunch.

### Lever 7. QC N4 content

**Evidence (R, QC-N-OPUS 19:5x).**
- st_a `flt_bank` r2 -> r0 runs about 1,000 um. The r1 -> r0 (482 um) and r2 -> r1 / r3 -> r2 (516 um) pairs are also over 405 um.
- clk_t115 has two clusters 200 um apart (W 330 to 359 ps, E 321 to 326 ps). clk_t50 is one hop latch: no split.
- tt_ctlm: 949 ps of data over 31 cells, about 700 ps of it logic. The period is 833 ps.
- The coll_core and cbn_q00__cldbcda913 clock-chain inputs are gone from every host (R, QC-PLAN-R3 19:48).

**Fix.**
1. QC-PLAN-R3, in N4:
   - 2 stations on r2 -> r0;
   - check the three other flt_bank pairs for live nets and add stations where they are live;
   - split clk_t115 at about (600, 2390) and (820, 2470);
   - add 1 pipeline stage in tt_ctlm `u_core`. A region alone removes at most about 250 ps of wire against a 760 ps budget for 700 ps of logic, so it cannot close.
2. QC-N-OPUS: regenerate the clock-chain inputs from the N3 plan before N4 applies. coll_core is `clock.source`, so all 43 new taps start unmeasured.
3. QC-TYPES-R3 with QC-PLAN-R3: the 7 types over 400 k cells need a partition split in N4. The +1,032 head-pad flops on hc in N3 make them larger, not smaller.
4. Carry the halo fix `claude/qc-pad-chain-halo-1117` into N3 by a tools refresh before the cb kits generate. Without it the third HB4 and the pipe register sit inside the r648 strip.

### Lever 8. KV D22

**State (R, KV-HG-OPUS 20:48 to 21:07).** D22 is composed on plan f9eeac833487 with:
- 189 PV stage rows and 612 stations (+99.5 k flops, +612 cycles on 187 lanes);
- `tap_spill_um 600` on 3 kv3_pc_v1 (this answers pc pilot4: 10 taps over the 1,200 cap, clk_t4 at 9,664);
- 6 raw-branch band rows;
- tail split `^kv3_pv`.

The tools refresh is applied (src `_t2509079`, with r641 and r657). Facegrow fix b917b3be is READY for the writer-face band class (kv3_hroot, pv_v2, pv_v2n, pv_v6: 5 rows). The build is moving to epyc7 because epyc10 scratch is full.

**Fix.**
1. Add lever 1 siting before the D22 kits generate. Without it, D22 PV kits repeat the st_a -912 result.
2. Merge b917b3be into the D22 tools.
3. On the first pc kit, run `tap_cap_census.py` on its CTS log and expect no tap over 1,200.
4. kv3_hub_Wo (528 k) needs a split row in D22, or it stays REFUSED.

## 2. Evidence I opened this round

| item | file | result |
|---|---|---|
| QC st_a tail split | epyc9 `tail-repl-qc-kit/{base,split}/run/reports/.../4_cts_final.rpt` | wns -901.39 / -912.09; tns -160,939 / -159,509; copy `u_pd2_x_hc1_i_0_u_r0_5` -> `u_u_r0/rs_n_c_p[0]`, slew 5,017.47, wire 1,585.02 |
| KV split kit | epyc7 `fable-fix-kv-hg-chain/tailsplit/kit_split/kv3_pv_v12/{config.mk,3_3_place_gp.tmp.log}` | no copy anchor; RSZ-0038 153,615 buffers in 40,945 nets; still in GPL (unit 229217 active) |
| S81 die GRT proto | epyc10 `s81-die-r3-proto/s81/d7w/{CHAIN.log,grt_*/mk.log,tta_TT.log}` | `ModuleNotFoundError die_sta` in all 3 arms; no `arr_TT.txt`; chain reported done; d8c the same |
| hd_lep0N p2 | epyc9 `fable-fix-head-lep0n/p2/hd_lep0N/{run_cts.log,landing_placement.tcl,1_synth_odb.v}` | GPL stop at 04:19 UTC (20:19 PST), OT_CLAND `g_plw.g_s[0]`; flop `\u_core.u.g_plw.g_s[0].u_st.q[0]$_DFF_PN0_` present |
| lep_pair vE28 | epyc9 `head-lep0n-opus/lep_ve28/.../5_1_grt.tmp.log` | `OT_HOLD_MM` SS setup -8.44 / FF hold -177.03, margin 10, repair in progress |
| tree2 die GRT | epyc9 `head-die-r/nf15e_e10/hr4/clock_rs8/tree2/kit/grt/grt.log` | derate 75 % on M4 to M7, extra iteration 11/50 at 05:10 UTC |
| H17 | epyc9 `fable-fix-s81-serdes2/H17/.../6_report.log` | ODB-0420 tilepin inside iterm, after fill |
| wave FAIL rows, last 12 h | intel2 `autopilot/kit_wave_state.json` | technical: VPW_BANK 4 (S81), FT off-row 2, PLACE-HPWL 2, MPL-0041 2 (kv_leaf t1/t3), GRTM edge_outline 3 (c1x_C t7/t9, slw_sc_v2), MPL-0034 2 (st_a), GPL-0305 1, SPLIT-NEEDED 8, KV CLAND band 5 |
| failure_breakdown 21:10 | intel2 | signed S81 42/394, HEAD 23/26, QC 24/130, KV 6/56 |

## 3. Stop list (the 19:20 list stands, plus these items)

1. Do not relaunch any tail-split kit (QC st_a, KV PV, D22) without copy siting. It is proven a no-op: -901 -> -912.
2. Do not read an `ot-run ... exit 0` from `proto_die.sh` as a die GRT result. Check that `arr_*.txt` exists.
3. Do not change region-guide box size or registers per region for GPL-0305. It was proven not to be the lever (QC-TYPES-R3 19:44).
4. tt_ctlm: a region-only fix cannot close 700 ps of logic. No clk_t50 split (one hop latch).
5. HEAD: no tree re-cut for lep0N (63 ps whole-set spread). No hd_lep0N relaunch from synth. No hold margin increase.
6. H17: no new route attempt. The defect is at finish (ODB-0420); test the fix on the routed/fill ODB copy.
7. S81: no D8d apply without a die GRT number on D7w. No hand edit of `rst_rl_N`. No VPW_BANK relaunch unchanged (t10 is at a9).
8. QC N3 cb kits: no generation before the halo fix is in the tree.
9. svc: do not raise the hold margin again while the area guard still cuts it. Fix the guard first (lever 4).

## 4. Not checked

- The S81 D8d build. I found no d8d directory on epyc8 or on the hub.
- smc/hslice mm4 results.
- The N3 bind result.
- The kv3_pv_v12 split kit past GPL.
- The tree2 GRT overflow numbers.
- Whether the hd_lep0N CLAND miss is the regex or `cland_done` (both are P).
- The VPW_BANK root cause beyond the error text (P).
- The 4 KIT_PREFLIGHT issues on dsdv_slice_c1x_C (14 rows; the class may be technical).

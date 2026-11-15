# FABLE-PD-QCC-0740 (11-15 07:0x PST): QC cores sta_region_nb0_h17_n6_s7 / h18_n6_s7 / h18_n6_s8

## 0. Headline
The three cores are the WRONG HARDWARE for the plan of record. S4p's bound RTL no longer instantiates n6_s7 / n6_s8.
Signing them (the ECOs CORE-ROWS-1115 launched 06:44) does not unblock the 4 parents.

Region pad params in the bound RTL (HI_PAD, SKEW_N, SKEW_S; u_u_r0..r3 identical per type), epyc9 qc-s28-hf1c/bind/bind_s29q103<X>/rtl/<type>.sv:

| bind | sle pv4242de79 | sle pv30dda31f | slw cl9f076a5c | slw clf4365a62 |
|---|---|---|---|---|
| S3R3BR, S4KQ, S4NQ | 17,6,7 | 18,6,7 | 18,6,8 | 18,6,8 |
| S4PR, S4PQ (= S4p, adopted, wave plan sha e7aff46e) | 17,8,9 | 18,8,9 | 18,8,10 | 18,8,10 |
| S4Q2Q (next candidate) | 17,9,10 | 18,9,10 | 18,9,11 | 18,9,11 |

Plan zz_s29_qc103_s4p.json still says module sta_region_nb0_h1x_n6_s7/8 and param_wrap SKEW_N 6, SKEW_S 7/8 on all 16 rows: a stale copy of S3R3. Bind reports errors 0 because bind does not compare param_wrap; kit_rtl (param_wrap.wrap_bound) does, so the 4 parents will fail CLASS C again (the same failure DIE-QC-103 decided 11-14 19:05), or, if a view is registered by name, would carry a child 2 cycles short on both skew lines.
Rule seen in the data: SKEW_N and SKEW_S move by the cb-column cycles each station event adds (S4p +2, S4q2 +1 more); HI_PAD does not move.

## 1. Why never closed: procedural, three steps
1. Masters created 11-14 19:05 (DIE-QC-103 CLASS C, plan S3R3). Private kits by TL-QCSTAV2 (6 forms + 3 non-slang twins), never a wave core row, never in OWNERS -> "no kit-wave row", "unowned". Wave only says "requested"; it has no recipe for the pin-register wrapper, so it never launches them.
2. Kits finished 11-14 21:35-21:45 PST, all NOT SIGNED on FF hold only. TL-QCSTAV2's last post is 19:57; its stated next step (late ECO) was never run; the 23:5x limit killed the lane and it was not resumed. Only the no-LLM waiter kept logging (~/qcstav2-wait.log).
3. S4p adoption (11-15 ~05:50 PST) changed the bound params; nobody re-derived the plan rows or master names.
No design failure: zero route, DRC or setup failures on any finished form. Slang forms lost 1 h+ in yosys OPT_DFF (55:42 vs 4:08), one died there (ma_h17, exit 2).

Finished forms (epyc9 /srv/opentallas-scratch2/claude/tl-qcstav2):

| master | form | DRC | TT setup | FF hold nonport | FF insertion mean / spread |
|---|---|---|---|---|---|
| h17_n6_s7 | mb (dens .4, _ns) | 0 | +13.29 | -6.97 x19 | 214.4 / 34.1 |
| h18_n6_s7 | ma (dens .5, _ns) | 0 | +14.1 | -4.88 x3 | - |
| h18_n6_s8 | mb (dens .4, slang) | 0 | +21.4 | -2.74 x9 | - |
| sta_region_nb0 (signed sibling) | w (dens .5) | 0 | +15.39 | -3.12 -> +3.36 after 1 ECO (16 endpoints, 13 buffers, 2324 s) | - |

Same outline 162x162, same 494-pin file (kit plan_pins = S4p cores/st_a/sta_region_nb0_pins.json, 0 geometry diff), same 5 SRAM sites, same clock (250 / 202.5 target, M2-M5). The masters differ from the sibling only in delay depth: 2 sram_delay D values, 4 two-bit ring delays, 3 HI_PAD pad lines (17-18 stages x 64+ bits; sibling 0). Wire size is the same class; nothing physical differs.

## 2. Design risks, ranked
R1 (blocking, functional): wrong skew depth vs bound RTL. Cause: latency-matched constants baked into a hard master, re-derived at every column station event, plan rows not regenerated. Evidence: table in section 0.
  Fix now: build the masters the adopted bind instantiates (section 3).
  Fix in structure (next QC plan event, DIE-QC-103): SKEW_N / SKEW_S become strap inputs of one master (sram_delay read offset + ring-delay tap select, 4-5 bits each, strap_* tied at parent, the 10-25 ID-strap precedent). One master then serves all 4 types and every later station event; today each event costs 3 re-hardenings (~2.5 h + ECO each) and one WAIT-CHILD round for 4 types.
  Fix in flow (KIT-OPS-5, small): bind (or G0) errors when a hard_core param_wrap differs from the bound instance, and the master name is derived from the bound params. S4p passed bind with 16 stale rows.
R2 (near miss, not structural): FF hold on SRAM inputs. Worst path h17: u_sks.wp[4] -> INV -> SRAM w_addr_in[4], data 56.6 ps; SRAM clk arrives 221.6 vs launch flop 204.8 (+16.8 ps at FF: the SRAM branch is a 9-stage delay-buffer chain that tracks TT, not FF), + SRAM hold 21.85 + 25 uncertainty = need 63.6, have 56.6. The rest are zero-logic flop-to-flop pad stages (-2.5 .. -1.5). CTS hold repair hit its buffer cap twice (2001 + 2001 inserted, 10-190 endpoints left) with HOLD_SLACK_MARGIN 15; the routed loss on these pins is ~20 ps. One nonport hold ECO (margin 5) closes it: sibling proof above. Setup is not at risk: these paths have > 700 ps TT setup slack; TT WNS +13..+21 is elsewhere.
R3 (minor): kit pins.json y 161.958 vs plan 161.952 on the N face (6 nm). Same generator as the signed sibling, whose LEF compare was 494/494, 0 diff; repeat that LEF compare after sign-off.

## 3. Build recipe for CORE-ROWS-1115
Ask DIE-QC-103 first: which bind do the 4 parents take, S4p or S4q2. Build that set; if not answered in 15 min build both (6 kits, small).
- S4p set: sta_region_nb0_h17_n8_s9 (sle pv4242de79), h18_n8_s9 (sle pv30dda31f), h18_n8_s10 (slw cl9f076a5c + clf4365a62).
- S4q2 set: h17_n9_s10, h18_n9_s10, h18_n9_s11.
Per master, generator epyc9 tl-qcstav2/mk_regionm.py, only the three wrapper params change:
1. Wrapper = pin-register form w (flt_bank_i / flt_vld_i registered), core qfd_dv_s8_station_tail1_nb0_core, params ADD_LAT 7, BT_LAT 1, CE_MUT 0, JB 8, MUT 0, NB_IN_PAD 0, NB_PAD 0, PIN_IN 1, RD_PAD 0, SCALE_LAT 7, SKEW 14 + the three from the bound RTL. Take the instance text from the adopted bind rtl, not from the plan.
2. Floorplan: DIE 0 0 162 162, CORE 1.08 .. 160.92, pins = plan cores/st_a/sta_region_nb0_pins.json unchanged, 5 SRAM ot_sram_1r1w_32x64_m1 at (38.88,32.4) (91.152,32.4) (38.88,71.28) (91.152,71.28) (38.88,110.16) R0, halo 4.32, M2-M5.
3. PLACE_DENSITY 0.5 (form a; the signed sibling's value) and 0.4 as the parallel twin. Both routed DRC 0.
4. Frontend: default yosys, NOT slang (4 min vs 55 min+; _ns twins passed lint and face_guard 492/492).
5. Clock as the kit has it: insertion 250 TT / 202.5 FF, CTS_ARGS -sink_clustering_enable -repair_clock_nets -delay_buffer_derate 0.5, macro_cts_cluster (2 pins, 40 um), OT_HOLD_MM 1.
6. Hold: expect FF -3..-7 on <= 20 nonport endpoints after route. Queue the late ECO in the same script, no human step: eco_loop.py run --from route --hold-margin 5 --strict-one-pass --lec, OT_HOLD_REPAIR_SCOPE=nonport (your core-rows-1115/eco.sh). ~2.5 h build + ~40 min ECO.
   Parallel form to skip the ECO: HOLD_SLACK_MARGIN 25 (was 15) on one twin per master. Untested; first to sign wins.
7. After sign-off: LEF pin compare vs plan (494 pins), archive AGIdock + rtx-pro, AUTO-RESIGN row, prov_view_sources under the NEW master name on all hosts (no host pin).
8. Plan side (DIE-QC-103 / KIT-OPS-5): the 16 hard_core rows of the 4 st_a_v2 types take the new module name and params, as a rows-only delta. Without it the parents fail kit_rtl.
Running n6_s7/8 ECOs: let them finish (they prove the recipe on these masters), but do not register views or AUTO-RESIGN rows for them as S4p children. They only count if the die returns to a bind with 6/7/8.

## 4. Not checked
- No what-if run. HOLD_SLACK_MARGIN 25 and the strap form are proposals, not measured.
- I did not confirm from wave files which bind dir the parent kits read; "S4p = S29Q103S4PQ" is from the DIE-QC-103 adoption post. S4Q2Q values are from a bind still under review.
- The three unfinished slang forms (mb_h18_s7, ma_h18_s8, ma_h17): cause of stop not examined beyond ma_h17 (yosys exit 2).

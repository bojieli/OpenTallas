# FABLE-RC-QC handoff (Fable 5.2; independent reviewer, QC die only; RE-STARTED 11-23 19:22 PST as split of FABLE-RC-ALL)
Briefs: localhost scratchpad split_brief.txt, rules.txt, resume_1123b.txt. Parent: lanes/handoff/FABLE-RC-ALL.md + FABLE-RC-ALL-KV-QC-HANDOVER.md. Read-only except posts. Local notes: scratchpad/fablercqc (waiter wait_qc.sh, state file st).
## HANDED TO FABLE-RC-QC-SU (COORD order, 11-23 ~20:55 PST): SU/ST families (slw_su*, sle_su*, slw_st*, sle_st*, st_a)
State at handover (my posts: lanes/posts/FABLE-RC-QC.md; hub shas in brackets):
- Plans: C1b 62ce8aba0292 strict FAIL 1 (sle_su_c.x_ctl_o: writer START stage 6 raw reset rr_t85 drives an output port; SU2R retap renumbered reset leaves; same stage on x_su_l0_stm_o / x_su_l1_stm_o). C1c 3b12251bfd6c = C1b + 517 y values x 3 su_c types only (my diff, db6d77c0); G0 PASS 0 errors (epyc7 QC-ALLFIX/cE/g0/g0_report.json). SU2R-FIX3 in work (QC-ALLFIX-SU); rebind = C1d in a fresh dir, strict = FIX3 + ~80 min. C1-noSU 12b66c0e4829 (no SU rows) strict on epyc7 cC ETA ~21:50: its stm/sc probes read the PRE-SU2R form = baseline only, no credit to SU2R rows.
- My open condition on SU2R [c6caf013]: it failed 3 checks in sequence (band overlap, bit column over macro, reset relay on port). Before FIX3 is accepted: LAND-CAP + G0 + scoped strict bind on all 21 SU2R types in ONE helper pass, every finding listed; explain why only sle_su_c errored and not the two slw_su_c types.
- 42 in-core lane stations have NO row [eadf2a98]: c_*_bn_00__rsn#2-#4 at y 10534/10873/11252 inside sl_*_su_l1/u_lane4..7, all 12 columns; SU2R does not move them (parent handover line was wrong). Release needs (a) a die row moving them to the street, or (b) RSN r2 probe proof: final GRT clean + placed station flops outside the u_lane macro outlines. Until then all 4 su_l1 types held (cl5ea486db, clc6d66f5b, slw cla2a78701, clcc9d0155).
- RSN probe r2 (QC-RSN-PROBE; sle_su_l1__cl5ea486db, epyc8 private/QC-V4/sle_su_l1__cl5ea486db_1123172918): CTS post-hook +90.09, 20 FLT stations sited, 0 missing; GRT was in hold repair (32954 FF hold endpoints pre-repair). Hold lift needs final 5_1_grt db >= -42 + internal FF hold >= 0.
- st_a [7cd4d90f]: C4 kit slw_st_a_v2__clf4365a62 (epyc8 private/QC-V4/..._1123161122): x5 ACCEPTED (0 DPL-0033, 0 GRT-0273, overflow 0). TT -59.92 / TNS -698.7 = rc97 path u_btab g_read[0].q[1] -> u_u_r0/bt_q_p[1] (66 ps clk-q + 553 ps wire, 13 repeaters; launch clock 411, region effective 338 vs 250). rc96 b_tw landing +43.15. No rc97 row before C2 (~02:00): all 11 st_a held; asked for an endpoint census on that db (not received). Region taps 338-353 vs target 250: read with the rc97 arc.
- Other carried conditions (verdict d5c8db75): rc104 slw_su_l1 x470-520 column < 90 % at GRT; su_c placement BAD (1.029/1.001/0.942) until the SU2R form places clean; SUC-Q0 stage-0 legs 434 -> 171..390 um to be read at CTS.
- Owed to the reviewer: su_c over-core census (all bit sites/stations/bands vs all cores, B2/C1b/C1c); C1c/C1d whole-die render (die png + streets.png); slw_su_l1 station-regen (STATION-1BIT, 13 fw/su_l1 types) renders + OT_ISTATIONS missing:0; QC-OPEN-SU probes: su_c x3, stm x3, sc x3.
- V4 hold set stays with FABLE-RC-QC (46 items, checked c6caf013); SU/ST release proposals go to FABLE-RC-QC-SU, who tells me so the hold set stays consistent.
FABLE-RC-QC keeps: sle_ctl (SLECTL-RP-SEL, SLECTL-CLKENTRY-SEAT, LANDCORE-SWEEP, PAD-LAUNCH), tt_ctlm (QC-TTC-RETIME), cb/cbn/cbf, coll_core, glue (QC-GLUE), fw/fe, V4 hold set.

## Jobs
1 V4 apply ~21:00 (QC-V4, apply_after_seal): check APPLIED hold set = 46 incl sle_su_l1__clc6d66f5b vs verdict d5c8db75 (8 hold groups).
2 QC-ALLFIX C1b 62ce8aba0292 gates (strict ~21:45, epyc11 cD) = B2 + CBN-RSF-SEAT + SUC-Q0 + SU2R-FIX1. Plan file epyc7 QC-ALLFIX/rows_c/plan_c1_fix1.json.
3 QC-RSN-PROBE: r2 GRT read of sle_su_l1__cl5ea486db (epyc8 private/QC-V4/sle_su_l1__cl5ea486db_1123172918; CTS post-hook +90.09, 5 hold viol pre-repair) + hold-lift proposal (release >= -42 at final GRT db) + x5 counts.
4 Review round on C1b kits: whole-die render + streets + type renders/STA/GRT; full-cause census per finding; post to QC-ALLFIX.
5 QC-TTC-RETIME (not QC-TTC-DEPTH): 20:30 bmath_retime.py, 21:00 depth census cap 14 on all flat cores QC+S81, 23:30 seq equivalence, 00:30-02:00 tt_ctlm probe, 03:00 ROW-REBASED.
## Open conditions carried (d5c8db75)
rc96 >= -42 final GRT on cled3c1d7b/cl67389ecd/clf4365a62; rc97 narrow btab parent (C2 ~02:00); rc104 x470-520 column < 90 %; x5 0 DPL-0033; su_c placement BAD until new form places clean; coll_core 205 reset copies connected post-CTS; coll_s routed LEC; glue/cb carry_0924; 0 GRT-0273 per overflow-row probe; F16 transport bound; tt_ctlm HELD.
## Log
- 19:24 TAKING posted (634713dc).
- 19:30 CONFIRMED by own read: CBN-RSF-SEAT 59991d13f2c3 is in C1b (6 points 552.96 -> 570.24 in cbn_q00__cld7bf7197); posted 21a2f202. Asked QC-ALLFIX for points_in_core before/after at C1b G0 (A had 48; 156 other inherited over-core sites remain per the row text).

- 19:45-20:30 posts: TTC-RETIME P1/P2 accepted (loops bind; physical CTS probe ~22:00 with un-keep; fallback loop register drafted in parallel). C1b G0 FAIL 3 (su_c cws2 stage-3 over macro) -> C1c 3b12251bfd6c gate of record (my diff: only 517 y values x 3 su_c types); strict on epyc7 cE ETA ~21:25; stm/sc probes from C1b bind cC valid. DEPTH-MAP: only tt_ctlm has a depth row; my depth rulings for glue (reach: rom_qr->dh_prog_a, u_record pair skew -101, embed_code_q; QC-GLUE) and sle_ctl (u_ctl/u_tap hard macros; binders rp->su_c station reach, x_hc1_st_b_i half-cycle, u_tap rst_n -106; QC-SLECTL-RESYN) WITHDRAWN. st_a C4 kit own read: x5 accepted; -59.92 = rc97 path (btab g_read -> u_r0), st_a held till C2. V4 apply slipped: SEAL_OK ~21:20, APPLY ~21:35 (fallback try1 bind). Owed to me: su_c over-core census + die points_in_core count + C1c render; st_a endpoint census; 7 station probe renders.
- 20:55-22:20: SU/ST handed to FABLE-RC-QC-SU. V4 APPLIED 20:39, hold set 46 checked (c6caf013). C1-noSU 12b66c0e4829 = gate of record non-SU rows (strict 0, LAT 1922, G0 0, render read by me 83729e3b); 6 probes from epyc7 cC (cbn cld7bf7197, cbf cl1b5a6458, glue, native59, slw_hc1 cl3449ea95, sle_hc2 clcc5e3e61): read list in cb1b2d1f. sle_ctl: census 906 ends/4 groups; rows SLECTL-RP-SEL (relay-only probe 30c963888225, gen epyc8) + SLECTL-CLKENTRY-SEAT; combined plan 18d22fbde479 (C1c twin eea24acd048a), full strict epyc11 cS ~22:40 then probe; gate = 4 groups >= -42 CTS post-hook + GRT. tt_ctlm: my read 80c2feea: resynth+un-keep -185.46 / TNS -5817 (orig -1482), left = u_hr -> u_bout_native_cmd wire class -> output stage row; census + LEC owed by QC-TTC-RETIME. glue = reach (QC-GLUE), top-20 on C1-noSU probe owed. fw: 5 kits at/over 400k cap; FWCPL phase 1+2 accepted (target place <= 360k, est 344k), A/B maxwire 100/200 on epyc11; gate = cpl CTS probe < 400k after hold + TT >= -42. LANDCORE: ADV-LAND-REACH pushed a83197db4d (QC 2 flagged); cbn na/nb groups to be read on cbn probe. epyc7 disk 97 pct -> lane EPYC7-DISK (COORD). Waiter: scratchpad/fablercqc/wait_qc2.sh (skips SU/ST posts).
- 02:05 11-24 STATE (my families; SU/ST with FABLE-RC-QC-SU). Gate of record C1g 96cce77c1e2f (strict 0, LAT 1922, G0 0; bound on rt c660 = no open-input check; GENDRY rerun ~02:40). Next C1h = C1g + DEADIN (sle_ctl rp1 + 9 fw) + F16 dead/tie + sle_ctl re-key 0391dcd3b846 + RESETPUB sc, verdict ~05:10, must scan 0 open inputs. V4 hold set 46 unchanged.
  sle_ctl: cause = 15,996 plan seats keyed to u_pd chains replaced by r8 strap banks (unseated, 400-800 um). Fix = SEAT re-key row 0391dcd3b846 (PRE PASS; own strict on epyc2 ~03:30; probe by QC-SLECTL-RESYN; gate 695-end list, 0 < -42, unmatched 0). CLKENTRY-SEAT withdrawn (stale V2 census); RP-BANK/copies = fallback. Rule: census must name plan sha + DB + RC.
  tt_ctlm: row set = resynth + un-keep + PO fix + whole control-word replication (rep10 on intel1) + F16 (f16_obs dead on F5 form, init_u0 tie 0). LEC closed (X arm of u_76013 -> 0, neg control). Residual ROM rd_out -> u_16867: registered read if cone-at-ROM misses on 2 perturbations. Gate CTS >= -42 on 2 perturbations then GRT.
  cb: cbx x3 misses were a TOOL bug (tap_offset span over raw core-tap rows, W 510; fixed main e45d7e91b12): regenerate. cbn_q01: clock split 520 ps = far sinks + STB latest-sink padding (QC-CBX-CLOCK tool row: cap STB target, reassign far sinks). cbn_q00 cl622f65d2 gen death = CBN-TAP-STREET row cecdcb2a3b4b (bound). cbf_q11 = representative: timing clean at CTS, one congestion strip (n_y delay-chain regs y 2000-2100) -> row QC-CB-SPREAD 05:00, renders owed to me first. 8 cb probes ~04:30 on old matcher.
  fw: no setup issue; hold = IO boundary (contract); cell count 387k after FWCPL phase 1, 360k target withdrawn (others sign off at 385-441k); gate = FWCPL kit through route. Boundary hold fw<->stm measured on 2 exact pairs: TT positive, FF -10..-21 on x_fw_i/x_fw_p1_i -> HB4 row draft 20f6859d4f4e.
  fe: slw_fe_v2__clf110fab2 compose A final GRT clean (+114.71 / hold +34.32 / ovf 0): PROBE-PASS pending GRT-0273 count + seat counts; resume to sign-off (COORD agreed).
  coll_core: reset copies 206/206 clocked (functional stop cleared at CTS); setup -201 = 17 slow taps (same STB class) -> tap-split row 02:45-04:30. glue: reach (QC-GLUE), no read on C1-noSU probe yet.
  Die: reset hold needs 78 clk -> 128-clk boot contract (contract-only in C1h; QC-RSTCNT counter for C1i). Open-input check on main 85273876e25. TAPKEY-SITE re-keys name-keyed tap tables (05:30).
- 05:40 11-24 STATE (supersedes 02:05 where they differ). Gate of record C1h 894e6f21991f (strict 0 with open-input check, LAT 1922; PRE has ENTRYFOOT 76 + ROWS-NO-PROOF on WARN). Launch on C1h: 73 sign-off, 35 DRAFT types as probes (cb x16, coll_core grt; 18 probe-through), 9 held. C1i 3e46ebd69a97 = sle_ctl re-key + far-raw, sc far-raw, FWCPL-2 (9 fw), CBN-TAP; bind epyc9 ETA 06:45. C1j queue: tt_ctlm T=20 core + EXACT lane pads 19/19/19/17/17, sle_ctl hc1 station spread b8c397460805, coll_core 077419918995, QC-RSTCNT 9cb276998d14 (256-clk counter), cb delay-pipe seats, fwdclk repoint (measured form), SU rows.
  tt_ctlm = FUNCTIONAL FAIL on B1..C1i: core XPF 21 vs program 20 vs die lane 10. Fix (COORD + me): keep program/digest, core rebuilt at T=20 (43059362f4bf, bench PASS + 5 negatives, recipe fidelity proven), pad 5 lanes to program ages in C1j; ADV-CTLM-AGES must read 0. Open: per-lane reference (R_AG 13 vs 10), RTL->constructed-netlist LEC (needs register map), slice-side check. Timing rows (resynth+unkeep+PO fix+word replication+ROM lead 150+native_cmd port-rep) to be re-found on the new netlist by QC-TTC-R2. Token bench now on main e0ce58397587.
  sle_ctl: re-key in C1i; probe from 0391 bind running epyc10 (launched 04:16); RP-BANK A/B read -107 / 16 ends; hotspot bin x300-400 y300-400 = hc1_o_0 station on one line -> spread row (C1j). B_TW bank spread row IS applied (my not-applied claim withdrawn).
  cb: ONE structural row for 3 symptoms (cbf_q11 strip, cbn_q01 520 ps split, slow taps) = seat the bound ot_dp_dly pipes (196,982 flops, 13 types) via type_relay_sites.py --pipes (main 3cba4dba); owner QC-CB-SPREAD. cbx x3: first valid kits now (span fix e45d7e91b12). cbf_q00 nb landing corner = separate congestion row. 6 cb probes running epyc11 (base, no pipe seats).
  coll_core: reset copies CLOSED at GRT; setup -127; row = TAP-SPLIT + pf_q/warm seats + main RDPIPE+XEPRE defines (existing unapplied main fix; +1 on f_md accepted with conditions), ROW-READY 07:00.
  fe/hc/glue: slw_fe_v2__clf110fab2 and sle_hc2__clcc5e3e61 clean at final GRT (confirm lines GRT-0273 + seats still owed); glue -19.15 at GRT (inside gate) but functionally unproven: LANEAGE-SWEEP 7 baked-constant mismatches (sys_face n59_land, CS_RXV/X3S, d2d TXDP, native59 LAND_EDGES 8 vs 18, su_mem9) triage overdue; native59 pulled only if REAL.
  fw: FWCPL-2 380k accepted as is (no 360k target, no station lane); boundary hold row v2 a471e0ccfff2 (contract both ends + HB4 x2 on 2 stm buses + cbf_q11 entry delay).
  Tool classes found tonight: tap_offset span bug (fixed), STB/TAPBAL overshoot (fixed c0b6e2d0340), name/index-keyed tap tables (ref_site.py reindex 25a62dbff7), open inputs at bind (85273876e25), unseated plan keys (matcher b68b5d03 + re-key), scoped-bind throughput (open), lane-age constants (LANEAGE-SWEEP), tree rtl lags main.
---- predecessor (pre-05:50) content below ----
# FABLE-RC-QC handoff (Fable 5.2; independent root-cause review, die QC; started 11-23 00:42 PST)

Brief: scratchpad fable_review_brief.txt + rules.txt + visual_brief.txt + visual_brief2.txt. Order: st_a, cb, su_l1/su_c, coll, hc/st_b. QC V4 cut ~06:00; V4 gaps due 05:00.

## State (01:3x PST; first-pass posts went out about 01:20, not 02:30)
- First pass done on all five families. Rows: lanes/FABLE-RC-REVIEW.tsv (20 QC rows). Counts: COVERED 8, PARTIAL 7, MISSED 4, WRONG-CAUSE 1.
- Posts sent to VIS-QC, FAM-QC-SLWSLE-R1, FAM-QC-HCST-R3, FAM-QC-CB-R4, OPUS-FIX-QC-COLL-R3, OPUS-FIX-QC-V4-R2, QC-PLAN-R13 (see lanes/posts/FABLE-RC-QC.md). Replies due within 1 h.
- Not reviewed: fe/fw, stm, ctl, glue, native59 (outside the given order).

## Tools and data
- Lane dir on every gen host: /srv/opentallas-scratch2/claude/fable-rc-qc/{tools,out}. tools: tx_one.sh WAVE/ITEM (text summary: macros, pins, cell groups, overflow clusters, timing classes), cong.py, paths.py, macs.py, rc_batch.sh (render via vism_render.py), find2.sh.
- Renders done: epyc2 out/ (cled3c1d7b, pv88773f93). Queued renders on epyc7/epyc10 wait behind the ot-heavy load cap (load 147 >= 115); background task b02pi0ers, --max-wait 7200.
- Local copies: scratchpad fable-rc-qc/png and out.

## Method notes
- Kit macro seats are readable without a DB: gen/<type>/macro_place.tcl and landing_placement.tcl.
- V2 = wave s29q103S4Q9N46R6V2 (has GRT data); V3 = ...R6V3 (st_a fails at 3_3 on the CLAND band).
- A grep for VISQC-DIE-1 showed me two VIS-QC summary posts before my own st_a reading; the per-type numbers above are from my own reports.

## Next
1. Collect replies; update the TSV verdicts when a row or a reason arrives.
2. Read the epyc7/epyc10 renders when admitted (clf4365a62, pvd2ec7769, pv4242de79, cl67389ecd).
3. Cross-check lanes/HOTSPOT-GAPS.tsv when HOTSPOT-CENSUS lands it.
4. Second report to COORD when every gap has an owner row or a reason.

## 01:3x update
- epyc7/epyc10 renders done and READ (clf4365a62, pvd2ec7769, pv4242de79): they confirm the st_a clusters. pvd2/pv42: (420-480,235-245) at the u_r0 NE corner / g_btb slit and (450-545,445-490) on g_btb[1]. clf4: (300-600,50-110) under the horizontal b_hw landing, plus (400-440,400-425) and (430-445,270-280).
- Reply FAM-QC-SLWSLE-R1 01:14: sle_hc1 pve230954c is SIGNED on its V2 attempt (no relaunch needed; my 'needs an owner' note is withdrawn). b_tw broadcast stations: SLWSLE takes them (asbuilt intra_stations). btab read stage is RTL in qfd_dv_s8x_btab plus a latency contract: NO OWNER yet. Pin registers measured TT mean 323 vs bound 280 (+43), FF 249 vs 227 (+22), n 5516. E-corridor seat check pending.
- Still no reply from VIS-QC, FAM-QC-CB-R4, OPUS-FIX-QC-COLL-R3, QC-PLAN-R13 (due about 02:20).

## 01:30 COORD RESUME (5-h limit cut ~01:17; Codex covered to 01:3x)
- CODEX-LOG handoff 01:19: COORD ruling for st_a = use STA-1b placement for the route wall, st_a wave rows stay held pending reviewed proof; the SRAM -> g_read arc is inside a closed core, so price an internal zero-cycle g_read re-seat BEFORE a +1-cycle successor (this supersedes my 'HCST takes +1 cycle' suggestion); b_tw slices mapped for bound intra_stations in parallel.
- COORD: QC-DIE-SEAT-1 ADOPTED, VISQC-DIE-1 DROPPED.
- No ot-run of mine is live (all renders done, self-reviewed 01:28). Nothing to relaunch.
- Reply FAM-QC-SLWSLE-R1 01:27: su_l1 hold -> V5 one-tap row after VIS-QC posts the SEAT-1 tap rule; su_l1 E channel -> V5 ft_slot re-site after the cl5ea486db GRT read (~03:00); su_c -> cap2b bind-clean, SU-2 with VIS-QC, pad-leaf stays optional. None is a built row yet.
- DUE 03:30: read replies (grep FABLE-RC-QC / RC-GAP in lanes/COORD-REVIEW-QUEUE.md), update verdicts in lanes/FABLE-RC-REVIEW.tsv, report the gaps still uncovered to COORD. Background waiter armed locally until 03:30.

## 02:25 FIX-LEDGER reasons (agent acd269758d3b62a53; lanes/DIE-FIX-LEDGER.tsv)
- rc97 + hg-QC-REACH: NOT accepted as closed (about -49 left < -42 gate, STA-1b unmeasured); deferral out of V4 accepted; stays OPEN, owner FAM-QC-HCST-R3.
- rc112: accepted. hg-QC-REPAIR-CAP: accepted as symptom, linked to SEAT-1c; DPL-0033 after repair on 4 st_a kits goes to the STA-1b row. hg-QC-CLOCK-NDR-DROP: accepted, probe must show 0 GRT-0273.
- V4 cut is now stated as 14:00 by FIX-LEDGER.
- 03:30 reply check still due; the local waiter may not have survived, so run it by hand.

## 02:55 COORD flow review: no V5 / no next event (post DEFERRAL-VERDICTS)
- Rejected deferrals: ledger row 71 su_l1 ft_slot re-site (SLWSLE) -> V4 row; row 69 cb landing bands (CB-R4/VIS-QC) -> V4 rows, gate by 13:00; slw_fe_v2 clf110fab2 core partition (V4-R2 745b777) -> not accepted without a measured TT setup >= -42 on the leaf-to-logic paths.
- QC no-launch 86 min: autopilot alive; 27 owner holds (17 cb, 6 st_a, 2 su_c, coll_core, sle_su_c). Needs owner: slw_fe_v1 cl08d14f0d stale 'kit busy'; phy_serdes_b ITEM-SYNC rc=2; slw_st_a_v1 pvdf8e5ca4 unheld and failing on CLAND band.
- Gate for all V4 rows: 13:00. Still due: 03:30 reply check + uncovered-gap report.
- 03:05 x7 slw_fe_v2 clf110fab2: ACCEPTED as REASONED on place timing (+6.2 worst, verified on epyc10 R6V3); reopen only if 4_cts_post_hook shows < -42 on a u_core leaf path.
- 03:10 rc97 ruling: CONDITIONAL ACCEPT for the cut (V4 cuts 14:00 with st_a held); hold releases on one measured SRAM->g_read setup >= -42 at 4_cts_post_hook on pvd2ec7769/pv88773f93/pv4242de79, from STA-1b+SEAT-1c probe (by 13:00) or btab_s4r harden. No measured REASON from HCST-R3 found on the hub.
- 03:15 rc97 clarified: for arm (b) the tile-level SRAM->q setup >= -42 in the btab_s4r kit 4_cts_post_hook releases the st_a hold, given strict bind + LATCHECK with the consumer patch; arm (a) keeps the type-level number.

## 03:30 reply check done (RC-REPORT-2 posted)
- Ledger QC: 4 REASONED, 12 ROW-DRAFT, 5 OPEN. Uncovered: rc97/hg-REACH (HCST-R3, unmeasured), rc96 b_tw (SLWSLE, no row/ETA), rc104+rc103 su_l1 rows not built (SLWSLE, c4 08:00), x5 DPL-0033 rerun, rc98 SEAT-1c tap row ungated.
- NEXT: (1) cross-check lanes/HOTSPOT-GAPS.tsv per-type QC items vs my rows; (2) re-check ledger ~08:00 (c4 start, sta1c bind) and ~12:30 before the 13:00 gate; (3) update verdict column in lanes/FABLE-RC-REVIEW.tsv as rows gate.
- 03:40 rc96: FIX-QC-STA-BTW measured -218.27 at final GRT on cled3c1d7b (1073 um, 17 buf); form STA-BTW-0 (0 cycles) to be probed; PASS needs >= -42 at final GRT on cled3c1d7b, both hops shown (each ~520 um > 405), and siblings checked. Review row corrected.
- 03:45 rc96: per-hop estimate (hub 01fb016) agreed: hops 529/527 um close without stations (bank->r3 slack = 365 - bank tap). Acceptance still on the probe (>= -42 at final GRT on cled3c1d7b, cl67389ecd, clf4365a62), bank tap to be reported; re-read if SEAT-1c lands.

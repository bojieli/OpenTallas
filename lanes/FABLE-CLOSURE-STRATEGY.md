# FABLE-CLOSURE-STRATEGY 2026-11-16 09:25 PST (FABLE-CLOSURE-1143): the fixes are composed; three of them are stuck on one technical error each, and one release gate reads 50-90 ps optimistic

Read-only review by FABLE-CLOSURE-1143 (Fable). Technical physical design only. HBM parked. Nothing launched, stopped or changed.
Read: FABLE-CLOSURE-STRATEGY 07:25 (0943), FABLE-DIE-HEAD / -S81 / -QC, FABLE-PD-S81-F2s3, the FABLE-DIE-KV 07:50 post
(there is no lanes/FABLE-DIE-KV.md), handoffs FABLE-FIX-{HEAD-TIMING, QC-CBGLUE, QC-KNEE-HC, S81-COLTAP, S81-CONG, S81-SERDES,
S81-SVC, KV-PVHUB}, S81-BKSEL-O, HEAD-SERDES-O, HEAD-TYPES-O, M7PIN-STRIPE-1116, S81-IFN0-HALVES, KV-PVHG-O, queue lines
07:25-09:12, `failure_breakdown.py` 09:10.
MEASURED = read by me 09:10-09:25 (plan JSON, bind logs, tool source; no odb opened, no STA run). REPORTED = lane post. INFERENCE is marked.

Signed types 07:13 -> 09:10: S81 41 -> 41 of 394, HEAD 20 -> 20 of 26, QC 7 -> 7 of 127 (+1 signed, count pending), KV 6 -> 6 of 56.
No technical class shrank in count. Three classes changed state from "cause unknown" to "fix composed".

## 0. Verdict

1. **The QC event cannot bind, and the retry in flight cannot fix it.** MEASURED: S4Q9DBQ2 and S4Q9DBQ3 (fe bump 2 and 3) both
   ended 16:59 UTC with the same `PARAM_REGEN W5: nb_od of region 0 is not the latest`, hcparam mismatches 48. The check is
   `nbo[r] = E[r] + delta(u_fup.l9_c[64r..64r+63])` with `nbo[0] == max` (qc_fabric_transport.py line 183). A uniform pin pad
   bump moves all eight regions together, so no fe or ctl value can pass. About 60 QC types wait on this one row.
2. **Two different plans are both called S4q9e.** MEASURED on epyc9: `fable-die-qc/delta/zz_s29_qc103_s4q9e.json` has reset
   leaves on coll_core / native59 / tt_ctlm and no glue stations; `fable-fix-qc-cbglue/delta/zz_s29_qc103_s4q9e.json` has the
   glue fault stations and no reset leaves on those three types. Binding either one drops the other.
3. **The post-CTS release gate under-reads.** Three reads today: hd_serdes sd6 CTS -26.55 -> GRT RC -112.45 (86 worse);
   hd_host_e he5 gate -44.86 -> routed -118.34 (73 worse); S81 col reset copies -100 CTS -> -151 routed (51 worse). The S81
   col waves (216 types) release on post-CTS TT >= -42.
4. **Lever E of 0943 was wrong** (my inference, refuted by M7PIN-STRIPE-1116 with odb numbers). The class is three small
   causes: 6 types by pin row, 1 by macro LEF, 1 ECO-session.
5. **S81 is one bind away on both halves** (F2s3: review ADOPT-OK, bind restarted 17:1x UTC with the bk_sel file). The first
   detail route of a ring-ff kit is still unread, 2 h after it was named the first read.

## 1. The 0943 levers: landed or not

| # | lever | landed? | class change, numbers |
|---|---|---|---|
| A | S81 adopt F2sv, then one delta | **PARTLY** | F2s2 (= F2sv + windows) adopted. F2s3 composed = strip rows t34 / t47 / t62 + col rows + reset copies + bk_sel file; review ADOPT-OK; bind not finished. serdes DPL fix PROVEN on F2sv: t13 0 violations in 4 m 59 s (was 233), FIRM ring cells 39,612 -> 9,237. svc: kit_rtl RC 0 with the memory closure on the v3 tree. Signed 41 -> 41 |
| B | S81 col F2s3, r2 read before bind | **PARTLY** | rows in F2s3 (372 swaps, 282 sequencer moves, tap lead 200, sequencer lead 100 on 132 types, reset copy_depth 3 on 216). The r2 evidence read is NOT possible before the bind (KIT_TOPOLOGY_BIND_STALE twice). IFN = 0 halves started (hw0 / he0 to GRT, no CTS number yet). 0 col types built |
| C | Sideband reach, one audit per die | **YES for the audits, NO for a bound fix** | QC: 1,142 FSTART flops audited, 128 on a shared reset in 9 types, 6 types get rows (65 flops over 405 um). HEAD: 6,400 hops audited, 122 over 405 um (hd_lep0N 85, hd_ctl 15, 22 raw relay hops in 10 types). S81: reset rows for 216 col types delivered. No kit has read any of these rows yet |
| D | QC S4q9c adopt, hc env, coll_n | **NO** | S4q9c / 9d: r8rc 0, LATCHECK 1921/1921, knee 0, G0 2 inherited, but BIND_RC 1 (verdict 1). hc TT env on 18 keys is in the wave; hc1 x2 placed on v2. coll_n a22 on v2: placed, GRT 0, in route |
| E | M7 scalar pins vs die-phase stripes | **REFUTED** | Rect Only = M6 PG pair under an 80-nm interior M7 pin with M8 obstructed: 4 / 4 failing pins, 0 / 109 passing. EOL = pin-width M7 OBS abutting the pin top in the u_epc LEF: 13 / 15 against 0 / 540. DRT-0206 = ECO session only. he6 (halo) cleared 3 spacing markers and left 29 EOL |
| F | HEAD timing | **PARTLY** | hd_serdes sd6 GRT RC -112.45: 55 u_out.bsrc endpoints, u_chn apply clk->q 400 ps + 480 ps of wire. sd7 = DOREG register on the 559-bit seam, from synth. hd_host_e: he4 -66.43 / he5 -118.34 / he6 -125.44, DRC 30 each. hd_host_w: ECO no gain (-80.96); hw4 CTS -11.93 after repair, routing |
| G | KV 7yhr + v25hv + k2r | **PARTLY** | 7yhr on v2: G0 0, strict bind 0, LATCHECK 2404/2404, kit_rtl RC 0 on 4 types, review no blocking finding; the gate's remaining kit_rtl / gen runs were in flight at 08:37. k2n gated; k2r at bind4. Not adopted; 0 KV kits on 7yhr |
| H | S81 strip congestion | **YES** | four types end GRT 0 / 0 / 0 with 0 NDR restarts: c_t34, c_t47, c_t62, c_t43b (ft5 only). t34 / t47 / t62 rows are in F2s3; t43 rows are READY (08:57) and not in F2s3. t75 / t8 / t28 open (b_t75 21 restarts) |

## 2. Levers now, ranked by types unblocked

| # | die | lever | unblocks | owner |
|---|---|---|---|---|
| 1 | S81 | col: F2s3 bind -> five pilots; release on the GRT-RC read; chain-flop sites for reset copies | 216 types | FABLE-FIX-S81-COLTAP, FABLE-DIE-S81, S81-IFN0-HALVES |
| 2 | S81 | non-col: F2s3 adopt; serdes only from a tree with f84ed61a70; read the first ring-ff detail route and the svc macro-gap GRT | about 137 (394 - 41 signed - 216 col), incl 16 svc, 11 serdes, strips | DIE-S81-92, FABLE-FIX-S81-SERDES / -SVC / -CONG |
| 3 | QC | W5 l9_c station row; ONE S4q9e | 34 knee + su_l0 + 3 PHY + 2 cbn_q00, 19 cb / glue, 3 reset types | FABLE-FIX-QC-KNEE-HC (event), FABLE-DIE-QC, FABLE-FIX-QC-CBGLUE |
| 4 | KV | adopt 7yhr; KV-HG1 = v25hv + k2r + the 13 START hops | 13 pv + 21 hg + 4 hub | FABLE-FIX-KV-PVHUB, KV-PVHG-O, FABLE-DIE-KV |
| 5 | all | gate calibration: decide on GRT RC with the die signal scale, never on post-CTS placement RC | every wave release; 216 col first | COORD ruling; FABLE-FIX-S81-COLTAP, HEAD lanes |
| 6 | HEAD | NF14 with rows A-C + pg_pin_rule on 2 types; serdes DOREG with a site rule; host_e flops at the u_epc pin row | 6 open types | FABLE-DIE-HEAD, HEAD-100, FABLE-FIX-HEAD-TIMING |
| 7 | all | die clock cells inside types, and die hold on real views | die closure on 4 dies; avoids a second build of signed types | FABLE-DIE-S81 / -HEAD / -KV / -QC |
| 8 | S81 | bksel_q fx6 (ETM clock landing v3) | last S81 core + bk_sel__t2 + 1 parent type | S81-BKSEL-O |

### Lever 1. S81 col (216 types)

Evidence.
- F2s3 tap lead 200 gives early taps 215.39 / 184.57 / 53.17 = the F2r tree values, the only tree that measured 460 / 468
  on the 465.39 halves (REPORTED, FABLE-PD-S81-F2s3).
- Unmeasured on these rows: sequencer lead 100 (132 types), the swap (372 tiles), every one of the 84 r0 / h10_r1 types
  (estimate go_tag +40, ef +23..+63 at CTS).
- Reset copies: copy_depth 3 chains carry NO sites. One common flop drives 70..110 chain heads; per-hop estimate 195..415 um.
- Gate: col-wave1 / 2 release on post-CTS TT >= -42. Verdict 3: this stage read 51..86 ps optimistic on three kits today.

Root cause of the risk: the wave gate is a placement-RC number, and two of the four col mechanisms have no measurement.

Fix.
1. Pilots from the real F2s3 bind (already the plan). Report per pilot: core pins within 20 ps, s arrival, go_tag, ef,
   reset-copy worst hop in um and slack.
2. Wave release = GRT-stage TT on the reloaded DB at the S81 signal scale >= -42 and overflow 0. Until that read exists,
   a post-CTS release needs >= +45 (the smallest margin that covers the 86 ps worst miss against -42).
3. Reset copies: if the r2 pilot shows a hop over 405 um or the class under -42, FABLE-DIE-S81 adds sites for the chain
   flops (300 um grid, taken from the F2s3 core positions) in the next delta. Compose them now; do not wait for wave 2.
4. r0 / h10_r1 (84 types): the estimate is below the +45 rule. Treat IFN = 0 halves as the main form for these 84, not the
   fallback. S81-IFN0-HALVES posts the face-branch insertion at CTS (target 300-370 he, 330-390 hw) today.
5. IFN = 0 check: FF hold on the 605 input ports (-137) is a port contract; it is closed only if the lib carries
   hold_rising on every data input AND the die seam window covers it. Read both before rows go to DIE-S81-92.

### Lever 2. S81 non-col

Evidence.
- serdes: DPL closed on F2sv (table). But main, the v2 tree and B6gF2s2/src lack the gen_phys TXPIPE hook (`OT_TXL_MID`,
  POST_GLOBAL_PLACE): pipe rows are not placed at the PMA faces. That was the -455..-719 ps TX class of 11-14. Branch
  f84ed61a70 approved r309 at 09:06.
- svc: cause (a) memory closure works in the tree (kit_rtl RC 0). Causes (b) ff bands and (c) 31 form-A sites are in
  B6gF2sv_formA. No floorplan or GRT read yet.
- strips: 4 types at GRT 0 with rows. c_t34 route was chained on epyc8; no route log exists on the hub (MEASURED 09:15).
- A_t65 route: no result posted.

Fix.
1. DIE-S81-92: adopt F2s3 on its gates (BIND 0, LATCHECK 873/873 with tl_o +3 priced, G0 new 0, hcparam 0). Add t43_rows
   (ft5 band x 440..600) and the svc form-A sites to the next delta, one event.
2. No serdes kit from a tree without f84ed61a70. The two F2sv proof kits now in route have no TXPIPE placement: read their
   TX-face paths at GRT before trusting the route.
3. First ring-ff detail route (c_t34 or A_t65): DRC at the ff bands. This is still the one unproven step for about 137 types.
   If epyc8 refused the chained route (disk), relaunch it on another host now.
4. svc pilots: read GRT overflow in the 10.8-um gaps between the 32x128 macros at the floorplan stage.

### Lever 3. QC event

Evidence: verdicts 1 and 2. S4q9d review ADOPT-OK (0 cycles, hops relay -> leaf at most 220.5 um). glue fault OR: two
unregistered hops of 1.3-1.5 mm; S4q9e-glue adds 214 station flops, lanes fltc 9 -> 12, fltvc 9 -> 12, fltt 9 -> 10.

Root cause of the bind error: the knee stations added delay on some `u_fup.l9_c` region slice of W5, so region 0 is no
longer the latest, and the transport code has a pad for regions 1-7 only (`NB_PAD = max - nbo[r]`).

Fix.
1. FABLE-FIX-QC-KNEE-HC: stop the fe / ctl bump scan. Print `nbo[0..7]` for W5 from the S4Q9DBQ view. Then one plan row:
   add the missing station(s) on W5 `l9_c[0..63]` (region 0) so that `nbo[0] = max` (cycles pre-approved), or give all
   eight l9_c slices the same station count. Same check on `r_d` (line 180) before the rebind.
2. One S4q9e = S4q9d + glue fault stations (aed254508723) + reset leaves on coll_core / native59 / tt_ctlm
   (c12269e24374). The type sets are disjoint. KNEE-HC composes it, renames nothing else S4q9e, binds once. LATCHECK must
   show exactly 3 lane deltas.
3. glue d2d_rom store (-64..-152, about 400 endpoints): keep the withdrawn SRAM move withdrawn. Decide from the glue a6
   post-CTS probe; prefer region rows for the store flops beside the SRAMs over the TT repair env (the env does not move
   a flop that is 1 mm from its SRAM).
4. Rect Only on slw / sle su_l0 (4 types): rebuild on v2, where PG-AWARE-1 is active; check `cland_tstart_in` is off the
   M6 PG pair before route.

### Lever 4. KV

Evidence: 7yhr gates as in the table. FABLE-DIE-KV: 13 types with a START reader hop of 405.4-573 um (10 pv, hg_v1p5,
hg_v1p6, io_cor_v1); 39 ports / 7,128 bits over 405 um (max 530.2); 21 taps with slew over 150 ps on pv_N_7 (max 224.7);
2,024 die clock cells on the signed hard kv3_phy / kv3_phy_v1.

Fix.
1. Adopt 7yhr when the gate's last gen runs end. Read the first hub_C / hub_Wo place on ring_place ff before more hub rows.
2. KV-HG1 = v25hv + k2r + the 13 START hop rows in one event. The 10 pv START hops are the same one-cycle sideband class
   that cost QC and HEAD a day; they are cheaper in the event than after the pv pilots fail at CTS.
3. The 2,024 clock cells over a signed hard PHY cannot exist: FABLE-DIE-KV fixes the die clock site rule (hard macros
   as keep-outs) before any KV die number is used.

### Lever 5. Gate calibration (all dies)

Evidence: verdict 3. HEAD-TYPES-O calls it "the 75-150 ps GRT under-read". Cause (INFERENCE): the post-CTS gate uses
placement RC without the die signal scale (HEAD 1.13, QC 1.25, KV 1.10) and without detours round macros.

Fix: one ruling. Decisions (wave release, keep / drop a form, "inside the gate") are taken on the GRT-stage TT of the
reloaded DB with the die signal scale. A post-CTS number is information unless it is >= +45. This costs about 1 h per
pilot and removes a 216-type false release.

### Lever 6. HEAD

Evidence.
- hd_lep0N: 85 sideband hops over 405 um (status up to 2,780, start 1,515); rows give worst hop 349-370 um, 0 data cycles,
  boot +8. Region tree FF spread 271.6 -> 128.6 with `actual_max_region {lep0N: 300}` (proven).
- hd_ctl: 15 hops over 405 um (931 / 840 / 842). r308 moved its rows to the next delta.
- hd_serdes: u_chn outputs on its top edge, y 386.0, under the VDDPHY floor at 400; consumers behind u_dmem.
- hd_host_e: every u_epc input is captured on the early clk_c0 tap (-63.32) with 93.55 ps macro setup; a normal-tap flop
  has about 230 ps. he5 worst net: CKINVDCx16 on 64 fF, slew 733, 231.8 ps of wire.
- LEF: FABLE-FIX-HEAD-TIMING's static A/B (merge OBS into pin: markers move to the new pin end) and M7PIN (OBS 13 / 15)
  disagree. he7 (merge + re-route) is the test.

Fix.
1. NF14 = rows A-C plus `pg_pin_rule=true` on hd_st_n3_turn and hd_spn_end (config only, moves 2 pins off the M6 pair).
2. hd_ctl: do not rebuild it on NF14 without its sideband rows; it would hit 931 um in one cycle again. Either the
   rows enter NF14 or hd_ctl waits for the delta.
3. hd_serdes sd7: DOREG works only if the 559 seam flops sit at the u_chn top edge (14-um strip). Add a region /
   pin-row rule for them and read their distance to the u_chn pins after place, before GRT. Without it the 400 ps
   clk->q + 480 ps wire path stays, one flop later.
4. hd_host_e: the form is flops at the u_epc pin row on the same early tap (launch 63 ps early, wire under 30 um). The
   skid slice already pays the cycle. FABLE-FIX-HEAD-TIMING owns it; nothing has been started since 08:58.
5. he7: accept only 0 EOL at the u_epc pins. If the markers move to the new pin tops, the cause is the M7 access stub
   end against internal macro metal: then give the 15 pins M8-only access (pin shape on M8) in the abstract.
6. hd_host_w hw4: -11.93 is a post-CTS number; hw3 hold -34 is open. Read GRT RC.

### Lever 7. Die clock cells and die hold (4 dies)

Evidence (REPORTED by the three die reports).
- Die clock cells inside type area with no reservation: S81 93,522 (2,586 inside ring-ff band rects, about 4,003 on ft
  station columns; 0 of 395 types reserve); HEAD 42,882 of 44,493; KV 30,264 + 2,024 on hard PHY. QC: 0 illegal.
- Hold on real views: 0 pairs measured on S81, HEAD (0 of 585,476, although 18 closed views are in the kit) and QC.
  Kit-contract hold: QC -114.9 intra / -59.2 seam; S81 seam skew 310 against a 40 ps contract; HEAD -80.6 declared-budget.
- S81 feed: 188 stages, 11.7 ns, K table still from the B6gsh kit (taps 22,895 -> 21,687). QC: 14.12 ns, late-early
  1,828 ps, same-type instance spread +-129 ps on 14 cb types.

Root cause: types are built without the die clock cells, and die STA has never been fed a signed view.

Fix.
1. S81 R3 now (clock kit of record: bands, ft stations and tap rows as keep-outs; 405 um leg cap), then R4 (K table from
   that kit) and R2 (reservation rows). Every col and ring type signed before R2 may need a second build; R3 first
   keeps that set small. Report the count of reserved sites that hit placed cells per signed type.
2. HEAD fix D now: load the 18 closed views into die STA. It is the first real hold number on any die.
3. QC row 3 (one region tree per type, reused per instance): start it; the +-129 ps spread is larger than the 87 / 110 ps
   kit windows.

### Lever 8. bksel_q

Evidence: pk2 clock pin 696 TT, 811 inputs FF hold -124, setup to u_fq r_addr -149.8. fx6 (BUFx24 at each ETM clock pin)
CTS: pk2 pin - regs -115.1 -> -156.9 against a target of -180; hc0 bank only -78.9.
Fix: read the 12 paths into pk2 and hc0 at post-GRT repair. If hc0 or pk2 misses, feed those two pins from one tree
level higher (a second measured tap choice), not a further hold-repair round.

## 3. Lanes whose approach looks wrong

| lane | issue | change |
|---|---|---|
| FABLE-FIX-QC-KNEE-HC | fe 2 / 3 bump scan for an error a uniform bump cannot move; next step in the handoff is fe 4 / 5 | stop; W5 l9_c region-0 station row (lever 3) |
| FABLE-DIE-QC + FABLE-FIX-QC-CBGLUE | two plans named S4q9e, different contents | one composed S4q9e |
| FABLE-FIX-S81-COLTAP | col waves release on post-CTS >= -42 | GRT-RC read, or post-CTS >= +45 |
| S81-IFN0-HALVES | treated as fallback; the 84 types have no measured tile and a +23..+63 estimate | main form for r0 / h10_r1 |
| HEAD-SERDES-O | sd7 DOREG without a site rule for the seam flops | region at the u_chn edge; read after place |
| FABLE-FIX-HEAD-TIMING | hd_host_e has no build since he6 failed; three RTL forms missed the same pin-row cause | pin-row flops on the early tap |
| HEAD-100 / FABLE-DIE-HEAD | hd_ctl rows deferred while hd_ctl rebuilds on NF14 | rows in NF14, or hd_ctl held |
| FABLE-FIX-S81-SERDES | F2sv proof kits in route have no TXPIPE placement | read TX-face paths at GRT; rebuild from f84ed61a70 |
| FABLE-FIX-S81-CONG / S81-STRIP-O | ring-ff detail route (c_t34, A_t65) still unread; STRIP-O silent since 05:42 | CONG owns the route read today |
| FABLE-DIE-KV | 2,024 clock cells on a signed hard PHY left for a later delta | site rule before any die number |

## 4. Stop list

1. fe / ctl pin-pad bumps to clear `PARAM_REGEN W5 nb_od`.
2. Binding either current S4q9e file as it is.
3. Releasing a volume wave on a post-CTS placement-RC number between -42 and +45.
4. Any S81 col kit before the F2s3 bind; hand-edited kits to get round KIT_TOPOLOGY_BIND_STALE.
5. Any S81 serdes kit from a tree without f84ed61a70; any kit on G3b / B6gE bands.
6. Route-keep ECO rounds on hd_host_e / hd_host_w / hd_ctl (three rounds, 0 gain: -116.51, -66.93, -80.96).
7. PDN halo as the fix for the u_epc EOL class (he6: 29 EOL left). A LEF OBS trim (markers stay).
8. hd_ctl or hd_lep0N rebuilt without sideband rows; reading u_chn or hd_serdes from sd5 or from a post-CTS number.
9. Hold repair with no iteration cap on bksel (fx1 / fx3 / fx5 stalled at -34.6 / -36.8 for more than 3 h).
10. Moving the 4 glue d2d store SRAMs with FDI stations (+3 cycles breaks the compiled link calendars on both dies).
11. Reading it5 / it10 / it15 as GRT convergence; relaunching b_t75 / b_t62 / b_t47 bases without rows.
12. Still valid from 0943: hold judged on a flat 165 ps window; dropping track-truth obstructions in an ECO session;
    raising the QC 403 um knee; KV pv on kvgeom6, 7p, v20 / v21.

## 5. Not checked

- F2s3 bind result, c_t34 / A_t65 routes, sd6 / sd7 / hw4 / he7 routes, coll_n a22 route, fx6, IFN0 CTS: all in flight.
- I did not read the W5 `nbo[]` values; the cause in lever 3 is from the code and the unchanged error, not from the numbers.
- The +45 margin is from three kits on two dies; S81 non-col and KV have no CTS-to-routed pair in my read.
- The die clock-cell counts and hold contract numbers are from the die reports, not re-run.
- No render opened. No KV die report file exists to read; KV die numbers are from one queue post.

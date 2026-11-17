# FABLE-CLOSURE-STRATEGY 2026-11-16 17:20 PST (1730): plans bind on all four dies; the open class is now routed internal hold, and three runs repeat a measured failure

Read-only review (Fable). Technical physical design only. HBM parked. Nothing launched, stopped or changed.
Read: FABLE-CLOSURE-STRATEGY 09:25, CODEX-LOG "Handoff to Claude 17:04" + 17:07 receipts, today's FABLE-DIE-HEAD / -S81 /
-QC / -KV, FABLE-PD-S81-F2s3 / -F2s4, -QC-S4q9e / 9k / 9l, -HEAD-NF14 / NF15a / NF15b, -KV-HG1, handoffs
FABLE-FIX-S81-COLTAP, S81-IFN0-HALVES, FABLE-FIX-QC-CBGLUE, HEAD-TYPES-O, HEAD-SERDES-O, FABLE-FIX-HEAD-TIMING,
FABLE-FIX-KV-PVHUB, KV-102, `failure_breakdown.py` 17:12.
MEASURED = read by me 17:05-17:20 from kit logs / sign-off JSON on the build hosts. REPORTED = lane or Codex post.
INFERENCE is marked. No odb opened, no STA run, no render opened.

Signed types 09:10 -> 17:12: S81 41 -> 41 of 394, HEAD 20 -> 20 of 26, QC 7 -> 7 of 127, KV 6 -> 6 of 56.
(hd_st_n3_turn is signed on the private NF15 pin form, TT +80.66 / FF +0.34, not in the count yet.)

## 0. Verdict

1. **The plan-level blockers of 09:25 are gone.** S81 current819 is adopted (BIND 0, LATCHECK 873/873, G0 new 0). KV HG1A is
   adopted (LATCHECK 2404/2404). QC Kf binds (LATCHECK 1921/1921, hcparam 0 mismatches: the W5 nb_od error is closed).
   HEAD NF15b is reviewed ADOPT-OK (bind 358, LATCHECK 329/329). No type was signed from any of them yet.
2. **The failure class that now ends every finished route is internal FF hold of -9 to -60 ps on 30-860 endpoints**, with
   DRC 0 and TT inside -42. MEASURED / REPORTED today on 9 builds on three dies (table in lever 1).
3. **A post-route fix for that class is proven.** MEASURED (epyc2 qc-pinaccess-o/coll_n_hold80_1116/signoff): coll_n with
   80 HB4 cells at 64 capture pins, 144 nets re-routed in 63 min, DRC report empty: TT -1.39, FF hold +0.47 (was -58.19 on
   64 endpoints). It is a hand-built pilot; no other type uses it.
4. **Three runs repeat a measured failure.**
   - S81: the five col pilot kits in GEN carry sequencer lead 100 / ROM 255. That value read ROM rd_out -> s at -57.0 with
     14 endpoints under -42 at CTS on the r2 evidence kit (15:0x). Lead 40 read q +9 / a -42.
   - QC: headseg44 detail route is at iteration 50 and does not converge. MEASURED violations per iteration: 17,686 ->
     1,192 (it 16), then five saw-teeth 4,960 / 5,309 / 8,461 / 6,747 / 8,746 with floors 922 / 1,164 / 909 / 1,001.
     Shorts on M2 / M3 / M4 (816 / 878 / 686) and M4 eolKeepOut 1,663. Design utilisation is 54 %.
   - QC P3 (sle_hc2): the 20 ps pre-route hold target selects 26,258 endpoints to repair 6 negative ones (-24.29).
     MEASURED: the repair has been at iteration 0 for 20 min.
5. **S81 col (216 types) is serial behind one core form that has only a CTS.** The old IFN = 0 halves bypassed the ICG on
   547 of 604 input flops and are void. The correct split form (he_splitclk1) reads TT +13.88 at CTS and QB -> IR hold
   -88 TT / -97 FF, because the 512 IR flops are clocked at 407-470 ps against 365-371 for the gated flops.

## 1. The 09:25 levers: landed or not

| # | lever (1143) | landed? | numbers |
|---|---|---|---|
| 1 | S81 col: F2s3 bind, pilots, GRT read, chain sites | **PARTLY** | F2s3 -> F2s4 -> current819 adopted. Swapped halves overlapped 1.116 um (MPL-0041 on every swapped col type); fixed in rows (366 pairs +-4.32 um). r2 CTS: go_tag +109..+137, ef +118..+151 (were -186 / -160): tile fix measured. Reset chain hop 1 is 836-1,174 um, -181; spread hook v4 gives 309 hops, max 316.4 um, pre-DPL only. 0 col types routed |
| 2 | S81 non-col | **PARTLY** | strips t8 / t28 / t75 / t43 rows in the plan; t34 FF form is a model only; eight-type GEN running. svc hi3 in floorplan repair (3.557 M std cells). serdes H at CTS, six holds stay |
| 3 | QC W5 row, one S4q9e | **YES** | one plan chain 9e -> 9k -> Kf; hcparam 0 mismatch. Clock rows L reviewed ADOPT-OK (tap gate 0 of 84,512 outside). Kf / L are not the plan of record yet |
| 4 | KV 7yhr + HG1 | **YES** | 7yhr then HG1A adopted; die run c1: GRT 0 overflow, setup +482.8 / +510.6, slew max 128.4. Three pilots only; 31 keys held on their CTS read |
| 5 | Gate on GRT RC, not post-CTS | **YES** | r310 read = TT >= -42 on the GRT DB at die RC scale + overflow 0; r371 gate = routed TT >= -42, internal FF >= 0 |
| 6 | HEAD NF14 rows, DOREG site, host_e pin row | **PARTLY** | NF15a / NF15b: lep0N worst hop 694.6 -> 377 um, M1-M7 walls gone. host_e he12h: 253 HB4, internal hold -23.71 -> +20.06, TT +4.65, GRT 0; in detail route. serdes sd9A closed at CTS, no GRT |
| 7 | Die clock cells in types, hold on real views | **PARTLY** | S81 clock kit ECOv3: 93,626 cells, 0 overlap, max edge 403.9 um (K2 failed on a 993.9 um leg). KV first real-view hold: 384 pairs, min +22.57; 1,426,596 unmeasured. HEAD, QC, S81: 0 pairs |
| 8 | bksel_q | **NO** | bc5 still in its second hold pass (470 / 462 buffers, +12.26), no route |

## 2. Levers now, ranked by types unblocked

| # | die | lever | unblocks | owner |
|---|---|---|---|---|
| 1 | all | routed internal hold: one post-route HB4 insert step in the flow + a 10 ps pre-route margin | every type that reaches route; today 9 builds, incl. QC head group (96 heads) and both S81 halves | FLEET-OPS-R; QC-TYPES-R, HEAD-TYPES-R, S81-CORES-R |
| 2 | S81 | col: halves closed in CTS (IR group), lead rows fixed before any pilot launch, reset spread in the flow | 216 types | S81-CORES-R (halves), S81-TYPES-R, S81-DIE-R (rows) |
| 3 | QC | head: no hold cells on port-only paths; rebuild the head from the CTS-scope fix | 96 heads in 9 SU types, 8 group forms | QC-TYPES-R, FLEET-OPS-R (a03 fix) |
| 4 | QC | Kf + L as one plan of record; +1 K on 3 serdes crossings | about 100 unsigned types now on S4q6d kits | QC-PLAN-R |
| 5 | KV | pilot CTS read releases 31 keys; rows B' without walls; E4 tap window | 31 + 14 waiting on child cores | KV-R |
| 6 | HEAD | M8 grant wherever M1-M7 is reserved; hw4 by lever 1; sd9A GRT read | 4 of the 6 open types | HEAD-TYPES-R, HEAD-DIE-R |
| 7 | S81 | non-col: t34 / t43 strips, svc size, serdes cohort guard | about 137 types | S81-TYPES-R, S81-CORES-R |
| 8 | all | clock rows have 0 margin; region tree per type | re-sign risk on 52 QC + 51 KV types at each tap move | QC-PLAN-R, KV-R, S81-DIE-R |

### Lever 1. Routed internal hold (all dies)

Evidence (FF corner, hold uncertainty 25, internal reg-to-reg only; all DRC 0 unless noted):

| build | TT setup | internal FF hold | endpoints | source |
|---|---|---|---|---|
| QC coll_n a22 | -1.09 | -58.19 | 64 | REPORTED; pilot2 after insert: -1.39 / **+0.47** MEASURED |
| QC group44 W0 | +12.40 | -16.89 | 858 (842 D, 13 RESETN) | REPORTED; all have >= 306.7 ps TT room |
| QC tail H17 / H16 | +45.05 / +61.17 | -15.69 / -8.65 | 327 / 171 | REPORTED; TT room >= 343 / 432 |
| QC P3 sle_hc2 (GRT RC) | +39.05 | -24.29 | 6 | MEASURED (p3_native_hold.log) |
| HEAD hd_host_w hw4 | -25.50 | -32.87 sign-off line; -12.32 internal | 31 | MEASURED (hw4.log) / REPORTED; TT room >= 173 |
| HEAD hd_host_e he12 | +4.65 | -23.71 -> +20.06 after 253 HB4 pre-route | 109 | REPORTED |
| S81 he half (void clock form) | +11.24 | -2.15 after 1,707 buffers | 285 before | REPORTED |
| S81 hw half (void clock form) | -11.94 | -68.88 | 635 | REPORTED |

Root cause. Pre-route hold repair closes to 0 on the GRT estimate; extraction then moves short paths by 9-17 ps (W0: same
frame, M6 / M7 unused, so it is estimate against RCX, not calibration). Every endpoint repaired to +0..+15 lands negative.
The endpoints have 170-430 ps of setup room, so the fix costs no timing.

Fix.
1. FLEET-OPS-R: make the coll_n pilot a flow stage (epyc2 qc-pinaccess-o: `qc_hold_insert_prepare_generic.py`,
   `qc_hold_insert_body.tcl`, `qc_hold_reservation_model_v2.py`). Trigger: routed DRC 0, TT >= -42, internal FF in
   [-70, 0), TT room on each endpoint >= 172 ps (the HB4 TT max 171.24 at slew <= 320). One HB4 per capture D pin on a
   filler site within 7.2 um, re-route of the touched nets only, then the normal sign-off.
2. Size it for +10, not 0. coll_n ended +0.47: a re-extraction can flip that. Two HB4 where the need is over 25 ps.
3. Pre-route margin: 10 ps on internal endpoints only, never 20. P3 shows the cost of 20 (26,258 endpoints for 6).
   he12h shows a targeted list works (253 cells, +25.8 um2).
4. Apply at once, by owner: QC-TYPES-R H16 (171 cells, structural insert already PASS), H17 (327), W0 (858, reservation
   found, 12 cells at 6.0-7.2 um); HEAD-TYPES-R hw4 (31; the eco_hw4/i1t run is this); P3 by insert of 6 after route.
5. RESETN / SETN removal endpoints (13-27 per type) take the same cell at the reset pin; keep them in the count.

### Lever 2. S81 col (216 types)

Evidence.
- he_splitclk1 (epyc2 s81-ifn0-halves), CTS only: 57 root / 547 on the original ICG / 512 IR flops. Arrival TT 393.9-395.3 /
  364.9-371.4 / 407.5-469.5. QB -> IR hold -88.36 TT / -97.07 FF with setup +679.8. IR downstream hold -4.02 / -24.17.
- Sequencer leads: lead 100 -> ROM rd_out -> s -57.0 (14 under -42); lead 40 / ROM 285 -> go_tag +64..70, ef +184..194,
  q +9, a -42. a + q per sequencer does not depend on the leads (s14 +44, s12 +64).
- Reset: copy_depth 3 chains are not spread by placement; hop 1 836-1,174 um, -181, 26 endpoints. v4 probe: 468 stale
  reset buffers removed, 206 flops re-sited, 309 hops, max 316.4 um (pre-DPL).
- The five pilot kits in GEN (epyc10 countable_F2s4tapfix1) are "current plan 100 lead / 255 ROM".

Root cause. Three independent mechanisms, each measured once on an evidence kit, none yet together on a countable kit;
and the main form waits on a core whose clock groups are 40-100 ps apart by construction.

Fix.
1. S81-CORES-R: close the halves in CTS, not by hold cells. Put the 512 IR sinks in the balance group of the gated
   sinks with target 365-371 (they are 40-100 ps late). That removes the -88 / -97 class at its source; the 679 ps of
   setup room pays for it. Then GRT read, then route; lever 1 covers the residue. The old form needed 1,707 buffers.
2. S81-DIE-R / S81-TYPES-R: before any physical launch of the five pilots, change `core_pin_lead_ps` to sequencer 40 /
   ROM 255 (the measured fallback). Do not route kits with lead 100. This is a row change on 132 types, 0 cycles.
3. Sequencer s14 is at a + q = +44 total, so the fallback is thin after route (HEAD lost 73-86 ps from CTS to route).
   The IFN = 0 delta (sequencer lead 0) stays the main form; the fallback pilots exist to measure reset and ef / go_tag
   on a countable kit now, not to sign.
4. FLEET-OPS-R: put reset_chain_spread v5 into gen_phys (PRE_RESIZE, on `reset_replicate copy_depth > 1`). Proof on the
   r2 pilot = post-DPL hop table (0 over 405 um) and the reset class at the GRT read.

### Lever 3. QC head (96 heads)

Evidence: lever 0.4 (route history). REPORTED: 5,585 hold cells sit on port-only paths; 581 of them in one 192 um2 spot
raise its fill from 69.1 % to 90.6 %. GRT overflow was 0, so the failure is local pin access, not global capacity.

Root cause: hold repair pads port paths that r371 no longer gates, and the cells pile up at the pin row.

Fix.
1. QC-TYPES-R: do not wait on headseg44 and do not relaunch it unchanged. Rebuild the head from CTS with the a03 scope
   fix (hold repair on internal endpoints only). Expected: -5,585 cells, hot spot back to about 69 %.
2. If the same spot still plateaus over 500 violations at iteration 16: placement blockage (partial, 60 %) on that
   192 um2 window. No outline growth.
3. Check group44 W0 for the same cells: its flow finished (MEASURED, 6_report written) with 858 internal negatives;
   the W1..W7 248-output form should be generated with the a03 scope from the start.

### Lever 4. QC plan of record

Evidence: Kf valid (bind 0, R8 0, LATCHECK 1921/1921). L = Kf + clock rows: tap gate PASS 0 of 84,512, seam window 180
against a need of 169.2, intra 79 / 79.0. Die STA with the count-align bind: 3 of 2,993 crossings fail, io_serdes_2 ->
c_W5_bf_01, margin lo -107.1 TT / -67.0 FF, hi +1,968. L private bind r2 failed on a missing bind sibling, not on hardware.
Fix (QC-PLAN-R): bind L once with the 12 bind siblings present; add +1 K on the three serdes ports in the same event (hi
margin has 1,968 ps of room); glue kit first on that plan and read it at GRT. Do not start more S4q6d kits.

### Lever 5. KV

Evidence: HG1A die run as in section 1. Rows B as cut: 997 merged strips, 125 walls with >= 276 core pins behind them
(worst 946 of 1,660 M5 pins of pvg1_p3); raw sites have 0 walls. E4 island: tap window need 277 + 10 against the T/4 =
208.25 guard on 40 ports. 39 wide ports over 405 um (max 530.2). 2,024 clock cells on the signed PHY types.
Fix (KV-R).
1. Post the pilot CTS read (cells, TT, krsp first hop) for kv3_hg_v1 / hg_v3 / pv_v1n as soon as each CTS ends; it frees
   31 keys. Wo3 died on host memory, not geometry: same kit, another host.
2. Rows B': no merged rect within 5 um of a core edge unless under 10 um long; check 0 walls with >= 50 pins; first build
   kv3_pv_v1n to GRT.
3. E4: do not clamp 277 to 208.25. Give the E4 regions a DME tree (form E did this for pv_N_7: 224.7 -> 138.9 slew and
   smaller spread) and re-measure; rows C only from that tree.
4. hg +1 station on the 7 types (19,219 FF bits) goes with B' / C in HG2, one event.

### Lever 6. HEAD

Evidence: he12 failed GRT with overflow 13, all clock entries inside NF15 M1-M7 reservations with max layer M7 (no M8
grant). he12h with the grant: GRT 0; detail route at iteration 1, 22,944 violations at 30 % (MEASURED 17:16). hw4 as in
lever 1. sd9A: every pipeline cap positive at CTS; sd9B DK -> chn -51.16. The four-net DRT-0206 A/B ended exit 2 (MEASURED)
on an unrelated net: inconclusive.
Fix.
1. HEAD-DIE-R: complete the NF15b switch and carry `die.layer_budget.type_m8_grant` (enable, frozen guide, 4w NDR) for
   every type with an M1-M7 clock reservation; hd_tile tp2 needs it too. The environment switch alone imports PG only.
2. HEAD-TYPES-R: sd9A to GRT now and read TT on the GRT DB (HEAD lost 73-86 ps there twice). Drop sd9B.
3. hw4: lever 1 on the 31 endpoints; TT -25.5 is inside the gate. Do not pad the 460 output ports.
4. he12h: read sign-off when route ends; EOL at the u_epc pins is the number to look at (he6 had 29).

### Lever 7. S81 non-col

Evidence: t34 ring-ff model: 256 existing FF, 336 shared comb clones, +18.2 um2, 0 cycles, margin 7.9 um (model only).
t43: partial coverage IN 69 / 595, OUT 410 / 668. leaf34 bare instance names are not handled by the ac601 helper. svc
hi3: 3.557 M std cells / 653 k FF in one type, floorplan repair at iteration 977, peak 31.4 GiB. serdes: start / reset
rows fix distance only; RX half-cycle skew 413 ps, reset relay skew 553 ps need the cohort guard (55b26f).
Fix: S81-TYPES-R builds t34 on current819 to GRT before more strip rows; t43 waits for full-width aliases. S81-CORES-R:
serdes pilots only from a tree with d5bd6d74 + 55b26f; read the svc hi3 floorplan result before lo7 goes past synth.

### Lever 8. Clock rows and die hold

Evidence: QC L rows: 2,607 of 15,391 ports at 0 margin, 3,597 under 5 ps; cb instance spread to 129 ps. KV rows C: 0 margin
on 6,129 ports; 44 % of ports moved past their window after one compose (p90 29 ps, max 91). S81 seam need 290 against 40.
Root cause: per-instance region trees and rows cut at exactly the measured need.
Fix: cut rows at need + 10 ps (setup room is +360..+540 on all three dies); QC row 3 (one region tree per type, reused
per instance) is still not started and removes most edge ports; S81 R4 K table from the ECOv3 kit before col kits sign.

## 3. Stop list

1. Routing the five S81 col pilots with sequencer lead 100.
2. Any number from the old IFN = 0 halves (604-hook, ICG bypassed); more hold buffers on the halves before the IR group
   is balanced in CTS.
3. Waiting on, or relaunching unchanged, QC headseg44 (plateau 900-1,200 for 33 iterations).
4. A 20 ps pre-route hold target on whole types (P3: 26,258 endpoints for 6).
5. Hold cells on port-only paths in any type kit.
6. KV rows B as merged; clamping the E4 window to 208.25; a second die run on HG1B before B'.
7. HEAD: host_e without the M8 grant; merged OBS pins (GRT-0116 twice); further four-net rip A/B runs; sd9B; the WEST
   reverse fallback while he12h is in route.
8. S81: F2s3 col GEN outputs (MPL-0041); the K2 clock kit; the t43 VSW / RXSB +198.72 move; serdes pilots without the
   cohort guard; splitting common 13 / 48 into separate arrival windows.
9. QC: more S4q6d kits; the C2993 3 + 1 ring graft on N43; the early-E collector pad.
10. Still valid from 09:25: route-keep ECO rounds on hd_host_e / hd_ctl; moving the 4 glue d2d SRAMs; reading it5-it15
    as GRT convergence; hold repair without an iteration cap on bksel.

## 4. Not checked

- The coll_n pilot sign-off line also says `face_guard FAIL` and DRC NOT RUN inside sign-off (the route report is empty);
  I did not read why face_guard fails.
- KV pilot kit logs: I could not find their kit directories on epyc10 in the time; pilot state is REPORTED.
- S81 svc hi3, serdes H, bksel bc5, the eight-type GEN, the clock R4 run: REPORTED only.
- The 9-17 ps estimate-to-RCX drift is from QC and HEAD; S81 has no valid pair yet. The IR-group fix is INFERENCE from
  the clock arrival table, not a run.
- Whether eco_hw4/i1t is still in route (ab206 ended exit 2; I did not read eco_hw4.log).

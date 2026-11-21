# M7PIN-STRIPE-1116 handoff (FABLE-CLOSURE-0943 lever E), 2026-11-16 ~08:40 PST

VERDICT: shared-cause claim REFUTED. The three classes have three separate causes, and none of them is the die-phase M7 stripes.
No flow change, no gate, no READY (the brief says fix only if confirmed).

## Step 1: types (fleet scan of 5_route_drc.rpt < 4 d plus posts; the HBM context runs are left out)
- Rect Only M7: hd_st_n3_turn (rst_start_raw_2), hd_spn_end (rst_start_raw_0), QC slw_su_l0 __cl1a1c1f8f/__cl76fb247e and
  sle_su_l0 __cl7a55c676/__cl086d85ba (cland_tstart_in[0], nearmiss-eco kits 11-14). 3 markers each.
- Lef58EolKeepOut M7: hd_host_e only (he3/he4/he5 and their ECOs: 24-30 EOL plus 1-6 Metal Spacing plus 1 Short).
- DRT-0206: hd_ctl route-keep ECO only (eco_hd_ctl/i1t: cland_up_ready_lepk_o0, rst_start_raw_2, rst_start_raw_0, cland_dn_fault_b7_rx_i).
- S81 and KV: none found.

## Step 2-3: measurements (odb probe epyc10/epyc2 /srv/opentallas-scratch2/claude/m7pin-stripe-1116/m7geo.py, run via ot-run; tables *.tsv)
- Rect Only: the cause is the M6 PG pair (0.288/0.096, pitch 4.32) under an 80x432-nm interior M7 BTerm, with M8 obstructed above.
  No V67 fits inside the pin, so DRT lands a 32-nm M7 wire from outside, and the union is not rectangular. M6 pair under the pin:
  4/4 failing pins and 0/109 other 80-nm pins (n3t 18, spe1 69, slw 22). M7 stripes do not separate fail from pass: the QC failing pin
  has no M7 PG within 2 um, and the n3t failing pin is 0.840 um from one while passing pins sit at 0.712.
  The main rule PG-AWARE-1 (tools/die_plan/pg_access.py down_access) flags exactly these pins (n3t 1, spe1 1, slw 1; hd_ctl 0).
  They kept their sites for two reasons:
  - hd_st_n3_turn and hd_spn_end are listed in pg_pin_rule_signed.json (signed types keep their sites).
  - The QC kits predate the rule.
- EOL (he5 5_route.odb, u_epc 555 M7 pins of 32x192 nm): the 26 markers sit on 13 pins. A stripe end within 0.2 um of the pin:
  3/13 failing pins vs 82/542 passing pins, so the stripe end is not the cause. Landing form is the same for failing and passing pins.
  What separates them is the macro LEF (ot_s81hd_he_epc.lef): a pin-width M7 OBS that abuts the pin top. 13/15 pins with that OBS fail;
  0/540 pins without it fail. The FHT trim A/B left the markers in place, so this is still open (macro abstract writer).
  Only the 3 Metal Spacing markers to VDD/VSS at y 60.38 are stripe ends, so he6 (halo) should clear those 3 and not the 26.
- DRT-0206: no geometric difference. M6 pair under the pin 0/4; rst_start_raw_3 has the same 0.712 M7 gap and passes. This is the
  ECO-session class (GENBUG-IMPL fix-spec items 2/3, force-rip A/B).

## Next (owners)
1. HEAD-100: in the next HEAD event, set partition_types.{hd_st_n3_turn,hd_spn_end}.pg_pin_rule=true. PG-AWARE-1 then moves
   rst_start_raw_2/_0 off the M6 pair. Re-floor and re-sign are pre-approved.
2. QC (QC-PINACCESS-O / KIT-OPS-5): rebuild slw/sle su_l0 on the v2 tree and confirm cland_tstart_in passes down_access.
3. HEAD-TYPES-O: he6 is expected to leave 26 EOL. The next test is the u_epc abstract: drop or trim pin-continuation OBS in the LEF generator.
Lane clone epyc10 .../m7pin-stripe-1116/repo: no changes.

## CODEX follow-through 11-16 10:0x
- PG-aware schema/exemption fix @6a4646b7e77c gate alreadyGREEN; READY posted. NF15pg prepared on NF14r, not adopted/gated.
- he9/he10 trim-OBS DRC proof and he7/he8 merge proof live, no abstract winner yet; retain M8 pin form fallback if both keep EOL.

## CODEX follow-through 11-16 11:5x PDT
- n3_turn/spn_end NF15pg fresh proofs are running on intel1 with r315 pin-rule source, approved TT PG replay and explicit PG env restored. n3 GRT TT +60.90ps; spn_end FF pre-GRT hold repair is progressing. Do not duplicate or adopt plan before independent Fable review.
- he7/he8 merged-LEF proofs failed GRT0116; he9 trimmed-LEF proof also failed GRT overflow44. he10 same trimmed-LEF source completed actual DRT with EOL0. It still failed DRC1: fixed reset BPin rst_start_raw_1 overlaps fixed clk_t5 BPin on M7 exactly (93.264,51.624)-(93.296,52.056). This is a separate fixed boundary-port allocation bug, not PG stripes or route tuning. he10 TT-125.19ps and FF-17.01ps also fail. he11r improved whole-bank layout continues; fixed-pin allocator correction is being prepared for a fresh future kit.
- The original DRT0206 four-net force-rip A/B is live as eco_ab206_rip4/i1t on epyc10, preserving actual PG protections. The earlier eco_ab206 without track truth died DRT0255 and remains inconclusive. Do not infer generic router fix until the current named-net comparison completes.

## CLAUDE RESET — parked 2026-11-16
- RECT ONLY n3_turn successor is now actual RMIN SIGNED (TT80.66/actualFF0.34/DRC0), both archives exported, record c9c079 approved r340. spn_end same NF15 pin-rule proof remains LIVE intel1 client936055 (DRT iteration1,30%/10661); HEAD-SERDES-O owns final result.
- EPC EOL trim source 1ef6fc4d571 is approved r334, reproducing measured LEF1633ae32 from original749af4 at clear0.261 without modifying original. Actual he10/he11r final macro EOL0. he11r NOT SIGNED: TT-35.69 passes academic setup, actual core FF-10.64 plus port issues, fixed M7 reset/clock short1. he12 pin/reservation correction placed and CTS passed, but initial GRT failed13 because approved M8 grant builder was omitted; NO restoration/new continuation exists yet. All keepouts must stay.
- DRT0206 named-four-net force-rip A/B continues in existing epyc10 eco_ab206_rip4/i1t. No final connectivity verdict; no shared generic generator fix justified yet. Preserve all previous failed/inconclusive records.

## CODEX notes 11-21 02:22 PST

- Closed as a shared class by the 11-20 03:38 archive read. hd_host_e, hd_st_n3_turn, hd_spn_end, hd_ctl and all four implicated QC Rect Only types have signed records. Legacy named-net ECO stopped on a different DRT-0255 SRAM path. EOL trim and M6 down-access changes remain per class.

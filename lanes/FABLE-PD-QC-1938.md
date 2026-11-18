# FABLE-PD-QC: structural review of QC event N3 (s29q103S4Q9N3)

2026-11-17, FABLE-FIX-QC-N, in parallel with the N3 bind (epyc2 unit oth-ubuntu-1970052-1794972267). N3 = N2B plan 25f880974553 byte-identical + main tools d9bbb638fa79 (r641, r644, r648, r649, r650). Read-only. **V** = read by me in a file this round or measured by my own runs today, **E** = my estimate.

## Verdict: no blocking finding. Bind N3; four lane checks below decide what is rebuilt after the apply.

## (a) Plan content

| item | numbers | risk | lane check |
|---|---|---|---|
| st_a core-edge move (2 types slw_st_a_v1__clfc5867a6 pvdf8e5ca4 / pvf82a6c28) | cl_b_hw_ctl_hc0_i x 570.24 -> 561.6, SRAM g_btb[0] 475.2 -> 457.92; box now 8.63 um inside the east core edge; SRAM 28 um from u_r0; seam-pin-to-band hop 196.6 um (limit 405); lane latency equal on 1921 lanes; census 0 outside (V) | The cland still abuts cl_b_tw_data_i with 0 gap in y (inherited; the sibling clb036e152 has the same pair at the same x). Both types have never placed (MPL-0034), so there is no placement evidence at all. Clock tap moved 8.64 um with unchanged tap_offset rows: under 1 ps (E) | QC-TYPES-R3: first place of pvf82a6c28 on N3 is the proof (MPL pass, macro halo report) |
| HI_PAD hold (bind hook, r-branch claude/qc-hi-pad-hold-1117) | HI_PAD back at the M5 value on 44 st_a rows; N_PAD 1 on 4 head columns x 12 slices = 516 b x 48 = 24,768 flops; S columns keep [1,1,0,1] (V, N2BBR param_regen) | hc0 / hc1 / hc3 types carry S_PAD 1 and N_PAD 1 (+1,032 flops each), hc2 N_PAD only: every hc type RTL changes against L2 / N1B | see "carry-over" below |
| 68 tap[0] pads | unchanged against N1B: 68 pads, 68 W(507), 0 W(508) in 18 types (V, N2BBR) | none new in the plan; tool interaction in (b) | |
| slw_sc_v2 strap | r8_strap_pad_max 28 -> 31, pad 29 on sl_W3_sc; strap stays 5 bits; bank depth = span (V) | none | |
| cbn_q00__cldbcda913 | NB core -43.2 um (in N1B already) + R-REACH-4: 5 fclk_out pins re-sourced to nearer taps, hops 543-975 um -> 15-64 um (V, reach4_fix.json) | Its 122 tap_offset rows were measured with the old tap site and old fclk sources; not re-measured (inherited from FABLE-PLAN-QC-N) | QC-PLAN-R3: tap-offset gate of this one type in the N3 clock chain; rewrite rows only if it fails |

**Carry-over (V, diff of bound RTL N1BBR vs N2BBR, 143 type files):** 65 type files differ. By family: sle_ctl 7, slw_stm 5 (+2), slw_sc 5, sle_sc 4, sle_fw 4 (+1), hc 18 (all hc0-hc3 variants), su_l0 5, su_l1 4, su_c 3, st_a 2, cbx_q10 2, cbn_q00 1. Unchanged: all fe, all st_b, st_a_v2, coll, the other 15 cb types.
- Of the 6 kits signed off today on L2: sle_fe_v1 x2 and sle_fe_v3 carry over; **sle_hc2__cl9c4c4509, slw_hc3__clccfc3e6b and slw_hc3__cld86a7ad4 do not** (their bound RTL changes).
- Of the routed L2 kits now in hold ECO: slw_fe_v1, slw_fe_v2 and both sle_st_b_v2 carry over; slw_hc2, slw_hc0, slw_stm_v1, slw_sc_v2, sle_su_l1 x2, slw_fw_v1, both sc_v1 do not.
- Not a plan fault (N START and the head pads are the event). Action: finish and sign only the carry-over kits on L2 / N1B; stop ECO work on the 9 changing ones at the N3 apply and rebuild them there.

## (b) New tools against this plan

| tool | what it does to a QC kit | numbers | lane check |
|---|---|---|---|
| r641 family hold margin | gen_phys line 5849-5853: margin = max(CLI, family). QC gen arg --hold-ff-margin 0 does NOT switch it off, so every N3 type kit gets OT_HOLD_FF_MARGIN = 40 (V, code; was 0 in the N1B cb kit config.mk) | Today at margin 0 the routed kits pad 121-792 pins, at most 36 with 2 HB4. At 40 ps every internal end under +40 is padded: count unknown (E: several times more pins, and most of the 105-118 ps cross-tap ends of hc need 2 HB4). Setup: the padded ends are short cross-tap paths; the 5 setup-failing kits fail on other paths (14-20 buffer chains), so 40 ps does not make them worse, and does not fix them | QC-TYPES-R3 on the first N3 kit of hc and of su_l1: HB4 count, TT setup on the padded ends, routed internal hold. Type key hold_ff_margin_ps is the per-type override if a family runs out of setup room |
| r641 against the tap[0] pads | The 3-HB4 pad was sized for FF hold +93.9 on cbn_q01 (in-memory ECO); FABLE-PLAN-QC-N estimates +15 on cbn_q00__cl622f65d2 and TT setup +10 on cbn_q11__cl49ae4555 (E, theirs). +15 is under the new 40 ps target, and r650 marks the pad-pin nets dont_touch | The hold repair cannot add cells on those nets. Either it leaves the end (fine: the gate is hold >= 0) or it stops on an unmet target | QC-TYPES-R3: the cbn_q00__cl622f65d2 pilot; read the GRT hold repair lines. If it stops: latch_except_hb4 {tap[0]: 4} for that type family only |
| r650 pad chain siting | 3 HB4 per chain at the core pin: last one 2 um outside, 4 um steps, so the chain reaches 10 um from the tile edge; FIRM at GPL | r648 fills crossing-station strips that start 9.0 um from the tile edge (u_t13: tile east edge 1149.12, strip 1158.12-1231.2, y 1757-2065) (V). Where a tap pin lies on a face with a strip inside that y range, the first HB4 and the strip fill share about 1 um | QC-TYPES-R3 on the cbn_q01 N3 kit: DPL displacement of u_hdly_lk_* cells after 3_5 (accept under 5 um) and OT_XSTN_STRETCH 0 |
| r648 | Already proven on the cbn_q01 copy: 4 of 4 stations moved, stretched 0 (V). x_1_2 now moves to face W: its paths have not been timed | | CTS per-tap insertion and post-CTS ends of the cbn_q01 pilot |
| r644, r649 | serdes pad wire hook (S81 only) and the stage-ODB watcher: no QC kit behaviour change | | |

## Not checked
- The N3 bind itself, and an N2B bind on main tools (N1B showed byte-equal RTL for pin and main tools; bind.py of d9bbb638 not diffed against 1e0504fe).
- Where the tile tap[0] pins sit relative to the station strips (the 1 um overlap is geometry of two rules, not a measured collision).
- HB4 delay at FF / TT, so the pad counts at 40 ps are estimates.
- The link_htree feed and the coll_core tap split (separate post 17:4x): not part of N3.

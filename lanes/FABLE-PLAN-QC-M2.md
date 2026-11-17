# FABLE-PLAN-QC-M2: structural review of QC plan event S4q9m M2

2026-11-17 01:55 PST. Plan `zz_s29_qc103_s4q9m2.json` sha 2c5124cc5c97, tag s29q103S4Q9M2BR, epyc2 unit oth-ubuntu-4087477.
Reviewer read-only; probes ran through ot-run on epyc2 (units 432047, 437377, 481868 and one more), files in
epyc2:/srv/opentallas-scratch3/claude/fable-plan-qc-m2/ (probe1-4.py, cb16_rerun.json).

## Verdict: NOT ADOPT. Compose M3 (new tag). Two blocking findings, both with numbers.

The M2BR bind is already dead: it crashed at 01:27 after 1,524 s (KeyError sl_E3_ctl, bind.py:4302), no bind_report.json,
BQ never ran. It cannot qualify CB16. The geometry, the reset/START reach, the cycle adds and the CB16 table itself are sound.

## Blocking

### B1. Four lane pads have no site (G0 FAIL 4 latency errors). This is the cause of the crash.

G0 on M2 finished after the bind was launched: FAIL, 4 errors, all class `latency`:

| lane | pad | sink site (lanes: pad) | source site (lanes: pad) |
|---|---|---|---|
| sl_E0_su_l0__x_su_l0_ctl | 2 | sle_ctl__cl503337ff.x_su_l0_i (E0 2, E1 1, E2 1, E4 0, E5 1) | sle_su_l0__cl7a55c676.x_ctl_o (E0 2, E1 1, E2 1, E3 1, E4 0) |
| sl_E1_su_l0__x_su_l0_ctl | 1 | same | same |
| sl_E2_su_l0__x_su_l0_ctl | 1 | same | same |
| sl_W5_su_l0__x_su_l0_ctl | 29 | sle_ctl__cl67434795.x_su_l0_i (W5 29, W4 28, W2 28) | slw_su_l0__cl76fb247e.x_ctl_o (W5 29, W3 28, W1 28) |

A pad is a type property, so one site needs one value. The spread is 2 cycles on the E sites (0 / 1 / 2) and 1 cycle on the
W sites (28 / 29). It comes only from clock_landing after the M count re-frame: E0 6, E1/E2/E3/E5 7, E4 8 (stations 9,
boundary 2, faces 3, fixed 5 are equal on all 12 lanes). Each lane is tied to its own slice's su_l1 lane (12 groups
su_vmw_ctl_<slice>, 2 lanes each), so raising a group target only moves the spread to the x_su_l1 site. In l2d the same
lanes had pads that fit (G0 0 latency errors).

Consequence chain, all observed:
1. bind sees unequal instances: TYPE_SPLIT sle_ctl__cl503337ff and sle_ctl__cl67434795;
2. bind.py:3102 names the auto-variant `<type>__v1`, which already exists in the plan (sl_E3_ctl, sl_W3_ctl);
3. tvals of the plan `__v1` type are overwritten, emit_top raises KeyError.

The same 4 errors are in the 00:05 receipt of the RS repair (`coll_calendar_MBR_diagnostic_1116/receipt.json`,
pad_assignment_errors), so they were known before the compose. plan_gate_pre does not check them (PASS, 0 findings).

Fix for M3 (pick one, in this order of cost):
- (a) Named plan variants by pad class, the form the plan already uses for E3 / W3: cl503337ff -> {E0}, {E1, E2, E5}, {E4};
  cl67434795 -> {W5}, {W2, W4}. That is +3 ctl variants (130 -> 133 types), same RTL, pad depth only. Names must not be
  `__v<k>`. Check whether E3 can rejoin {E1, E2, E5} (pad 1) and W3 {W2, W4} (pad 28): that would bring it back to 131.
  The su_l0 source sites then carry no pad. 0 added cycles.
- (b) Same-site-same-landing constraint in the count re-frame (QC-CLK-R2): E0 6 -> 7, E4 8 -> 7, and the W5 su_l1 partner
  landing equal to W0-W4. 0 types, 0 cycles, but it reopens the clock frame and the sidecar. For N, not M3.
Not a fix: raising column MAX 9, a tool rename alone (the split would then run unreviewed), or a retry.

### B2. The M2 chain cannot reach BQ: the first pass is seeded with the stale KF R8 table.

`chain_s4q9m2_1117.sh` runs BR with `R8_SEED=gates/r8_s29q103S4Q9KF.derived.json` (log r8=f6d2f5e120f4, the same seed as
the failed MBR) and then allows only R8_STALE errors before derive. The lane's own replay of the exact M2BR inputs up to
check_types (`gates/m2br_precheck_1117/precheck_receipt.json`) gives 71 errors, 41 of them not R8_STALE:

| class | n | detail |
|---|---|---|
| R8_STALE | 30 (capped) | c16_E0_0.u_fab.u_x_2_0.b_d <- c16_E0_1.u_fab.u_x_2_3.a_d@6: bind bound 7, table bound 9. Identical to MBR. |
| R8_STRAP_PAD | 36 | cl503337ff 6 ports pad 26 > cap 25; sle_su_c 2 at 18 > 15; slw_su_c__cl92142dac 28 at 18-38 > 15 |
| PARAM_REGEN | 1 | SC_TX: seam members shift by [5, 6]. New: RS0 hid it in MBR (coll_regen raises at the first failure) |
| TYPE_SPLIT | 4 | ctl503 5 -> 4 variants, ctl674 3 -> 2, sle_su_c 6 -> 2, slw_su_c__cl92142dac 5 -> 2 |

So even without the KeyError the guard `assert not other` stops the chain after BR. The caps (25 = base 24 + span 1, 28)
and the fresh CB16 table were sized on the fresh R8 base 027d (`r8_s29q103S4Q9MBR_BOOTSTRAP_DIAGNOSTIC_1116.json`). Under
that base the 00:29 callback shows 0 R8_STRAP_PAD, no SC_TX failure and only the 2 ctl splits of B1.

Fix for M3: seed the first pass with an R8 table derived for the M plan (027d or its re-derivation on the M3 plan), not KF.
Before any bind, run the 9-minute check_types replay on the M3 inputs. Launch only if it shows R8_STALE and nothing else.
The SC_TX [5, 6] shift is inferred to be a seed effect (it is absent under 027d). The replay proves or kills that. If it
stays, it is a real 1-cycle skew inside a seam bundle and needs a lane row.

## (1) Structure, checked

Reset and START reach (405 um):
- Bound reset trees of M2BR (written before the crash): 131 types, 46,120 relay edges, max 402.7 um
  (slw_su_c__cl19bb38ef), 0 above 405. Die-level hop max 368.2 um, 0 long hops, 0 unreachable, release max 160 clocks.
- The lane's 20 plan edges above 405 (max 431.3, 8 types) do not exist in the bound trees. No row needed.
- START (reach_rules rule 1, 127 types): reader worst 393.3 um (sle_fe_v2), writer worst 402.1 um
  (sle_fw_v2__cl69f5e854), 0 above 405. Collector reach: 0 edges over.
- SC reset localization (590) is not in M2 and rides N. Not checked here.

Mixed-edge rule (half-cycle hop <= 180 um): 0 hops to check.
- Plan `reset` has no relay_lockup (neither negedge nor latch form); START mode broadcast.
- Bound RTL, 414 files: 24 always blocks, all posedge clock. Every `negedge` is an async reset term. 0 falling-edge relays.
- Keep it so. 14,184 of the 46,120 relay edges cross clock taps. If hold ever calls for relay_lockup on QC, the negedge form
  puts hops of up to 402.7 um on a half cycle, and the latch form leaves a 201 um half hop on every hop above 360 um.

Cycle adds:
- RS0 +11 lane-cycles on 7 lanes (coll_n rx_s0 / fltk / fltv 20 -> 21; coll_s rx_s1 / rx_s2 / fltk / fltv 19 -> 21):
  justified. coll_regen needs core->face = face->core per port; beaa had 21 vs 20 and 21 vs 19. Both new bus groups
  (4 and 6 lanes) are at 21 on every lane. 14 latency groups, 0 unequal.
- G +33 on 19 lanes, measured l2d -> beaa: fixed_cycles +33 exactly (11 x_fe_fw_p1 lanes +1 / +2, 6 x_fw_st_b lanes +2,
  2 st_eo_st_wi lanes +1), net +30 cycles on those lanes. Justified by the station rows (756 um routes cut to 252 um hops).
- Whole die: 1,921 lanes, 21,749 (l2d) -> 21,601 (beaa) -> 21,612 (M2) lane-cycles. The re-frame changed clock_landing only
  on 865 lanes (-176). 0 negative clock_landing. Longest lane 53.

Stale rows:
- The stale 406-member extra (sha 600980) is not in the M2 spec. M2BR consumed exactly two extras: fresh CB16 e2f94854 and
  candidate_inner 46a62e7f (INPUTS_ISOLATED.json).
- Fresh vs stale: 468 vs 406 members, 363 common, 243 of those changed pad, 105 new, 43 dropped.
- The stale table that remains is the R8 seed (B2).

CB16 regeneration vs producer: consistent.
- 7 of 7 receipt hashes match the files on disk (6 inputs incl. cb16_pads.py c5be5c4f, 1 output).
- I re-ran the unchanged producer on the same inputs: output byte-identical, sha e2f94854.
- 468 members (124 lane, 344 inner), 48 clusters, 841,932 pad FF. landed = bound + pad on 468 / 468. Pads 1-12, 0 negative.
- bound = M2 lane cycles on 124 / 124 lane members. 0 members on the 7 lanes M2 changed. The table fits the M2 plan.

## (2) What qualifies CB16

M2BR does not: no report exists. On the M3 final bind (BQ, or BR if clean) all of these must hold:
1. bind_report errors = 0. In particular R8_STALE 0, PARAM_REGEN 0 (no "no column pad up to 9", no seam shift),
   TYPE_SPLIT 0, R8_STRAP_PAD 0.
2. INPUTS_ISOLATED extra_tables[0] sha = e2f94854. If M3 changes any c16 lane, regenerate first and re-check
   bound = lane cycles on all lane members.
3. All 468 members applied, 0 unmatched, pad FF 841,932.
4. `qc_r8_pinned.sh check` PASS on the final tag. The table was built on R8 base 027d, so the R8 the bind derives must
   agree with it on the 624 crossing members; a single R8_STALE on a c16 member means it does not.
5. coll_regen: every slice / side tree balances with column pads <= 9; W5 S = [0, 0, 0, 0] as in the replay; the -12 / -10
   root joins are gone.
6. LATCHECK PASS 1,921 / 1,921 as-bound, hcparam 0 mismatches, G0 0 latency errors (today 4).

## Advisory (not blocking)

- R-REACH-4 fwd_source, 2 types: slw_su_c__cl19bb38ef 12 outputs up to 1,895.3 um from their tap, cbn_q00__cldbcda913
  5 outputs up to 974.7 um; a tap sits within 38 / 15 um. Scripted and free: `reach_rules.py fix --rules 4`. Put the
  su_c one in M3; cbn_q00__cldbcda913 is the NB type and goes with N.
- bind.py:3102 should refuse an auto-variant name that exists in the plan instead of overwriting it (tool lane).
- plan_gate_pre should run bus_pads(): it passed a plan that G0 fails 40 minutes later.
- R-REACH-3 window_far 34 types, GEOM-INHERITED 40 sites: inherited.

## Not checked

SC reset rows (N), cb setup (kit placement order, r523), routed timing of any M2 type, the seam-bundle member dump
(lane diagnostic m2br_sctx_1117 still running), whether E3 / W3 are otherwise equal to their base type, the NB slot.

# OPUS-FIX-S81-SVC-R7 handoff (08:3x-11:0x PST 11-21; newest first). STOOD DOWN on context -> successor OPUS-FIX-S81-SVC-R8.
Nothing signed or exported yet.

## STOOD DOWN 11-21 11:0x PST
LIVE (successor: re-arm waiters FIRST):
- chain10i epyc10 PID 224179: /srv/opentallas-scratch2/claude/opus-fix-s81-svc-r5/bind_hi4x/chain10i.sh (posts as R7): split(done 18:16Z, OK)
  -> elab -> strict bind -> LATCHECK -> STATE -> att kit prep -> place -> route (KSTATE). Old outputs renamed *.h1.
- chain_rest8i epyc8 PID 2379962: bind_hi4x/chain_rest8i.sh: waits epyc10 STATE green -> rsync -> rest kit prep/place/route (KSTATE_REST).
  Verified in the new plan_c: rest piece 0 core taps, att 32, att physical_inst = u_bound.u_u_rsv_u_att_u_a_..._u_c (matches bound leaf).
hi4 (svc_hi_dsdv_svc_rs__t4 x split): chain10h (H8 base) strict bind + LATCHECK GREEN (881/881) 17:53Z, both kit preps failed kit_rtl:
  core taps not moved with the x_epoch-repacked cores + census-grouped physical_inst. Fix = base ub (bind_hi4x/mk_ub.py:
  tap = core origin + (78.828, 0.24), the R0 rule on 32/32 sibling taps) + private type_split patch (core tap follows its core, fails
  closed off-core; j8/patch_ts_coretap.py). MAIN COMMIT of that patch + 2 tests (lane clone epyc10 opus-fix-s81-svc-r7/repo, uncommitted,
  test logic verified by direct call; pytest needs a wider sparse cone): owner question posted to FLOW-STRIPBODY-1121 (one commit owner).
J7 FORM (R4 ask 10:00): plan-only merge onto J7 v5 CONFLICTS (j7hi4/steps.txt, build.log). J7's hi4 drifted from H8 r5b: edge_clocks 1 row,
  landing_contract collector_children 1 + pins 3, 3 ports, and 280/873 lanes die-wide. Recipe for a J7 GEN: hi4 type := ub hi4 + J7's
  versions of those clock rows, + J7's 3 ports; type_split spec (bind_hi4x/spec_x_epoch_r5.json) with the J7 tree's landing sidecar;
  output PLAN + FILE eW_sidecar + MANIFEST defines OT_SVC_ATT_LAND_SRAM/OT_SVC_ATTCUT (RTL claude/s81-svc-r5-land-sram-1121 @9bd318e90366,
  NOT merged) -> R4 candJ7d gate. COORD decision pending: (a) GEN by ~19:00 PST for the 20:00 cut, else (b) J8. hi4 rows to assembly only
  after BOTH kit preps are clean (COORD).
REACH>405 svc 8: GEN svc_s1 handed to R4 (epyc10 opus-fix-s81-svc-r7/reach/gen/mkft_svc_s1.py {IN} {OUT}, md5 24c17b27): kit S0 = input pin,
  +1 station as the new S1 via ft_add_station, 8/8 closed on v5, 6 lanes +1/+2. It imports from the lane clone, so keep it.
J8 (15 svc split types, COORD: J8): x cuts between windows are impossible on 8 types (2.1 um gaps, no 8.64 lattice point), so I used y cuts.
  Generator epyc10 opus-fix-s81-svc-r7/j8/gen16yc3.py (R6 gen16 ported to axis y by checked edits mk_gen16y.py/mk_corr*.py/mk_tapfix.py:
  att band [0,Y], W FT corridor variants, core taps follow cores). Composes 5/7 hi: pvso t1/t2 + rs t2 @Y1935.36, rs t5 @2194.56,
  rs t6 @1987.2 + 112.32 um W corridor (out_y/out_yc/out_yc2; rerun with gen16yc3 for the tap fix). Fails: rs t1 (FT hop / pack),
  rs t3 (attn_i2 landing band storage). lo (8): 72% macro by area, already <400k cells -> asked COORD whether lo needs a split (default: no).
  Next: private y split (type_split axis y, parts [_att, ""], keep 1) + strict bind on rep svc_hi_dsdv_svc_rs__t2.

# OPUS-FIX-S81-SVC-R7 handoff (started 2026-11-21 08:3x PST; newest first). Succeeds OPUS-FIX-S81-SVC-R6.
Nothing signed or exported yet.

## 11-21 10:2x PST STATE
hi4 (svc_hi_dsdv_svc_rs__t4 x split, J7): chain10h strict bind + LATCHECK GREEN 17:53Z (881/881). Rows posted to S81-J6-ASSEMBLY-R4
(post 'ROWS GREEN hi4 J7'). COORD: rows go to assembly only after the rest part preps clean -> tell R4 when chain10i preps both parts.
Both kit preps failed kit_rtl: (a) rest part kept att core tap u_rsv.u_att.u_a.u_eng.g_t[0]..g_h[0].u_c.clk, because the x_epoch repack moved
all 32 attn cores without their taps (offset should be core origin + (78.828, 0.24), the R0 rule on siblings); (b) att clk_c0: physical_inst was
census-grouped u_bound.u_u_rsv_09_u_u_att_u_a_...; the piece's bound leaf is u_bound.u_u_rsv_u_att_u_a_... (flattened inst).
FIX: bind_hi4x/mk_ub.py -> split-hi4-band-test/plan_svc_hi4_x_epoch_ub.json (32 taps re-sited, 32 physical_inst); private type_split
patched (core tap follows its core, fails closed off-core: j8/patch_ts_coretap.py). Main commit: same patch + 2 tests in lane clone,
waiting on FLOW-STRIPBODY-1121 (one commit owner for type_split.py). If no answer, push via ot-push-main after their commit.
LIVE (waiters needed):
- chain10i epyc10 PID 224179 (bind_hi4x/chain10i.sh, posts as R7): split -> elab -> strict bind -> LATCHECK -> STATE -> att kit prep/place/route (KSTATE).
- chain_rest8i epyc8 PID 2379962: waits STATE green -> rest kit prep/place/route (KSTATE_REST). Old outputs renamed *.h1.
REACH>405 svc 8: GEN svc_s1 handed to R4 (epyc10 opus-fix-s81-svc-r7/reach/gen/mkft_svc_s1.py {IN} {OUT}; md5 24c17b27).
J8 (COORD ruling: 15 types to J8): x cut between windows impossible on 8 types (2.1 um gaps, no 8.64 grid point). y cut (att band bottom)
generator j8/gen16yc3.py (gen16 port + W corridor + core taps follow cores). Composes 5 of 7 hi: pvso t1/t2 + rs t2 at Y 1935.36, rs t5 at
2194.56, rs t6 at 1987.2 + 112.32 um W FT corridor. Fails: rs t1 (FT hop/pack), rs t3 (attn_i2 landing band). lo (8): 72% macro, already
<400k: asked COORD whether lo needs a split at all (default: no split, own rep kit read). Outputs j8/out_y, out_yc, out_yc2.
Lane clone epyc10 opus-fix-s81-svc-r7/repo (main 197076cf03 + type_split patch, uncommitted). The svc_s1 GEN imports from it; keep it.
NEXT: chain10i STATE -> KSTATE/KSTATE_REST; post rest-prep-clean to R4; sign-off read (DRC 0, TT >= -42, FF hold >= 0, LEC, post-hook CTS); export.

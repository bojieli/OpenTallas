# side_rest / side_softplus LEC with lec.eq_const_resolve (HBM-CORES-REBAL-7, 2026-10-28 10:08 PDT)

Both diagnostic reruns: shared 9335c29df3 lec.py, --reuse of the kit AIGs, gate unchanged (CHECKED from lec.json).

| core | before (main lec.py) | with eq_const_resolve |
|---|---|---|
| side_rest _c20ek2s | NOT EQ, cp 23907, differ 1462 (u_egs g_dig 466+1, u_div 33) | NOT EQ, cp 23843, differ 1462, same groups (3256 s) |
| side_softplus _c20ek2s | NOT EQ, cp 28476, differ 1300 (all u_sp g_h[1..8].u_a.g_fast.u y/s2_val/s2_exp/err) | NOT EQ, same 1300 (4524 s) |

eq_const_resolve DID run (log: 1447/475/24/28/23 eq->const rewrites per round), but the rewritten constants were then
DROPPED by noreset_filter ("not that constant in the reset state"): e.g. u_egs rem_stage[0][71..], g_dig[5].src_rem[12..],
rad_stage[0][614..], u_div r_zero/f1_zero/f2_zero. So REBAL-6 cause (b) (eq blocks the base case) is NOT the cause.
Common cause for all three groups: unreset feed-forward constants deeper than the LEC reset-state window
(OT_LEC_RESET_CYCLES 4 + release 8 edges):
- u_div: zero flag, a = 1.0 constant, 18 unreset stages (ZERO_RST=1 fixes this one locally).
- u_egs (fsqrt): structural shift-in zeros rad_stage/rem_stage/root_stage through the digit-recurrence stages.
- side_softplus u_sp Horner: s1_sub = sign(pm[k]) ^ sign(coef(k)); pm[k] = pa[k-1]*u2 with u2 = u*u (sign 0) and
  positive coefficients, so s1_sub/s2_zero are constant 0 through m_u2 + k*(LM+LA) unreset stages.
Synthesis removal is legal; not design bugs. Existing tool paths (no new check): (i) a die reset contract
(KIT/reset_contract.json, schema opentallas.reset_contract.v1, proven die reset length + caught mutant) raises
OT_LEC_RESET_CYCLES; (ii) OT_LEC_RAW_BASE_STEPS (opt-in raw prefix bases; S81 uses 6) -- side_rest probe with 24 running.

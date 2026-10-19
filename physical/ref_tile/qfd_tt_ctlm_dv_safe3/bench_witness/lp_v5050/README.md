Generated lp.py lockstep bench (random inputs, flat qfd_tt_ctlm_dv_lpf vs landed qfd_tt_ctlm_dv_lpf_lp), Verilator 5.050,
fleet ot-epyc4 (units oth-ubuntu-1175519/1176018/1175529/1175670/1176022-1792453167), source 044e6d93a (branch claude/qw-ctlm3-1019).
Same witnesses apply to qfd_tt_ctlm_dv_safe3n (identical RTL).
- AUDIT PASS; AUDIT-UNLAND FAIL (expected; port_regions check restored in lp.py audit).
- MUT0 PASS 50,422 comparisons, flat reference reset depth 3 UNCHANGED, warm 33 (was 36): the 12-cycle dc first-word loss is gone
  in RTL (landing_reset_lead), not masked.
- MUT5 (landing rq released one edge late = the pre-fix RTL) FAIL 13 mismatches, port dc from cycle 34: the old MUT0 signature.
- MUT1 (landing 0 bypassed) FAIL 9,869; MUT2 (landing 0 read K+1) FAIL 8,359; MUT4 (u_gi reset one stage late) FAIL 13.
Fail regex for every mutant: "LP_LOCKSTEP FAIL"; pass regex for MUT0: "LP_LOCKSTEP PASS".

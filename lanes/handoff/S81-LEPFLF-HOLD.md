# S81-LEPFLF-HOLD handoff (Opus 5.5; from 11-23 22:40 PST). One job: lepe_mu_LP t2 f_lf[2] hold -11.86 structural fix (from S81-OPEN-DEMAND REPAIR-CAP-LEPFLF).
Brief: localhost scratchpad split_brief.txt + rules.txt + resume_1123b.txt. Local work copy: scratchpad lepflf/.
## Cause (kit FAM-S81-LEPE-4 dsdv_slice_lepe_mu_LP__t2_1122050440, epyc7; 5_global_route.rpt == final grt ws)
launch hard core u_u_lnl1 (ot_s81_mu72_lnland) k_st[1], ck_k = early-core port clk_c4 (src -16, CK->k_st 354.3 => 338.4);
zero logic (f_lf[2] = lf[2] = l1_st[1]), wire 0.30 ps; capture clk_t34 leaf 315.6 +25 unc +10 hold = 350.5.
## Fix LEPFLF-LFNEG-1
- RTL: bare selector OT_S81SL_LEP_LFNEG in physical/die_plan/s81/bind/source_modules/portfix178/ot_s81sl_slice_lep.sv
  (and rtl/ copy): negedge lf_n, posedge lf <= lf_n. main f9681588a5. Tree copy (amd1_tree 9032ca63) patched = f3c835ba.
- Ops: E9 /srv/opentallas-scratch2/claude/s81-lepflf-hold/row/ops_lepflf_lfneg.json (add define to mu_LP t2 verilog_defines).
- LEC/bench: E9 /srv/opentallas-scratch3/claude/s81-lepflf-hold/bench (lec1.log SUCCESS, lec_mut FAIL, hab/hab0 traces identical, host PASS).
- Row run: E9 row/run_row2.sh (c7a p5_deadin + op -> PRE vs base -> elab + scoped strict mu_LP t2, asbuilt copy w/ abs path to patched lep).
  row/run_row.sh first try: compose failed (missing base_sha12); its unit still produced pre_base.log.
## Next
ROW-REBASED to S81-ALLFIX-INT (cc FABLE-RC-ALL, S81-OPEN-DEMAND) after PRE + scoped strict; read c8 mu_LP t2 probe when INT has it; if violator gone -> report and stop.

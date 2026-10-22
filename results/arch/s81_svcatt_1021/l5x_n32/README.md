# l5x adder native32 (S81-ELEM2-SVCATT 10-21)
Whole-core G4 attw NORST+PINREG census (FAIL 8983, attribution tools/s81_dv/svc_rs/svcatt/attrib.py): ~5,760 of the
violations are inside the 320 merge adders ot_hdc_fp32_add_f12_l5x (u_m g[*].g_h[*].u_a.g_f5) -- the primitive itself
fails standalone (gold_census.log: 18 viol, max 123: K6 dab/dba, K3 lz, K3 w_sub, K5 rnd_c/u_byp, sum carry).
Fix (physical only, same function/cycles/reset): mapped OT_FP_DATA_NORST l5x -> bound graph limit 32 (25 kept driver
copies, ledger.json structural invariant) -> rtl/hdc/v41x/ot_hdc_fp32_add_f12_l5x_n32.v, selected by OT_F12_ADD5_N32 in
ot_hdc_v41x_qaddf g_f5.  Proof: yosys equiv_simple/equiv_induct gold(mapped l5x) vs n32: 35/35 outputs proven
(gold_equiv.log); n32 standalone native PASS max32 (n32_census.log); in the use_-mux merge context PASS max32
(wrap_n32_census.log).  Simulation benches keep the RTL l5x (no cell models); the define is physical-only.

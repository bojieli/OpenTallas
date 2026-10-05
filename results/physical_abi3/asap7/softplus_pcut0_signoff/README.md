# Softplus PCUT=0 signoff candidate

This is a preserved failed verdict for the 0.833 ns WC/BC signoff-target experiment on the current W11 short-softplus RTL. The candidate was wrapped as `ot_hdc_v41x_softplus_pcut0` so the source default remained unchanged. Yosys 0.68 failed during parameter elaboration with an internal duplicate-module assertion while deriving the repeated `ot_hdc_hstep`/`ot_hdc_fp32_mul_x2` CUT=0 instances. The record is intentionally retained as a failed verdict; it carries the invoked source hashes and tool metadata. No timing result was inferred.

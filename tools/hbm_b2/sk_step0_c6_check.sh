#!/bin/bash
# DIE-HBM-60/LEC C6 bench: new ot_hdc_sk_step0_en_phys vs the module before the sign-constant change.
#   tools/hbm_b2/sk_step0_c6_check.sh [old-rev] [N] [seeds...]   (run from the repo root; iverilog -g2012)
set -euo pipefail
OLD=${1:-19af2d0dd06}; N=${2:-4000}; shift 2 || true; SEEDS=${*:-1 2 3}
F=rtl/hbm_accel/cores_split/sk_en_q4/ot_hdc_sinkhorn_se_phys.sv
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
git show "$OLD:$F" | sed -n '/^module ot_hdc_sk_step0_en_phys/,/^endmodule/p' \
    | sed 's/^module ot_hdc_sk_step0_en_phys/module ot_hdc_sk_step0_en_phys_old/' > "$T/old.sv"
grep -q 'output reg  \[511:0\] b_q' "$T/old.sv"     # the old form: b_q a 512-bit register
rc=0
for s in $SEEDS; do
    iverilog -g2012 -o "$T/sim" -P sk_step0_c6_tb.N="$N" -P sk_step0_c6_tb.SEED="$s" -s sk_step0_c6_tb \
        tools/hbm_b2/sk_step0_c6_tb.sv "$T/old.sv" "$F" rtl/hdc/v41/ot_hdc_sk_arith.sv rtl/hdc/v41/ot_hdc_sk_recip_rom.sv
    out=$(vvp -n "$T/sim"); echo "$out"
    grep -q "SK_STEP0_C6 PASS" <<< "$out" || rc=1
done
exit $rc

#!/bin/bash
# pv_join port-copy equivalence: old module (git HEAD~ text, renamed pvj_old) vs new, 6000 random cycles + mid reset + faults.
set -e; W=$(git -C "$(dirname "$0")" rev-parse --show-toplevel); T=$(mktemp -d); F=rtl/hdc/nearhbm/ot_qwen_tp8_pv_wide_pair.sv
git -C $W show ${OLD:-6da688b91f}:$F | sed -n "/^module ot_qwen_tp8_pv_join_t/,/^endmodule/p" | sed "s/module ot_qwen_tp8_pv_join_t/module pvj_old/" > $T/old.sv
sed -n "/^module ot_qwen_tp8_pv_join_t/,/^endmodule/p" $W/$F > $T/new.sv
iverilog -g2012 -o $T/sim $(dirname "$0")/tb_pvjoin_portcopy_eq.sv $T/old.sv $T/new.sv $W/rtl/hdc/ot_hdc_fp32_add_lat.sv $W/rtl/hdc/ot_hdc_fastfp.sv $W/rtl/hdc/ot_hdc_prefix.sv
vvp -n $T/sim | grep DONE

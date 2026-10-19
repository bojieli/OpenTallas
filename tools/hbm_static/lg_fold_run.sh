#!/bin/bash
# LG tap fold lockstep bench (coordinator 0db 10-17). usage: lg_fold_run.sh OUT [MUT]
set -euo pipefail
out=$1; mut=${2:-0}; mkdir -p "$out"
iverilog -g2012 -s tb_hgi_lg_pair_tap_fold -Ptb_hgi_lg_pair_tap_fold.MUT=$mut -o "$out/fold.vvp" rtl/hdc/ot_hdc_delay.sv \
 rtl/hbm_accel/generic/peers/ot_hgi_sfu_lg_pair_leaf.sv rtl/hbm_accel/generic/peers/ot_hgi_sfu_lg_pair_tap_leaf.sv \
 rtl/hbm_accel/generic/vm/static/ot_hbm_vm_lg_pair_tap.sv rtl/hbm_accel/generic/vm/static/ot_hbm_vm_lg_static_bank.sv \
 rtl/hbm_accel/generic/vm/static/ot_hbm_vm_lg_static_bank_term.sv rtl/test/hbm_accel/generic/tb_hgi_lg_pair_tap_fold.sv
vvp "$out/fold.vvp"

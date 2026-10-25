#!/usr/bin/env bash
set -eu
O=${1:?out}; mkdir -p "$O"
SL=rtl/dsrom_sys/s81_dv/slice
eval "$(sed -n '/^V=verilator/,/^D=/p' $SL/test/run_lep_idx_bench.sh)"
eval "$(sed -n '/^build() {/,/^}/p' $SL/test/run_lep_idx_bench.sh)"
build abmu tb_s81sl_lep_mu_ab_tpr tb_s81sl_lep_mu_ab_tpr.sv -GP_RX_SRAM=1 -GP_IN_PIPE=1 -GP_NATIVE32=1
"$O/abmu/Vtb_s81sl_lep_mu_ab_tpr" > "$O/abmu.log" 2>&1
grep '^PASS lep_mu' "$O/abmu.log"
build mut_copy tb_s81sl_lep_mu_ab_tpr tb_s81sl_lep_mu_ab_tpr.sv -GP_RX_SRAM=1 -GP_IN_PIPE=1 -GP_NATIVE32=1 +define+OT_S81SL_LEP_MUT_WRONGCOPY
"$O/mut_copy/Vtb_s81sl_lep_mu_ab_tpr" > "$O/mut_copy.log" 2>&1
grep '^FAIL lep_mu' "$O/mut_copy.log"
build abtp tb_s81sl_lep_idxnet tb_s81sl_lep_idxnet.sv +define+OT_S81SL_TEST_AB_TPR +define+OT_S81SL_TEST_HAB_TP
"$O/abtp/Vtb_s81sl_lep_idxnet" > "$O/abtp.log" 2>&1
grep '^PASS lep_idxnet' "$O/abtp.log"
echo 'LEP_AB_TPR_GATE PASS'

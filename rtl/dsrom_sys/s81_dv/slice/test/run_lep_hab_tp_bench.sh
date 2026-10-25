#!/usr/bin/env bash
# HOST + reserve copy-B + TP4 endpoint. Uses the existing independent MU queues
# and the TP/query seven-endpoint scoreboard; no physical sign-off is claimed.
set -eu
O=${1:?output directory}; mkdir -p "$O"
SL=rtl/dsrom_sys/s81_dv/slice
eval "$(sed -n '/^V=verilator/,/^D=/p' $SL/test/run_lep_idx_bench.sh)"
eval "$(sed -n '/^build() {/,/^}/p' $SL/test/run_lep_idx_bench.sh)"
build habmu tb_s81sl_lep_mu_hab_tp tb_s81sl_lep_mu_hab_tp.sv -GP_RX_SRAM=1 -GP_IN_PIPE=1 -GP_NATIVE32=1
"$O/habmu/Vtb_s81sl_lep_mu_hab_tp" > "$O/habmu.log" 2>&1
grep '^PASS lep_mu' "$O/habmu.log"
build mut_copy tb_s81sl_lep_mu_hab_tp tb_s81sl_lep_mu_hab_tp.sv -GP_RX_SRAM=1 -GP_IN_PIPE=1 -GP_NATIVE32=1 +define+OT_S81SL_LEP_MUT_WRONGCOPY
"$O/mut_copy/Vtb_s81sl_lep_mu_hab_tp" > "$O/mut_copy.log" 2>&1
grep '^FAIL lep_mu' "$O/mut_copy.log"
build habtp tb_s81sl_lep_idxnet tb_s81sl_lep_idxnet.sv +define+OT_S81SL_TEST_HAB_TP
"$O/habtp/Vtb_s81sl_lep_idxnet" > "$O/habtp.log" 2>&1
grep '^PASS lep_idxnet' "$O/habtp.log"
echo 'LEP_HAB_TP_GATE PASS'

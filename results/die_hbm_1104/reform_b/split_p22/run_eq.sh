#!/bin/bash
# HBM-REFORM-B3 part 22: kport_q ACK_PIPE bench. run_eq.sh REF_KPORT_SV OBJ  (repo root as cwd)
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator; R=$1; O=$2; S=rtl/hbm_accel/loader/service_native; D=results/die_hbm_1104/reform_b/split_p22
for M in 0 1; do rm -rf $O/m$M
 $V --binary --timing -j 16 -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN --top-module tb_kq -GMUT=$M -Mdir $O/m$M -o sim $D/tb_kq.sv $R $S/ot_hbm_svc_wb_kport_q.sv $S/ot_hbm_svc_wb_cutthrough_cdc.sv $S/ot_hbm_svc_pc_ctrl_leaf.sv $(git grep -l "^module ot_hbm_accel_cdc_fifo" -- rtl | grep -v test | head -1) rtl/lib/ot_reset_sync.sv physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v > $O/b$M.log 2>&1 || { tail -12 $O/b$M.log | cut -c1-200; exit 2; }
 echo "MUT $M: $($O/m$M/sim 2>&1 | grep -E "^KQ|rror" | tr "\n" " " | cut -c1-200)"
done

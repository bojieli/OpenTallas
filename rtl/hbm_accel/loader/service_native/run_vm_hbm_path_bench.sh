#!/usr/bin/env bash
# H-NETLIST/vmsm 2026-10-15: benches of the static HBM -> VM write path (G-VM-HBM-PATH) and the stack fault home.
#   run_vm_hbm_path_bench.sh OUTDIR      (Icarus iverilog -g2012; ~10 min single core)
# 1) ot_hbm_svc_vm_kshare unit bench: 3 clock ratios + mutants MUT=1 (window does not drain the group) / MUT=2 (PC hash)
# 2) quadrant integration (fill calendar + 8 kshare + 8 vmdel lanes + 32 K-port controller models): MUT=0 / MUT=1 (early start)
# 3) ot_hbm_svc_stack_fault: MUT=0 / MUT=1 (wrong CA pair)
# 4) ot_hbm_xp_aq_tree13_fmt vs the closed ot_hbm_xp_aq_tree13 (FP4=0/1 equal; mode and MUT controls differ)
set -u
out=${1:?outdir}; mkdir -p "$out"; R=$(git rev-parse --show-toplevel)
S=$R/rtl/hbm_accel/loader/service_native
DEP="$S/ot_hbm_svc_pc_ctrl_leaf.sv $S/ot_hbm_svc_async_fifo.sv $R/rtl/lib/ot_reset_sync.sv"
SRAM="$R/physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v $R/physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v"
AQ="$R/physical/hbm_xp_aq_tree13_1014/ot_hbm_xp_aq_tree13.sv $R/physical/hbm_xp_aq_tree13_1014/ot_hbm_xp_aq_scale13.sv $R/rtl/hdc/ot_hdc_delay.sv"
run(){ name=$1; shift; top=$1; shift; args=$1; shift
  iverilog -g2012 -s $top "$@" -o "$out/$name.vvp" > "$out/$name.build.log" 2>&1 || { echo "BUILD_FAIL $name"; return; }
  vvp -n "$out/$name.vvp" $args > "$out/$name.log" 2>&1; echo "$name: $(grep -E 'PASS|FAIL|DIFF' "$out/$name.log" | tail -n 1)"; }
for M in 0 1 2; do
  run ks_m$M tb_hbm_svc_vm_kshare "+WINDOWS=8" -P tb_hbm_svc_vm_kshare.MUT=$M $S/tb_hbm_svc_vm_kshare.sv $S/ot_hbm_svc_vm_kshare.sv $DEP &
done
run ks_m0_fasthbm tb_hbm_svc_vm_kshare "+WINDOWS=8 +HBM_HALF=400 +STR_HALF=700" $S/tb_hbm_svc_vm_kshare.sv $S/ot_hbm_svc_vm_kshare.sv $DEP &
run ks_m0_slowhbm tb_hbm_svc_vm_kshare "+WINDOWS=8 +HBM_HALF=700 +STR_HALF=400" $S/tb_hbm_svc_vm_kshare.sv $S/ot_hbm_svc_vm_kshare.sv $DEP &
for M in 0 1; do
  run q_m$M tb_hbm_vm_hbm_path_q "" -P tb_hbm_vm_hbm_path_q.MUT=$M $S/tb_hbm_vm_hbm_path_q.sv $S/ot_hbm_svc_vm_kshare.sv $DEP $SRAM \
    $R/rtl/hbm_accel/generic/vm/static/ot_vms_calendar_static.sv $S/split/ot_hbm_svc_static_vm_delivery_split.sv &
  run sf_m$M tb_hbm_svc_stack_fault "" -P tb_hbm_svc_stack_fault.MUT=$M $S/tb_hbm_svc_stack_fault.sv $S/ot_hbm_svc_stack_fault.sv &
done
P=$R/rtl/hbm_accel/generic/peers
for cfg in "0 0 0" "1 1 0" "0 1 0" "0 0 1"; do set -- $cfg
  run aq_f$1_r$2_m$3 tb_hbm_xp_aq_tree13_fmt "" -P tb_hbm_xp_aq_tree13_fmt.FP4=$1 -P tb_hbm_xp_aq_tree13_fmt.REF_FP4=$2 -P tb_hbm_xp_aq_tree13_fmt.MUT=$3 \
    $P/tb_hbm_xp_aq_tree13_fmt.sv $P/ot_hbm_xp_aq_tree13_fmt.sv $AQ &
done
wait

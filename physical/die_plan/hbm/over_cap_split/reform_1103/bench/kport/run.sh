#!/bin/bash
# run_kp.sh REPO OUT : bench the split composition with the unchanged quadrant WB bench.
R=$1; O=$2; mkdir -p $O; cd $R
n=rtl/hbm_accel/loader/service_native; K=rtl/hbm_accel/cores_split/reform_1103/ot_hbm_svc_wb_kport_q
vl=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator; command -v $vl >/dev/null || vl=verilator
SRC="$n/tb_hbm_svc_wb_kshare_qh.sv $K/ot_hbm_svc_wb_kp_root.sv $K/ot_hbm_svc_wb_kp_hub.sv $K/ot_hbm_svc_wb_kport_q__split.sv $n/ot_hbm_svc_wb_kport.sv $n/ot_hbm_svc_vm_kshare.sv $n/ot_hbm_svc_wb_cutthrough_cdc.sv $n/ot_hbm_svc_async_fifo.sv $n/ot_hbm_svc_native_sector_pipeline_leaves.sv $n/ot_hbm_svc_pc_ctrl_leaf.sv $n/ot_hbm_svc_pc_ctrl_leaf_cfg.sv $n/tb_hbm_svc_command_dram_pipeline_fixture.sv rtl/model_ready_hbm_r14/ot_hbm_r14_stream_pc_strap.sv rtl/hbm_accel/service/ot_hbm_accel_cdc_fifo.sv rtl/lib/ot_reset_sync.sv rtl/lib/ot_rst_relay.sv physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v"
ls $SRC >/dev/null || exit 2
run(){ L=$1; E=$2; shift 2
 $vl --binary --timing -j 16 -O1 -Wno-fatal -Wno-lint -Wno-style --top-module tb_hbm_svc_wb_kshare_qh --Mdir $O/obj-$L -o sim -DKP_SPLIT_BENCH=2 "$@" $SRC > $O/build-$L.log 2>&1 || { echo "$L BUILD FAIL"; tail -4 $O/build-$L.log; return; }
 rc=0; timeout 900 $O/obj-$L/sim > $O/$L.log 2>&1 || rc=$?; rm -rf $O/obj-$L
 echo "$L expect=$E rc=$rc $(grep -E '^PASS|WB_INTEGRITY|FAIL' $O/$L.log | head -1 | cut -c1-160)"; tail -2 $O/$L.log | cut -c1-200; }
run e pass -GQE=1 & run w pass -GQE=0 & run e_wopen pass -GQE=1 -GWOPEN=1 &
run mq fail -GQE=1 -GWBMUT=2 & run ms fail -GQE=1 -GWBMUT=3 & run mp fail -GQE=1 -GWBMUT=1 &
run mcr fail -GQE=1 -GWBMUT=11 & run mid fail -GQE=1 -GWBMUT=12 &
wait

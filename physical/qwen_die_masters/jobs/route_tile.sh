#!/bin/bash
# Margin route of the die tile master (qfd_tile / qfd_tile_e = ot_qwen_rom_tile_w12, 1,536 copies) in its r20c frame
# 266.952 x 1291.656 um: 10 x ot_rom_4096x266_m8 + 2 x ot_sram_1r1w_128x256_m1_r2c2, M2-M7 (die M8/M9 above).
# Margin RTL: MUL_LAT 8 (kept per-lane input register + decode register; tp2_t4 SS -83.8 class), KV_PREP 4 (CSA rows
# registered before the offset prefix sum; tp4_t4 SS -18.9 class) on the TARGET arithmetic (ACC 7 / TREE 7 / FAST_ISSUE 1).
# usage: route_tile.sh NAME   (env: SRC source snapshot, R run root, PD place density)
set -uo pipefail
NAME=$1; SRC=${SRC:?}; R=${R:?}; W=$R/$NAME; mkdir -p $W; cd $SRC
D=/src/physical/qwen_die_masters
S=""; for f in rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_delay.sv \
  rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_matvec.sv rtl/hdc/ot_qwen_me_array_w12.sv rtl/hdc/ot_qwen_rom_tile_w12.sv \
  rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_qwen_w12_matvec.sv \
  rtl/hdc/ot_qwen_w12_arith.sv rtl/proto/ot_fp32_add_rne_pipe.sv \
  physical/asap7_memory_macros/ot_rom_4096x266_m8/ot_rom_4096x266_m8_bb.v \
  physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2_bb.v; do S="$S --source $f"; done
export OT_ORFS_NUM_CORES=16 OT_SYNTH_TIMEOUT_SECONDS=unlimited OT_FLOW_TIMEOUT_SECONDS=unlimited
echo "$(date -Is) start $NAME src=$(cat SOURCE_COMMIT 2>/dev/null)" >> $W/STATUS
python3 tools/run_abi3_physical.py --view asap7 --top ot_qwen_rom_tile_w12 $S \
  --param GT=6144 --param NW=18 --param SMIN=7 --param CODE_BANKS=5 --param KV_VB=131072 --param KV_NH=2 \
  --param MEM_EXTRA=1 --param ACC_LAT=7 --param TREE_LAT=7 --param MUL_LAT=${MUL_LAT:-8} --param FAST_ISSUE=1 \
  --param KV_PREP=${KV_PREP:-4} \
  --macro-view ot_rom_4096x266_m8=physical/asap7_memory_macros/ot_rom_4096x266_m8 \
  --macro-view ot_sram_1r1w_128x256_m1_r2c2=physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2 \
  --macro-place-halo 2.16 2.16 --die-area 0 0 266.952 1291.656 --core-area 2.16 2.16 264.792 1289.496 \
  --pin-region '^(n_a|n_b|n_va)=left:300-880' --pin-region '^(t_out|t_vout|n_y|n_vy)=left:880-1100' \
  --pin-region '^(ib|ib_go|xl|tile_id|fault|rst_n|clk)(\[|$)=right:450-850' --pin-region '^kvw_=right:870-1100' \
  --routing-layers M2 M7 --clock-port clk --clock-period-ns 0.770 --clock-uncertainty-ns 0.06 \
  --clock-uncertainty-hold-ns 0.025 --orfs-corner WC --hold-corners WC,BC --io-delay-fraction 0.2 --stages pnr \
  --place-density ${PD:-0.45} --hold-margin-ns 0.02 --synth-timeout-seconds unlimited --flow-timeout-seconds unlimited \
  --orfs-var ADDER_MAP_FILE= --orfs-var NUM_CORES=16 --orfs-var SDC_FILE=$D/tile_p770.sdc --orfs-var QDM_SDC_DIR=$D \
  --orfs-var PDN_TCL=/src/physical/qwen_slab_m5/pdn_m5.tcl --orfs-var MACRO_PLACEMENT_TCL=$D/macro_place_tile.tcl \
  --orfs-var 'GLOBAL_ROUTE_ARGS=-congestion_report_iter_step 5 -verbose -critical_nets_percentage 0' \
  --step-tcl PRE_CTS=physical/qwen_die_masters/pre_cts_skew.tcl --step-tcl POST_CTS=physical/qwen_die_masters/post_plain.tcl \
  --step-tcl PRE_GLOBAL_ROUTE=physical/qwen_die_masters/pre_ref_skew.tcl --step-tcl POST_GLOBAL_ROUTE=physical/qwen_die_masters/post_plain.tcl \
  --step-tcl PRE_DETAIL_ROUTE=physical/qwen_die_masters/pre_ref_skew.tcl --step-tcl POST_DETAIL_ROUTE=physical/qwen_die_masters/post_plain.tcl \
  --step-tcl PRE_FILLCELL=physical/qwen_die_masters/pre_ref_skew.tcl --step-tcl POST_FILLCELL=physical/qwen_die_masters/post_plain.tcl \
  --orfs-var 'CTS_ARGS=-sink_clustering_enable -repair_clock_nets -delay_buffer_derate 0.75' \
  --orfs-var OT_IO_SKEW=90 --orfs-var OT_IO_HOLD_SKEW=50 --orfs-var 'OT_REF_GLOB=*go_q*' \
  --orfs-var 'OT_IO_INTER=n_a*,n_b*,n_va,n_y*,n_vy,t_out*,t_vout' --orfs-var OT_IO_SKEW_INTER=150 \
  --slew-margin-percent 30 --purpose signoff_target --nickname-tag qdm_$NAME \
  --keep-workdir $W/work --force --output $W/physical.json > $W/flow.log 2>&1
echo $? > $W/flow.exit
# sign-off copy with the route's boundary settings bound (the STA container gets no environment)
{ echo 'set ::env(OT_IO_SKEW) 90'; echo 'set ::env(OT_IO_HOLD_SKEW) 50'; echo 'set ::env(OT_REF_GLOB) {*go_q*}'
  echo 'set ::env(OT_IO_INTER) {n_a*,n_b*,n_va,n_y*,n_vy,t_out*,t_vout}'; echo 'set ::env(OT_IO_SKEW_INTER) 150'
  cat physical/qwen_die_masters/io_ref_skew.sdc; } > $W/io_ref_skew_signoff.sdc
python3 tools/w18/corner_sta_ref.py --orfs-dir $W/work/orfs --extra-sdc $W/io_ref_skew_signoff.sdc \
  --macro physical/asap7_memory_macros/ot_rom_4096x266_m8 --macro physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2 \
  --output $W/corner_sta_ref.json > $W/sta_ref.log 2>&1
echo $? > $W/sta.exit
echo "$(date -Is) done flow=$(cat $W/flow.exit) sta=$(cat $W/sta.exit)" >> $W/STATUS

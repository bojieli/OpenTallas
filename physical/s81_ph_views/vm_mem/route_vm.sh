#!/bin/bash
# CLAUDE S81-PH VM: margin route of the VM memory subsystem ot_s81ph_vm_mem (NP 8, NB 32, QD 4: 128 SRAM macros) as a
# hard sub-macro of the VM slab.  VM = SERIAL 0.9 GHz domain: period 1.1111 ns; routed over-constrained by the
# margin SDC (setup uncertainty 123 ps = 60 + 63, IO 0.2 T + 150 ps vs vclk at the measured insertion), signed off at
# 1.1111 ns / 60 ps (signoff_unc60.sdc).  Copy of ../common/route_view.sh with a sub-macro pin plan (io_place.tcl,
# no generator master) and the SRAM macro view.
#   route_vm.sh <label>   env: SRC OUT PD (0.40) CORES (16) NEED (GB, 48) DW DH
set -u
lab=$1; W=$OUT/$lab; mkdir -p $W; cd $SRC
export OT_ORFS_NUM_CORES=${CORES:-16} NUM_CORES=${CORES:-16} OT_SYNTH_TIMEOUT_SECONDS=unlimited OT_FLOW_TIMEOUT_SECONDS=unlimited
DW=${DW:-1015.176}; DH=${DH:-2000.16}
MV=physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2
cat SOURCE_COMMIT > $W/SOURCE_COMMIT
echo "SRC=$SRC DW=$DW DH=$DH PD=${PD:-0.40} period=1.1111 margin" > $W/args
/srv/opentallas-scratch/admit.sh ${NEED:-48} -- python3 tools/run_abi3_physical.py --view asap7 --top ot_s81ph_vm_mem \
  --source rtl/dsrom_sys/s81_ph/vm/ot_s81ph_vm_mem.sv --macro-view ot_sram_1r1w_512x128_m4_r2c2=$MV --macro-place-halo 5 5 \
  --clock-port clk --clock-period-ns 1.1111 --clock-uncertainty-ns 0.06 --clock-uncertainty-hold-ns 0.025 \
  --orfs-corner WC --hold-corners WC,BC --io-delay-fraction 0.2 --sdc-append physical/s81_ph_views/common/io_vclk_m_770.sdc --stages pnr \
  --die-area 0 0 $DW $DH --core-area 0 0.54 $DW $(python3 -c "print(round($DH-0.54,4))") --place-density ${PD:-0.40} --routing-layers M2 M7 \
  --orfs-var PDN_TCL=/src/physical/s81_ph_views/common/pdn_view.tcl --orfs-var IO_CONSTRAINTS=/src/physical/s81_ph_views/vm_mem/io_place.tcl \
  --orfs-var ADDER_MAP_FILE= \
  --step-tcl PRE_CTS=physical/abi3/v41x_karb_repair_buffer_cap.tcl --step-tcl POST_CTS=physical/s81_ph_views/common/post_cts_vclk.tcl \
  --step-tcl PRE_GLOBAL_ROUTE=physical/abi3/v41x_karb_repair_buffer_cap.tcl \
  --slew-margin-percent 60 --hold-margin-ns 0.010 --purpose signoff_target --nickname-tag s81ph_$lab \
  --synth-timeout-seconds unlimited --flow-timeout-seconds unlimited \
  --keep-workdir $W/work --force --output $W/physical.json > $W/run.log 2>&1
echo "rc=$?" > $W/exit
python3 tools/w18/corner_sta.py --macro $MV --post-sdc physical/s81_ph_views/common/signoff_unc60.sdc --orfs-dir $W/work/orfs --output $W/corner_sta.json > $W/corner.log 2>&1
echo "corner_rc=$?" >> $W/exit
python3 tools/hbm_fmax_attn_abstract.py --orfs-dir $W/work/orfs --name ot_s81ph_vm_mem --out $W/view --macro-view $MV --tmp-dir $W/abs_tmp > $W/export.log 2>&1
echo "export_rc=$?" >> $W/exit
echo DONE >> $W/exit

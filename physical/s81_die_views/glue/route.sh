#!/bin/bash
# CLAUDE S81-RERUN: route one S81 die-glue view (generator master; top module of the same name in the glue RTL) at the
# generator's outline with every pin at the generator's position (physical/s81_die_views/ports/<die>/<master>, written
# by tools/s81_die_view_ports.py), calibrated closure-loop flow (adapted from physical/s81_ph_views route_view.sh).
#   route.sh <label> <master> [extra run_abi3_physical args, e.g. --pnr-stop-after cts]
# env: SRC, OUT, CK_SS_MEAN (calibrated insertion; planning 150 when absent), GLUE (glue RTL), SDCGEN (make_sdc_stn.sh),
#      CORES (8), PD (0.5), DIE (layer), SRCS (extra sources)
set -u
lab=$1; master=$2; shift 2
W=$OUT/$lab; mkdir -p $W $SRC/.views/$lab; cd $SRC
P=physical/s81_die_views/ports/${DIE:-layer}/$master
read DW DH < <(python3 -c "import json;d=json.load(open('$P/ports.json'));print(d['w_um'],d['h_um'])")
cp $P/io_place.tcl $SRC/.views/$lab/io_place.tcl
physical/s81_die_views/glue/${SDCGEN:-make_sdc_stn.sh} ${CK_SS_MEAN:-150} $SRC/.views/$lab/route.sdc
srcargs="--source ${GLUE:-results/rtl/dsrom_s81_fulldie_20261004/r9m215/dsfd_glue.sv} --source rtl/common/ot_fwd_link_stage.sv"
for s in ${SRCS:-}; do srcargs="$srcargs --source $s"; done
echo "master=$master DW=$DW DH=$DH L=${CK_SS_MEAN:-150} PD=${PD:-0.5} $*" > $W/args
export OT_ORFS_NUM_CORES=${CORES:-8} NUM_CORES=${CORES:-8} OT_SYNTH_TIMEOUT_SECONDS=unlimited OT_FLOW_TIMEOUT_SECONDS=unlimited
python3 tools/run_abi3_physical.py --view asap7 --top $master $srcargs \
  --clock-port ${CLK:-fi0} --clock-period-ns 0.833333 --clock-uncertainty-ns 0.06 --clock-uncertainty-hold-ns 0.025 \
  --orfs-corner WC --hold-corners WC,BC --io-delay-fraction 0.2 --orfs-var SDC_FILE=/src/.views/$lab/route.sdc --stages synth,pnr \
  --die-area 0 0 $DW $DH --core-area 0 0.54 $DW $(python3 -c "print(round($DH-0.54,4))") --place-density ${PD:-0.5} --routing-layers M2 M7 \
  --orfs-var PDN_TCL=/src/physical/s81_die_views/common/pdn_view.tcl --orfs-var IO_CONSTRAINTS=/src/.views/$lab/io_place.tcl \
  --orfs-var ADDER_MAP_FILE= \
  --step-tcl PRE_CTS=physical/s81_die_views/common/pre_cts_fclk_root_buf.tcl --step-tcl POST_CTS=physical/s81_die_views/common/post_cts_vclk.tcl \
  --step-tcl PRE_GLOBAL_ROUTE=physical/abi3/v41x_karb_repair_buffer_cap.tcl \
  --slew-margin-percent 60 --hold-margin-ns 0.030 --purpose signoff_target --nickname-tag s81g_$(echo $lab | tr -c "A-Za-z0-9_\n" _) \
  --synth-timeout-seconds unlimited --flow-timeout-seconds unlimited "$@" \
  --keep-workdir $W/work --force --output $W/physical.json > $W/run.log 2>&1
echo "rc=$?" > $W/exit
python3 tools/w18/corner_sta.py --post-sdc physical/s81_die_views/common/signoff_unc60.sdc --orfs-dir $W/work/orfs --output $W/corner_sta.json > $W/corner.log 2>&1
echo "corner_rc=$?" >> $W/exit

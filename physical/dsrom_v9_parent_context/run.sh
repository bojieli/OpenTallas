#!/bin/bash
set -eu
# Execute only in this agent's pinned clean source worktree on an admitted EPYC host.
: "${V9_PARENT_OUTPUT:?absolute persistent run root required}"
export OT_ORFS_NUM_CORES=4
python3 tools/run_abi3_physical_persistent.py \
 --persistent-workdir "$V9_PARENT_OUTPUT/work" --launch-receipt "$V9_PARENT_OUTPUT/launch.json" \
 --view asap7 --top ot_v41_v9_parent_clock_context \
 --source physical/dsrom_v9_parent_context/ot_v41_v9_parent_clock_context.sv \
 --source rtl/v41die/ot_v41_pair_pq_ld.sv --source rtl/v41die/ot_v41_retn_w17w10.sv \
 --source rtl/v41rom/ot_v41_ret.sv --source rtl/v41rom/ot_v41_kreg.sv \
 --source rtl/hdc/ot_hdc_cg.sv --source rtl/hdc/ot_hdc_delay.sv \
 --source rtl/proto/ot_fp32_add_rne_pipe.sv \
 --clock-period-ns 0.833333333333 --clock-uncertainty-ns .060 --clock-uncertainty-hold-ns .025 \
 --core-input-delay-min-ns .360 --core-input-delay-max-ns .727 \
 --output-delay-min-ns .360 --output-delay-max-ns .727 \
 --sdc-append physical/dsrom_v9_parent_context/boundary.sdc \
 --stages pnr --orfs-corner WC --hold-corners WC,BC \
 --orfs-var SYNTH_HDL_FRONTEND=slang \
 --die-area 0 0 1040.256 239.76 --core-area 2.16 2.16 1038.096 237.60 \
 --place-density .5 --orfs-var PLACE_DENSITY_LB_ADDON= \
 --orfs-var PDN_TCL=/src/tools/chip_assembly/tcl/pdn_w10_elem_m7_ir.tcl \
 --orfs-var FASTROUTE_TCL=/src/physical/dsrom_v9_parent_context/fastroute.tcl \
 --routing-layers M2 M8 \
 --step-tcl POST_PDN=physical/dsrom_v9_parent_context/regions.tcl \
 --step-tcl PRE_CTS=physical/dsrom_v9_parent_context/clock.tcl \
 --step-tcl POST_CTS=physical/dsrom_v9_parent_context/clock.tcl \
 --step-tcl PRE_GLOBAL_ROUTE=physical/dsrom_v9_parent_context/replay_checks.tcl \
 --keep-heavy-artifacts --output "$V9_PARENT_OUTPUT/physical.json"

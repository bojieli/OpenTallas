#!/bin/bash
# ONE margin route of the CODE pair (claude/takeover-code-pair-20261006 @ 3b26daaa5; pinned archive commit in src/.git).
set -uo pipefail
D=/srv/opentallas-scratch/claude/takeover-ds/code-pair
cd $D/src_pinned
mkdir -p $D/route
export OT_SYNTH_TIMEOUT_SECONDS=unlimited OT_FLOW_TIMEOUT_SECONDS=unlimited TMPDIR=$D/tmp
mkdir -p $TMPDIR
P=physical/qwen_code_pair_margin
/srv/opentallas-scratch/admit.sh 40 -- python3 tools/run_abi3_physical.py --view asap7   --top ot_qwen_hbm_code_pair_margin --param ENABLE=1 --param COLUMN_BASE=0 --param ROWS=4496   --source rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv --source rtl/model_ready_hbm_r14/ot_hbm_r14_pkg.sv   --source rtl/hbm_accel/qwen/payload/ot_qwen_hbm_code_pair_margin.sv   --clock-period-ns 0.770 --clock-uncertainty-ns 0.060 --clock-uncertainty-hold-ns 0.025   --core-input-delay-min-ns 0 --core-input-delay-max-ns 0.120 --output-delay-min-ns 0 --output-delay-max-ns 0.120   --false-path-from por_n --sdc-append $P/boundary_append.sdc   --orfs-corner WC --hold-corners WC,BC --stages pnr --hold-margin-ns 0.020 --max-fanout 32   --die-area 0 0 864 673.92 --core-area 8.64 8.64 855.36 665.28 --place-density 0.55   --macro-view ot_sram_1r1w_1024x256_m2_r2c2=physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2   --macro-view ot_sram_1r1w_128x256_m1_r2c2=physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2   --macro-place-halo 2.16 2.16 --routing-layers M2 M9   --orfs-var SYNTH_HDL_FRONTEND=slang --orfs-var SYNTH_HIERARCHICAL=1 --orfs-var SYNTH_MINIMUM_KEEP_SIZE=0   --orfs-var MACRO_PLACEMENT_TCL=/src/$P/macros.tcl --orfs-var FOOTPRINT_TCL=/src/$P/pins.tcl   --orfs-var ADDER_MAP_FILE= --orfs-var GPL_ROUTABILITY_DRIVEN=0   --orfs-var MIN_CLK_ROUTING_LAYER=M4 --orfs-var MAX_CLK_ROUTING_LAYER=M9     --synth-timeout-seconds unlimited --flow-timeout-seconds unlimited   --purpose characterization --nickname-tag code_pair_margin_r1   --keep-workdir $D/route/work --output $D/route/physical.json > $D/route.log 2>&1
rc=$?
echo $rc > $D/route.exit
exit $rc

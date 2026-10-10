#!/bin/bash
set -eu
r=/srv/opentallas-scratch/codex/hc-row-shard-r2/physical_private64
cd "$r/source"
export OT_ORFS_NUM_CORES=32 NUM_CORES=32
export OT_ROUTE_HOLD_CORNERS=mm
unset OT_ORFS_CORNER_OVERRIDE OT_ORFS_CORNER
export OPENTALLAS_ORFS_IMAGE=sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29
mkdir -p "$r/bin"
cat > "$r/bin/docker" <<'DOCKER'
#!/bin/bash
if [ "$1" = run ]; then shift; exec /usr/bin/docker run -e LEC_CHECK=0 -e OT_FP_LINT=1 "$@"; fi
exec /usr/bin/docker "$@"
DOCKER
chmod +x "$r/bin/docker"
export PATH="$r/bin:$PATH"
python3 tools/run_abi3_physical.py --view asap7 --top ot_hbm_hc_row_private \
 --source rtl/hdc/hbm/ot_hbm_hc_row_private.sv --source rtl/hdc/hbm/ot_hbm_hc_row_operand_sram.sv --source rtl/hdc/hbm/ot_hbm_hc_flat_operand_sram.sv \
 --source rtl/common/ot_secded.sv --source rtl/hdc/v41x/ot_hdc_v41x_hcp.sv \
 --source rtl/hdc/ot_hdc_fastfp.sv --source rtl/hdc/v41/ot_hdc_fdiv.sv --source rtl/hdc/ot_hdc_delay.sv --source rtl/hdc/ot_hdc_sfu.sv \
 --macro-view ot_sram_1r1w_128x256_m1_r2c2=physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2 --macro-place-halo 12 12 \
 --clock-port clk --clock-period-ns 1.111111111 --clock-uncertainty-ns .060 --clock-uncertainty-hold-ns .025 \
 --orfs-corner WC --hold-corners WC,BC --io-delay-fraction .2 --sdc-append physical/hbm_hc_row_shard_20261009/pathfinding_clock.sdc \
 --stages pnr --die-area 0 0 1400 1400 --core-area 1.08 1.08 1398.92 1398.92 --place-density .55 --routing-layers M2 M7 \
 --max-transition-ns library --max-fanout 32 --orfs-var ADDER_MAP_FILE= --orfs-var "CTS_ARGS=-apply_ndr none -repair_clock_nets -balance_levels" \
 --orfs-var PDN_TCL=/src/physical/hbm_accel_die_views/coll/rtl_ps/pdn_port.tcl \
 --orfs-var MACRO_PLACEMENT_TCL=/src/physical/hbm_hc_row_shard_20261009/macro_rows_private.tcl \
 --orfs-var VERILOG_INCLUDE_DIRS=/src/rtl/common \
 --step-tcl PRE_CTS=physical/abi3/v41x_karb_repair_buffer_cap.tcl --step-tcl PRE_GLOBAL_ROUTE=physical/abi3/v41x_karb_repair_buffer_cap.tcl \
 --slew-margin-percent 60 --hold-margin-ns .025 --purpose characterization --nickname-tag hc_row64_private900_pathfinding \
 --synth-timeout-seconds unlimited --flow-timeout-seconds unlimited --keep-workdir "$r/work" --output "$r/physical.json" > "$r/route.log" 2>&1
python3 tools/w18/corner_sta.py --macro physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2 --post-sdc physical/hbm_hc_row_shard_20261009/pathfinding_clock.sdc --orfs-dir "$r/work/orfs" --output "$r/corner_sta.json" > "$r/corner.log" 2>&1

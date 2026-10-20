#!/bin/bash
set -euo pipefail
D=$(pwd)
for width in 328 257; do
  mkdir -p "$D/map_kept_$width"
  cat > "$D/map_kept_$width/config.mk" <<EOF
export DESIGN_NAME = ot_hbm_parent_station32
export DESIGN_NICKNAME = hbm_parent_station_$width
export PLATFORM = asap7
export VERILOG_FILES = /src/ot_hbm_parent_station32.sv
export VERILOG_DEFINES = -DSYNTHESIS
export VERILOG_TOP_PARAMS = W $width
export SDC_FILE = /work/clock.sdc
export DIE_AREA = 0 0 172.8 172.8
export CORE_AREA = 2.16 2.16 170.64 170.64
export PLACE_DENSITY = 0.5
export SYNTH_REPEATABLE_BUILD = 1
export SYNTH_HIERARCHICAL = 0
export SYNTH_CANONICALIZE_TCL = /src/physical/common_flow/ot_keep_regs.tcl
export OT_KEEP_PIN_REGS = 1
export LEC_CHECK = 0
export CORNER = WC
export ASAP7_USE_VT = RVT
export ADDER_MAP_FILE =
export NUM_CORES = 4
EOF
  cat > "$D/map_kept_$width/clock.sdc" <<'EOF'
current_design ot_hbm_parent_station32
create_clock -name source -period 833.333 [get_ports ck]
set_clock_uncertainty -setup 60 [get_clocks source]
set_clock_uncertainty -hold 25 [get_clocks source]
EOF
  docker run --rm -e LEC_CHECK=0 -v "$D/src:/src:ro" -v "$D/map_kept_$width:/work" -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base synth' > "$D/map_kept_$width/synth.log" 2>&1
  mapfile -t LIBS < <(sed -n 's/.*Executing Liberty frontend: //p' "$D/map_kept_$width/synth.log" | sort -u)
  if [[ ${#LIBS[@]} == 0 ]]; then echo 'NO ACTUAL LIB INVENTORY'; exit 1; fi
  ARGS=()
  for lib in "${LIBS[@]}"; do ARGS+=(--liberty "$lib"); done
  docker run --rm -v "$D/src:/src:ro" -v "$D/map_kept_$width:/work" openroad/orfs:asap7lock python3 /src/tools/ref_tile/native_census.py --netlist /work/results/asap7/hbm_parent_station_$width/base/1_2_yosys.v --top ot_hbm_parent_station32 "${ARGS[@]}" --out /work/native_census.json > "$D/map_kept_$width/native.log" 2>&1
done

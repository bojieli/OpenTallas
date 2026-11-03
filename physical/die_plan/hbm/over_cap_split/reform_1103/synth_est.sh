#!/usr/bin/env bash
# DIE-HBM-61/SPLIT 11-03: ORFS ASAP7 synth cell estimate of one RE-FORM sub-block (same image + flat synth as the kits).
#   synth_est.sh WORKDIR TOP MEM_GB FILE.sv...     (run on a fleet host: epyc2 / intel1; docker memory-capped)
# Writes WORKDIR/{config.mk,constraint.sdc,rtl/}, runs `make synth`, prints "CELLS <top> <n>" from synth_stat.txt.
# Clock: every input port named clk*/ck* at 833 ps (1.2 GHz).  Timing is NOT judged here (synth only).
set -u
W=$1; TOP=$2; MEM=$3; shift 3
mkdir -p "$W/rtl"; cp "$@" "$W/rtl/"
IMAGE=${OT_ORFS_IMAGE:-openroad/orfs:asap7lock}
FILES=$(cd "$W/rtl" && ls *.sv *.v 2>/dev/null | sed 's#^#/work/rtl/#' | tr '\n' ' ')
cat > "$W/config.mk" <<EOF
export DESIGN_NICKNAME = est_$TOP
export DESIGN_NAME = $TOP
export PLATFORM = asap7
export VERILOG_FILES = $FILES
export VERILOG_INCLUDE_DIRS = /work/rtl
export VERILOG_DEFINES = -DSYNTHESIS
export SDC_FILE = /work/constraint.sdc
export CORE_UTILIZATION = 40
export SYNTH_HIERARCHICAL = 0
export SYNTH_REPEATABLE_BUILD = 1
export SYNTH_MEMORY_MAX_BITS = 1000000
EOF
cat > "$W/constraint.sdc" <<'EOF'
set clks [get_ports -quiet {clk* ck*}]
create_clock -name clk -period 833.0 $clks
set_input_delay 166.6 -clock clk [all_inputs -no_clocks]
set_output_delay 166.6 -clock clk [all_outputs]
EOF
NAME=hbm61split-est-$(echo "$TOP" | tr -c 'A-Za-z0-9_' _ | cut -c1-40)-$$
docker run --rm --name "$NAME" --cpus=4 --memory="${MEM}g" --memory-swap="${MEM}g" -v "$W":/work -w /OpenROAD-flow-scripts/flow \
  "$IMAGE" bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base synth > /work/synth.log 2>&1; rc=\$?; chown -R $(id -u):$(id -g) /work; exit \$rc"
rc=$?
S=$(ls "$W"/run/reports/asap7/*/base/synth_stat.txt 2>/dev/null | head -1)
N=$( [ -n "$S" ] && awk '/^=== design hierarchy ===/{h=1} h && / cells$/{print $1; exit}' "$S")
[ -z "$N" ] && [ -n "$S" ] && N=$(grep -E ' cells$' "$S" | tail -1 | awk '{print $1}')
echo "CELLS $TOP ${N:-NA} rc=$rc"

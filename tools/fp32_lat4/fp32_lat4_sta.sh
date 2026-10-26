#!/bin/bash
# FP32 lane (owner decision 16, 2026-10-24): standalone timing of one binary32 add / multiply unit at 833 ps, ASAP7 RVT.
# ORFS synth -> floorplan -> place (CORNER TC = TT libraries), then OpenSTA on 3_place.odb with placement parasitics:
# setup at TT, hold at FF, ideal clock, 60 ps setup / 25 ps hold uncertainty; per-endpoint slack (format end) for the
# per-stage table (stages.py).  Wrapper: operand / valid registers in front (the producer's operand register), the
# unit's own output register at the end, so every stage is register to register.
# usage: fp32_lat4_sta.sh <out_dir> <name> <dut_module> <kind: std|ve> [period_ps=833]
set -euo pipefail
WT=$(cd "$(dirname "$0")/../.." && pwd); OUT=$1; NAME=$2; DUT=$3; KIND=$4; PER=${5:-833}
mkdir -p "$OUT/$NAME"; D=$(realpath "$OUT/$NAME"); cd "$D"
SRCS="rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_fp32_f12.sv rtl/dsrom_sys/s81_dv/eng/ot_s81sl_ve_fp.sv tools/fp32_lat4/tb_fp32_lat4_eq.sv"
mkdir -p src; for s in $SRCS; do cp "$WT/$s" src/; done
rm -f src/tb_fp32_lat4_eq.sv; sed -n '/^\/\/ fixed-parameter shells/,$p' "$WT/tools/fp32_lat4/tb_fp32_lat4_eq.sv" > src/shells.sv
if [ "$KIND" = ve ]; then
  DUTI="(* keep *) reg [31:0] qa2, qb2; always @(posedge clk) begin qa2 <= a; qb2 <= b; end
    wire [31:0] y2; $DUT u_dut (.clk(clk), .rst_n(rst_n), .valid_in(qv), .a(qa), .a2(qa2), .b(qb), .b2(qb2), .y(y), .y2(y2), .err(err), .valid_out(valid_out));"
else
  DUTI="$DUT u_dut (.clk(clk), .rst_n(rst_n), .valid_in(qv), .a(qa), .b(qb), .y(y), .err(err), .valid_out(valid_out));"
fi
cat > src/fp32_sta_top.sv <<V
\`timescale 1ns/1ps
module fp32_sta_top (input wire clk, input wire rst_n, input wire valid_in, input wire [31:0] a, input wire [31:0] b,
                     output wire [31:0] y, output wire [1:0] err, output wire valid_out);
    (* keep *) reg qv; (* keep *) reg [31:0] qa, qb;
    always @(posedge clk or negedge rst_n) if (!rst_n) qv <= 1'b0; else qv <= valid_in;
    always @(posedge clk) begin qa <= a; qb <= b; end
    $DUTI
endmodule
V
cat > constraint.sdc <<S
create_clock -name clk -period $PER [get_ports clk]
set_clock_uncertainty -setup 60 [get_clocks clk]
set_clock_uncertainty -hold 25 [get_clocks clk]
set_input_delay 0 -clock clk [delete_from_list [all_inputs] [get_ports clk]]
set_output_delay 0 -clock clk [all_outputs]
S
cat > config.mk <<M
export DESIGN_NAME = fp32_sta_top
export DESIGN_NICKNAME = $NAME
export PLATFORM = asap7
export CORNER = TC
export VERILOG_FILES = $(for f in src/*.sv; do printf '/d/%s ' "$f"; done)
export SDC_FILE = /d/constraint.sdc
export CORE_UTILIZATION = 45
export PLACE_DENSITY = 0.60
export SYNTH_HIERARCHICAL = 0
export WORK_HOME = /d/orfs
M
cat > sta.tcl <<T
foreach f [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef] { read_lef \$f }
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
proc ot_libs {c} {
  set L /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
  foreach f [list \$L/asap7sc7p5t_AO_RVT_\${c}_nldm_211120.lib.gz \$L/asap7sc7p5t_INVBUF_RVT_\${c}_nldm_220122.lib.gz \
                  \$L/asap7sc7p5t_OA_RVT_\${c}_nldm_211120.lib.gz \$L/asap7sc7p5t_SIMPLE_RVT_\${c}_nldm_211120.lib.gz \
                  \$L/asap7sc7p5t_SEQ_RVT_\${c}_nldm_220123.lib] { read_liberty \$f }
}
ot_libs \$::env(OT_CORNER)
read_db /d/orfs/results/asap7/$NAME/base/3_place.odb
read_sdc /d/constraint.sdc
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
estimate_parasitics -placement
set side \$::env(OT_SIDE)
puts "OT_WORST \$::env(OT_CORNER) \$side [sta::worst_slack_cmd \$side]"
report_checks -path_delay \$side -group_path_count 100000 -endpoint_path_count 1 -unique_paths_to_endpoint -format end > /d/ends_\$::env(OT_CORNER)_\$side.rpt
report_checks -path_delay \$side -group_path_count 3 -fields {fanout cap slew} -digits 1 > /d/paths_\$::env(OT_CORNER)_\$side.rpt
if {\$side eq "max"} { report_design_area; puts "OT_CELLS [llength [get_cells *]] OT_REGS [llength [all_registers -cells]]" }
exit
T
IMG=openroad/orfs:asap7lock
s0=$(date +%s)
docker run --rm --name "ot-fp32-$NAME-$$" --memory 6g -v "$D:/d" -u "$(id -u):$(id -g)" -e HOME=/tmp $IMG bash -c \
  "cd /OpenROAD-flow-scripts/flow && make DESIGN_CONFIG=/d/config.mk synth floorplan place" > flow.log 2>&1 || { tail -30 flow.log; exit 3; }
for cs in TT:max FF:min; do
  c=${cs%%:*}; s=${cs##*:}
  docker run --rm --name "ot-fp32-sta-$NAME-$c-$$" --memory 4g -v "$D:/d" -u "$(id -u):$(id -g)" -e OT_CORNER=$c -e OT_SIDE=$s $IMG \
    bash -c "/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /d/sta.tcl" > sta_${c}_${s}.log 2>&1 || { tail -20 sta_${c}_${s}.log; exit 4; }
done
grep -h "OT_WORST\|Design area\|OT_CELLS" sta_*.log
grep -m1 -A3 "Chip area" orfs/reports/asap7/$NAME/base/synth_stat.txt 2>/dev/null || true
echo "OT_FP32_STA_DONE $NAME wall_s=$(( $(date +%s) - s0 ))"

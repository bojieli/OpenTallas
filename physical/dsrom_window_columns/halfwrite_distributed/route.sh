#!/bin/bash
# Codex structural halfwrite successor, default-off RTL selected explicitly.
# Derived from pinned01a487c86 M2-M6 calibrated route recipe.
# Predecessor: re-harden a WINDOW column (ot_dsrom_window_column_<W>) with signal routing capped at
# M6, so that M7..M9 above the column are free and the WINDOW stage parent can drop its power grid onto the column's
# M6 VDD/VSS straps (route_r3 died PDN-0006: "VDD on M6 is blocked by obstructions on M7, M8, M9" -- the 2026-10-06
# columns were routed M2..M9 and their abstracts obstruct every via site above the PG pins).  RTL unchanged.
# Margin-first: route at 770 ps (PER), sign off at 833.333 ps; IO against vclk at the MEASURED insertion (closure-loop
# calibrate exports CK_SS_MEAN / CK_FF_MIN / CK_FF_MAX), 0.2 T + 90 ps intra-region die allowance (the columns sit inside
# the stage parent's single clock region), FF-true hold model with 50 ps IO hold skew.
#   route_col.sh <label> <width 128|256> [extra run_abi3_physical args, e.g. --pnr-stop-after cts]
# env: SRC, OUT, CORES (16), UTIL (45), PER (0.770), CK_SS_MEAN / CK_FF_MIN / CK_FF_MAX (defaults before calibration)
set -u
lab=$1; w=128; shift
W=$OUT/$lab; mkdir -p $W; cd $SRC
L=${CK_SS_MEAN:-250}; FMIN=${CK_FF_MIN:-140}; FMAX=${CK_FF_MAX:-170}; FMID=${CK_FF_MEAN:-$(awk "BEGIN{print ($FMIN+$FMAX)/2}")}
C=physical/dsrom_window_columns/halfwrite_distributed/cl_$lab; mkdir -p $C
cat > $C/io_route.sdc <<EOT
# IO against vclk at the measured SS insertion $L ps, 0.2 T + 90 ps (intra-region), FF-true hold mins
create_clock -name vclk -period [get_property [get_clocks core_clk] period]
set_clock_uncertainty -setup 60 [get_clocks vclk]
set_clock_uncertainty -hold 25 [get_clocks vclk]
set_clock_latency $L [get_clocks {core_clk vclk}]
set ot_in [all_inputs -no_clocks]
unset_input_delay -clock core_clk \$ot_in
unset_output_delay -clock core_clk [all_outputs]
set_input_delay [expr {[get_property [get_clocks core_clk] period] * 0.2 + 90}] -clock vclk \$ot_in
set_output_delay [expr {[get_property [get_clocks core_clk] period] * 0.2 + 90}] -clock vclk [all_outputs]
set_input_delay -min [expr {$FMID - $L}] -clock vclk \$ot_in
# RULE H1 (h1-verify 2026-10-08): capture at the latest FF leaf + 50 (was FMIN - L + 25: required 2L - FMIN, wrong sign)
set_output_delay -min [expr {$L - $FMAX - 25}] -clock vclk [all_outputs]
EOT
cat > $C/signoff_ss.sdc <<EOT
create_clock -name core_clk -period 833.333 [get_ports clk]
set_clock_uncertainty -setup 60 [get_clocks core_clk]
set_clock_uncertainty -hold 25 [get_clocks core_clk]
set_propagated_clock [get_clocks core_clk]
create_clock -name vclk -period 833.333
set_clock_uncertainty -setup 60 [get_clocks vclk]
set_clock_uncertainty -hold 25 [get_clocks vclk]
set_clock_latency $L [get_clocks vclk]
set ot_in [all_inputs -no_clocks]
set_input_delay [expr {833.333 * 0.2 + 90}] -clock vclk \$ot_in
set_output_delay [expr {833.333 * 0.2 + 90}] -clock vclk [all_outputs]
set_input_delay -min 0 -clock vclk \$ot_in
set_output_delay -min 0 -clock vclk [all_outputs]
EOT
cat > $C/signoff_ff_guarded.sdc <<EOT
if {[llength [get_libs -quiet *_FF_*]]} {
# RULE H1 (h1-verify 2026-10-08): outputs vs the LATEST FF leaf + 50 (sender); inputs launch at the FF mean, 25 (receiver)
set_clock_latency $FMAX [get_clocks vclk]
create_clock -name vclki -period [get_property [get_clocks core_clk] period]
set_clock_latency $FMID [get_clocks vclki]
set ot_in [all_inputs -no_clocks]
unset_input_delay -clock vclk \$ot_in
set_input_delay [expr {[get_property [get_clocks core_clk] period] * 0.2}] -clock vclki \$ot_in
set_input_delay -min 0 -clock vclki \$ot_in
set_clock_uncertainty -hold 25 -from [get_clocks vclki] -to [get_clocks core_clk]
set_clock_uncertainty -hold 50 -from [get_clocks core_clk] -to [get_clocks vclk]
}
EOT
echo "SRC=$SRC lab=$lab w=$w UTIL=${UTIL:-45} PER=${PER:-0.770} L=$L FMIN=$FMIN FMAX=$FMAX $*" > $W/args
export OT_ORFS_NUM_CORES=${CORES:-16} NUM_CORES=${CORES:-16} OT_SYNTH_TIMEOUT_SECONDS=unlimited OT_FLOW_TIMEOUT_SECONDS=unlimited
python3 tools/run_abi3_physical.py --view asap7 --top ot_dsrom_window_column_halfwrite_distributed --param HALFWRITE=1 \
  --source rtl/dsrom_sys/s81_window_la/pipeline/ot_dsrom_window_stage_pipeline.sv \
  --source rtl/dsrom_sys/s81_window_la/ot_dsrom_window_column_halfwrite_distributed.sv \
  --clock-period-ns ${PER:-0.770} --clock-uncertainty-ns 0.060 --clock-uncertainty-hold-ns 0.025 \
  --orfs-corner WC --hold-corners WC,BC --io-delay-fraction 0.2 --sdc-append $C/io_route.sdc --stages pnr \
  --core-utilization ${UTIL:-45} --place-density 0.60 --max-fanout 32 --max-transition-ns 0.15 \
  --hold-margin-ns ${HM:-0.010} --slew-margin-percent 30 --orfs-var ADDER_MAP_FILE= \
  --routing-layers M2 M6 --synth-timeout-seconds unlimited --flow-timeout-seconds unlimited \
  --purpose characterization --nickname-tag $lab "$@" \
  --keep-workdir $W/work --force --output $W/physical.json > $W/run.log 2>&1
echo "rc=$?" > $W/exit
python3 tools/w18/corner_sta.py --post-sdc $C/signoff_ss.sdc --post-sdc $C/signoff_ff_guarded.sdc \
  --orfs-dir $W/work/orfs --output $W/corner_sta.json > $W/corner.log 2>&1
echo "corner_rc=$?" >> $W/exit
python3 tools/hbm_fmax_attn_abstract.py --orfs-dir $W/work/orfs --name ot_dsrom_window_column_halfwrite_distributed --out $W/view \
  --tmp-dir $W/abs_tmp > $W/export.log 2>&1
echo "export_rc=$?" >> $W/exit
cp $C/*.sdc $W/ 2>/dev/null
# the column's PG straps must be reachable from M7..M9: no M7/M8/M9 obstruction in the exported abstract
python3 - $W/view/ot_dsrom_window_column_halfwrite_distributed.lef > $W/pg_check.txt 2>&1 <<'PY'
import re,sys
t=open(sys.argv[1]).read(); o=re.search(r'\n\s*OBS(.*?)\n\s*END\s*\n',t,re.S); o=o.group(1) if o else ''
up=[l for l in re.findall(r'LAYER (\S+)',o) if l in ('M7','M8','M9')]
print('upper-layer OBS layers:', up); sys.exit(1 if up else 0)
PY
echo "pg_rc=$?" >> $W/exit

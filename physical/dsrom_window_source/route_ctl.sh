#!/bin/bash
# CLAUDE takeover-ds 2026-10-07: route the WINDOW source control leaf (ot_dsrom_window_source_ctl, MARGIN=2) in the
# closure loop.  route_r2 (MARGIN=1, ideal-clock IO) sat 11.5 h in GRT hold repair (9,287 a_data input endpoints at
# -468 ps against ~780 ps insertion) with reg2reg -447 ps; MARGIN=2 fixes the reg2reg classes in RTL and this flow
# takes the IO against vclk at the MEASURED insertion (closure-loop calibrate: CK_SS_MEAN / CK_FF_MIN / CK_FF_MAX),
# 0.2 T + 150 ps die clock-arrival allowance, FF-true hold mins (50 ps IO hold skew); route 770 ps, sign off 833.333.
#   route_ctl.sh <label> [extra run_abi3_physical args, e.g. --pnr-stop-after cts]
# env: SRC, OUT, CORES (16), DIE (um, square, default 540), PD (place density, default 0.50), MARGIN (2), HM (0.010)
set -u
lab=$1; shift
W=$OUT/$lab; mkdir -p $W/work/orfs/tmp; cd $SRC
L=${CK_SS_MEAN:-700}; FMIN=${CK_FF_MIN:-380}; FMAX=${CK_FF_MAX:-460}; DIE=${DIE:-540}
C=physical/dsrom_window_source/cl_$lab; mkdir -p $C
cat > $C/io_route.sdc <<EOT
# IO against vclk at the measured SS insertion $L ps, 0.2 T + 150 ps, FF-true hold mins
create_clock -name vclk -period [get_property [get_clocks core_clk] period]
set_clock_uncertainty -setup 60 [get_clocks vclk]
set_clock_uncertainty -hold 25 [get_clocks vclk]
set_clock_latency $L [get_clocks {core_clk vclk}]
set ot_in [all_inputs -no_clocks]
unset_input_delay -clock core_clk \$ot_in
unset_output_delay -clock core_clk [all_outputs]
set_input_delay [expr {[get_property [get_clocks core_clk] period] * 0.2 + 150}] -clock vclk \$ot_in
set_output_delay [expr {[get_property [get_clocks core_clk] period] * 0.2 + 150}] -clock vclk [all_outputs]
set_input_delay -min [expr {$FMAX - $L - 25}] -clock vclk \$ot_in
set_output_delay -min [expr {$FMIN - $L + 25}] -clock vclk [all_outputs]
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
set_input_delay [expr {833.333 * 0.2 + 150}] -clock vclk \$ot_in
set_output_delay [expr {833.333 * 0.2 + 150}] -clock vclk [all_outputs]
set_input_delay -min 0 -clock vclk \$ot_in
set_output_delay -min 0 -clock vclk [all_outputs]
EOT
cat > $C/signoff_ff_guarded.sdc <<EOT
if {[llength [get_libs -quiet *_FF_*]]} {
set_clock_latency $FMIN [get_clocks vclk]
create_clock -name vclki -period [get_property [get_clocks core_clk] period]
set_clock_latency $FMAX [get_clocks vclki]
set ot_in [all_inputs -no_clocks]
unset_input_delay -clock vclk \$ot_in
set_input_delay [expr {[get_property [get_clocks core_clk] period] * 0.2}] -clock vclki \$ot_in
set_input_delay -min 0 -clock vclki \$ot_in
set_clock_uncertainty -hold 50 -from [get_clocks vclki] -to [get_clocks core_clk]
set_clock_uncertainty -hold 50 -from [get_clocks core_clk] -to [get_clocks vclk]
}
EOT
E=$(python3 -c "print($DIE-5)")
echo "SRC=$SRC lab=$lab MARGIN=${MARGIN:-2} DIE=$DIE PD=${PD:-0.50} L=$L FMIN=$FMIN FMAX=$FMAX $*" > $W/args
export OT_ORFS_NUM_CORES=${CORES:-16} NUM_CORES=${CORES:-16} OT_SYNTH_TIMEOUT_SECONDS=unlimited OT_FLOW_TIMEOUT_SECONDS=unlimited
python3 tools/run_abi3_physical.py --view asap7 --top ot_dsrom_window_source_ctl \
  --source rtl/dsrom_sys/s81_window_la/pipeline/ot_dsrom_window_source_ctl.sv \
  --source rtl/dsrom_sys/s81_window_la/pipeline/ot_dsrom_window_writer_pipeline.sv \
  --source rtl/dsrom_sys/s81_window_la/ot_dsrom_window_stream_la_s81.sv \
  --source rtl/chip/ot_chip_v41x_window_stage4.sv --source rtl/chip/ot_chip_v41x_window_row_codec.sv \
  --source rtl/hdc/ot_hdc_prefix.sv \
  --param MARGIN=${MARGIN:-2} --param REFILL_OWNER_SAFE=1 --param REFILL_CREDITS=8 --param LA_ISSUE_PC=1 \
  --clock-period-ns 0.770 --clock-uncertainty-ns 0.060 --clock-uncertainty-hold-ns 0.025 \
  --orfs-corner WC --hold-corners WC,BC --io-delay-fraction 0.2 --sdc-append $C/io_route.sdc --stages pnr \
  --hold-margin-ns ${HM:-0.010} --max-fanout 32 \
  --die-area 0 0 $DIE $DIE --core-area 5 5 $E $E --place-density ${PD:-0.50} --orfs-var ADDER_MAP_FILE= \
  --orfs-var "IO_PLACER_H=M4 M6 M8" --orfs-var "IO_PLACER_V=M5 M7 M9" --orfs-var TMPDIR=/work/tmp \
  --routing-layers M2 M9 --synth-timeout-seconds unlimited --flow-timeout-seconds unlimited \
  --purpose characterization --nickname-tag $lab "$@" \
  --keep-workdir $W/work --force --output $W/physical.json > $W/run.log 2>&1
echo "rc=$?" > $W/exit
python3 tools/w18/corner_sta.py --post-sdc $C/signoff_ss.sdc --post-sdc $C/signoff_ff_guarded.sdc \
  --orfs-dir $W/work/orfs --output $W/corner_sta.json > $W/corner.log 2>&1
echo "corner_rc=$?" >> $W/exit
python3 tools/hbm_fmax_attn_abstract.py --orfs-dir $W/work/orfs --name ot_dsrom_window_source_ctl --out $W/view \
  --tmp-dir $W/abs_tmp > $W/export.log 2>&1
echo "export_rc=$?" >> $W/exit
cp $C/*.sdc $W/ 2>/dev/null

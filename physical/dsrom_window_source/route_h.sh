#!/bin/bash
# el1011-ds-misc 2026-10-11: the HIERARCHICAL ot_dsrom_window_source_ctl MARGIN 3: the core (writer, skids, FSM, issue
# walk; ~12-14k sinks) routed around the hardened leaves (4 x ot_dsrom_wsrc_land8, 1 x ot_dsrom_wsrc_mirror) placed by
# h/macro_place.tcl, PDN h/pdn_wsrc_h.tcl (top M8 straps, leaf grid M7-M8), face plan pinplan_m3.py, die 620.  Same IO
# recipe as route_ctl.sh.  Leaf views: LANDV / MIRV (dirs in the source tree holding NAME.lef, NAME_{ss,ff,tt}.lib).
#   route_h.sh <label> [extra run_abi3_physical args]
# env: SRC, OUT, LANDV, MIRV, CORES (16), DIE (620), PD (0.50), HM (0.010), CTSA (optional CTS_ARGS)
set -u
lab=$1; shift
W=$OUT/$lab; mkdir -p $W/work/orfs/tmp; cd $SRC
L=${CK_SS_MEAN:-700}; FMIN=${CK_FF_MIN:-380}; FMAX=${CK_FF_MAX:-460}; DIE=${DIE:-620}; LANDV=${LANDV:?land8 view dir}; MIRV=${MIRV:?mirror view dir}
C=physical/dsrom_window_source/cl_$lab; mkdir -p $C
cat > $C/io_route.sdc <<EOT
# IO against vclk at the measured SS insertion $L ps, 0.2 T + 150 ps, FF-true hold mins
create_clock -name vclk -period [get_property [get_clocks core_clk] period]
set_clock_uncertainty -setup 60 [get_clocks vclk]
set_clock_uncertainty -hold 25 [get_clocks vclk]
# BEFORE CTS the real clock is ideal: its nominal interior network delay must
# equal the virtual reference. AFTER CTS set_propagated_clock ignores this
# ideal network latency and checks the actual tree; source remains local zero.
set_clock_latency $L [get_clocks {core_clk vclk}]
# LOCAL BLOCK CHARACTERIZATION ONLY: clock port is the local time origin.
# Source0 is provisional, not option-1 die clock qualification. Before native
# adoption attach the actual balanced die-tree tap source latency and recheck
# boundary timing/lockups against the parent clock plan and corner budgets.
set_clock_latency -source 0 [get_clocks core_clk]
set ot_in [all_inputs -no_clocks]
unset_input_delay -clock core_clk \$ot_in
unset_output_delay -clock core_clk [all_outputs]
set_input_delay [expr {[get_property [get_clocks core_clk] period] * 0.2 + 150}] -clock vclk \$ot_in
set_output_delay [expr {[get_property [get_clocks core_clk] period] * 0.2 + 150}] -clock vclk [all_outputs]
set_input_delay -min [expr {$FMAX - $L - 25}] -clock vclk \$ot_in
# CLAUDE s81-blocks 2026-10-07: sign fixed (was FMIN - L + 25 = -371 at L 1068 / FMIN 672: required = L + 25 - min
# became L + FMIN-free 1464 ps, the -356 / -525 GRT hold-repair walls of wsrc-m2 / m2big); now required = FMIN + 50 as the
# guarded FF sign-off (vclk latency FMIN, hold uncertainty 50)
set_output_delay -min [expr {$L - $FMIN - 25}] -clock vclk [all_outputs]
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
# PINPLAN=m3 (el1011-ds-misc 2026-10-11, MARGIN 3): the face plan of pinplan_m3.py (lanes 0-15 S / 16-31 N, K-port E,
# control + clk W); default: the clock pin alone, as before.
PINARGS=()
if true; then export OT_PIN_GROUP_MAX=1 OT_PIN_BALANCE_H="M4 M6" OT_PIN_BALANCE_V="M5 M7"; PINARGS=(); while IFS= read -r l; do PINARGS+=(--pin-region "$l"); done < <(python3 physical/dsrom_window_source/pinplan_m3.py top $DIE $DIE); fi
echo "SRC=$SRC lab=$lab MARGIN=${MARGIN:-2} PINPLAN=${PINPLAN:-} DIE=$DIE PD=${PD:-0.50} L=$L FMIN=$FMIN FMAX=$FMAX $*" > $W/args
export OT_ORFS_NUM_CORES=${CORES:-16} NUM_CORES=${CORES:-16} OT_SYNTH_TIMEOUT_SECONDS=unlimited OT_FLOW_TIMEOUT_SECONDS=unlimited
python3 tools/run_abi3_physical.py --view asap7 --top ot_dsrom_window_source_ctl \
  --source rtl/dsrom_sys/s81_window_la/recovered_ctl_m2/ot_dsrom_window_source_ctl.sv \
  --source rtl/dsrom_sys/s81_window_la/recovered_ctl_m2/ot_dsrom_window_writer_pipeline.sv \
  --source rtl/dsrom_sys/s81_window_la/recovered_ctl_m2/ot_dsrom_window_stream_la_s81.sv \
  --source rtl/dsrom_sys/s81_window_la/recovered_ctl_m2/ot_chip_v41x_window_stage4.sv --source rtl/dsrom_sys/s81_window_la/recovered_ctl_m2/ot_chip_v41x_window_row_codec.sv \
  --source rtl/dsrom_sys/s81_window_la/recovered_ctl_m2/ot_hdc_prefix.sv \
  --macro-view ot_dsrom_wsrc_land8=$LANDV --macro-view ot_dsrom_wsrc_mirror=$MIRV --macro-place-halo 5 5 \
  --orfs-var MACRO_PLACEMENT_TCL=/src/physical/dsrom_window_source/h/macro_place.tcl \
  --orfs-var PDN_TCL=/src/physical/dsrom_window_source/h/pdn_wsrc_h.tcl ${CTSA:+--orfs-var "CTS_ARGS=$CTSA"} \
  --param MARGIN=3 --param REFILL_OWNER_SAFE=1 --param REFILL_CREDITS=8 --param LA_ISSUE_PC=1 \
  --clock-period-ns 0.770 --clock-uncertainty-ns 0.060 --clock-uncertainty-hold-ns 0.025 \
  --orfs-corner WC --hold-corners WC,BC --io-delay-fraction 0.2 --sdc-append $C/io_route.sdc --stages pnr \
  --hold-margin-ns ${HM:-0.010} --max-fanout 32 \
  --die-area 0 0 $DIE $DIE --core-area 5 5 $E $E --place-density ${PD:-0.50} --orfs-var ADDER_MAP_FILE= \
  --orfs-var "IO_PLACER_H=M4 M6" --orfs-var "IO_PLACER_V=M5 M7" \
  "${PINARGS[@]}" \
  --orfs-var "PRE_GLOBAL_PLACE_TCL=/src/physical/qwen_die_masters/io_flop_at_pins.tcl" \
  --orfs-var "PRE_DETAIL_PLACE_TCL=/src/physical/qwen_die_masters/out_flop_release.tcl" --orfs-var TMPDIR=/work/tmp \
  --routing-layers M2 M9 --synth-timeout-seconds unlimited --flow-timeout-seconds unlimited \
  --purpose characterization --nickname-tag $lab "$@" \
  --keep-workdir $W/work --force --output $W/physical.json > $W/run.log 2>&1
echo "rc=$?" > $W/exit
python3 tools/w18/corner_sta.py --macro $LANDV --macro $MIRV --post-sdc $C/signoff_ss.sdc --post-sdc $C/signoff_ff_guarded.sdc \
  --orfs-dir $W/work/orfs --output $W/corner_sta.json > $W/corner.log 2>&1
echo "corner_rc=$?" >> $W/exit
python3 tools/hbm_fmax_attn_abstract.py --orfs-dir $W/work/orfs --name ot_dsrom_window_source_ctl --out $W/view --macro-view $LANDV --macro-view $MIRV \
  --tmp-dir $W/abs_tmp > $W/export.log 2>&1
echo "export_rc=$?" >> $W/exit
cp $C/*.sdc $W/ 2>/dev/null

#!/bin/bash
# el1011-ds-misc 2026-10-11: route one hardened leaf of ot_dsrom_window_source_ctl MARGIN 3 (ot_dsrom_wsrc_land8 /
# ot_dsrom_wsrc_mirror) with the same IO / sign-off recipe as route_ctl.sh (vclk at the measured insertion, 0.2 T +
# 150 ps, FF-true hold mins; route 770 ps, sign off 833.333), its own outline and the pinplan_m3.py edge plan; exports
# the abstract view the hierarchical controller composes.  PDN = s81_ph_views/common/pdn_view.tcl (M7 straps: the leaf exposes
# VDD / VSS on M7 so the controller grid connects M7-M8 over it, the engram_c_h recipe).
#   route_leaf.sh <label> [extra run_abi3_physical args]
# env: INHOLD=1 (uniform input hold stage, leaf_inhold.tcl), SRC, OUT, LEAF (land8 | mirror), CORES (16), DX / DY (um), PD (place density, default 0.50), HM (0.010)
set -u
lab=$1; shift
W=$OUT/$lab; mkdir -p $W/work/orfs/tmp; cd $SRC
L=${CK_SS_MEAN:-700}; FMIN=${CK_FF_MIN:-380}; FMAX=${CK_FF_MAX:-460}; LEAF=${LEAF:?land8|mirror}; case $LEAF in land8) DX=${DX:-140.4}; DY=${DY:-43.224}; TOP=ot_dsrom_wsrc_land8;; mirror) DX=${DX:-82.08}; DY=${DY:-82.08}; TOP=ot_dsrom_wsrc_mirror;; esac
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
EX=$(python3 -c "print(round($DX-2.16,3))"); EY=$(python3 -c "print(round($DY-2.16,3))")
export OT_PIN_GROUP_MAX=1 OT_PIN_BALANCE_H="M4 M6" OT_PIN_BALANCE_V="M5 M7"   # explicit uniform pins, layers alternating (pincheck_m3.sh)
PINARGS=(); while IFS= read -r l; do PINARGS+=(--pin-region "$l"); done < <(python3 physical/dsrom_window_source/pinplan_m3.py $LEAF $DX $DY)
D=rtl/dsrom_sys/s81_window_la/recovered_ctl_m2
SRCS=(--source $D/ot_dsrom_wsrc_$LEAF.sv); [ $LEAF = land8 ] && SRCS+=(--source $D/ot_hdc_prefix.sv)
echo "SRC=$SRC lab=$lab LEAF=$LEAF DX=$DX DY=$DY PD=${PD:-0.50} L=$L FMIN=$FMIN FMAX=$FMAX $*" > $W/args
export OT_ORFS_NUM_CORES=${CORES:-16} NUM_CORES=${CORES:-16} OT_SYNTH_TIMEOUT_SECONDS=unlimited OT_FLOW_TIMEOUT_SECONDS=unlimited
python3 tools/run_abi3_physical.py --view asap7 --top $TOP "${SRCS[@]}" \
  --clock-period-ns 0.770 --clock-uncertainty-ns 0.060 --clock-uncertainty-hold-ns 0.025 \
  --orfs-corner WC --hold-corners WC,BC --io-delay-fraction 0.2 --sdc-append $C/io_route.sdc --stages pnr \
  --hold-margin-ns ${HM:-0.010} --max-fanout 32 \
  --die-area 0 0 $DX $DY --core-area 2.16 2.16 $EX $EY --place-density ${PD:-0.50} --orfs-var ADDER_MAP_FILE= \
  --orfs-var "IO_PLACER_H=M4 M6" --orfs-var "IO_PLACER_V=M5 M7" \
  "${PINARGS[@]}" --orfs-var TMPDIR=/work/tmp --orfs-var PDN_TCL=/src/physical/s81_ph_views/common/pdn_view.tcl \
  ${INHOLD:+--orfs-var PRE_GLOBAL_PLACE_TCL=/src/physical/dsrom_window_source/leaf_inhold.tcl} \
  --routing-layers M2 M7 --synth-timeout-seconds unlimited --flow-timeout-seconds unlimited \
  --purpose characterization --nickname-tag $lab "$@" \
  --keep-workdir $W/work --force --output $W/physical.json > $W/run.log 2>&1
echo "rc=$?" > $W/exit
python3 tools/w18/corner_sta.py --post-sdc $C/signoff_ss.sdc --post-sdc $C/signoff_ff_guarded.sdc \
  --orfs-dir $W/work/orfs --output $W/corner_sta.json > $W/corner.log 2>&1
echo "corner_rc=$?" >> $W/exit
python3 tools/hbm_fmax_attn_abstract.py --orfs-dir $W/work/orfs --name $TOP --out $W/view \
  --tmp-dir $W/abs_tmp > $W/export.log 2>&1
echo "export_rc=$?" >> $W/exit
cp $C/*.sdc $W/ 2>/dev/null

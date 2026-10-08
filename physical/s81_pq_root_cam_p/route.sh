#!/bin/bash
# CLAUDE pq-rootcam 2026-10-08: pipelined ROOTD128 CAM ot_s81_pq_ret_root_cam_p in a grown root slot
# (132.192 x DIE_H um; DIE_H default 211.68 for ~55-60% util; old 133.92 slot placed at 85.8%).
# Source model: results/uarch/s81_pq_root_cam_20261007/model.json.
# Parent column-CTS and upstream/downstream load validation remain adoption holds.
set -u
lab=$1; w=128; shift
DIE_H=${DIE_H:-211.68}
W=$OUT/$lab; mkdir -p $W; cd $SRC
L=${CK_SS_MEAN:-0}; FMIN=${CK_FF_MIN:-0}; FMAX=${CK_FF_MAX:-0}; FMID=${CK_FF_MEAN:-$(awk "BEGIN{print ($FMIN+$FMAX)/2}")}
# Zero insertion is ONLY the initial calibration coordinate, never sign-off.
if [[ -z "${CK_SS_MEAN+x}" && "$*" != *"--pnr-stop-after cts"* ]]; then
  echo "missing calibrated CK_SS_MEAN/CK_FF_MIN/CK_FF_MAX" >&2; exit 2
fi
if [[ -n "${CK_SS_MEAN+x}" && ( -z "${CK_FF_MIN+x}" || -z "${CK_FF_MAX+x}" ) ]]; then
  echo "incomplete calibrated clock extrema" >&2; exit 2
fi
C=physical/s81_pq_root_cam_p/cl_$lab; mkdir -p $C
cat > $C/io_route.sdc <<EOT
# Fixed planning IO against calibrated root insertion; parent skew bound90ps and max wire100um.
create_clock -name vclk -period [get_property [get_clocks core_clk] period]
set_clock_uncertainty -setup 60 [get_clocks vclk]
set_clock_uncertainty -hold 25 [get_clocks vclk]
set_clock_latency $L [get_clocks {core_clk vclk}]
set ot_in [all_inputs -no_clocks]
unset_input_delay -clock core_clk \$ot_in
unset_output_delay -clock core_clk [all_outputs]
set_input_delay 333.5 -clock vclk \$ot_in
set_output_delay 274.5 -clock vclk [all_outputs]
set_input_delay -min [expr {$FMID - $L + 32.2}] -clock vclk \$ot_in
# CLAUDE s81-blocks: sign fixed (was FMIN - L + 65: required = L + 25 - min must equal the sign-off FMIN + 50 - 15)
# RULE H1 (h1-verify 2026-10-08): capture at the FF mean leaf FMID + 50 - 15
set_output_delay -min [expr {$L - $FMID - 10}] -clock vclk [all_outputs]
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
set_input_delay 333.5 -clock vclk \$ot_in
set_output_delay 274.5 -clock vclk [all_outputs]
set_input_delay -min 32.2 -clock vclk \$ot_in
set_output_delay -min 15 -clock vclk [all_outputs]
EOT
cat > $C/signoff_ff_guarded.sdc <<EOT
if {[llength [get_libs -quiet *_FF_*]]} {
# RULE H1 (h1-verify 2026-10-08): outputs vs the FF mean leaf + 50 (sender, latest capture); inputs launch at the FF mean, 25 (receiver)
set_clock_latency $FMID [get_clocks vclk]
create_clock -name vclki -period [get_property [get_clocks core_clk] period]
set_clock_latency $FMID [get_clocks vclki]
set ot_in [all_inputs -no_clocks]
unset_input_delay -clock vclk \$ot_in
set_input_delay 333.5 -clock vclki \$ot_in
set_input_delay -min 32.2 -clock vclki \$ot_in
set_clock_uncertainty -hold 25 -from [get_clocks vclki] -to [get_clocks core_clk]
set_clock_uncertainty -hold 50 -from [get_clocks core_clk] -to [get_clocks vclk]
}
EOT
echo "SRC=$SRC lab=$lab w=$w DIE_H=$DIE_H UTIL=${UTIL:-45} PER=${PER:-0.770} L=$L FMIN=$FMIN FMAX=$FMAX $*" > $W/args
export OT_ORFS_NUM_CORES=${CORES:-16} NUM_CORES=${CORES:-16} OT_SYNTH_TIMEOUT_SECONDS=unlimited OT_FLOW_TIMEOUT_SECONDS=unlimited
python3 tools/run_abi3_physical.py --view asap7 --top ot_s81_pq_ret_root_cam_p --param D=128 --param QD=128 \
  --source rtl/proto/ot_fp32_add_rne_pipe.sv \
  --source rtl/hdc/ot_hdc_delay.sv \
  --source rtl/v41rom/ot_v41_ret.sv \
  --source rtl/dsrom_sys/s81_pq_parent/ot_s81_pq_ret_root_cam_p.sv \
  --clock-period-ns ${PER:-0.770} --clock-uncertainty-ns 0.060 --clock-uncertainty-hold-ns 0.025 \
  --orfs-corner WC --hold-corners WC,BC --io-delay-fraction 0.2 --sdc-append $C/io_route.sdc --stages pnr \
  --core-utilization 55 --place-density 0.60 \
  --die-area 0 0 132.192 $DIE_H --core-area 2.16 2.16 130.032 $(awk "BEGIN{printf \"%.3f\", $DIE_H - 2.16}") --max-fanout 32 --max-transition-ns 0.15 \
  --hold-margin-ns ${HM:-0.010} --slew-margin-percent 30 --orfs-var ADDER_MAP_FILE= \
  --routing-layers M2 M6 --synth-timeout-seconds unlimited --flow-timeout-seconds unlimited \
  --purpose characterization --nickname-tag $lab "$@" \
  --keep-workdir $W/work --force --output $W/physical.json > $W/run.log 2>&1
echo "rc=$?" > $W/exit
python3 tools/w18/corner_sta.py --post-sdc $C/signoff_ss.sdc --post-sdc $C/signoff_ff_guarded.sdc \
  --orfs-dir $W/work/orfs --output $W/corner_sta.json > $W/corner.log 2>&1
echo "corner_rc=$?" >> $W/exit
python3 tools/hbm_fmax_attn_abstract.py --orfs-dir $W/work/orfs --name ot_s81_pq_ret_root_cam_p --out $W/view \
  --tmp-dir $W/abs_tmp > $W/export.log 2>&1
echo "export_rc=$?" >> $W/exit
cp $C/*.sdc $W/ 2>/dev/null
# the column's PG straps must be reachable from M7..M9: no M7/M8/M9 obstruction in the exported abstract
python3 - $W/view/ot_s81_pq_ret_root_cam_p.lef > $W/pg_check.txt 2>&1 <<'PY'
import re,sys
t=open(sys.argv[1]).read(); o=re.search(r'\n\s*OBS(.*?)\n\s*END\s*\n',t,re.S); o=o.group(1) if o else ''
up=[l for l in re.findall(r'LAYER (\S+)',o) if l in ('M7','M8','M9')]
print('upper-layer OBS layers:', up); sys.exit(1 if up else 0)
PY
echo "pg_rc=$?" >> $W/exit

#!/bin/bash
# DS-ROM field SPINE (ot_v41_spine_pqc_w17w10 v9) SS/FF screens at 1.2 GHz (0.833 ns), 60/25 ps uncertainty
# (WC = SS setup corner; hold at WC + BC = FF), ADDER_MAP_FILE disabled, the quantiser's f12 multiplier kept as its own
# hierarchy, routed in context of registered neighbours.  Run from a source root holding tools/ rtl/ physical/.
# Usage: phys.sh <scratch dir> <tag>...   tag = c<PQ>r<R>_<v>:  R 16 (core-utilization 35) or 128 (480 x 480 um die);
#   v = a (hold target 20 ps, slew margin 30%), b (20 ps, 40%), c (25 ps, 40%), d (22 ps, 45%, routability-off GPL)
# Peak memory declared to admit.sh: 40 GB (R16), 48 GB (R128) (v8 measured 29.6 / 36.0 GB; v9 adds ~25k quantiser flops).
E=${1:?scratch dir}; shift
O=$E/out; J=$E/jobs; mkdir -p $O $J
export OT_ORFS_NUM_CORES=16 NUM_CORES=16 OT_FLOW_TIMEOUT_SECONDS=unlimited OT_SYNTH_TIMEOUT_SECONDS=unlimited
COMMON="--view asap7 --clock-period-ns 0.833333 --clock-uncertainty-ns 0.060 --clock-uncertainty-hold-ns 0.025 --corner TT --orfs-corner WC --hold-corners WC,BC --max-transition-ns --max-fanout 32 --orfs-var ADDER_MAP_FILE= --orfs-var NUM_CORES=16 --keep-heavy-artifacts --synth-timeout-seconds unlimited --flow-timeout-seconds unlimited --stages pnr"
SP="--false-path-io --top ot_v41_pqc_spine_screen --source physical/dsrom_field_spine/ot_v41_pqc_spine_screen.sv --source rtl/v41die/ot_v41_spine_pqc_w17w10.sv --source rtl/hdc/ot_hdc_delay.sv --source rtl/v41rom/ot_v41_kreg.sv --source rtl/common/ot_prefix.sv --source rtl/hdc/v41x/ot_dsrom_aq12.sv --source rtl/hdc/ot_hdc_sfu.sv --source rtl/hdc/ot_hdc_fastfp_lat_f12.sv --source rtl/hdc/ot_hdc_fp32_f12.sv --source rtl/hdc/ot_hdc_fastfp.sv --source rtl/hdc/ot_hdc_fp32_mul_lat.sv --source rtl/hdc/ot_hdc_fp32_add_lat.sv --source rtl/hdc/ot_hdc_prefix.sv"
OV=(--orfs-var "VERILOG_DEFINES=-DSYNTHESIS -DOT_PQ_ROM_PORTS" --orfs-var "SYNTH_KEEP_MODULES=ot_hdc_fp32_mul_f12_l5")
run() { # tag
  t=$1; c=${t%%_*}; v=${t##*_}; pq=${c:1:1}; r=${c#*r}
  case $v in a) H=0.020; S=30; X=();; b) H=0.020; S=40; X=();; c) H=0.025; S=40; X=();;
             d) H=0.022; S=45; X=(--orfs-var GPL_ROUTABILITY_DRIVEN=0);; esac
  if [ "$r" = 128 ]; then g=48; SH=(--die-area 0 0 480 480 --core-area 2.16 2.16 477.84 477.84); else g=40; SH=(--core-utilization 35); fi
  mkdir -p $O/tmp_$t; export TMPDIR=$O/tmp_$t
  echo "$(date -Is) START $t $(hostname)" >> $J/MANIFEST
  /srv/opentallas-scratch/admit.sh $g -- python3 tools/run_abi3_physical.py $COMMON $SP "${OV[@]}" "${X[@]}" --slew-margin-percent $S --hold-margin-ns $H --param PQ=$pq --param R=$r "${SH[@]}" --nickname-tag dsfs9_$t --keep-workdir $O/work_$t --output $O/$t.json --force > $J/$t.log 2>&1
  echo $? > $J/$t.exit
  python3 tools/w18/corner_sta.py --orfs-dir $O/work_$t/orfs --output $O/${t}_corner_sta.json > $J/${t}_sta.log 2>&1
  python3 physical/dsrom_field_spine/terminal.py $O $t > $J/${t}_terminal.log 2>&1
  echo "$(date -Is) END $t exit=$(cat $J/$t.exit) $(tail -1 $J/${t}_terminal.log)" >> $J/MANIFEST
}
for t in "$@"; do run $t & done
wait

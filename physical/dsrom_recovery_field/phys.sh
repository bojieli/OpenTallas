#!/bin/bash
# DS-ROM recovery lever "field" (PQ): SS/FF screen of the new hardware at 1.2 GHz (0.833 ns), 60/25 ps uncertainty,
# ORFS on ot-epyc1tb (WC = SS setup corner; hold at WC + BC = FF), ADDER_MAP_FILE disabled, unique nicknames.
#   pair    ot_v41_pq_pair_screen: per-pair loader with pending load + element banked tags / parity / guard / shadow
#   sp16    ot_v41_spine_pq_w17w10 at R = 16 (one row-count group), KMAX 256, die PHW 6 / SAW 14 / VAW 19, ROM ports
#   sp128   the same at the die's R = 128 region roots
E=/srv/opentallas-scratch/claude/dsrom-recovery-field/phys; W=/srv/opentallas-scratch/claude/dsrom-recovery-field/src
O=$E/out; J=$E/jobs; mkdir -p $O $J
cd $W
export OT_ORFS_NUM_CORES=16
COMMON="--view asap7 --clock-period-ns 0.833333 --clock-uncertainty-ns 0.060 --clock-uncertainty-hold-ns 0.025 --corner TT --orfs-corner WC --hold-corners WC,BC --max-transition-ns --max-fanout 32 --slew-margin-percent 30 --io-delay-fraction 0.2 --orfs-var ADDER_MAP_FILE= --keep-heavy-artifacts --hold-margin-ns 0.01 --stages pnr"
SP="--top ot_v41_spine_pq_w17w10 --source rtl/v41die/ot_v41_spine_pq_w17w10.sv --source rtl/hdc/v41/ot_hdc_actquant.sv --source rtl/hdc/ot_hdc_fpu.sv --source rtl/hdc/ot_hdc_fp32_mul_pipe.sv --source rtl/proto/ot_fp32_add_rne_pipe.sv --source rtl/hdc/ot_hdc_delay.sv --source rtl/common/ot_prefix.sv --param PQ=1 --param KMAX=256 --param PHW=6 --param SAW=14 --param VAW=19"
run() { # tag peakGB args...
  t=$1; g=$2; shift 2
  echo "$(date -Is) START $t" >> $J/MANIFEST
  /srv/opentallas-scratch/admit.sh $g -- python3 tools/run_abi3_physical.py $COMMON "$@" --nickname-tag dsrf_$t --keep-workdir $O/work_$t --output $O/$t.json --force > $J/$t.log 2>&1
  echo $? > $J/$t.exit
  python3 tools/w18/corner_sta.py --orfs-dir $O/work_$t/orfs --output $O/${t}_corner_sta.json > $J/${t}_sta.log 2>&1
  echo "$(date -Is) END $t exit=$(cat $J/$t.exit)" >> $J/MANIFEST
}
run pair 8 --top ot_v41_pq_pair_screen --source physical/dsrom_recovery_field/ot_v41_pq_pair_screen.sv --source rtl/v41die/ot_v41_pair_pq_ld.sv --source rtl/v41rom/ot_v41_elem_pq_tags.sv --param PHW=6 --param PQ=1 --core-utilization 40 &
run sp16 24 $SP --param R=16 --orfs-var "VERILOG_DEFINES=-DSYNTHESIS -DOT_PQ_ROM_PORTS" --core-utilization 35 &
run sp128 48 $SP --param R=128 --orfs-var "VERILOG_DEFINES=-DSYNTHESIS -DOT_PQ_ROM_PORTS" --die-area 0 0 560 560 --core-area 2.16 2.16 557.84 557.84 &
wait
echo "$(date -Is) TERMINAL" >> $J/MANIFEST

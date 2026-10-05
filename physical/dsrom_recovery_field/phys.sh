#!/bin/bash
# DS-ROM recovery lever "field" (PQ): SS/FF screen (ot-epyc2) of the new hardware at 1.2 GHz (0.833 ns), 60/25 ps uncertainty,
# ORFS on ot-epyc1tb (WC = SS setup corner; hold at WC + BC = FF), ADDER_MAP_FILE disabled, unique nicknames.
#   pair1/pair0  ot_v41_pq_pair_screen (PQ 1 / PQ 0 baseline: the added area is the difference): per-pair loader with pending load + element banked tags / parity / guard / shadow
#   spw     ot_v41_pq_spine_screen: the PQ spine (R 16, KMAX 256, PHW 6, SAW 8, VAW 19) with registered neighbours,
#           register-file ROMs and the pinned quantisers stubbed (a full-spine screen was dominated by the pinned
#           actquant (-941 ps) and port fixtures)
E=/srv/opentallas-scratch/claude/dsrom-recovery-field/phys2; W=/srv/opentallas-scratch/claude/dsrom-recovery-field/src
O=$E/out; J=$E/jobs; mkdir -p $O $J
cd $W
export OT_ORFS_NUM_CORES=16
COMMON="--view asap7 --clock-period-ns 0.833333 --clock-uncertainty-ns 0.060 --clock-uncertainty-hold-ns 0.025 --corner TT --orfs-corner WC --hold-corners WC,BC --max-transition-ns --max-fanout 32 --slew-margin-percent 30 --orfs-var ADDER_MAP_FILE= --keep-heavy-artifacts --hold-margin-ns 0.01 --stages pnr"
SP="--top ot_v41_pq_spine_screen --source physical/dsrom_recovery_field/ot_v41_pq_spine_screen.sv --source rtl/v41die/ot_v41_spine_pq_w17w10.sv --source physical/dsrom_recovery_field/ot_hdc_actquant_screen_stub.sv --source rtl/hdc/ot_hdc_delay.sv"
run() { # tag peakGB args...
  t=$1; g=$2; shift 2
  echo "$(date -Is) START $t" >> $J/MANIFEST
  /srv/opentallas-scratch/admit.sh $g -- python3 tools/run_abi3_physical.py $COMMON "$@" --nickname-tag dsrf_$t --keep-workdir $O/work_$t --output $O/$t.json --force > $J/$t.log 2>&1
  echo $? > $J/$t.exit
  python3 tools/w18/corner_sta.py --orfs-dir $O/work_$t/orfs --output $O/${t}_corner_sta.json > $J/${t}_sta.log 2>&1
  echo "$(date -Is) END $t exit=$(cat $J/$t.exit)" >> $J/MANIFEST
}
run pair1 8 --io-delay-fraction 0.2 --top ot_v41_pq_pair_screen --source physical/dsrom_recovery_field/ot_v41_pq_pair_screen.sv --source rtl/v41die/ot_v41_pair_pq_ld.sv --source rtl/v41rom/ot_v41_elem_pq_tags.sv --param PHW=6 --param PQ=1 --core-utilization 40 &
run pair0 8 --io-delay-fraction 0.2 --top ot_v41_pq_pair_screen --source physical/dsrom_recovery_field/ot_v41_pq_pair_screen.sv --source rtl/v41die/ot_v41_pair_pq_ld.sv --source rtl/v41rom/ot_v41_elem_pq_tags.sv --param PHW=6 --param PQ=0 --core-utilization 40 &
run spw1 24 --false-path-io $SP --param PQ=1 --param R=16 --orfs-var "VERILOG_DEFINES=-DSYNTHESIS -DOT_PQ_ROM_PORTS" --core-utilization 35 &
run spw0 24 --false-path-io $SP --param PQ=0 --param R=16 --orfs-var "VERILOG_DEFINES=-DSYNTHESIS -DOT_PQ_ROM_PORTS" --core-utilization 35 &
run spw128 48 --false-path-io $SP --param PQ=1 --param R=128 --orfs-var "VERILOG_DEFINES=-DSYNTHESIS -DOT_PQ_ROM_PORTS" --die-area 0 0 480 480 --core-area 2.16 2.16 477.84 477.84 &
wait
echo "$(date -Is) TERMINAL" >> $J/MANIFEST

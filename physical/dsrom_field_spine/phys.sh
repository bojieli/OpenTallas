#!/bin/bash
# DS-ROM field SPINE redesign (Claude:dsrom-field-spine): SS/FF screens of the timing-closed spine ot_v41_spine_pqc_w17w10
# at 1.2 GHz (0.833 ns), 60/25 ps uncertainty, the same flow and wrapper as physical/dsrom_recovery_field/phys.sh
# (WC = SS setup corner; hold at WC + BC = FF), ADDER_MAP_FILE disabled, unique nicknames, routed in context of its
# registered neighbours:
#   c0r16 / c1r16    PQ 0 (closed baseline) / PQ 1 (closed PQ), R 16 regions
#   c0r128 / c1r128  the same at full die scale, R 128 regions (480 x 480 um die)
# Usage: phys.sh <scratch dir> [tags...]   (run from the source root; default: all four)
E=${1:?scratch dir}; shift
TAGS=${*:-c0r16 c1r16 c0r128 c1r128}
O=$E/out; J=$E/jobs; mkdir -p $O $J
export OT_ORFS_NUM_CORES=${OT_ORFS_NUM_CORES:-16}
COMMON="--view asap7 --clock-period-ns 0.833333 --clock-uncertainty-ns 0.060 --clock-uncertainty-hold-ns 0.025 --corner TT --orfs-corner WC --hold-corners WC,BC --max-transition-ns --max-fanout 32 --slew-margin-percent 30 --orfs-var ADDER_MAP_FILE= --keep-heavy-artifacts --hold-margin-ns 0.01 --stages pnr"
SP="--false-path-io --top ot_v41_pqc_spine_screen --source physical/dsrom_field_spine/ot_v41_pqc_spine_screen.sv --source rtl/v41die/ot_v41_spine_pqc_w17w10.sv --source physical/dsrom_recovery_field/ot_hdc_actquant_screen_stub.sv --source rtl/hdc/ot_hdc_delay.sv --source rtl/v41rom/ot_v41_kreg.sv --source rtl/common/ot_prefix.sv"
DEF=(--orfs-var "VERILOG_DEFINES=-DSYNTHESIS -DOT_PQ_ROM_PORTS")
run() { # tag peakGB args...
  t=$1; g=$2; shift 2
  echo "$(date -Is) START $t" >> $J/MANIFEST
  /srv/opentallas-scratch/admit.sh $g -- python3 tools/run_abi3_physical.py $COMMON "$@" --nickname-tag dsfs_$t --keep-workdir $O/work_$t --output $O/$t.json --force > $J/$t.log 2>&1
  echo $? > $J/$t.exit
  python3 tools/w18/corner_sta.py --orfs-dir $O/work_$t/orfs --output $O/${t}_corner_sta.json > $J/${t}_sta.log 2>&1
  echo "$(date -Is) END $t exit=$(cat $J/$t.exit)" >> $J/MANIFEST
}
for t in $TAGS; do
  case $t in
    c0r16)  run $t 32 $SP "${DEF[@]}" --param PQ=0 --param R=16 --core-utilization 35 & ;;
    c1r16)  run $t 32 $SP "${DEF[@]}" --param PQ=1 --param R=16 --core-utilization 35 & ;;
    c0r128) run $t 64 $SP "${DEF[@]}" --param PQ=0 --param R=128 --die-area 0 0 480 480 --core-area 2.16 2.16 477.84 477.84 & ;;
    c1r128) run $t 64 $SP "${DEF[@]}" --param PQ=1 --param R=128 --die-area 0 0 480 480 --core-area 2.16 2.16 477.84 477.84 & ;;
  esac
done
wait
echo "$(date -Is) TERMINAL $TAGS" >> $J/MANIFEST

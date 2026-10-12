#!/bin/bash
# el1011-ds-misc 2026-10-11: cheap IO-placement check of a MARGIN 3 face plan before a route is queued: synthesis of
# a port-identical stub (top) or the real leaf, floorplan, global placement and place_pins with the pinplan_m3.py
# regions (stopped after CTS; PPL errors fail it).  pincheck_m3.sh <top|land8|mirror> <DX> <DY> <out dir>
# Pins are placed explicitly (OT_PIN_BALANCE_*: uniform spacing along the region, consecutive pins alternating between
# the two edge layers): an ordered -group of a face's region is laid on one layer and groups on different layers do
# not share an interval (PPL-0107 in four runs at ~10 pins/um N/S, ~2.5 pins/um W/E).
set -u
kind=$1; DX=$2; DY=$3; W=$4; mkdir -p $W/work/orfs/tmp
export OT_PIN_GROUP_MAX=1 OT_PIN_BALANCE_H="M4 M6" OT_PIN_BALANCE_V="M5 M7"
D=rtl/dsrom_sys/s81_window_la/recovered_ctl_m2
case $kind in
  top) S=physical/dsrom_window_source/cl_pchk_top/stub.sv; mkdir -p $(dirname $S); python3 physical/dsrom_window_source/pincheck_m3.py $S; SRCS=(--source $S); TOP=ot_dsrom_window_source_ctl
       M=5; P=(--param MARGIN=3);;
  land8) SRCS=(--source $D/ot_dsrom_wsrc_land8.sv --source $D/ot_hdc_prefix.sv); TOP=ot_dsrom_wsrc_land8; M=2.16; P=();;
  mirror) SRCS=(--source $D/ot_dsrom_wsrc_mirror.sv); TOP=ot_dsrom_wsrc_mirror; M=2.16; P=();;
esac
EX=$(python3 -c "print(round($DX-$M,3))"); EY=$(python3 -c "print(round($DY-$M,3))")
PINARGS=(); while IFS= read -r l; do PINARGS+=(--pin-region "$l"); done < <(python3 physical/dsrom_window_source/pinplan_m3.py $kind $DX $DY)
export OT_ORFS_NUM_CORES=8 NUM_CORES=8
python3 tools/run_abi3_physical.py --view asap7 --top $TOP "${SRCS[@]}" "${P[@]}" --clock-period-ns 0.770 \
  --die-area 0 0 $DX $DY --core-area $M $M $EX $EY --place-density 0.50 --orfs-var ADDER_MAP_FILE= \
  --orfs-var "IO_PLACER_H=M4 M6" --orfs-var "IO_PLACER_V=M5 M7" "${PINARGS[@]}" --orfs-var TMPDIR=/work/tmp \
  --routing-layers M2 M9 --stages pnr --pnr-stop-after cts --purpose characterization --nickname-tag pchk_$kind \
  --keep-workdir $W/work --force --output $W/physical.json > $W/run.log 2>&1
rc=$?
n=$(grep -c 'PPL-0102\|ERROR PPL' $W/run.log)
ls $W/work/orfs/results/asap7/*/base/3_2_place_iop.odb >/dev/null 2>&1 && reached=1 || reached=0
echo "pincheck $kind ${DX}x${DY} rc=$rc ppl_errors=$n reached_iop=$reached"
[ $n = 0 ] && [ $reached = 1 ] && echo "PINCHECK PASS $kind" || echo "PINCHECK FAIL $kind"

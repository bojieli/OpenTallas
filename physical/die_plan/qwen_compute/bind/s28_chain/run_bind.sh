#!/bin/bash
# QC-S28-BIND strict bind on the ONE real event tree (no overlay, no links).
# usage: run_bind.sh TAG PLAN SIDECAR [ELAB_SEED_DIR]
#  - plan is copied to the tree plan_of_record/zz_bind_TAG.json (pins_file etc. resolve plan-folder relative)
#  - sidecar -> runtime/sidecar_pv.json (= manifest clock_landing_table); rm first, never write through a link
#  - no ELAB_SEED: `bind.py elab` on the event tree (fresh elaboration of the tree RTL + manifest), then `bind --strict`
#  - ELAB_SEED: hard-link the elaboration files of an earlier elab of THIS tree + manifest (elab does not read the plan)
set -u; cd /
E=${EVENT_TREE:-/srv/opentallas-scratch2/claude/wt/qc-s28-event}; W=/srv/opentallas-scratch2/claude/qc-s28-hf1c/bind
POR=physical/die_plan/qwen_compute/plan_of_record; RT=physical/die_plan/qwen_compute/qc_start_1106/runtime
TAG=$1; PL=$2; SIDE=$3; SEED=${4:-}
O=$W/bind_$TAG; L=$W/bind_$TAG.log; SP=$E/$POR/zz_bind_$TAG.json; M=$RT/asbuilt_sw2_pv.json
[ "$(cd $E && git rev-parse --is-inside-work-tree)" = true ] || { echo "not a git tree"; exit 9; }
find $E/physical $E/tools $E/rtl -maxdepth 3 -type l | head -1 | grep -q . && { echo "LINKS IN TREE"; exit 9; }
rm -f $SP; cp $PL $SP
if ! cmp -s $SIDE $E/$RT/sidecar_pv.json; then rm -f $E/$RT/sidecar_pv.json; cp $SIDE $E/$RT/sidecar_pv.json; fi
rm -rf $O; mkdir -p $O
# clock_merge source: $CM_FILE, else the sibling <PLAN stem>.clock_merge.json of the input plan
[ -z "${CM_FILE:-}" ] && [ -e "${PL%.json}.clock_merge.json" ] && CM_FILE=${PL%.json}.clock_merge.json
export CM_FILE=${CM_FILE:-}; CMREF=${CM_REF:-$W/bind_c8}
[ -z "${KP_FILE:-}" ] && [ -e "${PL%.json}.kit_pricing.json" ] && KP_FILE=${PL%.json}.kit_pricing.json
export KP_FILE=${KP_FILE:-}
CMK=$(python3 -I $W/cm_inject.py has $SP)
echo "bind start $(date) host=$(hostname) tree=$E head=$(cd $E && git rev-parse --short=12 HEAD) plan=$(sha256sum $SP|cut -c1-12) sidecar=$(sha256sum $E/$RT/sidecar_pv.json|cut -c1-12) manifest=$(sha256sum $E/$M|cut -c1-12) bind.py=$(sha256sum $E/tools/die_plan/bind.py|cut -c1-12) r8=$(sha256sum $E/$RT/r8_sw2.json|cut -c1-12) cm=$CMK cm_file=${CM_FILE:-none} kp_file=${KP_FILE:-none} manifest_used=see-asbuilt_manifest_injected seed=${SEED:-none}" > $L
s=$(date +%s); cd $E
if [ -z "$SEED" ]; then
  nice -n 19 python3 -I -B -X faulthandler tools/die_plan/bind.py elab $SP --out $O --asbuilt $M >> $L 2>&1; echo "ELAB_RC=$? wall=$(( $(date +%s)-s )) s" >> $L
else
  for f in asbuilt.json asbuilt.yosys.log asbuilt.ys asbuilt_lib_stubs.sv asbuilt_sources.json provenance_elab.json; do [ -e $SEED/$f ] && ln -f $SEED/$f $O/$f; done
fi
# guarded clock_merge inject (cm_inject.py): plan-side asbuilt.clock_merge -> a manifest copy beside the manifest
# guarded kit_source_station_pricing inject (kp_inject.py, QC-BIND-IST-PAD): sibling <PLAN stem>.kit_pricing.json
MB=$M; MC=$RT/zz_manifest_cm_$TAG.json; MK=$RT/zz_manifest_kp_$TAG.json; MF=$RT/zz_manifest_ab_$TAG.json; rm -f $MC $MK $MF
python3 -I $W/cm_inject.py inject $SP $M $MC $CMREF >> $L 2>&1 || { echo "BIND_RC=11 clock_merge inject refused" >> $L; tail -1 $L; exit 11; }
if [ -n "$KP_FILE" ]; then
  KP_FILE=$KP_FILE python3 -I $W/kp_inject.py inject $SP $M $MK >> $L 2>&1 || { echo "BIND_RC=11 kit pricing inject refused" >> $L; tail -1 $L; exit 11; }
fi
AB=(); [ -s $MC ] && AB+=(clock_merge=$MC); [ -s $MK ] && AB+=(kit_source_station_pricing=$MK)
if [ ${#AB[@]} -gt 0 ]; then
  python3 -I $W/ab_compose.py $M $MF "${AB[@]}" >> $L 2>&1 || { echo "BIND_RC=11 manifest compose refused" >> $L; tail -1 $L; exit 11; }
  MB=$MF; cp $MF $O/asbuilt_manifest_injected.json
fi
timeout -s ABRT 5400 nice -n 19 python3 -I -B -X faulthandler tools/die_plan/bind.py bind $SP --out $O --asbuilt $MB --strict ${ALLGAPS:+--all-gaps} >> $L 2>&1
rc=$?
if [ "$CMK" = True ] && [ -d $O/rtl ]; then                  # also on a failed bind (report), rc escalates only from 0
  [ -n "$CM_FILE" ] && cp $CM_FILE $O/clock_merge.json; crc=0
  for ty in $(python3 -I $W/cm_inject.py types $SP); do     # kit_rtl.json bound_only_pins of each merged type
    nice -n 19 python3 -I -B tools/die_plan/bind.py kit-rtl $SP --out $O --type $ty --asbuilt $MB >> $L 2>&1 || { echo "KIT_RTL FAIL $ty" >> $L; crc=13; }
  done
  python3 -I $W/cm_inject.py check $SP $O $CMREF >> $L 2>&1 || crc=12
  echo "CM_RC=$crc" >> $L; [ $rc = 0 ] && rc=$crc
fi
if [ -n "$KP_FILE" ]; then cp $KP_FILE $O/kit_pricing.json
  python3 -I $W/kp_inject.py check $L > $O/kp_check.log 2>&1; krc=$?; cat $O/kp_check.log >> $L; echo "KP_RC=$krc" >> $L
  [ $rc = 0 ] && [ $krc != 0 ] && rc=14
fi
echo "BIND_RC=$rc wall=$(( $(date +%s)-s )) s end $(date)" >> $L
[ -s $O/bus_groups.json ] && echo "bus_groups=$(sha256sum $O/bus_groups.json|cut -c1-12)" >> $L
tail -1 $L

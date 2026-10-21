#!/bin/bash
# QW2-NEXTGEN 10-21: next g5r3 GEN = qw2-diefix-kit (11e0f16ee serdes2 bus-group frame pads + clkrx overflow slots) + the
# slice2 W/E parent slot grown to 2462.4 x 4276.8 um (dv_slice_slot_plan.py; env SLOT_W / SLOT_H).  The COORD slot
# 4060.8 x 2592 (+907.2 VM8 group, +2 x 345.6 lrly strips = 10.53 mm2) does not fit the reticle: each of the 12 die
# columns is one slice wide (2592 pitch, the slice N/S faces carry its column's cw/rs words face to face), so +1598.4 x
# per slot = die W 52,164 um > 33,000.  The same area as a taller slot (2462.4 x 4276.8 = 10.53 mm2) moves cluster rows
# 2-3 N by 1684.8 um; die 32,983.2 x 25,898.4 (SG 129.6) / 25,984.8 (SG 172.8) um, under 33,000 x 26,000.  No squeeze.
# QW-C3-DIE 10-21: setup_g5r3.sh of qw-g5r3w-kit + SG (6th arg) = OT_SPLIT_DV_SLICE_GAP_UM, the channel above AND below the
# dvs slice row. G4 / w1-w3 failed 'tree pads: no free spot' (dv_rs_E5_2_a, q3h_col_47_1): the slice<->cluster vertical-flow
# pads (narrow classes, 2 cols x 3 rows = 129.6 x 90.7 um) must sit in the 43.2-um slice-row gap between c16_*_1 / dvs_* /
# c16_*_2, which no frame taller than ~43 um fits; the w1-w3 x-widening of slice column gaps is 2.4 mm from the sink. A
# 129.6 / 172.8-um slice-row channel (the cluster-row gaps are already 129.6) adds real relay room; the die grows
# 2 x (SG - 43.2) um in y (H stays under the 26-mm reticle side). No squeeze, no stage added.
# QW-G5R3 10-21 run-dir setup (ep6): successor GEN of Codex classgeom0150 on claude/qw-g5r3-1021.
# src = copy of codex-qw-classgeom0030/src + overlay tar (every tools/rtl/results/physical file changed eb527c909..tip).
# usage: setup_g5r3.sh TAG GEOM FAULT BASE   GEOM = 0030 (B172.8/west86.4, corefeed 17409.6) | 0125 (E1/E2 259.2, west129.6,
#        corefeed 17280); FAULT = 1 (fault-OR emission, plan regenerated from BASE's data-only GEN case) | 0; BASE = data-only tag
set -eu
T=${1:?tag}; GEOM=${2:?geom}; FAULT=${3:?fault}; BASE=${4:-}; [ "$BASE" = - ] && BASE=; CLASSES=${5:-1}; SG=${6:-43.2}
R=/srv/opentallas-scratch/claude/mu-die-qw; K=$R/qw2-nextgen-kit; S=$R/$T; C=/srv/opentallas-scratch/claude/codex-qw-classgeom0030
G=/srv/opentallas-scratch/claude/codex-qw-classgeom$GEOM
[ -e $S ] && { echo "$S exists"; exit 3; }
mkdir -p $S
echo "$(date '+%F %T %Z') QW-C3-DIE setup start ($T geom=$GEOM sgap=$SG fault=$FAULT base=$BASE)" >> $S/PILOT.log
cp -a $C/src $S/src
tar -xf $K/overlay.tar -C $S/src
cp $K/SOURCE_COMMIT $S/src/SOURCE_COMMIT
for f in gen.sh run.sh run_candidate.sh land_plan_bi_chain.json reset_release_prior_g4try3.json; do cp $C/$f $S/; done
cp $G/receiver_plan.json $S/receiver_plan.json
python3 $S/src/tools/qwen_split/dv_slice_slot_plan.py $G/receiver_plan.json $S/receiver_plan.json --slot-w ${SLOT_W:-2462.4} --slot-h ${SLOT_H:-4276.8} --sgap $SG --record $S/slice_slot.json >> $S/PILOT.log 2>&1 || { echo "slice slot plan refused (PILOT.log)"; exit 4; }
sed -i "s#$C#$S#g" $S/gen.sh $S/run.sh $S/run_candidate.sh
sed -i 's#^O=../out; L=../out.log;#O=$S/out; L=$S/out.log;#' $S/run.sh
sed -i "s#OT_SPLIT_DV_SLICE_GAP_UM=\${SGAP:-43.2}#OT_SPLIT_DV_SLICE_GAP_UM=\${SGAP:-$SG}#" $S/run.sh
grep -q "OT_SPLIT_DV_SLICE_GAP_UM=\${SGAP:-$SG}" $S/run.sh || { echo "slice gap not set"; exit 4; }
grep -q '^O=\$S/out; L=\$S/out.log;' $S/run.sh || { echo "run.sh out path not switched"; exit 4; }
[ "$GEOM" = 0125 ] && sed -i 's#CORE_FEED_XY=17409.6,12096.0#CORE_FEED_XY=17280.0,12096.0#' $S/gen.sh
# QW-G5R3W (REFILL-2): widened class-carrying gap geometries carry their E0-relative core feed (dvs_E0.x-86.4)
[ -e $G/core_feed ] && sed -i "s#CORE_FEED_XY=17409.6,12096.0#CORE_FEED_XY=$(cat $G/core_feed),12096.0#" $S/gen.sh
# 54009fee1: reserve the real 104x106 bend frame (max H/HV/VH) for side-by-side DV class paths before native site allocation
sed -i 's#^export OT_SPLIT_FWD_CLASSES=1 #export OT_SPLIT_FWD_CLASS_BEND_RESERVE=1 OT_SPLIT_FWD_CLASSES=1 #' $S/run_candidate.sh
grep -q OT_SPLIT_FWD_CLASS_BEND_RESERVE=1 $S/run_candidate.sh || { echo "bend reserve not set"; exit 4; }
# QW-G5R3N: narrow class split (every part <= 128 b -> closed 64.776x30.216 128-b classes) for GEN, bind and chain
sed -i "s#^export OT_SPLIT_FWD_CLASS_BEND_RESERVE=1 #export OT_SPLIT_FWD_CLASS_MAXW=${MAXW:-128} OT_SPLIT_FWD_CLASS_COLS=${COLS:-2} OT_SPLIT_FWD_CLASS_BEND_RESERVE=1 #" $S/run_candidate.sh
grep -q "^export OT_SPLIT_FWD_CLASS_MAXW=" $S/run_candidate.sh || { echo "maxw not set"; exit 4; }
if [ "$FAULT" = 1 ]; then
  sed -i 's#^env \$X \$G #env \$X \$G OT_SPLIT_FAULT_EMIT=\${FAULT_EMIT:-1} OT_SPLIT_FAULT_ORPHAN=\${ORPHAN:-fail} OT_RELAY_RIP_ROUNDS=\${RIP:-120} OT_SPLIT_FAULT_DEG=\${FDEG:-8} OT_SPLIT_FAULT_WIDE_BITS=512 OT_SPLIT_FAULT_PLAN=\$S/fault_emit_plan.json #' $S/run.sh
  grep -q 'OT_SPLIT_FAULT_EMIT=' $S/run.sh || { echo 'fault env not set'; exit 4; }
fi
# die chain scripts (dv2f20g5r2b, the last chain that ran GEN -> bind -> reset proj -> phase2 -> phase3 to completion)
for f in pre.sh chain.sh follow.sh phase2_fleet.sh phase3.sh; do sed "s#dv2f20g5r2b#$T#g" $K/r2b/$f > $S/$f; done
# GEN = Codex class candidate (class flags + shared ew595_r16 image) instead of the bare gen.sh
sed -i "s#^bash \$S/gen.sh; rc=\$?#cd \$S \&\& bash \$S/run_candidate.sh; rc=\$?#" $S/pre.sh
grep -q 'run_candidate.sh; rc=' $S/pre.sh || { echo "pre.sh GEN not switched"; exit 4; }
CLS="export OT_SPLIT_FWD_CLASS_MAXW=${MAXW:-128} OT_SPLIT_FWD_CLASS_COLS=${COLS:-2} OT_BIND_FWD_CLASSES=1 OT_SPLIT_FWD_CLASSES=1 OT_SPLIT_FWD_CLASS_PACK=1 OT_SPLIT_FWD_CLASS_BEND_RESERVE=1 OT_BIND_VIEW_SELECT=results/arch/qwen_split_compute_1014/bind_view_select.json OT_QWEN_D2D_IMAGE=rtl/qwen_sys/d2d_static_20261015/d2d_cal_image_mu_ew595_r16.svh OT_SPLIT_RST_REGION_LAND=1 OT_SPLIT_FWD_RST_SYNC=1 OT_RST_REP_VIEW=closed   # QW-G5R3N: strict bind / chain see the narrow class GEN"
sed -i "/^S=/a $CLS" $S/pre.sh $S/chain.sh
if [ "$CLASSES" = 0 ]; then
  # QW-G5R3 E: no landing-class emission (classgeom0030 + BEND_RESERVE fails class packing at every 129.6-um slice gap
  # filled by the two 64.8-um data-landing columns: dv2f21g5r3c W4 rt_rd 104x106); physical fallback = g5r2b-style GEN
  # QW2-NEXTGEN: the MAXW/COLS prefix (QW-G5R3N) is stripped too (c3/diefix kits never matched here: 'classes not switched off')
  sed -i 's#^export \(OT_SPLIT_FWD_CLASS_MAXW=[^ ]* OT_SPLIT_FWD_CLASS_COLS=[^ ]* \)\?OT_SPLIT_FWD_CLASS_BEND_RESERVE=1 OT_SPLIT_FWD_CLASSES=1 OT_SPLIT_FWD_CLASS_PACK=1 OT_BIND_FWD_CLASSES=1#export OT_SPLIT_FWD_CLASSES=0 OT_SPLIT_FWD_CLASS_PACK=0 OT_BIND_FWD_CLASSES=0#' $S/run_candidate.sh
  grep -q '^export OT_SPLIT_FWD_CLASSES=0' $S/run_candidate.sh || { echo "classes not switched off"; exit 4; }
  sed -i 's#^export \(OT_SPLIT_FWD_CLASS_MAXW=[^ ]* OT_SPLIT_FWD_CLASS_COLS=[^ ]* \)\?OT_BIND_FWD_CLASSES=1 OT_SPLIT_FWD_CLASSES=1 OT_SPLIT_FWD_CLASS_PACK=1 OT_SPLIT_FWD_CLASS_BEND_RESERVE=1 #export OT_BIND_FWD_CLASSES=0 OT_SPLIT_FWD_CLASSES=0 OT_SPLIT_FWD_CLASS_PACK=0 #' $S/pre.sh $S/chain.sh
  grep -q '^export OT_BIND_FWD_CLASSES=0' $S/chain.sh || { echo "chain classes not switched off"; exit 4; }
fi
if [ "$FAULT" = 1 ]; then
  # fault plan = reserved relay/landing boxes + landing centres of the EXACT data-only GEN of this geometry (BASE)
  sed -i "/^echo .*pre start/a B=$R/$BASE; while [ ! -e \$B/GEN_DONE ] \&\& [ ! -e \$B/FINAL_GEN_FAIL ] \&\& [ ! -e \$B/FINAL_LANDPLAN_INVALID ] \&\& [ ! -e \$B/SETUP_FAIL ]; do sleep 60; done\n[ -e \$B/GEN_DONE ] || { echo \"\$(date '+%F %T %Z') QW-G5R3 base \$B GEN failed: no fault plan\" >> \$S/PILOT.log; echo base > \$S/FINAL_GEN_FAIL; exit 4; }\npython3 \$S/src/results/rtl/qw_g5froot_1020/mkplan_rfs.py \$B/out/case \$S/fault_emit_plan.json >> \$S/PILOT.log 2>\&1 || { echo plan > \$S/FINAL_GEN_FAIL; exit 4; }" $S/pre.sh
  grep -q mkplan_rfs $S/pre.sh || { echo "pre.sh plan step missing"; exit 4; }
fi
sed -i 's#"reason":"g5f3: g5 + emitted fault-OR tree (QW-G5STA);#"reason":"g5r3 (QW-G5R3N): narrow-class (<=128 b) class-geometry GEN + nextgen + g5noroot + main;#' $S/phase3.sh
cp $R/project_reset.sh $S/project_reset_g5.sh
ln -sfn $S /srv/opentallas-scratch/claude/qwen-split-compute/$T
( cd $S && sha256sum gen.sh run.sh run_candidate.sh receiver_plan.json land_plan_bi_chain.json reset_release_prior_g4try3.json pre.sh chain.sh follow.sh phase2_fleet.sh phase3.sh src/SOURCE_COMMIT src/tools/qwen_rom_fulldie_b3r2.py src/tools/qwen_split/fwd_class_emit.py src/tools/qwen_split/fault_emit.py src/tools/qwen_split/dv_slice_slot_plan.py slice_slot.json src/results/arch/qwen_split_compute_1014/bind_view_select.json src/rtl/qwen_sys/d2d_static_20261015/d2d_cal_image_mu_ew595_r16.svh > SHA256SUMS )
SG_UM=$SG python3 - $S $T $GEOM $FAULT "$BASE" $K/SOURCE_COMMIT $CLASSES <<'PY'
import json, sys, hashlib
s, t, geom, fault, base, sc, _cls = sys.argv[1:]
h = {l.split()[1]: l.split()[0] for l in open(s + '/SHA256SUMS')}
json.dump(dict(tag=t, lane='QW2-NEXTGEN', slice_slot=json.load(open(s + '/slice_slot.json')), slice_gap_um=float(__import__('os').environ.get('SG_UM','43.2')), class_maxw=128, class_cols=int(__import__('os').environ.get('COLS','2')), source_commit=open(sc).read().split()[0], branch='claude/qw2-nextgen-1021',
               src='copy of codex-qw-classgeom0030/src + overlay of every tools/rtl/results/physical file changed eb527c909..tip',
               geometry_recipe='classgeom' + geom, fault_emit=fault == '1', landing_classes=sys.argv[7] == '1', fault_plan_base=base or None,
               flags=dict(OT_SPLIT_FWD_CLASS_BEND_RESERVE=1, OT_SPLIT_FWD_CLASSES=1, OT_SPLIT_FWD_CLASS_PACK=1, OT_BIND_FWD_CLASSES=1) if _cls == '1' else dict(OT_SPLIT_FWD_CLASSES=0, OT_SPLIT_FWD_CLASS_PACK=0, OT_BIND_FWD_CLASSES=0),
               image='rtl/qwen_sys/d2d_static_20261015/d2d_cal_image_mu_ew595_r16.svh (blob db9eda03, KV-PROG17 shared)',
               status='PILOT_NOT_A_GATE: diagnostic die chain', sha256=h), open(s + '/source.json', 'w'), indent=2)
PY
echo "$(date '+%F %T %Z') QW2-NEXTGEN setup done" >> $S/PILOT.log

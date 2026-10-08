#!/bin/bash
# BF native pair (PINREG=1, HITFIX=1) closure variants (2026-10-07), same recipe as route_cl.sh (ORFS repairs at WC, route IO
# from the MEASURED SS insertion CK_SS_MEAN, sign-off signoff_ref.sdc at 833.333 ps) plus the variant:
#   BF_VAR=half  : HALF=1 (SAFE B: element on the half-rate gated clock), route SDC + sign-off add half_mc.sdc (MC 2/1)
#   BF_VAR=recut : RECUT=2 (A: q-element re-cuts + BF lanes re-cut)
#   BF_VAR=halfphl: half + HALF_PHL=1 (phase FF on the ICG clock net, ph_local.tcl PRE_CTS / ph_local_post.tcl POST_CTS)
#   BF_VAR=recutcgl: RECUT=2 + element clock-gate enable FF on an ancestor clock net (cg_local.tcl, OT_CGL_FRAC)
#   BF_CORNER=TC: ORFS corner / route repair at TT (owner option B sign-off: setup TT, hold FF)
#   BF_VAR=deep4 / deep5: RECUT=4 / 5 deep full-rate BF (ot_v41_bf16_lanes3 DEEP 1 / 2; OPTIONAL lever, s81-bf)
#   BF_VAR=unroll: RECUT=3 (A + BF lane chunk chains unrolled by 2 on a half-rate gated clock; + u2_mc.sdc)
# Route at 730 ps (owner SAFE rule: route target 730, sign-off 833.333); BF_PERIOD=<ns> overrides the route target only.
# usage: OUT=<dir> SRC=<src root> BF_VAR=half|recut route_var.sh <label> [extra run_abi3_physical args]
set -o pipefail
L=${1:?label}; shift; S=${SRC:-.}; O=${OUT:?out}/$L; mkdir -p $O; cd $S
V=${BF_VAR:?BF_VAR=half|recut}
SS=${CK_SS_MEAN:-1042}
export OT_ORFS_NUM_CORES=16 OPENTALLAS_ORFS_IMAGE=${OPENTALLAS_ORFS_IMAGE:-sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29}
POST="--post-sdc physical/s81_native_bf/margin/signoff_ref.sdc"
[[ "$V" = half || "$V" = halfphl ]] && POST="$POST --post-sdc physical/s81_native_bf/margin/half_mc.sdc"
VA="--$V"
[ "$V" = halfphl ] && VA="--half --half-phl"
[ "$V" = recutcgl ] && VA="--recut --recut-level 2 --recut-cgl"
[ "$V" = deep4 ] && VA="--recut --recut-level 4"
[ "$V" = deep5 ] && VA="--recut --recut-level 5"
[ "$V" = unroll ] && { VA="--recut --recut-level 3"; POST="$POST --post-sdc physical/s81_native_bf/margin/u2_mc.sdc"; }
echo "$(date -Is) START $(hostname) var=$V ss=$SS args=$*" >> $O/MANIFEST
python3 tools/s81/run_bf_native_physical.py --margin --wc-only --hitfix $VA --corner ${BF_CORNER:-WC} --period ${BF_PERIOD:-.730} --work $O/work --output $O/physical.json \
  --util ${BF_UTIL:-45} --tag $L --ins-ss $SS --ins-ff $SS --extra="$*" > $O/run.log 2>&1; rc=$?
echo "rc=$rc" > $O/exit
if [ $rc -eq 0 ] && [[ " $* " != *"--pnr-stop-after"* ]]; then
  python3 tools/w18/corner_sta.py --orfs-dir $O/work/orfs --macro physical/asap7_memory_macros_v2/ot_rom_4096x274_m8 \
    $POST --output $O/corner_sta.json > $O/sta.log 2>&1; echo "corner_rc=$?" >> $O/exit
  # owner option B (2026-10-07): setup sign-off at TT -- the same sign-off script with the TT libraries (ROM _tt.lib)
  if [ -f $O/work/orfs/w18_sta_ss.tcl ]; then
    sed -e 's/_RVT_SS_/_RVT_TT_/g; s/_ss\.lib/_tt.lib/g; s/OT_CORNER ss/OT_CORNER tt/' $O/work/orfs/w18_sta_ss.tcl > $O/work/orfs/w18_sta_tt.tcl
    docker run --rm -v $O/work/orfs:/work -v $PWD:/src:ro ${OPENTALLAS_ORFS_IMAGE} bash -lc \
      "/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /work/w18_sta_tt.tcl" > $O/work/orfs/w18_sta_tt.log 2>&1
    echo "tt_rc=$? $(grep '^OT_WS ' $O/work/orfs/w18_sta_tt.log)" >> $O/exit
  fi
fi

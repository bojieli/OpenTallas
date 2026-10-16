#!/bin/bash
# ECTL A native-capture HELD recovery r1 (Q-ELEM, 2026-10-15). Manual canonical successor of the CLOSED
# qkd_ectl_a_tp8_epoch_direct_h5-h5-fbaf25d48; the CLOSED run is only READ (hash-checked) and never written.
#   recovery_r1.sh <new run dir M (must not exist)> <src tar: git archive fbaf25d48 sign-off paths + this commit's plan>
# reroute_reason: {kind: pin_register, source: diagnosis.json, cell: qkd_ectl_a_tp8_epoch_direct, capture_ps: 220.98393,
#   fix: remove 1826 redundant routed hold-pair cells (913 inputs), keep pin capture regs + ot_inhold/ot_ihdrv pads}
# Unchanged: sign-off SDC set of the CLOSED ECO (signoff.sdc + io_ref_routed.sdc), HM 18 / SM 40 / FILT 40 / 2 passes,
# full repair, TT setup / FF hold acceptance 0, DRC 0; plan applied inside the incremental GRT of the original guides (as the closed ECO); KEEPCLK=0 (as the closed ECO)
# (attempt 1 KEEPCLK=1 died DRT-0206: DPL moved a clock buffer under a kept wire -> hold_eco.tcl now re-routes dirty clock nets;
# attempt 2 KEEPCLK=0 fresh-routed the whole clock tree: reg2reg TT -106 / FF -297 ps = clock skew, rejected;
# attempt 3 fresh GRT + KEEPCLK=1: kept clock wires had no guides -> DRT-0206 on 596 clock terms. 
# attempt 4 incremental guides + KEEPCLK=1: DRT-0206 on kept clock wires again -> KEEPCLK=0 with guides = the CLOSED ECO's method). KEEPWIRES / FREEZE are refused by hold_eco.sh/.tcl with the normalization.
set -euo pipefail
M=$1; TAR=$2
J=/srv/opentallas-scratch2/claude/closure-loop/qkd_ectl_a_tp8_epoch_direct_h5-h5-fbaf25d48
L=qkd_ectl_a_tp8_epoch_direct_h5_h5_fbaf25d48
D=opentallas_qkd_ectl_a_tp8_epoch_direct_asap7_ref_qkd_ectl_a_tp8_epoch_direct_h5_h5_fbaf25d48
ODB_SHA=e667770dccecdbf1ee0e637408d034fb3eafb0ca05b0e71545e3d6e67e814f44
PLAN=results/arch/qwen_split_1014/ectl_a_capture_2116/normalize/apply_unqualified.tcl
PLAN_SHA=e2abc3b9388f30a05520749364bde8a3fea90ed4b4146f02a57415badac55132
[ "$(sha256sum $J/routes/$L/work/orfs/results/asap7/$D/base/6_final.odb | cut -d' ' -f1)" = $ODB_SHA ] || { echo "CLOSED ODB changed"; exit 2; }
mkdir "$M"   # exclusive
mkdir -p $M/src $M/routes $M/record
tar -xf "$TAR" -C $M/src
[ "$(sha256sum $M/src/$PLAN | cut -d' ' -f1)" = $PLAN_SHA ] || { echo "plan hash mismatch"; exit 2; }
cp -a $J/routes/$L $M/routes/$L
rm -rf $M/routes/$L/view.pre_eco
cp -a $M/src/tools/closure_loop $M/cl          # reviewed helpers of this commit (hold_eco.sh/.tcl + guard)
RB=$M/routes/$L/work/orfs/results/asap7/$D/base
[ "$(sha256sum $RB/6_final.odb | cut -d' ' -f1)" = $ODB_SHA ] || { echo "copied ODB hash mismatch"; exit 2; }
echo "{\"closed_job\":\"$J\",\"input_odb_sha256\":\"$ODB_SHA\",\"plan\":\"$PLAN\",\"plan_sha256\":\"$PLAN_SHA\",\"started\":\"$(date -Is)\"}" > $M/record/inputs.json
cd $M/src
ECO_SESSION=mm ALLOW_FRESH_GRT=0 NATIVE_FRESH_GRT=0 NATIVE_NORMALIZE_TCL=$M/src/$PLAN NATIVE_NORMALIZE_SHA256=$PLAN_SHA \
  HM=18 SM=40 FILT=40 PASSES=2 RESAWARE=1 HOLDCELLS=1 ACC_SS=0.0 ACC_FF=0.0 SETUP_LIB=TT KEEPCLK=0 BUF=30 \
  MACROS=physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2 THREADS=8 SDC_NAME=6_final.sdc ECO_RB_DB=6_final.odb \
  ROUTE_CFG=$M/routes/$L/work/orfs/config.mk \
  bash $M/cl/hold_eco.sh $RB $RB $M/eco qkd_ectl_a_tp8_epoch_direct \
    physical/ref_tile/qkd_ectl_a_tp8_epoch_direct_h5/signoff.sdc physical/common_flow/io_ref_routed.sdc
cat $M/eco/result.json
# install into the COPY (never the CLOSED run) and export the view for the native audit
EB=$(ls -d $M/eco/orfs/results/asap7/*/base)
for f in 6_final.odb 6_final.spef 6_final.v; do mv $RB/$f $RB/$f.closed_in; cp $EB/$f $RB/$f; done
cp $M/routes/$L/corner_sta.json $M/routes/$L/corner_sta.json.closed_in; cp $M/eco/corner_sta.json $M/routes/$L/corner_sta.json
python3 tools/ref_tile/ref_tile.py export --orfs-dir $M/routes/$L/work/orfs --kit physical/ref_tile/qkd_ectl_a_tp8_epoch_direct_h5 \
  --out $M/record/views/qkd_ectl_a_tp8_epoch_direct --macro-view physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2 \
  > $M/record/export.log 2>&1
echo RECOVERY_R1_DONE

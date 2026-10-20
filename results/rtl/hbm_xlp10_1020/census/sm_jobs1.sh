#!/usr/bin/env bash
# HBM-XLP10 SM.MATVEC measured runs (tb_toksim_smhbm, MC3, FETCH 200; = SMXL2 xl_ds*_f200 knobs, SMB_XMODE varied)
cd /home/ubuntu/wt/hbm-xlp10-1020
export L=/srv/opentallas-scratch/claude/hbm-xlp10-1020/sm
B="SMB_CENSUS_R=1 SMB_OP_GAP=16 SMB_X_GAP=16 SMB_PACE_NUM=80 SMB_PACE_DEN=64 SMB_PACE_ADD=8 SMB_BSCALE=1 TOKSIM_DEFINES=XSLOT,OPEN_IL,PTRACE TOKSIM_PC=mc3 SMB_FETCH=200 SMB_FLAT=200 SMB_RMARGIN=8"
run() { bash tools/hbm_layer_vehicle/run_toksim_smhbm.sh run "$1" "$2" $B $3 > /tmp/xlp10/sm_$1.out 2>&1; }
run xl_dsA "L00:0,L02:2" "SMB_XMODE=xl" &
run xl_dsB "L14:14,head:0" "SMB_XMODE=xl" &
run xr_dsA "L00:0,L02:2" "SMB_XMODE=xlr" &
run xr_dsB "L14:14,head:0" "SMB_XMODE=xlr" &
run xp_dsA "L00:0,L02:2" "SMB_XMODE=xp" &
run xp_dsB "L14:14,head:0" "SMB_XMODE=xp" &
run xpr_dsA "L00:0,L02:2" "SMB_XMODE=xpr" &
run xpr_dsB "L14:14,head:0" "SMB_XMODE=xpr" &
run mxra_dsA "L00:0,L02:2" "SMB_XMODE=xlr SMB_MUT=xr_any" &
run mxra_dsB "L14:14,head:0" "SMB_XMODE=xlr SMB_MUT=xr_any" &
wait

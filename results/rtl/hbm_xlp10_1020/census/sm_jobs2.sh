#!/usr/bin/env bash
cd /home/ubuntu/wt/hbm-xlp10-1020
export L=/srv/opentallas-scratch/claude/hbm-xlp10-1020/sm SRC=/srv/opentallas-scratch/claude/hbm-xlp10-1020/sm/src2
B="SMB_CENSUS_R=1 SMB_OP_GAP=16 SMB_X_GAP=16 SMB_PACE_NUM=80 SMB_PACE_DEN=64 SMB_PACE_ADD=8 SMB_BSCALE=1 TOKSIM_DEFINES=XSLOT,OPEN_IL,PTRACE TOKSIM_PC=mc3 SMB_FETCH=200 SMB_FLAT=200 SMB_RMARGIN=8"
run() { bash tools/hbm_layer_vehicle/run_toksim_smhbm.sh run "$1" "$2" $B $3 > /tmp/xlp10/sm_$1.out 2>&1; }
for a in 2 4 16; do
  run xp${a}_dsA "L00:0,L02:2" "SMB_XMODE=xp SMB_XAHEAD=$a" &
  run xp${a}_dsB "L14:14,head:0" "SMB_XMODE=xp SMB_XAHEAD=$a" &
  run xpr${a}_dsA "L00:0,L02:2" "SMB_XMODE=xpr SMB_XAHEAD=$a" &
  run xpr${a}_dsB "L14:14,head:0" "SMB_XMODE=xpr SMB_XAHEAD=$a" &
done
wait

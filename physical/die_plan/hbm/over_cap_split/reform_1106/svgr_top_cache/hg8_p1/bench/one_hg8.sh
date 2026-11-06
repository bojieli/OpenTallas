#!/bin/bash
# one_hg8.sh TREE LAYERS NAME
T=$1; L=$2; N=$3; B=/srv/opentallas-scratch3/claude/hbm-gaps-8/bench; S=/srv/opentallas-scratch2/claude/hbm-gaps-5-lec/bench
mkdir -p $B/work_$T $B/out; cd $B/src_$T
VERILATOR=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator VL_JOBS=6 HDC_V41_ARITH=chunk8 nice python3 tools/hbm_layer_vehicle/smb_unit.py run --fix $B/src_$T/results/rtl/hbm_ds_layer_tput_1018/fixtures --smw $S/smw --bundle $S/bundle --work $B/work_$T --layers $L --name $N --out $B/out/$T.$N.json > $B/out/$T.$N.log 2>&1
echo "$T $N rc $? $(grep -m1 -E 'SMB_UNIT|FAULT|Error|failed' $B/out/$T.$N.log | cut -c1-200)" >> $B/out/rc.txt

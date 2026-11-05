#!/bin/bash
# one.sh TREE LAYERS NAME
T=$1; L=$2; N=$3; B=/srv/opentallas-scratch2/claude/hbm-reform-b5/bench
mkdir -p $B/work_$T $B/out; cd $B/src_$T
VERILATOR=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator VL_JOBS=10 HDC_V41_ARITH=chunk8  flock $B/work_$T/build.lock nice python3 tools/hbm_layer_vehicle/smb_unit.py run --fix $B/src_$T/results/rtl/hbm_ds_layer_tput_1018/fixtures --smw $B/smw --bundle $B/bundle --work $B/work_$T --layers $L --name $N --out $B/out/$T.$N.json > $B/out/$T.$N.log 2>&1
echo "$T $N rc $?" >> $B/out/rc.txt

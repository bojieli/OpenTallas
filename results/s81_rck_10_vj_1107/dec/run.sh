#!/usr/bin/env bash
# usage: run.sh <rtl dir> [mutant define]
set -uo pipefail
R=$1; M=${2:-}; D=$(mktemp -d); H=$(cd $(dirname $0); pwd)
F="$R/ot_s81_kp4_common.sv $R/ot_s81_kp4_enc.sv $R/ot_s81_kp4_dsyn.sv $R/ot_s81_kp4_bm.sv $R/ot_s81_kp4_ddly.sv $R/ot_s81_kp4_dout.sv $R/ot_pl_land.sv $R/ot_s81_kp4_dec_native_flat_lp.sv $H/stubs.sv"
ren(){ local f=$1 sfx=$2; for m in $(grep -oP '^\s*module\s+\K\w+' $f | sort -u); do sed -i -E "s/\b$m\b/${m}${sfx}/g" $f; done; }
BASE="-DOT_KP4_DEC_HARD -DOT_S81_KP4_AM_FACE3 -DOT_S81_RCK_RELAY4"
verilator -E -P $BASE $F > $D/ref.sv 2>$D/pp.log || { cat $D/pp.log; exit 2; }; ren $D/ref.sv _r
sed -i -e 's/\bot_s81_kp4_dec_native_flat_lp_r\b/dec_r/' -e 's/\bot_s81_kp4_enc_r\b/enc_r/' $D/ref.sv
verilator -E -P $BASE -DOT_S81_KP4_SYN_LOCAL -DOT_S81_LPL_CHUNK ${M:+-D$M} $(echo $F | sed "s#$R/ot_s81_kp4_enc.sv##") > $D/new.sv 2>$D/pp2.log || { cat $D/pp2.log; exit 2; }; ren $D/new.sv _n
sed -i 's/\bot_s81_kp4_dec_native_flat_lp_n\b/dec_n/' $D/new.sv
verilator --binary --timing -j 8 -O1 -Wno-fatal -Wno-WIDTH -Wno-MULTIDRIVEN -Wno-UNOPTFLAT --top-module tb --Mdir $D/obj -o tb $H/tb_dec.sv $D/ref.sv $D/new.sv > $D/build.log 2>&1 || { grep -i error $D/build.log | head -20; exit 2; }
$D/obj/tb 2>&1 | grep -v '^- ' | grep -v Done | tail -45

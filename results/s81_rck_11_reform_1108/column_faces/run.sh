#!/usr/bin/env bash
# usage: run.sh <vJ kit rtl dir> <reform col file> <reform file> <stubs.sv> [mutant define]
# reference = the vJ column; new = the same + OT_S81_RCK_REFORM (+ optional bench mutant)
set -uo pipefail
R=$1; COLN=$2; RF=$3; ST=$4; M=${5:-}; D=$(mktemp -d); H=$(cd $(dirname $0); pwd)
COMMON="$R/ot_pdie_serdes.sv $R/ot_pdie_serdes_locksafe.sv $R/ot_s81_kp4_common.sv $R/ot_s81_kp4_enc.sv $R/ot_s81_kp4_dsyn.sv $R/ot_s81_kp4_bm.sv $R/ot_s81_kp4_ddly.sv $R/ot_s81_kp4_dout.sv $R/ot_pl_land.sv $R/ot_s81_kp4_dec_native_flat_lp.sv $ST"
DEF="-DOT_KP4_DEC_HARD -DOT_S81_KP4_AM_FACE3 -DOT_S81_RCK_RELAY4 -DOT_S81_RM_STAGED -DOT_S81_RM_LOCAL4 -DOT_S81_SERDES_RST_COPIES -DOT_S81_RM_WFULL8 -DOT_S81_KP4_SYN_LOCAL -DOT_S81_LPL_CHUNK -DOT_S81_SERDES_COL_PIN"
ren(){ local f=$1 sfx=$2; for m in $(grep -oP '^\s*module\s+\K\w+' $f | sort -u); do sed -i -E "s/\b$m\b/${m}${sfx}/g" $f; done; }
# reference column: the repo column file without the RE-FORM define (= vJ column + PMA models)
verilator -E -P -I"$R" $DEF $COMMON $COLN > $D/ref.sv 2>$D/pp.log || { cat $D/pp.log; exit 2; }; ren $D/ref.sv _r
sed -i 's/\bot_pdie_serdes_col_r\b/col_r/' $D/ref.sv
verilator -E -P -I"$R" $DEF -DOT_S81_RCK_REFORM ${M:+-D$M} $COMMON $COLN $RF > $D/new.sv 2>$D/pp2.log || { cat $D/pp2.log; exit 2; }; ren $D/new.sv _n
sed -i 's/\bot_pdie_serdes_col_n\b/col_n/' $D/new.sv
verilator --binary --timing -j 8 -O1 -Wno-fatal -Wno-WIDTH -Wno-MULTIDRIVEN -Wno-UNOPTFLAT --top-module tb --Mdir $D/obj -o tb $H/tb_rf.sv $D/ref.sv $D/new.sv > $D/build.log 2>&1 || { grep -i error $D/build.log | head -20; exit 2; }
$D/obj/tb 2>&1 | grep -v '^- ' | tail -25

#!/bin/bash
# S81 x-gear EQ bench (Verilator 5.032, docker).  Usage: run_xeq.sh DIR [h9|h10]
# DIR holds eq_sel.txt + the listed sources (tb_s81_xgear_eq.sv, the as-built models incl. s81_asb_xgear_models.sv from
# xgear_die.py, the col_h<9|10> plan kit and their closure).  One build per H (2, 3); MUT / SEED are runtime plusargs.
# Expect: MUT 0 = XEQ PASS for every SEED (start parities 0..3: the TX is framed by xw_v); MUT 1 (no declared delay),
# MUT 2 (one lane corrupted) and MUT 3 (two words on consecutive edges; flt) and MUT 4 (TX phase-lock removed) = XEQ FAIL.  Exit 1 on any unexpected result.
cd "$1" || exit 2
FR=${2:-h9}; XD=""; [ "$FR" = h10 ] && XD="+define+XEQ_H10"
D="-DDSFD_PQ_STATIC_X2 -DS81CTRL_SRAM_FIFO -DS81CTRL_SRAM_P192 -DS81CTRL_NATIVE32 -DOT_COLL_NATIVE32 -DOT_COLL_NATIVE32_OFF -DOT_S81ENG_TAP_N32R2 -DOT_S81SL_KV_TRANSPORT -DOT_SVC_ALLQ -DSU_SMU_T -DOT_ATTN_HCORE -DOT_S81ENG_RR_N32 -DOT_S81C_HCORE_CTLA -DOT_S81C_HCORE_RST_TIMED -DS81_HOSTB_LAND_OBS -DOT_S81_SH_SRAM -DOT_S81_SH_RSZ -DOT_S81_SH_P192 -DOT_S81_SH_APIPE9 -DOT_S81_SH_APIPE10"
bad=0
for H in 2 3; do
  o=obj_${FR}_h$H
  docker run --rm -m 48g --cpus 16 -u $(id -u):$(id -g) -e CCACHE_DISABLE=1 -e HOME=/tmp -v $PWD:/w -w /w verilator/verilator:v5.032 --binary --timing -j 16 \
    -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN -Wno-UNOPTFLAT --top-module tb -GH=$H $D $XD --Mdir $o \
    $(cat eq_sel.txt) > $o.build.log 2>&1 || { echo "${FR}_h$H BUILD FAIL"; tail -5 $o.build.log; bad=1; continue; }
  if [ $H = 2 ]; then CF="0:1:PASS 0:2:PASS 0:3:PASS 0:4:PASS 1:1:FAIL 2:1:FAIL 3:1:FAIL 4:1:FAIL 4:2:FAIL"; else CF="0:1:PASS 0:2:PASS"; fi
  for c in $CF; do IFS=: read m sd ex <<< "$c"
    l=${o}_m${m}_s${sd}.log
    docker run --rm -m 16g -u $(id -u):$(id -g) -v $PWD:/w -w /w --entrypoint /w/$o/Vtb verilator/verilator:v5.032 +MUT=$m +SEED=$sd > $l 2>&1
    r=$(grep -E "XEQ (PASS|FAIL)" $l); echo "${FR}_h${H}_m${m}_s${sd} expect=$ex :: $r"
    case "$ex:$r" in PASS:*"XEQ PASS"*|FAIL:*"XEQ FAIL"*) ;; *) bad=1;; esac
  done
done
[ $bad = 0 ] && echo "XEQ BENCH PASS ($FR)" || { echo "XEQ BENCH FAIL ($FR)"; exit 1; }

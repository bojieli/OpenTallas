#!/bin/bash
# S81 x-gear EQ bench (Verilator 5.032, docker).  Usage: run_xeq.sh DIR [h9|h10]
# DIR holds eq_sel.txt + the listed sources (tb_s81_xgear_eq.sv, the as-built models incl. s81_asb_xgear_models.sv from
# xgear_die.py, the col_h<9|10> plan kit and their closure).  Expect: H 2/3 MUT 0 = XEQ PASS (geared path identical to
# the ungeared path delayed by the declared 1 edge, at frame A (x) and at frame B (nx, fed from the xo of A));
# MUT 1 (no declared delay), MUT 2 (one lane corrupted on word edges) and MUT 3 (words on the wrong parity) = XEQ FAIL.
# Exit 1 on any unexpected result.
cd "$1" || exit 2
FR=${2:-h9}; XD=""; [ "$FR" = h10 ] && XD="+define+XEQ_H10"
D="-DDSFD_PQ_STATIC_X2 -DS81CTRL_SRAM_FIFO -DS81CTRL_SRAM_P192 -DS81CTRL_NATIVE32 -DOT_COLL_NATIVE32 -DOT_COLL_NATIVE32_OFF -DOT_S81ENG_TAP_N32R2 -DOT_S81SL_KV_TRANSPORT -DOT_SVC_ALLQ -DSU_SMU_T -DOT_ATTN_HCORE -DOT_S81ENG_RR_N32 -DOT_S81C_HCORE_CTLA -DOT_S81C_HCORE_RST_TIMED -DS81_HOSTB_LAND_OBS -DOT_S81_SH_SRAM -DOT_S81_SH_RSZ -DOT_S81_SH_P192 -DOT_S81_SH_APIPE9 -DOT_S81_SH_APIPE10"
bad=0
for c in "2 0 PASS" "3 0 PASS" "2 1 FAIL" "2 2 FAIL" "2 3 FAIL"; do set -- $c
  o=obj_${FR}_h$1_m$2
  docker run --rm -m 48g --cpus 16 -u $(id -u):$(id -g) -e CCACHE_DISABLE=1 -e HOME=/tmp -v $PWD:/w -w /w verilator/verilator:v5.032 --binary --timing -j 16 \
    -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN -Wno-UNOPTFLAT --top-module tb -GH=$1 -GMUT=$2 $D $XD --Mdir $o \
    $(cat eq_sel.txt) > $o.build.log 2>&1 || { echo "${FR}_h$1_m$2 BUILD FAIL"; tail -5 $o.build.log; bad=1; continue; }
  docker run --rm -m 16g -u $(id -u):$(id -g) -v $PWD:/w -w /w --entrypoint /w/$o/Vtb verilator/verilator:v5.032 > $o.log 2>&1
  r=$(grep -E "XEQ (PASS|FAIL)" $o.log); echo "${FR}_h$1_m$2 expect=$3 :: $r"
  case "$3:$r" in PASS:*"XEQ PASS"*|FAIL:*"XEQ FAIL"*) ;; *) bad=1;; esac
done
[ $bad = 0 ] && echo "XEQ BENCH PASS ($FR)" || { echo "XEQ BENCH FAIL ($FR)"; exit 1; }

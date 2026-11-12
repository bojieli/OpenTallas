#!/bin/bash
# BUS-GEAR-1 S81 x-gear EQ bench (Verilator 5.032). Usage: run_xeq.sh DIR (DIR holds eq_sel.txt + the listed sources)
cd "$1" || exit 2
D="-DDSFD_PQ_STATIC_X2 -DS81CTRL_SRAM_FIFO -DS81CTRL_SRAM_P192 -DS81CTRL_NATIVE32 -DOT_COLL_NATIVE32 -DOT_COLL_NATIVE32_OFF -DOT_S81ENG_TAP_N32R2 -DOT_S81SL_KV_TRANSPORT -DOT_SVC_ALLQ -DSU_SMU_T -DOT_ATTN_HCORE -DOT_S81ENG_RR_N32 -DOT_S81C_HCORE_CTLA -DOT_S81C_HCORE_RST_TIMED -DS81_HOSTB_LAND_OBS -DOT_S81_SH_SRAM -DOT_S81_SH_RSZ -DOT_S81_SH_P192 -DOT_S81_SH_APIPE9 -DOT_S81_SH_APIPE10"
for c in "2 0" "2 1" "2 2"; do set -- $c
  o=obj_h$1_m$2
  docker run --rm -m 48g --cpus 16 -u $(id -u):$(id -g) -v $PWD:/w -w /w verilator/verilator:v5.032 --binary --timing -j 16 \
    -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN -Wno-UNOPTFLAT --top-module tb -GH=$1 -GMUT=$2 $D --Mdir $o \
    $(cat eq_sel.txt) > $o.build.log 2>&1 || { echo "h$1_m$2 BUILD FAIL"; tail -5 $o.build.log; continue; }
  docker run --rm -m 16g -u $(id -u):$(id -g) -v $PWD:/w -w /w --entrypoint /w/$o/Vtb verilator/verilator:v5.032 > $o.log 2>&1
  echo "h$1_m$2 :: $(grep -E 'XEQ (PASS|FAIL)' $o.log)"
done

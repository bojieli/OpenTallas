#!/bin/bash
# KV-TOK 10-24: token phase of the KV die-slice vehicle: boot replay, then the die's own token programme with the compute-die
# far end on the UCIe link (+FAR=1, kvs_compute_end.sv) and the HBM history preloaded (kv_preload.py, CONTRACT map v2).
#   run_tok.sh BUILDDIR IMGDIR OUT NAME VECDIR [extra plusargs ...]
#   env: CTX (256)  POST (core cycles after the boot verdict, default 300000)  PRELOAD (1; 0 = empty HBM)
#        PRELOAD_ARGS (extra kv_preload.py args, e.g. "--mut-kswap phy_WS_0" for mutant m3)  HBM_LOG (16)
set -u
H=$(cd "$(dirname "$0")" && pwd); R=$(cd $H/../../.. && pwd)
B=$(readlink -f $1)/obj/Vtb_kvslice; I=$(readlink -f $2); O=$(mkdir -p $3 && readlink -f $3); N=$4; V=$(readlink -f $5); shift 5
CTX=${CTX:-256}; POST=${POST:-300000}
mkdir -p $O/$N; cd $O/$N
PL=""
if [ "${PRELOAD:-1}" = 1 ]; then
  python3 $H/kv_preload.py --kv $V/kv.hex --ctx $CTX --asbuilt $R/physical/die_plan/qwen_kvsys/bind/asbuilt_map.json \
    ${PRELOAD_ARGS:-} > preload.txt 2> preload.log || exit 2
  PL="+HBM_PRELOAD=$O/$N/preload.txt"
fi
/usr/bin/time -f "%e s %M KB" -o time $B +FRAMES=$I/frames.hex +EXPECT=$I/expect.txt +EPOCH=$(cat $I/epoch.txt) ${RUNARGS:-} \
  +FAR=1 +VEC=$V +CTX=$CTX +POST=$POST +HBM_LOG=${HBM_LOG:-16} $PL "$@" > sim.log 2>&1; echo $? > exit
echo "$N exit=$(cat exit) $(cat time) | $(grep -m1 '^KVSLICE_BOOT' sim.log | cut -c1-60) | $(grep -m1 '^FAR_SUMMARY' sim.log)"

#!/bin/bash
# TOK-QK-KVL 10-27: per-layer KV attention phase of the B48 KV die (native tb_kvslice, +FAR=1 +VECL): boot replay, then one
# compiled 8K token (36 layers on the B48 static calendar) against the compute die's real d2d far end, every layer with its
# own q / new K,V row / gold and its own HBM history (kv_preload.py per layer, --skip-last: row T-1 arrives over KVN).
#   run_kvl.sh BIN VEC OUT NAME HEAD [plusargs ...]     HEAD = d<d>_g<g> (the KV head this KV die serves, TP8)
#   env: IMG (boot image dir, required)  PHY_MAP (default dirname(BIN)/../phy_slice_map.json)  CTX (8192)  POST (300000 core cycles after the boot verdict)  MUT_L01 (1: preload layers 0,1 swapped, m5)
#        MUT_KSWAP (partition, e.g. phy_WS_0: mutant m3)  PRELOAD_ARGS (extra kv_preload.py args)
set -u
H=$(cd "$(dirname "$0")" && pwd)
B=$1; V=$2; O=$3; N=$4; HD=$5; shift 5
CTX=${CTX:-8192}; POST=${POST:-300000}
# TOK-KV-2 10-28: the boot image (IMG) and the PHY slice map (PHY_MAP, generated from the bind by build.sh /
# kv_phy_slice_map.py) belong to THIS build; no hard-coded older-bind paths.  Both are required (fail closed).
I=$(readlink -f ${IMG:?IMG=<boot image dir: frames.hex expect.txt epoch.txt>})
PM=$(readlink -f ${PHY_MAP:-$(dirname $(readlink -f $B))/../phy_slice_map.json})
[ -f "$PM" ] || { echo "run_kvl: no generated PHY slice map $PM"; exit 2; }
mkdir -p $O/$N/vecl; cd $O/$N
: > preload.txt; : > preload.log
for n in $(seq 0 35); do
  S=$V/L${n}_$HD; D=vecl/L$n; mkdir -p $D
  [ "$(cat $S/ctx)" = "$CTX" ] || { echo "ctx mismatch L$n $(cat $S/ctx) != $CTX"; exit 2; }
  ln -sfn $S/q.hex $D/q.hex; ln -sfn $S/gold.hex $D/gold.hex
  sed -n "${CTX}p;$((2 * CTX))p" $S/kv.hex > $D/kvn.hex
  AS=$n; [ "${MUT_L01:-0}" = 1 ] && [ $n -lt 2 ] && AS=$((n ^ 1))
  /usr/bin/python3 $H/kv_preload.py --kv $S/kv.hex --ctx $CTX --asbuilt $PM \
    --layers $n --as-layer $AS --skip-last ${MUT_KSWAP:+--mut-kswap $MUT_KSWAP} ${PRELOAD_ARGS:-} >> preload.txt 2>> preload.log || exit 2
done
sha256sum preload.txt vecl/L*/kvn.hex $PM $I/frames.hex > inputs.sha256
/usr/bin/time -v stdbuf -oL $B +PHASE=boot +FRAMES=$I/frames.hex +EXPECT=$I/expect.txt +EPOCH=$(cat $I/epoch.txt) +START_AFTER_SETUP \
  +FAR=1 +VECL=$O/$N/vecl +CTX=$CTX +POST=$POST +HBM_LOG=16 +HBM_PRELOAD=$O/$N/preload.txt +HB=20000 "$@" > sim.log 2> time.log
rc=$?; echo $rc > exit
# TOK-QK-3 10-27: exit 0 is not a pass; VERDICT = kv_verdict.py (boot PASS + all 36 FAR_LAYER_SUMMARY PASS, fail-closed).
# Negative controls (MUT_L01 / MUT_KSWAP / +MUT_* plusargs) must be CAUGHT, i.e. a FAIL verdict.
X=pass; [ "${MUT_L01:-0}" != 0 ] && X=fail; [ -n "${MUT_KSWAP:-}" ] && X=fail
case " $* " in *" +MUT_"*) X=fail ;; esac
V=$(/usr/bin/python3 -I $H/kv_verdict.py . --layers 36 --expect $X); vrc=$?
echo "$N rc=$rc VERDICT $V | $(grep -m1 '^KVSLICE_BOOT' sim.log | cut -c1-40) | $(grep -m1 '^FAR_SUMMARY' sim.log)"
grep '^FAR_LAYER_SUMMARY' sim.log | awk '{p+=($NF=="PASS")} END{print "layers PASS " p "/" NR}'
[ $vrc = 0 ] || exit 3
exit 0

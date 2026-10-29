#!/bin/bash
# KV-TOK 10-24: token phase of the KV die-slice vehicle: boot replay, then the die's own token programme with the compute-die
# far end on the UCIe link (+FAR=1, kvs_compute_end.sv) and the HBM history preloaded (kv_preload.py, CONTRACT map v2).
#   run_tok.sh BUILDDIR IMGDIR OUT NAME VECDIR [extra plusargs ...]
#   env: PHY_MAP (default BUILDDIR/phy_slice_map.json, generated from the bind)  CTX (256)  POST (core cycles after the boot verdict, default 300000)  PRELOAD (1; 0 = empty HBM)
#        PRELOAD_ARGS (extra kv_preload.py args, e.g. "--mut-kswap phy_WS_0" for mutant m3)  HBM_LOG (16)
#        LAYERS (N: the verdict also needs FAR_LAYER_SUMMARY PASS for layers 0..N-1)
set -u
H=$(cd "$(dirname "$0")" && pwd); R=$(cd $H/../../.. && pwd)
BD=$1; B=$(readlink -f $1)/obj/Vtb_kvslice; I=$(readlink -f $2); O=$(mkdir -p $3 && readlink -f $3); N=$4; V=$(readlink -f $5); shift 5
CTX=${CTX:-256}; POST=${POST:-300000}
mkdir -p $O/$N; cd $O/$N
# Native token continuation needs the same functional ROM and mission START
# ordering as the boot and per-layer runners.
BD=$(readlink -f "$BD")
if [ -f "$BD/vl.f" ]; then
  python3 -I "$H/runtime_rom.py" --build "$BD" --runtime . ${KV_DCAL_VIAMAP:+--viamap "$KV_DCAL_VIAMAP"} || exit 2
fi
START_ARGS=()
if [ -f "$BD/native_boot.profile" ] && [ "$(cat "$BD/native_boot.profile")" = 1 ]; then
  START_ARGS=(+START_AFTER_SETUP)
fi
PL=""
if [ "${PRELOAD:-1}" = 1 ]; then
  # TOK-KV-2 10-28: the PHY slice map is GENERATED from the bind of this build (kv_phy_slice_map.py, by build.sh), never
  # the hand-kept bind/asbuilt_map.json of an older bind; PHY_MAP overrides; a missing map fails closed.
  PM=${PHY_MAP:-$(readlink -f $BD)/phy_slice_map.json}
  [ -f "$PM" ] || { echo "run_tok: no generated PHY slice map $PM" >&2; exit 2; }
  python3 $H/kv_preload.py --kv $V/kv.hex --ctx $CTX --asbuilt $PM \
    ${PRELOAD_ARGS:-} > preload.txt 2> preload.log || exit 2
  PL="+HBM_PRELOAD=$O/$N/preload.txt"
fi
/usr/bin/time -f "%e s %M KB" -o time $B +FRAMES=$I/frames.hex +EXPECT=$I/expect.txt +EPOCH=$(cat $I/epoch.txt) \
  +FAR=1 +VEC=$V +CTX=$CTX +POST=$POST +HBM_LOG=${HBM_LOG:-16} $PL "${START_ARGS[@]}" "$@" > sim.log 2>&1
sim_rc=$?
printf "%s\n" "$sim_rc" > exit
# TOK-QK-3 10-27: exit 0 is not a pass -- the verdict comes from the bench verdict lines (kv_verdict.py, fail-closed).
V=$(python3 -I $H/kv_verdict.py . ${LAYERS:+--layers $LAYERS})
echo "$N exit=$(cat exit) $(cat time) VERDICT $V | $(grep -m1 '^KVSLICE_BOOT' sim.log | cut -c1-60) | $(grep -m1 '^FAR_SUMMARY' sim.log)"
# Keep a nonzero simulator result; a clean exit with a FAIL verdict returns 3.  Callers classify expected negative
# controls explicitly (kv_verdict.py --expect fail).
[ "$sim_rc" != 0 ] && exit "$sim_rc"
case "$V" in PASS*) exit 0 ;; *) exit 3 ;; esac

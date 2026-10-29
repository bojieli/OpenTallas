#!/bin/bash
# TOK-KV-2 10-28 (runs on intel2 = ot-run head; sims on intel1): wait for the TOK-KV-1 B48 builds (b48n bind5, b48m bind5m)
# and the 36-layer KV vectors, then launch: boot qual on b48n (nominal + mut_frame), token d0_g0 on b48n (MUST PASS 36/36
# bit-exact), token on b48m (MUST FAIL), token m3_kswap on b48n (generated PHY map in use -> MUST FAIL).  One ot-run each.
set -u
D=/srv/opentallas-scratch2/claude/tok-kv-1-1028; K=/srv/opentallas-scratch2/claude/tok-kv-2-1028
W=/srv/opentallas-scratch2/claude/wt/tok-kv-1/tools/qwen_layerbench/kv_dieslice
L=$HOME/tok-kv-2; mkdir -p $L; log() { echo "$(date "+%F %T") $*" >> $L/chain.log; }
OTR="$HOME/.local/bin/ot-run --hosts intel1 --dir $K --disk 50"
built() { grep -q "BUILD_DONE $1 rc=0" $HOME/tok-kv-1/otrun_b48$2.log; }
dead() { grep -q "BUILD_DONE $1 rc=[1-9]\|ot-run: NOT" $HOME/tok-kv-1/otrun_b48$2.log; }
log "armed"
until built veh5 n && built veh5m m && ssh -o ControlPath=none intel1 test -f $K/vec/.done; do
  dead veh5 n && { log "b48n build FAILED"; exit 1; }
  dead veh5m m && { log "b48m build FAILED"; exit 1; }
  ssh -o ControlPath=none intel1 test -f $K/vec/.failed && { log "vec FAILED"; exit 1; }
  sleep 120; done
log "builds rc=0 + vec done -> launch"
IMG=$D/vimg5; VEC=$K/vec
nohup $OTR --mem 64 --threads 2 -- bash $W/run.sh $D/b48n $IMG $K/boot_n 100 > $L/boot_n.otrun.log 2>&1 < /dev/null &
nohup $OTR --mem 32 --threads 1 -- env IMG=$IMG POST=300000 bash $W/run_kvl.sh $D/b48n/obj/Vtb_kvslice $VEC $K/runs tok_n d0_g0 > $L/tok_n.otrun.log 2>&1 < /dev/null &
nohup $OTR --mem 32 --threads 1 -- env IMG=$IMG POST=300000 bash $W/run_kvl.sh $D/b48m/obj/Vtb_kvslice $VEC $K/runs tok_m d0_g0 > $L/tok_m.otrun.log 2>&1 < /dev/null &
nohup $OTR --mem 32 --threads 1 -- env IMG=$IMG POST=40000 MUT_KSWAP=phy_WS_0 bash $W/run_kvl.sh $D/b48n/obj/Vtb_kvslice $VEC $K/runs m3_kswap_n d0_g0 > $L/m3_kswap_n.otrun.log 2>&1 < /dev/null &
sleep 60; grep -h "admitted\|NOT" $L/*.otrun.log >> $L/chain.log
wait
log "all terminal"; for f in $L/*.otrun.log; do log "$(basename $f) $(tail -n 2 $f | tr "\n" " ")"; done

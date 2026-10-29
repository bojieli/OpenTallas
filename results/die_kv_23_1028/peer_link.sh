#!/bin/bash
# DIE-KV-19 10-28 (COORD ruling on TOK-QK-PEER-1, 20:4x): every KV re-bind derives the QC<->KV pair image at bind time from
# BOTH current binds and proves it on the link stage:
#   1. regen_constants --die qwen_compute --bound QCB --peer KVB  and  --die qwen_kvsys --bound KVB --peer QCB (both PASS)
#   2. pair image at the regen D2D_DIE_STAGES (both bind hashes recorded), TOK-QK-PEER-1 stage_link_peer1.sh (ASM 5832e6722)
#   3. xdie on the bound image (PASS, every built-in mutant FAIL) + seam mutant KS_RXV +1 on its own RUNROOT (must FAIL)
# Tools = claude/tok-qk-peer-1-1028@bece5e5da2 results/token_pass/qc_kv_link_bind5_1028 (read with git show, not copied by hand).
# usage: peer_link.sh KV_BIND OUT [QC_BIND]     (~15 min / 8 GB; run through ot-run)
set -u
W=/srv/opentallas-scratch2/claude/wt/die-kv-23; cd $W
KVB=$1; O=$2; QCB=${3:-/srv/opentallas-scratch2/claude/tok-qk-peer-1-1028/qc_fresh_v6}
PEER=${PEER_SHA:-bece5e5da245b28d3e5931359dbed06e102bbbf1}; PB=results/token_pass/qc_kv_link_bind5_1028
mkdir -p $O/const $O/peer_tools
python3 tools/die_plan/regen_constants.py --die qwen_compute --bound $QCB --peer $KVB --out-json $O/const/qc_peer_kv.json > $O/const/qc_peer_kv.log 2>&1; QRC=$?
python3 tools/die_plan/regen_constants.py --die qwen_kvsys --bound $KVB --peer $QCB --out-json $O/const/kv_peer_qc.json > $O/const/kv_peer_qc.log 2>&1; KRC=$?
echo "REGEN qwen_compute rc=$QRC $(grep -c '^\[OK' $O/const/qc_peer_kv.log) OK; qwen_kvsys rc=$KRC $(grep -c '^\[OK' $O/const/kv_peer_qc.log) OK"
grep -v '^\[OK' $O/const/qc_peer_kv.log | grep '^\[' | head -5; grep -v '^\[OK' $O/const/kv_peer_qc.log | grep '^\[' | head -5
ST=$(python3 -c "import json,re,sys;r=json.load(open(sys.argv[1]))['recipes'];r=r if isinstance(r,dict) else eval(r);print(re.search(r'D2D_DIE_STAGES=(\S+)',r['xdie_pair_image']).group(1))" $O/const/qc_peer_kv.json)
echo "D2D_DIE_STAGES=$ST  QC bound_sha $(python3 -c "import json;print(json.load(open('$O/const/qc_peer_kv.json'))['bound_sha'])")  KV bound_sha $(python3 -c "import json;print(json.load(open('$O/const/kv_peer_qc.json'))['bound_sha'])")"
for f in scripts/stage_link_peer1.sh scripts/run_link.sh scripts/lanes_from_constants.py scripts/summ.py \
         tools_bound/bound_txdp.py tools_bound/stage_xdie.collect.py tools_bound/stage_xdie_bound.sh tools_bound/xdie_image_cal.py; do
  mkdir -p $O/peer_tools/$(dirname $f); git show $PEER:$PB/$f > $O/peer_tools/$f || exit 3
done
QCCONST=$O/const/qc_peer_kv.json QCB=$QCB KVB=$KVB D2D_STAGES=$ST MU_LS=407 L=$O/link/rr \
  bash $O/peer_tools/scripts/stage_link_peer1.sh > $O/stage.log 2>&1 || { echo STAGE_FAIL; tail -5 $O/stage.log; exit 4; }
tail -6 $O/stage.log
XQ_CUR=$ST bash $O/link/rr/run_link.sh xdie > $O/xdie.log 2>&1; XRC=$?; echo "XDIE rc=$XRC"; tail -3 $O/xdie.log
# seam mutant: KS_RXV (first K seam) +1 on a copy of the staged root, bench seam only
M=$(python3 -c "import sys;a,b=sys.argv[1].split('/');k=b.split(',');k[0]=str(int(k[0])+1);print(a+'/'+','.join(k))" $ST)
rm -rf $O/link/rr_mseam; cp -a $O/link/rr $O/link/rr_mseam; rm -rf $O/link/rr_mseam/logs
XQ_CUR=$M XQ_IMAGE=$O/link/rr/xdie/fx/img_bound/d2d_cal_image.svh bash $O/link/rr_mseam/run_link.sh xdie > $O/xdie_mseam.log 2>&1; MRC=$?
# verdict from the xdie "runs:" line {config: (expected, got)}: the stage rc is 0 either way, so count expectation misses
miss() { python3 -c 'import ast,sys;l=[x for x in open(sys.argv[1]) if x.startswith("runs: ")][-1];r=ast.literal_eval(l[6:]);print(sum(e!=g for e,g in r.values()), len(r))' "$1"; }
read XM XN <<< "$(miss $O/link/rr/logs/xdie.log)"; read MM MN <<< "$(miss $O/link/rr_mseam/logs/xdie.log)"
echo "XDIE bound: $XM/$XN configs off expectation (must be 0)"
echo "XDIE_MSEAM ($M): $MM/$MN configs off expectation (must be >0: seam +1 caught)"
[ $QRC -eq 0 ] && [ $KRC -eq 0 ] && [ $XRC -eq 0 ] && [ "$XM" = 0 ] && [ "${MM:-0}" -gt 0 ] && echo "PEER_LINK PASS" || echo "PEER_LINK FAIL"

#!/bin/bash
# KV-ECTL4 10-18: NETLIST-ONLY KV die GEN (kvs14q flags + kvs14p's RST_PIN_REG / NTX 3) on claude/kv-ectl4-1018 with
#   OT_KV_ECTL_ST_FRAME (default on): the ECTL slots at the hardened qkd_ectl3_kiss_st frame 725.76 x 261.36 + its kit pins;
#   OT_KV_K_RT_EQ (default on): every frame's K round trip padded to K_RT_BUDGET 80 on its request chain (kv_k_rt_eq.py);
#   qkd_ectlk bound #(.RESPONSE_LAT(80), .QK_ISSUE_AGE(91)).
# Reports K_RT_EQ (natural min..max, pads), BUNDLE_EQ, LANDSLOT, strict bind, plan PNG, RELAY_CHECK; then the static
# compiler unit tests.  usage (fleet, ot-run --priority die): kvs14e4.sh COMMIT
set -euo pipefail
C=$1
B=/srv/opentallas-scratch/claude/qwen-kvsys
W=$B/wt-kvs14e4-$C
R=$B/kvs14e4-$C${KVS14E4_SUFFIX:-}
M=/srv/opentallas-scratch/claude/git-mirror/OpenTallas.git
GH=https://github.com/bojieli/OpenTallas
mkdir -p $R
say() { echo "$(date '+%F %T %Z') $*" >> $R/STATUS.log; }
if [ ! -d $W ]; then git -C $M fetch -q $GH claude/kv-ectl4-1018; git -C $M worktree add --detach $W $C; fi
cd $W
[ "$(git rev-parse --short=9 HEAD)" = $C ] || { echo "wrong commit"; exit 2; }
export OT_KV_PV_CTL_KIT=qkd_pv_ctl_rstpin_a72 OT_KV_HOST_V14=1 OT_KV_HOST_NORTH=1 OT_KV_TREES=1 OT_KV_V143=1 OT_KV_V143C=1 OT_KV_ECTL_H13=1 OT_KV_RLY_STD=1 OT_KV_DCAL=1 OT_KV_HOP=1 OT_KV_V144=1 OT_KV_V144_R6=1 OT_KV_PV_W=82 OT_KV_PV_AGE=96 OT_KV_SERDES_N=1 OT_KV_PV_PINY=1 OT_KV_KVNC=1 OT_KV_SEQ_STATIC=1 OT_KV_REACH=400 OT_KV_RST_REGIONAL=1 OT_KV_PHY_REG=1 OT_KV_REACH_W=36:400,296:370,100000:340 OT_KV_PV_T=1 OT_KV_PV_T_CTL_STANDIN=1 OT_KV_REACH_FIX=1 OT_KV_PVT_PINS=1 OT_KV_PVT_HDR_CTL=1 OT_KV_PVT_SOFT_SLACK=0 OT_KV_SEAM=1 OT_KV_STATIC_DIE=1
export OT_KV_HROOT=1 OT_KV_FANFOLD=1 OT_KV_V144_DW=2462.4 OT_KV_SN_LIFT=432 OT_KV_CTL_BAND=302.4 OT_KV_PVT_HUB_CLEAR=172.8 OT_KV_KV_CHAN_EXTRA=86.4 OT_KV_V144_RLY_FIRST=pvin_,krs_,kvn_,ap_,aq_,am_,ks_acal_,pve_
export OT_KV_STATIC_DIE_DIAGNOSTIC=1 OT_KV_TILE_KITS=1 OT_KV_PVFORK_GAP=64.8 ${KVS14E4_EXTRA:-}
export OT_KV_EXPAND=qkd_rhead,qkd_rhead_ft,qkd_ectl,qkd_ctrl,qkd_ctrl_n,qkd_pvfork,qkd_pvtap2,qkd_pvtap3,qkd_pvtap4
export OT_KV_RST_PER_TREE=1 OT_KV_FWD=1 OT_KV_LANDSLOT=1 OT_KV_FWD_NETLIST_ONLY=1 OT_KV_RST_PIN_REG=1 OT_KV_BUNDLE_EQ=1 OT_KV_D2D_NTX=3
say "kvs14e4 $C prep start (netlist-only; ECTL_ST_FRAME=${OT_KV_ECTL_ST_FRAME:-default} K_RT=${OT_KV_K_RT:-80})"
bash tools/qwen_kv_die/chain/kvsys_prep.sh $R > $R/prep.log 2>&1 || { say "PREP FAIL (prep.log): $(grep -m3 -E 'kv_k_rt_eq|Error|error' $R/prep.log | tr '\n' ' ' | cut -c1-600) | $(tail -3 $R/prep.log | tr '\n' ' ' | cut -c1-400)"; }
say "K_RT_EQ: $(grep -m1 'K_RT_EQ' $R/prep.log | head -c 400)"
say "BUNDLE_EQ: $(grep -m1 'BUNDLE_EQ' $R/prep.log | head -c 400)"
say "LANDSLOT: $(grep -m1 'LANDSLOT' $R/prep.log | head -c 300)"
say "die: $(grep -m1 -E 'die [0-9.]+ x [0-9.]+|mm2' $R/prep.log | head -c 300)"
say "STRICT BIND: $(tail -1 $R/port_bind_v2/port_bind_v2.txt 2>/dev/null | head -c 400)"
grep -o 'qkd_ectl3_kiss_st #([^)]*)[^)]*)[^)]*)[^)]*)' $R/port_bind_v2/die_bound.v 2>/dev/null | sort | uniq -c > $R/ectl_params.txt || true
say "ECTL params bound: $(head -3 $R/ectl_params.txt | tr '\n' ' ')"
python3 tools/qwen_kv_die/case_png.py $R/case_kv --slots $R/rly_std.json --out $R/plan.png --title "kvs14e4 $C (netlist-only, ECTL 725.76x261.36, K RT 80)" > $R/plan_png.log 2>&1 || true
bash tools/qwen_kv_die/kv_relay_check.sh $R $W > $R/relay_check.log 2>&1 || true
say "$(tail -1 $R/relay_check.log | head -c 600)"
(cd tools/qwen_kv_die && python3 -m unittest test_kv_static_ages test_kv_static_programme test_kv_static_attn_join test_kv_static_ectl_pair test_kv_bundle_eq) > $R/pytest.log 2>&1 || true
say "PYTEST: $(tail -1 $R/pytest.log)"
say DONE

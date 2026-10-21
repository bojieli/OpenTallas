#!/bin/bash
# QLB-KV 10-18 (lanes/Q-LBGAP.md, TOKEN-XDIE-QWEN F6): NETLIST-ONLY KV die GEN in its own run dir, kvs14d's config
# (kvs14c landed regions + LANDSLOT + forwarded lanes, relay netlist: OT_KV_FWD_NETLIST_ONLY=1, no lane views) plus
#   SEAMK 1d913106e  record-bundle sink-end pads (OT_KV_BUNDLE_EQ default 1) + kv_relay_check.sh (never skipped);
#   TXDP_K           d2d_kv bound as qkd_d2d_static #(.TXDP) from the calendar image (QXF-LINK 6ef1a097f);
#   FACE b6d08acc2   qkd_attn_result_face_s / qkd_pv_fin_s RTL (in the tree);
#   OT_KV_RST_PIN_REG=1 (qkd_rst_region_pr, CLOSED + native PASS; KV-PLAN4 adopt line).
# Then RELAY_CHECK on the bound netlist (kv_relay_check.sh: netlist die-run table -> layer_compile.py against THIS die ->
# TXDP bound == compiled -> die_relay_check stage diffs + torn bundles).  When only the TXDP differs, the GEN is re-run once
# with OT_KV_D2D_TXDP_K = the compiled vector (run dir suffix -t) and checked again.  No physical chain (die lanes own it).
# SOURCE: branch claude/qlb-kv-gsrc-1018 = KV-LANDSLOT c1989d8c5 (the KV generator + KV RTL lineage) + overlays from
# claude/qlb-kv-1018 (tools/qwen_kv_die incl. SEAMK, tools/qwen_split, tools/qwen_layerbench, tools/die_relay_*, the LINK/FACE RTL).
# usage (on the fleet, via ot-run): kvs14q.sh COMMIT
set -euo pipefail
C=$1
B=/srv/opentallas-scratch/claude/qwen-kvsys
WT=$B/wt-kvs14q-$C
M=/srv/opentallas-scratch/claude/git-mirror/OpenTallas.git
[ -d $WT ] || { git -C $M fetch -q https://github.com/bojieli/OpenTallas claude/qlb-kv-gsrc-1018; git -C $M worktree add --detach $WT $C; }
cd $WT
[ "$(git rev-parse --short=9 HEAD)" = "$C" ] || { echo "wrong commit"; exit 2; }
export OT_KV_PV_CTL_KIT=qkd_pv_ctl_rstpin_a72 OT_KV_HOST_V14=1 OT_KV_HOST_NORTH=1 OT_KV_TREES=1 OT_KV_V143=1 OT_KV_V143C=1 OT_KV_ECTL_H13=1 OT_KV_RLY_STD=1 OT_KV_DCAL=1 OT_KV_HOP=1 OT_KV_V144=1 OT_KV_V144_R6=1 OT_KV_PV_W=82 OT_KV_PV_AGE=96 OT_KV_SERDES_N=1 OT_KV_PV_PINY=1 OT_KV_KVNC=1 OT_KV_SEQ_STATIC=1 OT_KV_REACH=400 OT_KV_RST_REGIONAL=1 OT_KV_PHY_REG=1 OT_KV_REACH_W=36:400,296:370,100000:340 OT_KV_PV_T=1 OT_KV_PV_T_CTL_STANDIN=1 OT_KV_REACH_FIX=1 OT_KV_PVT_PINS=1 OT_KV_PVT_HDR_CTL=1 OT_KV_PVT_SOFT_SLACK=0 OT_KV_SEAM=1 OT_KV_STATIC_DIE=1
export OT_KV_HROOT=1 OT_KV_FANFOLD=1 OT_KV_V144_DW=2462.4 OT_KV_SN_LIFT=432 OT_KV_CTL_BAND=302.4 OT_KV_PVT_HUB_CLEAR=172.8 OT_KV_KV_CHAN_EXTRA=86.4 OT_KV_V144_RLY_FIRST=pvin_,krs_,kvn_,ap_,aq_,am_,ks_acal_,pve_
export OT_KV_STATIC_DIE_DIAGNOSTIC=1 OT_KV_TILE_KITS=1 OT_KV_PVFORK_GAP=64.8
export OT_KV_EXPAND=qkd_rhead,qkd_rhead_ft,qkd_ectl,qkd_ctrl,qkd_ctrl_n,qkd_pvfork,qkd_pvtap2,qkd_pvtap3,qkd_pvtap4
export OT_KV_RST_PER_TREE=1 OT_KV_FWD=1 OT_KV_LANDSLOT=1 OT_KV_FWD_NETLIST_ONLY=1 OT_KV_RST_PIN_REG=1 OT_KV_BUNDLE_EQ=1
gen() {   # gen RUN -> prep + RELAY_CHECK; last line of RUN/relay_check.log
  local R=$1; mkdir -p $R
  say() { echo "$(date '+%F %T %Z') $*" >> $R/STATUS.log; }
  say "kvs14q $C prep start (netlist-only; OT_KV_D2D_TXDP_K=${OT_KV_D2D_TXDP_K:-image})"
  bash tools/qwen_kv_die/chain/kvsys_prep.sh $R > $R/prep.log 2>&1 || { say "PREP FAIL (prep.log): $(tail -3 $R/prep.log | tr '\n' ' ' | cut -c1-400)"; return 1; }
  say "prep done: $(tail -1 $R/prep.log | head -c 300)"
  say "BUNDLE_EQ: $(grep -m1 -i 'bundle' $R/prep.log | head -c 400)"
  say "LANDSLOT: $(grep -m1 'LANDSLOT' $R/prep.log | head -c 300)"
  say "relay_stages.json (generator model): $(grep -m1 'relay_stages.json' $R/prep.log | head -c 300)"
  say "STRICT BIND: $(tail -1 $R/port_bind_v2/port_bind_v2.txt 2>/dev/null | head -c 400)"
  python3 tools/qwen_kv_die/case_png.py $R/case_kv --slots $R/rly_std.json --out $R/plan.png --title "kvs14q $C (netlist-only)" > $R/plan_png.log 2>&1 || true
  bash tools/qwen_kv_die/kv_relay_check.sh $R $WT > $R/relay_check.log 2>&1 || true
  say "$(grep -E '^TXDP_K' $R/relay_check.log | head -1)"
  say "$(tail -1 $R/relay_check.log | head -c 600)"
}
R=$B/kvs14q-$C
gen $R || exit 1
if grep -q '^RELAY_CHECK FAIL TXDP_K FAIL' $R/relay_check.log && [ -s $R/layer_compile/d2d/txdp.svh ]; then
  K=$(python3 -c "
import re,sys
m=re.search(r\"QKD_D2D_TXDP\s*=\s*\{8'd(\d+),\s*8'd(\d+),\s*8'd(\d+),\s*8'd(\d+)\}\",open(sys.argv[1]).read())
print('0x%02x%02x%02x%02x'%tuple(int(x) for x in m.groups()))" $R/layer_compile/d2d/txdp.svh)
  echo "$(date '+%F %T %Z') TXDP differs: re-GEN with OT_KV_D2D_TXDP_K=$K -> $R-t" >> $R/STATUS.log
  OT_KV_D2D_TXDP_K=$K gen $R-t || exit 1
fi
echo DONE

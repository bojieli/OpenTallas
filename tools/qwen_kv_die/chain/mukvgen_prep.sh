#!/bin/bash
# MU-KV-GEN 10-19: PREP-only strict bind of the KV GEN with OT_KV_MU=1 (copy of KVR-PLACE2 kvrplace_prep.sh @ccc2039b6 + MU).
# Original header: DIE-KV-LEAD 10-19 kvs14r: the REAL KV die chain (no diagnostic gate) on claude/die-kv-lead-1019 =
#   HKV-DIE integration (ATTN_LAND codec 2 compiler, pair D2D image TXDP_K [24,4,3,3], seq KVN pads, ahub Z_IN_STRIDE 4)
#   + HKV-STATIONS real relay stations (reach gate 17,130 overreaching bits -> 0; rly_aq_WS_73 / rly_pvin_WN_3_40 framed)
#   + measured lane second-clock insertion (landsh0 ck_s / landsh ckf, no R=0) + origin/main closed views (kvs_attn g3,
#   ectl_b/ectla, astk relay/fault/er_owner) + F-K1 loader (kv-hroot) + die-placed parents qkd_seq_st / qkd_pvw_s|n
#   (closed pv_ctl_t view, no stand-in) + kvsys_prep static-die lprg fix + d2d cfg single producer (boot target 11).
# chain: prep (strict laned bind, reach gate, RELAY_CHECK) -> real case -> PDN -> GRT -> STA TT/FF -> DCC -> dieclk TT+FF
#   + landed pairs -> reset release window. Any marker file -> NOT_A_DIE_RESULT and OT_BIND_DIAGNOSTIC (never masked).
# usage (fleet, ot-run --priority die --remote auto): kvs14r.sh COMMIT
set -euo pipefail
C=${1:?usage: kvs14r.sh COMMIT}
B=/srv/opentallas-scratch/claude/qwen-kvsys
W=$B/wt-kvs14r-$C${KVS14R_TAG:+-$KVS14R_TAG}
R=$B/kvs14r-$C${KVS14R_TAG:+-$KVS14R_TAG}
M=/srv/opentallas-scratch/claude/git-mirror/OpenTallas.git
GH=https://github.com/bojieli/OpenTallas
mkdir -p $R
rm -f "$R/NOT_A_DIE_RESULT"
say() { echo "$(date '+%F %T %Z') $*" >> $R/STATUS.log; }
if [ ! -d $W ]; then
  [ -d $M ] || { mkdir -p $(dirname $M); git clone -q --mirror $GH $M; }
  git -C $M fetch -q $GH "${KVS14R_REF:-claude/mu-kv-gen-1019}"
  git -C $M worktree add --detach $W $C
fi
cd $W
[ "$(git rev-parse --short=9 HEAD)" = $C ] || { echo "wrong commit"; exit 2; }
miss=
while IFS=$'\t' read -r n rb sha; do
  case $n in qkd_d2d_static*) f=physical/ref_tile/qkd_d2d_static_r5_native/views/qkd_d2d_static/qkd_d2d_static.lef;;
    *) f=physical/ref_tile/$n/views/$n/$n.lef;; esac
  [ -s $f ] || miss="$miss $n"
done < <(grep -v "^qkd_d2d_static" tools/qwen_kv_die/chain/kvs14p_views.tsv)
[ -z "$miss" ] || { say "committed views missing:$miss -- kvs14p not run"; exit 1; }
cp tools/qwen_kv_die/chain/kvs14p_views.tsv $R/lane_views.tsv
say "MU-KV-GEN prep-only (OT_KV_MU=1) $C: lane views 16 committed (lane_views.tsv); prep start $(git rev-parse HEAD)"
export OT_KV_PV_CTL_KIT=qkd_pv_ctl_rstpin_a72 OT_KV_HOST_V14=1 OT_KV_HOST_NORTH=1 OT_KV_TREES=1 OT_KV_V143=1 OT_KV_V143C=1 OT_KV_ECTL_H13=1 OT_KV_RLY_STD=1 OT_KV_DCAL=1 OT_KV_HOP=1 OT_KV_V144=1 OT_KV_V144_R6=1 OT_KV_PV_W=82 OT_KV_PV_AGE=96 OT_KV_SERDES_N=1 OT_KV_PV_PINY=1 OT_KV_KVNC=1 OT_KV_SEQ_STATIC=1 OT_KV_REACH=400 OT_KV_RST_REGIONAL=1 OT_KV_PHY_REG=1 OT_KV_REACH_W=36:400,296:370,100000:340 OT_KV_PV_T=1 OT_KV_PV_T_CTL_KIT=qkd_pv_ctl_t_d54f58a95 OT_KV_REACH_FIX=1 OT_KV_PVT_PINS=1 OT_KV_PVT_HDR_CTL=1 OT_KV_PVT_SOFT_SLACK=0 OT_KV_SEAM=1 OT_KV_STATIC_DIE=1
export OT_KV_HROOT=1 OT_KV_FANFOLD=1 OT_KV_V144_DW=2462.4 OT_KV_SN_LIFT=432 OT_KV_CTL_BAND=302.4 OT_KV_PVT_HUB_CLEAR=172.8 OT_KV_KV_CHAN_EXTRA=86.4 OT_KV_V144_RLY_FIRST=pvin_,krs_,kvn_,ap_,aq_,am_,ks_acal_,pve_
export OT_KV_MU=1 OT_KV_STATIC_DIE_STRICT=1 OT_KV_TILE_KITS=1 OT_KV_PVFORK_GAP=64.8 OT_KV_ATTN_LAND=1 ${KVS14R_EXTRA:-}
export OT_KV_EXPAND=qkd_rhead,qkd_rhead_ft,qkd_ectl,qkd_ctrl,qkd_ctrl_n,qkd_pvfork,qkd_pvtap2,qkd_pvtap3,qkd_pvtap4,qkd_seq_st,qkd_pvw_s,qkd_pvw_n
export OT_KV_RST_PER_TREE=1 OT_KV_FWD=1 OT_KV_LANDSLOT=1 OT_KV_RST_PIN_REG=1 OT_KV_BUNDLE_EQ=1 OT_KV_D2D_NTX=3
# KVR-VIEWS 10-19 view defaults (each binds ONLY a CLOSED view; overridable from the caller's environment / KVS14R_EXTRA):
#  * OT_KV_FACE_LAND=astk_rly_296: the expanded ASTK strip's relay child binds the CLOSED face-landed view
#    qkd_astk_rly_296_fl (qkd_astk_rly_296-fl1-bd369b99e; +3 reset-release edges taken by the compiler)
#  * OT_KV_D2DS_VIEW=auto: qkd_d2ds binds the r7v view only once it is on the branch with TXDP == the die's 0x03030418
#    (d2ds_view_select.py; fails closed on a mismatch; frame while absent)
#  * OT_KV_HROOT_VIEW=auto (kvsys_prep): qkd_kvs_hroot binds the CLOSED k1 view as a stand-in (native FAIL)
export OT_KV_FACE_LAND=${OT_KV_FACE_LAND:-astk_rly_296}
export OT_KV_D2DS_VIEW=${OT_KV_D2DS_VIEW:-auto} OT_KV_HROOT_VIEW=${OT_KV_HROOT_VIEW:-auto}
# Clock evidence and legal landing reservations are mandatory even in diagnostics.
unset OT_KV_FWD_UNLANDED_DIAG OT_KV_CLK_UNMEASURED_DIAG
[ -f tools/qwen_kv_die/kv_lane_reach.py ] || {
  say 'PREP REFUSED: missing mandatory actual lane reach preflight'; exit 8;
}
unset OT_KV_FWD_NETLIST_ONLY OT_KV_STATIC_DIE_DIAGNOSTIC
bash tools/qwen_kv_die/chain/kvsys_prep.sh $R > $R/prep.log 2>&1 || { say "PREP FAIL (prep.log): $(tail -3 $R/prep.log | tr '\n' ' ' | cut -c1-400)"; exit 1; }
if [ -s $R/FWD_UNLANDED_DIAGNOSTIC ]; then
  say "FWD UNLANDED DIAGNOSTIC: $(tr '\n' ' ' < $R/FWD_UNLANDED_DIAGNOSTIC) left as relays (no reserved landing frame) -- run is DIAGNOSTIC, NOT A DIE RESULT"
  echo "FWD_UNLANDED_DIAGNOSTIC_ONLY" >> $R/NOT_A_DIE_RESULT
fi
if [ -s $R/libs/CLK_UNMEASURED_DIAGNOSTIC ]; then
  say "CLK UNMEASURED DIAGNOSTIC (R=0): $(cat $R/libs/CLK_UNMEASURED_DIAGNOSTIC | head -c 300) -- NOT A DIE RESULT"
  echo "CLK_UNMEASURED_DIAGNOSTIC_ONLY" >> $R/NOT_A_DIE_RESULT
fi
# KVR-LANDLAG 10-19: landed crossings vs compiled ages (kvsys_prep kv-check; only OT_KV_LAND_LAG_DIAG=1 lets a FAIL through)
if [ -s $R/LAND_LAG_DIAGNOSTIC ]; then
  say "LAND_LAG DIAGNOSTIC: $(head -c 400 $R/LAND_LAG_DIAGNOSTIC) -- NOT A DIE RESULT"
  echo "LAND_LAG_DIAGNOSTIC_ONLY" >> $R/NOT_A_DIE_RESULT
fi
say "LAND_LAG: $(tail -1 $R/land_lag.log 2>/dev/null | head -c 400)"
say "D2DS VIEW: $(grep -m1 'OT_KV_D2DS_VIEW' $R/prep.log | head -c 300)"
say "BUNDLE_EQ: $(grep -m1 -i 'bundle' $R/prep.log | head -c 400)"
say "prep done: $(tail -1 $R/prep.log | head -c 300)"
say "LANDSLOT: $(python3 -c "import json;d=json.load(open('$R/case_kv/land_slots.json'));print(d['crossings'],'crossing runs, tiers',d['tiers'],'legality',d['legality']['overlaps'],'/',d['legality']['outside'])" 2>&1)"
say "FWD: $(tail -1 $R/fwd_lanes.log | head -c 600)"
say "STATIONS + REACH GATE: $(python3 -c "import json;d=json.load(open('$R/fwd_lanes.json'));print(json.dumps(dict(stations=d.get('stations'),reach_gate=d.get('reach_gate'))))" 2>&1 | head -c 900)"
say "RST_PER_TREE: $(grep -c '#g' $R/rst_regional.json || true) split reset nets"
say "STRICT BIND (laned netlist): $(tail -1 $R/port_bind_v2/port_bind_v2.txt 2>/dev/null | head -c 400)"
python3 tools/qwen_kv_die/kv_fwd_lane_price.py --lanes $R/fwd_lanes.json --out $R/fwd_lane_price.json > $R/fwd_lane_price.log 2>&1 \
  && say "FWD PRICE: $(tail -1 $R/fwd_lane_price.log | head -c 400)" || say "FWD PRICE FAIL (fwd_lane_price.log)"
python3 tools/qwen_kv_die/kv_static_ages.py --fwd-lanes $R/fwd_lanes.json --out $R/die_ages_fwd.json > $R/die_ages_fwd.log 2>&1 || true
python3 tools/qwen_kv_die/case_png.py $R/case_kv --slots $R/rly_std.json --out $R/plan_kvs14r.png --title "kvs14r $C (real KV chain)" > $R/plan_png.log 2>&1 || true
# reset release window hops on the netlist the chain times (laned die.v)
python3 tools/qwen_kv_die/kv_rst_window.py hops --die-v $R/case_kv/die.v --lef $R/case_kv/elements.lef --out $R/rst_window_hops.json > $R/rst_window_hops.log 2>&1 \
  && say "$(tail -1 $R/rst_window_hops.log | head -c 400)" || say "RST WINDOW HOPS FAIL (rst_window_hops.log)"
export OT_RST_WINDOW_HOPS=$R/rst_window_hops.json
say "MU-KV-GEN prep-only (OT_KV_MU=1) DONE"
exit 0

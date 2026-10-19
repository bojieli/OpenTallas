#!/bin/bash
# KV-PLAN5 10-18 kvs14p: the PHYSICAL KV die chain on the QLB-KV GEN source (claude/qlb-kv-gsrc-1018 @64ce0504d: KV-LANDSLOT
# c1989d8c5 + SEAMK BUNDLE_EQ / RELAY_CHECK + TXDP_K + LINK/FACE RTL + closed qkd_rst_region_pr), kvs14q's flags (netlist-only
# kvs14q-8503e0c89: strict bind / TXDP_K / RELAY_CHECK PASS) made physical = kvs14d's chain:
#   * 377.6 mm2 kit point (PVFORK_GAP 64.8, no AHUB_SDW), regional trees, per-tree resets, forwarded lanes, LANDSLOT landing
#     frames (KV-LANDSLOT / KV-CLOCK), the LANED netlist (no OT_KV_FWD_NETLIST_ONLY): the 16 closed lane views are COMMITTED
#     on this branch from their closure records (kvs14d extracted them untracked -> kvsys_prep 'dirty tree: commit first');
#   * OT_KV_RST_PIN_REG=1 (qkd_rst_region_pr CLOSED, native PASS);
#   * OT_KV_D2DS_VIEW=1: d2d_kv = qkd_d2d_static #(.NTX(3), .TXDP(compiled)) on the CLOSED r7t view
#     qkd_d2d_static_r7t-r7t-28642e9aa (TT +22.73 / FF +10.31), committed from its closure record;
#   * OT_KV_STATIC_DIE_STRICT=1 (a real GEN: the chain's strict bind / RELAY_CHECK gate it; a refused gate re-runs DIAGNOSTIC);
#   * chain: strict bind -> real case -> PDN -> GRT (repeaters) -> STA TT + FF -> DCC TT + FF -> reset release window;
#     beside it die CTS + die_clock_check TT + FF + kv_landed_pairs (kv_die_clock_regions.sh).
# usage (fleet, via ot-run --priority die --remote auto): kvs14p.sh COMMIT
set -euo pipefail
C=$1
B=/srv/opentallas-scratch/claude/qwen-kvsys
W=$B/wt-kvs14p-$C
R=$B/kvs14p-$C
M=/srv/opentallas-scratch/claude/git-mirror/OpenTallas.git
GH=https://github.com/bojieli/OpenTallas
mkdir -p $R
say() { echo "$(date '+%F %T %Z') $*" >> $R/STATUS.log; }
if [ ! -d $W ]; then
  [ -d $M ] || { mkdir -p $(dirname $M); git clone -q --mirror $GH $M; }
  git -C $M fetch -q $GH claude/kv-plan5-1018
  git -C $M worktree add --detach $W $C
fi
cd $W
[ "$(git rev-parse --short=9 HEAD)" = $C ] || { echo "wrong commit"; exit 2; }
miss=
while IFS=$'\t' read -r n rb sha; do
  case $n in qkd_d2d_static*) f=physical/ref_tile/qkd_d2d_static_r5_native/views/qkd_d2d_static/qkd_d2d_static.lef;;
    *) f=physical/ref_tile/$n/views/$n/$n.lef;; esac
  [ -s $f ] || miss="$miss $n"
done < tools/qwen_kv_die/chain/kvs14p_views.tsv
[ -z "$miss" ] || { say "committed views missing:$miss -- kvs14p not run"; exit 1; }
cp tools/qwen_kv_die/chain/kvs14p_views.tsv $R/lane_views.tsv
say "kvs14p $C: views 17 committed (lane_views.tsv); prep start $(git rev-parse HEAD)"
export OT_KV_PV_CTL_KIT=qkd_pv_ctl_rstpin_a72 OT_KV_HOST_V14=1 OT_KV_HOST_NORTH=1 OT_KV_TREES=1 OT_KV_V143=1 OT_KV_V143C=1 OT_KV_ECTL_H13=1 OT_KV_RLY_STD=1 OT_KV_DCAL=1 OT_KV_HOP=1 OT_KV_V144=1 OT_KV_V144_R6=1 OT_KV_PV_W=82 OT_KV_PV_AGE=96 OT_KV_SERDES_N=1 OT_KV_PV_PINY=1 OT_KV_KVNC=1 OT_KV_SEQ_STATIC=1 OT_KV_REACH=400 OT_KV_RST_REGIONAL=1 OT_KV_PHY_REG=1 OT_KV_REACH_W=36:400,296:370,100000:340 OT_KV_PV_T=1 OT_KV_PV_T_CTL_STANDIN=1 OT_KV_REACH_FIX=1 OT_KV_PVT_PINS=1 OT_KV_PVT_HDR_CTL=1 OT_KV_PVT_SOFT_SLACK=0 OT_KV_SEAM=1 OT_KV_STATIC_DIE=1
export OT_KV_HROOT=1 OT_KV_FANFOLD=1 OT_KV_V144_DW=2462.4 OT_KV_SN_LIFT=432 OT_KV_CTL_BAND=302.4 OT_KV_PVT_HUB_CLEAR=172.8 OT_KV_KV_CHAN_EXTRA=86.4 OT_KV_V144_RLY_FIRST=pvin_,krs_,kvn_,ap_,aq_,am_,ks_acal_,pve_
export OT_KV_STATIC_DIE_STRICT=1 OT_KV_TILE_KITS=1 OT_KV_PVFORK_GAP=64.8 ${KVS14P_EXTRA:-}
export OT_KV_EXPAND=qkd_rhead,qkd_rhead_ft,qkd_ectl,qkd_ctrl,qkd_ctrl_n,qkd_pvfork,qkd_pvtap2,qkd_pvtap3,qkd_pvtap4
export OT_KV_RST_PER_TREE=1 OT_KV_FWD=1 OT_KV_LANDSLOT=1 OT_KV_RST_PIN_REG=1 OT_KV_BUNDLE_EQ=1 OT_KV_D2DS_VIEW=1 OT_KV_D2D_NTX=3
unset OT_KV_FWD_NETLIST_ONLY OT_KV_STATIC_DIE_DIAGNOSTIC
bash tools/qwen_kv_die/chain/kvsys_prep.sh $R > $R/prep.log 2>&1 || { say "PREP FAIL (prep.log): $(tail -3 $R/prep.log | tr '\n' ' ' | cut -c1-400)"; exit 1; }
say "D2DS VIEW: $(grep -m1 'OT_KV_D2DS_VIEW' $R/prep.log | head -c 300)"
say "BUNDLE_EQ: $(grep -m1 -i 'bundle' $R/prep.log | head -c 400)"
say "prep done: $(tail -1 $R/prep.log | head -c 300)"
say "LANDSLOT: $(python3 -c "import json;d=json.load(open('$R/case_kv/land_slots.json'));print(d['crossings'],'crossing runs, tiers',d['tiers'],'legality',d['legality']['overlaps'],'/',d['legality']['outside'])" 2>&1)"
say "FWD: $(tail -1 $R/fwd_lanes.log | head -c 600)"
say "RST_PER_TREE: $(grep -c '#g' $R/rst_regional.json || true) split reset nets"
say "STRICT BIND (laned netlist): $(tail -1 $R/port_bind_v2/port_bind_v2.txt 2>/dev/null | head -c 400)"
python3 tools/qwen_kv_die/kv_fwd_lane_price.py --lanes $R/fwd_lanes.json --out $R/fwd_lane_price.json > $R/fwd_lane_price.log 2>&1 \
  && say "FWD PRICE: $(tail -1 $R/fwd_lane_price.log | head -c 400)" || say "FWD PRICE FAIL (fwd_lane_price.log)"
python3 tools/qwen_kv_die/kv_static_ages.py --fwd-lanes $R/fwd_lanes.json --out $R/die_ages_fwd.json > $R/die_ages_fwd.log 2>&1 || true
python3 tools/qwen_kv_die/case_png.py $R/case_kv --slots $R/rly_std.json --out $R/plan_kvs14p.png --title "kvs14p $C (laned, landing slots, d2d r7t)" > $R/plan_png.log 2>&1 || true
# reset release window hops on the netlist the chain times (laned die.v)
python3 tools/qwen_kv_die/kv_rst_window.py hops --die-v $R/case_kv/die.v --lef $R/case_kv/elements.lef --out $R/rst_window_hops.json > $R/rst_window_hops.log 2>&1 \
  && say "$(tail -1 $R/rst_window_hops.log | head -c 400)" || say "RST WINDOW HOPS FAIL (rst_window_hops.log)"
export OT_RST_WINDOW_HOPS=$R/rst_window_hops.json
python3 tools/phy_pg/apply_case.py $R/case_kv --ack-assumed-phy-contract > $R/phy_pg_apply.log 2>&1 || { say "PHY PG HOOK FAIL"; exit 1; }
printf "{\"status\":\"PASS\",\"actual_git_commit\":\"%s\",\"method\":\"clean detached worktree at the exact commit; lane + d2d views committed from their closure records (tools/qwen_kv_die/chain/kvs14p_views.tsv)\"}\n" "$(git rev-parse HEAD)" > $R/source_verified.json
touch $R/READY_FOR_CHAIN
nohup bash tools/qwen_kv_die/chain/kv_die_clock_regions.sh $R $W > $R/dieclk.log 2>&1 &
set -a; . $R/kv_flags.env; set +a
export OT_DIE_REPAIR=1 OT_ADMIT=pass OT_PDN=run OT_PDN_BBOX_OBS=1
export OT_CORNERS="tt ff" OT_DCC_CORNERS="tt ff"
# strict bind PASS -> a real chain; otherwise the chain still runs, stamped DIAGNOSTIC (never a die result)
if tail -1 $R/port_bind_v2/port_bind_v2.txt 2>/dev/null | grep -q PASS; then unset OT_BIND_DIAGNOSTIC; else export OT_BIND_DIAGNOSTIC=1; fi
say "chain start (laned netlist; OT_BIND_DIAGNOSTIC=${OT_BIND_DIAGNOSTIC:-0})"
bash "$W/tools/qwen_kv_die/chain/die_chain.sh" kv "$R" "$W" > "$R/chain.log" 2>&1 || say "chain rc=$?"
# a refused launch gate (native bind / RELAY_CHECK) stops die_chain before GRT: re-run once stamped DIAGNOSTIC so the GRT /
# STA / DCC evidence of this floorplan still exists (NOT_A_DIE_RESULT names the failed gate; never a die result)
if [ -z "${OT_BIND_DIAGNOSTIC:-}" ] && tail -3 $R/STATUS.log | grep -q 'no die job launched'; then
  export OT_BIND_DIAGNOSTIC=1; say "launch gate refused: chain re-run DIAGNOSTIC (not a die result)"
  bash "$W/tools/qwen_kv_die/chain/die_chain.sh" kv "$R" "$W" > "$R/chain_diag.log" 2>&1 || say "chain (diagnostic) rc=$?"
fi
wait
# the release window again with the measured die clock arrivals (dieclk finishes beside / after the STA)
python3 tools/qwen_kv_die/kv_rst_window.py report --hops $R/rst_window_hops.json --tt $R/sta_kv_tt/rst_window_tt.tsv \
  --ff $R/sta_kv_ff/rst_window_ff.tsv $( [ -s $R/dieclk/dump_tt.tsv ] && echo --dump-tt $R/dieclk/dump_tt.tsv ) \
  $( [ -s $R/dieclk/dump_ff.tsv ] && echo --dump-ff $R/dieclk/dump_ff.tsv ) --out $R/rst_window.json > $R/rst_window.log 2>&1 || true
say "$(tail -1 $R/rst_window.log | head -c 500)"
say "kvs14p done"

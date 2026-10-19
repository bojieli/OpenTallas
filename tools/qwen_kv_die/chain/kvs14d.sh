#!/bin/bash
# KV-LANDSLOT 10-18 kvs14d (lanes/KV-LANDSLOT.md): kvs14c (KV-CLOCK try 2 @f05f9338f: kv-wire's placing kit point,
# 377.6 mm2, PVFORK_GAP 64.8, regional trees, per-tree resets, forwarded lanes) with
#   (1) OT_KV_LANDSLOT=1: the die planner reserves the LANDING frame (qkd_rly_<W>_land, landing-kit outlines) at the last
#       stage of every crossing run, abutted to the receiving block face (kv_land_slot.py; RUN/case_kv/land_slots.json);
#   (2) the PHYSICAL chain on the LANED netlist (kv_fwd_lanes.py without --netlist-only: the 16 closed lane views bound
#       from their closure records; kvs14c ran the relay netlist): strict bind (laned), real case, PDN, GRT(repeaters),
#       STA TT + FF, DCC TT + FF;
#   (3) die CTS + die_clock_check TT + FF on this floorplan and the crossing-pair check (kv_landed_pairs: GAP 0);
#   (4) the reset release window of every cross-tree reset root hop in the die STA (kv_rst_window.py: MCP setup E_r /
#       hold E_r-1, TT setup + FF hold, measured dieclk arrivals) -> RUN/rst_window.json.
# Starts after kvs14c's prep reported (same config: a kvs14c PREP FAIL stops this run before it spends the fleet) and
# once all 16 lane views have closure records.
# usage (on ot-epyc4, via ot-run): kvs14d.sh COMMIT
set -euo pipefail
C=$1
B=/srv/opentallas-scratch/claude/qwen-kvsys
W=$B/wt-kvs14d-$C
R=$B/kvs14d-place
M=/srv/opentallas-scratch/claude/git-mirror/OpenTallas.git
GH=https://github.com/bojieli/OpenTallas
mkdir -p $R
say() { echo "$(date '+%F %T %Z') $*" >> $R/STATUS.log; }
K14C=$B/kvs14c-place/STATUS.log
say "kvs14d $C: waiting for kvs14c prep ($K14C)"
for i in $(seq 1 ${KVS14D_PREP_WAIT_POLLS:-144}); do
  grep -q 'PREP FAIL' $K14C 2>/dev/null && { say "kvs14c PREP FAILED (same config): kvs14d not run"; exit 1; }
  grep -q 'prep done' $K14C 2>/dev/null && break
  sleep 300
done
grep -q 'prep done' $K14C 2>/dev/null || { say "kvs14c prep never reported: kvs14d not run"; exit 1; }
say "kvs14c prep: $(grep -m1 'prep done' $K14C | cut -c1-200)"
if [ ! -d $W ]; then
  git -C $M fetch -q $GH claude/kv-landslot-1018
  git -C $M worktree add --detach $W $C
fi
cd $W
[ "$(git rev-parse --short=9 HEAD)" = $C ] || { echo "wrong commit"; exit 2; }
# lane views from their closure records (untracked under physical/ref_tile/<m>/views; provenance in RUN/lane_views.tsv)
LANES="rlysh0 rlysh landsh landsh0"
: > $R/lane_views.tsv
for i in $(seq 1 ${KVS14D_VIEW_WAIT_POLLS:-72}); do
  git -C $M fetch -q $GH '+refs/heads/codex/closure-record-qkd_rlysh*:refs/remotes/rec/codex/closure-record-qkd_rlysh*' \
    '+refs/heads/codex/closure-record-qkd_landsh*:refs/remotes/rec/codex/closure-record-qkd_landsh*' || true
  miss=
  for f in $LANES; do for s in 1 36 296 528; do n=qkd_${f}_$s
    [ -s physical/ref_tile/$n/views/$n/$n.lef ] && continue
    rb=$(git -C $M for-each-ref --format='%(refname)' "refs/remotes/rec/codex/closure-record-$n-f1-*" | tail -1)
    if [ -n "$rb" ] && git -C $M cat-file -e "$rb:physical/ref_tile/$n/views/$n/$n.lef" 2>/dev/null; then
      git -C $M archive "$rb" physical/ref_tile/$n/views | tar -x -C $W
      printf '%s\t%s\t%s\n' $n "$rb" "$(git -C $M rev-parse $rb)" >> $R/lane_views.tsv
    else miss="$miss $n"; fi
  done; done
  [ -z "$miss" ] && break
  [ $i = 1 ] && say "lane views missing:$miss (waiting for their closure records)"
  sleep 600
done
[ -z "$miss" ] || { say "lane views still missing after the wait:$miss -- kvs14d not run"; exit 1; }
say "lane views: 16 bound from closure records ($R/lane_views.tsv)"
say "prep start $(git rev-parse HEAD)"
export OT_KV_PV_CTL_KIT=qkd_pv_ctl_rstpin_a72 OT_KV_HOST_V14=1 OT_KV_HOST_NORTH=1 OT_KV_TREES=1 OT_KV_V143=1 OT_KV_V143C=1 OT_KV_ECTL_H13=1 OT_KV_RLY_STD=1 OT_KV_DCAL=1 OT_KV_HOP=1 OT_KV_V144=1 OT_KV_V144_R6=1 OT_KV_PV_W=82 OT_KV_PV_AGE=96 OT_KV_SERDES_N=1 OT_KV_PV_PINY=1 OT_KV_KVNC=1 OT_KV_SEQ_STATIC=1 OT_KV_REACH=400 OT_KV_RST_REGIONAL=1 OT_KV_PHY_REG=1 OT_KV_REACH_W=36:400,296:370,100000:340 OT_KV_PV_T=1 OT_KV_PV_T_CTL_STANDIN=1 OT_KV_REACH_FIX=1 OT_KV_PVT_PINS=1 OT_KV_PVT_HDR_CTL=1 OT_KV_PVT_SOFT_SLACK=0 OT_KV_SEAM=1 OT_KV_STATIC_DIE=1
export OT_KV_HROOT=1 OT_KV_FANFOLD=1 OT_KV_V144_DW=2462.4 OT_KV_SN_LIFT=432 OT_KV_CTL_BAND=302.4 OT_KV_PVT_HUB_CLEAR=172.8 OT_KV_KV_CHAN_EXTRA=86.4 OT_KV_V144_RLY_FIRST=pvin_,krs_,kvn_,ap_,aq_,am_,ks_acal_,pve_
export OT_KV_STATIC_DIE_DIAGNOSTIC=1 OT_KV_TILE_KITS=1 OT_KV_PVFORK_GAP=64.8 ${KVS14D_EXTRA:-}
export OT_KV_EXPAND=qkd_rhead,qkd_rhead_ft,qkd_ectl,qkd_ctrl,qkd_ctrl_n,qkd_pvfork,qkd_pvtap2,qkd_pvtap3,qkd_pvtap4
export OT_KV_RST_PER_TREE=1 OT_KV_FWD=1 OT_KV_LANDSLOT=1
unset OT_KV_FWD_NETLIST_ONLY
bash tools/qwen_kv_die/chain/kvsys_prep.sh $R > $R/prep.log 2>&1 || { say "PREP FAIL (prep.log): $(tail -3 $R/prep.log | tr '\n' ' ' | cut -c1-400)"; exit 1; }
say "prep done: $(tail -1 $R/prep.log | head -c 300)"
say "LANDSLOT: $(python3 -c "import json;d=json.load(open('$R/case_kv/land_slots.json'));print(d['crossings'],'crossing runs, tiers',d['tiers'],'legality',d['legality']['overlaps'],'/',d['legality']['outside'])" 2>&1)"
say "FWD: $(tail -1 $R/fwd_lanes.log | head -c 600)"
say "RST_PER_TREE: $(grep -c '#g' $R/rst_regional.json || true) split reset nets"
say "STRICT BIND (laned netlist): $(tail -1 $R/port_bind_v2/port_bind_v2.txt 2>/dev/null | head -c 400)"
python3 tools/qwen_kv_die/kv_fwd_lane_price.py --lanes $R/fwd_lanes.json --out $R/fwd_lane_price.json > $R/fwd_lane_price.log 2>&1 \
  && say "FWD PRICE: $(tail -1 $R/fwd_lane_price.log | head -c 400)" || say "FWD PRICE FAIL (fwd_lane_price.log)"
python3 tools/qwen_kv_die/kv_static_ages.py --fwd-lanes $R/fwd_lanes.json --out $R/die_ages_fwd.json > $R/die_ages_fwd.log 2>&1 || true
python3 tools/qwen_kv_die/case_png.py $R/case_kv --slots $R/rly_std.json --out $R/plan_kvs14d.png --title "kvs14d $C (laned, landing slots)" > $R/plan_png.log 2>&1 || true
# reset release window hops on the netlist the chain times (laned die.v)
python3 tools/qwen_kv_die/kv_rst_window.py hops --die-v $R/case_kv/die.v --lef $R/case_kv/elements.lef --out $R/rst_window_hops.json > $R/rst_window_hops.log 2>&1 \
  && say "$(tail -1 $R/rst_window_hops.log | head -c 400)" || say "RST WINDOW HOPS FAIL (rst_window_hops.log)"
export OT_RST_WINDOW_HOPS=$R/rst_window_hops.json
python3 tools/phy_pg/apply_case.py $R/case_kv --ack-assumed-phy-contract > $R/phy_pg_apply.log 2>&1 || { say "PHY PG HOOK FAIL"; exit 1; }
printf "{\"status\":\"PASS\",\"actual_git_commit\":\"%s\",\"method\":\"clean detached worktree at the exact commit + untracked lane views from closure records (lane_views.tsv)\"}\n" "$(git rev-parse HEAD)" > $R/source_verified.json
touch $R/READY_FOR_CHAIN
nohup bash tools/qwen_kv_die/chain/kv_die_clock_regions.sh $R $W > $R/dieclk.log 2>&1 &
set -a; . $R/kv_flags.env; set +a
export OT_DIE_REPAIR=1 OT_ADMIT=pass OT_PDN=run OT_PDN_BBOX_OBS=1
export OT_CORNERS="tt ff" OT_DCC_CORNERS="tt ff"
# strict bind PASS -> a real chain; otherwise the chain still runs, stamped DIAGNOSTIC (never a die result)
if tail -1 $R/port_bind_v2/port_bind_v2.txt 2>/dev/null | grep -q PASS; then unset OT_BIND_DIAGNOSTIC; else export OT_BIND_DIAGNOSTIC=1; fi
say "chain start (laned netlist; OT_BIND_DIAGNOSTIC=${OT_BIND_DIAGNOSTIC:-0})"
bash "$W/tools/qwen_kv_die/chain/die_chain.sh" kv "$R" "$W" > "$R/chain.log" 2>&1 || say "chain rc=$?"
wait
# the release window again with the measured die clock arrivals (dieclk finishes beside / after the STA)
python3 tools/qwen_kv_die/kv_rst_window.py report --hops $R/rst_window_hops.json --tt $R/sta_kv_tt/rst_window_tt.tsv \
  --ff $R/sta_kv_ff/rst_window_ff.tsv $( [ -s $R/dieclk/dump_tt.tsv ] && echo --dump-tt $R/dieclk/dump_tt.tsv ) \
  $( [ -s $R/dieclk/dump_ff.tsv ] && echo --dump-ff $R/dieclk/dump_ff.tsv ) --out $R/rst_window.json > $R/rst_window.log 2>&1
say "$(tail -1 $R/rst_window.log | head -c 500)"
say "kvs14d done"

#!/bin/bash
# KV-CLOCK 10-18 kvs14c (lanes/KV-CLOCK.md): the KV die on the landed-regions standard, folded on kvs14b (KV-CASE2 84d1b3e7b,
# plan m1 + kits + hub kit frame) + KV-WIRE2 b14a597ce (BOOT/SEQ/ASTK) on claude/kv-clock-1018:
#   (1) prep with OT_KV_RST_PER_TREE=1 (reset station trees per core tree) + OT_KV_FWD=1 (forwarded half-cycle lanes +
#       landings on every c <-> stack relay run; netlist-only until the qkd_rlysh*/landsh* kits close) -> strict bind of
#       the LANED netlist (port_bind_v2_fwd/) + RUN/fwd_lanes.json + price (kv_fwd_lane_price.py);
#   (2) the physical case / PDN / GRT(repeaters) / STA tt ff ss run on the same geometry with the relay masters (die.v.prefwd:
#       the lanes keep every frame and position), DCC at TT and FF;
#   (3) DIE CTS on THIS floorplan (tools/die_clock/build.py, spec tools/die_clock/specs/kv_regions_1018.json: five
#       independent core region trees, no balance group, TT + FF two-corner trim), re-measured at FF, die_clock_check at
#       TT + FF per region (families = regions), cross-region pairs classified landed / reset root / GAP.
# usage (on ot-epyc4, via ot-run): kvs14c.sh COMMIT
set -euo pipefail
C=$1
B=/srv/opentallas-scratch/claude/qwen-kvsys
W=$B/wt-kvs14-$C
R=$B/kvs14c-place
M=/srv/opentallas-scratch/claude/git-mirror/OpenTallas.git
mkdir -p $R
say() { echo "$(date '+%F %T %Z') $*" >> $R/STATUS.log; }
if [ ! -d $W ]; then
  git -C $M fetch -q https://github.com/bojieli/OpenTallas claude/kv-clock-1018
  git -C $M worktree add --detach $W $C
fi
cd $W
[ "$(git rev-parse --short=9 HEAD)" = $C ] || { echo "wrong commit"; exit 2; }
say "prep start $(git rev-parse HEAD)"
export OT_KV_PV_CTL_KIT=qkd_pv_ctl_rstpin_a72 OT_KV_HOST_V14=1 OT_KV_HOST_NORTH=1 OT_KV_TREES=1 OT_KV_V143=1 OT_KV_V143C=1 OT_KV_ECTL_H13=1 OT_KV_RLY_STD=1 OT_KV_DCAL=1 OT_KV_HOP=1 OT_KV_V144=1 OT_KV_V144_R6=1 OT_KV_PV_W=82 OT_KV_PV_AGE=96 OT_KV_SERDES_N=1 OT_KV_PV_PINY=1 OT_KV_KVNC=1 OT_KV_SEQ_STATIC=1 OT_KV_REACH=400 OT_KV_RST_REGIONAL=1 OT_KV_PHY_REG=1 OT_KV_REACH_W=36:400,296:370,100000:340 OT_KV_PV_T=1 OT_KV_PV_T_CTL_STANDIN=1 OT_KV_REACH_FIX=1 OT_KV_PVT_PINS=1 OT_KV_PVT_HDR_CTL=1 OT_KV_PVT_SOFT_SLACK=0 OT_KV_SEAM=1 OT_KV_STATIC_DIE=1
export OT_KV_HROOT=1 OT_KV_FANFOLD=1 OT_KV_V144_DW=2462.4 OT_KV_SN_LIFT=432 OT_KV_CTL_BAND=302.4 OT_KV_PVT_HUB_CLEAR=172.8 OT_KV_KV_CHAN_EXTRA=86.4 OT_KV_V144_RLY_FIRST=pvin_,krs_,kvn_,ap_,aq_,am_,ks_acal_,pve_
# kvs14c try 1 @4aafe91ff (kv-case AHUB_SDW 363.5 mm2 + PVFORK_GAP 86.4 with the kv-wire buses): 4 unrepaired pin hops
# (pve_WS/ES/EN astk erd -> first relay ~10.1 mm).  The KV die may grow (owner 10-18 02:15): take kv-wire's placing kit
# point (plan k2, 377.6 mm2: kits + static hub, legacy hub frame, PVFORK_GAP 64.8); OT_KV_AHUB_SDW waits for a re-plan.
export OT_KV_STATIC_DIE_DIAGNOSTIC=1 OT_KV_TILE_KITS=1 OT_KV_PVFORK_GAP=64.8 ${KVS14C_EXTRA:-}
export OT_KV_EXPAND=qkd_rhead,qkd_rhead_ft,qkd_ectl,qkd_ctrl,qkd_ctrl_n,qkd_pvfork,qkd_pvtap2,qkd_pvtap3,qkd_pvtap4
export OT_KV_RST_PER_TREE=1 OT_KV_FWD=1 OT_KV_FWD_NETLIST_ONLY=1
bash tools/qwen_kv_die/chain/kvsys_prep.sh $R > $R/prep.log 2>&1 || { say "PREP FAIL (prep.log)"; exit 1; }
say "prep done: $(tail -1 $R/prep.log | head -c 300)"
say "FWD: $(tail -1 $R/fwd_lanes.log | head -c 400)"
say "RST_PER_TREE: $(grep -c '#g' $R/rst_regional.json || true) split reset nets"
mv $R/port_bind_v2 $R/port_bind_v2_fwd
say "STRICT BIND (laned netlist): $(tail -1 $R/port_bind_v2_fwd/port_bind_v2.txt | head -c 400)"
python3 tools/qwen_kv_die/kv_fwd_lane_price.py --lanes $R/fwd_lanes.json --out $R/fwd_lane_price.json > $R/fwd_lane_price.log 2>&1 \
  && say "FWD PRICE: $(tail -1 $R/fwd_lane_price.log | head -c 400)" || say "FWD PRICE FAIL (fwd_lane_price.log)"
python3 tools/qwen_kv_die/kv_static_ages.py --fwd-lanes $R/fwd_lanes.json --out $R/die_ages_fwd.json > $R/die_ages_fwd.log 2>&1 || true
# (2) physical run on the relay netlist of the same geometry (lane views not closed yet)
cp $R/case_kv/die.v $R/case_kv/die.v.fwd
cp $R/case_kv/die.v.prefwd $R/case_kv/die.v
python3 tools/qwen_kv_die/kvsys_clocks.py --case $R/case_kv --views $R/libs/views.json --out $R/libs > $R/clocks_prefwd.log 2>&1 || { say "CLOCKS (relay netlist) FAIL"; exit 1; }
python3 tools/phy_pg/apply_case.py $R/case_kv --ack-assumed-phy-contract > $R/phy_pg_apply.log 2>&1 || { say "PHY PG HOOK FAIL"; exit 1; }
printf "{\"status\":\"PASS\",\"actual_git_commit\":\"%s\",\"method\":\"clean detached worktree at the exact commit\"}\n" "$(git rev-parse HEAD)" > $R/source_verified.json
touch $R/READY_FOR_CHAIN
# (3) die CTS on this floorplan, started as soon as the real case has written it (runs beside PDN / GRT)
nohup bash tools/qwen_kv_die/chain/kv_die_clock_regions.sh $R $W > $R/dieclk.log 2>&1 &
set -a; . $R/kv_flags.env; set +a
export OT_DIE_REPAIR=1 OT_ADMIT=pass OT_BIND_DIAGNOSTIC=1 OT_PDN=run OT_PDN_BBOX_OBS=1
export OT_CORNERS="tt ff ss" OT_DCC_CORNERS="tt ff"
say "chain start"
bash "$W/tools/qwen_kv_die/chain/die_chain.sh" kv "$R" "$W" > "$R/chain.log" 2>&1 || say "chain rc=$?"
wait
say "kvs14c done"

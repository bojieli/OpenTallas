#!/bin/bash
# DIE-KV-LEAD 10-19 kvs14r: the REAL KV die chain (no diagnostic gate) on claude/die-kv-lead-1019 =
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
  git -C $M fetch -q $GH "${KVS14R_REF:-claude/die-kv-lead-1019}"
  git -C $M worktree add --detach $W $C
fi
cd $W
[ "$(git rev-parse --short=9 HEAD)" = $C ] || { echo "wrong commit"; exit 2; }
# KVR-PLACE 10-19: kv_astk_expand.view_readiness recovers each ASTK leaf's gate-snapshot source blob (git show
# <start_commit>:<src>); the mirror fetches only the run ref, so a fresh mirror lacked f932059e1 and the prep refused
# ("exact selected source not bound by gate snapshot") -- fetch every leaf gate's start commit the mirror is missing
for c_ in $(python3 -c "import json,glob;print(' '.join(sorted({json.load(open(f)).get('source_binding',{}).get('start_commit','') for f in glob.glob('physical/ref_tile/qkd_astk*/gate_result.json')}-{''})))"); do
  git cat-file -e "$c_^{commit}" 2>/dev/null || git -C $M fetch -q $GH "$c_" || true
done
# KV-BIND4 10-19: kv_tile_views identifies a kvs_* tile view by its closure route's source commit (provenance orfs_dir
# .../<kit>-<tag>-<sha9>/); a view hardened on another branch (attention r16 rv3 @6fdacf98c) needs that commit in the mirror
for c_ in $(python3 -c "import glob,re;print(' '.join(sorted({m.group(1) for f in glob.glob('physical/ref_tile/qkd_kvs_*/views/*/provenance/view_export.abstract.json') for m in [re.search(r'closure-loop/[^/\"]+-([0-9a-f]{9})/', open(f).read())] if m})))"); do
  git cat-file -e "$c_^{commit}" 2>/dev/null || { f_=$(git -C $M rev-parse -q --verify "$c_^{commit}" 2>/dev/null) || f_=; [ -n "$f_" ] || git -C $M fetch -q $GH claude/kv-attn2b-1019 || true; }
done
miss=
while IFS=$'\t' read -r n rb sha; do
  case $n in qkd_d2d_static*) f=physical/ref_tile/qkd_d2d_static_r5_native/views/qkd_d2d_static/qkd_d2d_static.lef;;
    *) f=physical/ref_tile/$n/views/$n/$n.lef;; esac
  [ -s $f ] || miss="$miss $n"
done < <(grep -v "^qkd_d2d_static" tools/qwen_kv_die/chain/kvs14p_views.tsv)
[ -z "$miss" ] || { say "committed views missing:$miss -- kvs14p not run"; exit 1; }
cp tools/qwen_kv_die/chain/kvs14p_views.tsv $R/lane_views.tsv
say "kvs14r $C: lane views 16 committed (lane_views.tsv); prep start $(git rev-parse HEAD)"
export OT_KV_PV_CTL_KIT=qkd_pv_ctl_rstpin_a72 OT_KV_HOST_V14=1 OT_KV_HOST_NORTH=1 OT_KV_TREES=1 OT_KV_V143=1 OT_KV_V143C=1 OT_KV_ECTL_H13=1 OT_KV_RLY_STD=1 OT_KV_DCAL=1 OT_KV_HOP=1 OT_KV_V144=1 OT_KV_V144_R6=1 OT_KV_PV_W=82 OT_KV_PV_AGE=96 OT_KV_SERDES_N=1 OT_KV_PV_PINY=1 OT_KV_KVNC=1 OT_KV_SEQ_STATIC=1 OT_KV_REACH=400 OT_KV_RST_REGIONAL=1 OT_KV_PHY_REG=1 OT_KV_REACH_W=36:400,296:370,100000:340 OT_KV_PV_T=1 OT_KV_PV_T_CTL_KIT=qkd_pv_ctl_t_d54f58a95 OT_KV_REACH_FIX=1 OT_KV_PVT_PINS=1 OT_KV_PVT_HDR_CTL=1 OT_KV_PVT_SOFT_SLACK=0 OT_KV_SEAM=1 OT_KV_STATIC_DIE=1
export OT_KV_HROOT=1 OT_KV_FANFOLD=1 OT_KV_V144_DW=2462.4 OT_KV_SN_LIFT=432 OT_KV_CTL_BAND=302.4 OT_KV_PVT_HUB_CLEAR=172.8 OT_KV_KV_CHAN_EXTRA=86.4 OT_KV_V144_RLY_FIRST=pvin_,krs_,kvn_,ap_,aq_,am_,ks_acal_,pve_
export OT_KV_STATIC_DIE_STRICT=1 OT_KV_TILE_KITS=1 OT_KV_PVFORK_GAP=64.8 OT_KV_ATTN_LAND=1 ${KVS14R_EXTRA:-}
export OT_KV_EXPAND=qkd_rhead,qkd_rhead_ft,qkd_ectl,qkd_ctrl,qkd_ctrl_n,qkd_pvfork,qkd_pvtap2,qkd_pvtap3,qkd_pvtap4,qkd_seq_st,qkd_pvw_s,qkd_pvw_n
# KV-HEALTH 10-19 (MU release defaults): health plane installed, reset roots on the HOLD273 view
export OT_KV_HEALTH=${OT_KV_HEALTH:-1} OT_KV_RST_HOLD=${OT_KV_RST_HOLD:-273}
export OT_KV_RST_PER_TREE=1 OT_KV_FWD=1 OT_KV_LANDSLOT=1 OT_KV_RST_PIN_REG=1 OT_KV_BUNDLE_EQ=1 OT_KV_D2D_NTX=3
# KVR-VIEWS 10-19 view defaults (each binds ONLY a CLOSED view; overridable from the caller's environment / KVS14R_EXTRA):
#  * OT_KV_FACE_LAND=astk_rly_296: the expanded ASTK strip's relay child binds the CLOSED face-landed view
#    qkd_astk_rly_296_fl (qkd_astk_rly_296-fl1-bd369b99e; +3 reset-release edges taken by the compiler)
#  * OT_KV_D2DS_VIEW=auto: qkd_d2ds binds the r7v view only once it is on the branch with TXDP == the die's 0x03030418
#    (d2ds_view_select.py; fails closed on a mismatch; frame while absent)
#  * OT_KV_HROOT_VIEW=auto (kvsys_prep): qkd_kvs_hroot binds the CLOSED k1 view as a stand-in (native FAIL)
export OT_KV_FACE_LAND=${OT_KV_FACE_LAND:-astk_rly_296}
# KV-BIND4 10-19: GEN9 d2ds kit = the CLOSED KV-SRAM-D2D successor qkd_d2d_static_r7w_sfm2 (sfm2-1c6c02ed7, TT +76.47 /
#    FF +2.91; top qkd_d2d_static_sfm, TXDP 0x03030416 NTX 3 SAFE_RC 1 SRAMV 2 FEG 1): kv_die.d2ds_kit binds the sfm RTL
#    with those params, d2ds_view_select its views/qkd_d2d_static_sfm (still fails closed on a TXDP / NTX mismatch)
export OT_KV_D2DS_VIEW=${OT_KV_D2DS_VIEW:-auto} OT_KV_HROOT_VIEW=${OT_KV_HROOT_VIEW:-auto}
export OT_KV_D2DS_KIT=${OT_KV_D2DS_KIT:-qkd_d2d_static_r7w_sfm2}
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
# KV-GEN8 10-19: OT_KV_PARAM_DIAG=1 = expanded leaves keep their exact parameters on unreviewed auto-profiles (no native
# parameter receipt, K.STA.PARAMS) -> DIAGNOSTIC, never a die result
if [ "${OT_KV_PARAM_DIAG:-0}" = 1 ]; then
  say "PARAM DIAGNOSTIC: expanded leaf parameter profiles unqualified (OT_KV_PARAM_DIAG=1) -- NOT A DIE RESULT"
  echo "PARAM_PROFILE_DIAGNOSTIC_ONLY" >> $R/NOT_A_DIE_RESULT
fi
if [ -s $R/libs/CLK_UNMEASURED_DIAGNOSTIC ]; then
  say "CLK UNMEASURED DIAGNOSTIC (R=0): $(cat $R/libs/CLK_UNMEASURED_DIAGNOSTIC | head -c 300) -- NOT A DIE RESULT"
  echo "CLK_UNMEASURED_DIAGNOSTIC_ONLY" >> $R/NOT_A_DIE_RESULT
fi
# KV-HEALTH 10-19: an incomplete health plane / HOLD128 reset roots are diagnostics, never a die result
for mk in HEALTH_DIAGNOSTIC RST_HOLD_DIAGNOSTIC; do
  if [ -s $R/$mk ]; then say "$mk: $(head -c 400 $R/$mk) -- NOT A DIE RESULT"; echo "${mk}_ONLY" >> $R/NOT_A_DIE_RESULT; fi
done
say "HEALTH: $(grep -m1 '^KV_HEALTH {' $R/health_plane.log 2>/dev/null | head -c 600)"
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
python3 tools/phy_pg/apply_case.py $R/case_kv --ack-assumed-phy-contract > $R/phy_pg_apply.log 2>&1 || { say "PHY PG HOOK FAIL"; exit 1; }
printf "{\"status\":\"PASS\",\"actual_git_commit\":\"%s\",\"method\":\"clean detached worktree at the exact commit; lane views committed from their closure records (tools/qwen_kv_die/chain/kvs14p_views.tsv)\"}\n" "$(git rev-parse HEAD)" > $R/source_verified.json
touch $R/READY_FOR_CHAIN
nohup bash tools/qwen_kv_die/chain/kv_die_clock_regions.sh $R $W > $R/dieclk.log 2>&1 &
set -a; . $R/kv_flags.env; set +a
export OT_DIE_REPAIR=1 OT_ADMIT=pass OT_PDN=run OT_PDN_BBOX_OBS=1
export OT_CORNERS="tt ff" OT_DCC_CORNERS="tt ff"
# strict bind PASS -> a real chain; a marker or a refused launch gate stamps it DIAGNOSTIC (never a die result)
unset OT_BIND_DIAGNOSTIC
[ -s $R/FWD_UNLANDED_DIAGNOSTIC ] && export OT_BIND_DIAGNOSTIC=1
[ -s $R/libs/CLK_UNMEASURED_DIAGNOSTIC ] && export OT_BIND_DIAGNOSTIC=1
[ -s $R/LAND_LAG_DIAGNOSTIC ] && export OT_BIND_DIAGNOSTIC=1
[ -s $R/HEALTH_DIAGNOSTIC ] && export OT_BIND_DIAGNOSTIC=1
[ -s $R/RST_HOLD_DIAGNOSTIC ] && export OT_BIND_DIAGNOSTIC=1
[ "${OT_KV_PARAM_DIAG:-0}" = 1 ] && export OT_BIND_DIAGNOSTIC=1
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
say "kvs14r done"

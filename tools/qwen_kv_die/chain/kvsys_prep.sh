#!/bin/bash
# qwen-split/kvsys v1.1 (2026-10-14): local prep of one KV/system die chain run, from a CLEAN committed tree.
#   case (kv_die.py case --kv-wq-mirror --split) -> die_top_lint stubs -> ASSUMED element libs (frames, relays) -> closed
#   real views bound (bind_views.py) -> phi - R compensated die clocks (kvsys_clocks.py) -> NO-STUBS port bind
#   (die_port_bind_kv.py) -> per-bit 2-D window check (kvsys_window.py).  Then rsync OUT to the host and run
#   die_chain.sh kv with OT_STA_CLOCKS=<run>/libs/clocks_{corner}.tcl OT_CORNERS="tt ff ss" (SS = sensitivity only).
# usage: kvsys_prep.sh OUT
set -eu
O=$(readlink -f $1); S=$(cd $(dirname $0)/../../.. && pwd); cd $S
[ -z "$(git status --porcelain -- tools rtl physical)" ] || { echo "dirty tree: commit first"; exit 2; }
mkdir -p $O/libs
# Q-KV 2026-10-16 18:40: record the OT_KV_* build flags so die_chain.sh re-exports them for the strict bind
# (kv_port_bind_v2.sh / die_port_bind_kv.py re-import kv_die: without the flags they used the non-V144_R6 vport binding
# and reported 256 phantom undriven pvin epoch bits on kvs13h)
env | grep -E '^OT_KV_[A-Z0-9_]*=' | sed -E "s/^([^=]*)=(.*)$/export \1='\2'/" > $O/kv_flags.env
# v1.4 (OT_KV_HOST_V14=1): real HOST root core + 128 die-placed PC slices + PLL model (kv_die.py --host-v14)
H14=; V14=
if [ "${OT_KV_HOST_V14:-0}" = 1 ]; then H14=--host-v14; V14=,host_v14; fi
# v1.4.1 (OT_KV_HOST_NORTH=1): the HOST root core directly below the static D2D end (kv_die.py --host-north)
if [ "${OT_KV_HOST_NORTH:-0}" = 1 ]; then H14="--host-v14 --host-north"; V14=,host_v14,host_north; fi
# v1.4.2 (OT_KV_TREES=1, needs OT_KV_HOST_NORTH=1): HOST reset / boot fan-outs as registered relay trees (kv_die.py --host-trees)
if [ "${OT_KV_TREES:-0}" = 1 ]; then H14="$H14 --host-trees"; V14=$V14,host_trees; fi
# v1.4.3 (OT_KV_V143=1, needs OT_KV_TREES=1): G3S2 staged head ingress on the closed gather / sstage views, near-head
# feed-through frames, grown groups, regional reset roots (kv_die.py --v143)
BV=
if [ "${OT_KV_RST_PIN_REG:-1}" = 1 ]; then   # default ON (KV-KITS/NATIVE 10-18, = kv_die.py RST_PIN_REG)
  RPV=physical/ref_tile/qkd_rst_region_pr/views/qkd_rst_region_pr
  python3 tools/qwen_kv_die/check_rst_pin_view.py --view "$RPV" > "$O/rst_pin_view_audit.json" || {
    cat "$O/rst_pin_view_audit.json"; echo 'OT_KV_RST_PIN_REG: selected view is not native PASS'; exit 6;
  }
  BV="$BV --view qkd_rst_region=$RPV"
fi
# KV-PLAN5 10-18 (OT_KV_D2DS_VIEW=1): the static D2D end qkd_d2ds on the CLOSED qkd_d2d_static r7t view (NTX = 3,
# qkd_d2d_static_r7t-r7t-28642e9aa, TT +22.73 / FF +10.31; committed from its closure record).  The die binds .NTX(3) +
# the compiled TXDP; the view was hardened at the r7t wrapper's TXDP {3,3,4,3} (port 0 shift 3 vs the die's 23: +20 one-bit
# flops inside, same ports) -> re-harden owed (lanes/KV-PLAN5.md).  The prep FAILS if the view does not bind.
# KVR-VIEWS 10-19: OT_KV_D2DS_VIEW = 0 (frame) | auto | 1 via d2ds_view_select.py: the kit OT_KV_D2DS_KIT (default the
# r7v re-harden at the die's TXDP_K 0x03030418, lanes/HKV-D2D18.md) binds ONLY when its CLOSED view is on the branch AND
# its spec params {TXDP, NTX} equal the die's compiled kv_static.d2d_txdp_k / d2d_ntx_k; a mismatched view FAILS CLOSED
# (exit 7); auto keeps the frame while the view is absent, 1 refuses then.  RUN/d2ds_view.json records the decision.
D2DSV=
if [ "${OT_KV_D2DS_VIEW:-0}" != 0 ]; then
  D2DSV=$(python3 tools/qwen_kv_die/d2ds_view_select.py --mode "${OT_KV_D2DS_VIEW}" --kit "${OT_KV_D2DS_KIT:-qkd_d2d_static_r7v}" \
    --json $O/d2ds_view.json) || { echo "OT_KV_D2DS_VIEW: view selection FAILED ($(python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['why'])" $O/d2ds_view.json))"; exit 7; }
  echo "OT_KV_D2DS_VIEW=${OT_KV_D2DS_VIEW}: $(python3 -c "import json,sys; d=json.load(open(sys.argv[1])); print(d['decision'], d['why'])" $O/d2ds_view.json)"
  if [ -n "$D2DSV" ]; then BV="$BV --view qkd_d2ds=$D2DSV"; fi; fi
# KVR-VIEWS 10-19 (OT_KV_HROOT_VIEW = auto (default) | 0): the static die's per-stack control root tile qkd_kvs_hroot
# (OT_KV_STATIC_DIE + OT_KV_TILE_KITS + OT_KV_HROOT + OT_KV_FANFOLD tile file qkd_kvs_tiles_hroot_ff_k.sv) binds the CLOSED
# k1 view (qkd_kvs_hroot_k1-k1-6355d06bd, TT +77.62 / FF +16.39; native_pin_audit FAIL capture 452.7 -> a STAND-IN for
# bind / GRT / STA, not a release view: results/rtl/ref_tile/qkd_kvs_hroot_k1/native_pin_audit_k1-6355d06bd.json).
# The k1 kit's qkd_kvs_hroot module is byte-identical to this tile file's; never bound under OT_KV_HROOT_LAND=1 (the
# pin-registered _hl tile is a different RTL: its own kit must close first).  Absent view -> frame (ASSUMED) as before.
if [ "${OT_KV_HROOT_VIEW:-auto}" != 0 ] && [ "${OT_KV_STATIC_DIE:-0}" = 1 ] && [ "${OT_KV_TILE_KITS:-0}" = 1 ] && \
   [ "${OT_KV_HROOT:-0}" = 1 ] && [ "${OT_KV_FANFOLD:-0}" = 1 ] && [ "${OT_KV_HROOT_LAND:-0}" != 1 ]; then
  HRV=physical/ref_tile/${OT_KV_HROOT_KIT:-qkd_kvs_hroot_k1}/views/qkd_kvs_hroot
  if [ -f $HRV/qkd_kvs_hroot.lef ] && [ -f $HRV/qkd_kvs_hroot_tt.lib ] && [ -f $HRV/qkd_kvs_hroot_ff.lib ]; then
    BV="$BV --view qkd_kvs_hroot=$HRV"; echo "OT_KV_HROOT_VIEW: qkd_kvs_hroot -> $HRV (stand-in: native FAIL view, CLOSED)"
  else echo "OT_KV_HROOT_VIEW: no closed view at $HRV (frame ASSUMED)"; fi
fi
if [ "${OT_KV_V143:-0}" = 1 ]; then H14="$H14 --v143"; V14=$V14,v143
  BV="$BV --view qkd_hgs=physical/ref_tile/qkh_head_gather_stage/views/qkh_head_gather_stage --view qkd_hss=physical/ref_tile/qkh_head_sstage/views/qkh_head_sstage"; fi
# OT_KV_DCAL=1 (Q-KVSYS-DIE 10-16): the link calendar sequencer qkd_d2d_cal_seq_pin on its CLOSED view (kv_die.py DCAL)
[ "${OT_KV_DCAL:-0}" = 1 ] && BV="$BV --view qkd_dcal=physical/ref_tile/qkd_d2d_cal_seq_pin_ep3/views/qkd_d2d_cal_seq_pin"
# MU-DIE-KV2 10-19: the MU die's calendar sequencer must be hardened from ot_qwen_d2d_cal_seq_dies_mu.sv (d2d_cal_image_mu.svh:
# C RX / K TX +1 entry, SEG2 8 -> 9); until that kit closes the ep3 view (production image) is a LABELLED STAND-IN
[ "${OT_KV_DCAL:-0}" = 1 ] && [ "${OT_KV_MU:-0}" = 1 ] && echo "OT_KV_DCAL STAND-IN: qkd_dcal bound to qkd_d2d_cal_seq_pin_ep3 (production image), MU image kit owed (ot_qwen_d2d_cal_seq_dies_mu.sv)"
# OT_KV_KVNC=1 (Q-KVSYS PVJOIN 10-16, needs OT_KV_DCAL=1): the KVN context leaf qkd_kvn_ctx_cal (kv_die.py KVNC) on its view
# when the kit has closed (OT_KV_KVNC_KIT, default qkd_kvn_ctx_cal_r2); without a view the frame stays ASSUMED (diagnostic)
if [ "${OT_KV_KVNC:-0}" = 1 ]; then KVV=physical/ref_tile/${OT_KV_KVNC_KIT:-qkd_kvn_ctx_cal_r2}/views/qkd_kvn_ctx_cal
  [ -f $KVV/qkd_kvn_ctx_cal.lef ] && BV="$BV --view qkd_kvnc=$KVV" || echo "OT_KV_KVNC: no closed view at $KVV (frame ASSUMED)"; fi
# OT_KV_SEQ_STATIC=1 (Q-KVSYS PVJOIN 10-16, needs DCAL + KVNC): qkd_seq_static in slot seq (cluster frame, as qkd_seq) and
# the compile-time-image layer programme lprg on its closed view when available (OT_KV_LPRG_KIT, default qkd_layer_prog_img_r3)
# DIE-KV-LEAD 10-19 (coordinator 0je; QLB-C4b item 4): on the static die (OT_KV_STATIC_DIE=1) qkd_lprg is SUPERSEDED
# (kv_static_die.SUPERSEDED: the layer programme is boot-loaded into qkd_kvs_ctl, no qkd_lprg instance), so the obsolete
# qkd_layer_prog_img_r3 view must not be bound nor its old committed image checked. Fail closed if a lprg view is forced.
if [ "${OT_KV_SEQ_STATIC:-0}" = 1 ] && [ "${OT_KV_STATIC_DIE:-0}" = 1 ]; then
  [ -z "${OT_KV_LPRG_KIT:-}" ] || { echo "OT_KV_LPRG_KIT=$OT_KV_LPRG_KIT set on the static die: qkd_lprg is superseded (boot-loaded kvs_ctl programme)"; exit 5; }
  echo "OT_KV_SEQ_STATIC: static die -> qkd_lprg superseded (programme boot-loaded by qkd_kvs_ctl); no lprg view bound, no lprg image check"
elif [ "${OT_KV_SEQ_STATIC:-0}" = 1 ]; then LPV=physical/ref_tile/${OT_KV_LPRG_KIT:-qkd_layer_prog_img_r3}/views/qkd_static_kv_layer_programme_img
  [ -f $LPV/qkd_static_kv_layer_programme_img.lef ] && BV="$BV --view qkd_lprg=$LPV" || echo "OT_KV_SEQ_STATIC: no closed view at $LPV (frame ASSUMED)"
  # the layer image binds the INSTALLED program (digest / epoch checked at the programme start): recompile the roots for
  # OT_KV_LPRG_PROGRAM (PW1024 + DW8 hex; default the sys_face bench program) / OT_KV_LPRG_EPOCH (default 0x0b0b) on the
  # link compiler's calendar and refuse a committed image (= the hardened view's constants) that differs
  mkdir -p $O/lprg_image
  # HKV-DIE2 10-19: the SAME compile as the committed image = kv_static_programme.py --profile component (production link
  # calendar: d2d image die stages + compiled token path; the pre-TXDP '--txd-c 1,1,1,2 --txd-k 1,2,1,1' compile is gone)
  python3 tools/qwen_kv_die/kv_static_programme.py --profile component --out $O/lprg_image/lp \
    ${OT_KV_LPRG_PROGRAM:+--program $OT_KV_LPRG_PROGRAM} --epoch ${OT_KV_LPRG_EPOCH:-0x0b0b} > $O/lprg_image/roots.log
  if cmp -s $O/lprg_image/lp/layer_programme_image.svh rtl/qwen_sys/static_kv_20261014/layer_programme_image.svh; then echo MATCH > $O/lprg_image/verdict
  else echo MISMATCH > $O/lprg_image/verdict; echo "OT_KV_SEQ_STATIC: committed layer image != installed program's (re-run layer_roots_from_link.py, re-harden lprg)"
    [ "${OT_KV_LPRG_ALLOW_MISMATCH:-0}" = 1 ] || exit 5; fi
fi
# v1.4.4 (OT_KV_V144=1, read by kv_die.py; needs OT_KV_V143C=1): PV16 wide pairs in the centre spine (closed r5 leaves placed
# by kv_expand) + the 16 V ports qkd_pv16_vport bound to their closed view (r5, the V issuer)
if [ "${OT_KV_V144:-0}" = 1 ]; then
  VPK=qkd_pv16_vport_r5; [ "${OT_KV_V144_R6:-0}" = 1 ] && VPK=qkd_pv16_vport_r6   # kvs13d: r6 (DQ 0 / RT 8, epoch on the V word)
  VPM=qkd_pv16_vport
  # MU-DIE-KV2 10-19: OT_KV_BOOT_AGES=1 binds the boot-age successor qkd_pv16_vport_b (CLOSED qkd_pv16_vport_b1-b1-cebb296c4)
  [ "${OT_KV_BOOT_AGES:-0}" = 1 ] && { VPK=qkd_pv16_vport_b1; VPM=qkd_pv16_vport_b; }
  VP=physical/ref_tile/${OT_KV_VPORT_KIT:-$VPK}/views/$VPM
  [ -f $VP/$VPM.lef ] || { echo "v1.4.4: no closed V port view at $VP"; exit 4; }
  BV="$BV --view qkd_pv16_vport=$VP"
fi
# HKV-DIE3 10-19 (coordinator: OT_KV_ASTK_EXPAND production, option B; default ON = kv_static_die): the ASTK strip slots
# reserve the actual 328.32-um two-column envelope (case + lint), and kv_expand places the strip's CLOSED leaves
# (ctl_s / ep_s / ex_s / zn / rly_296[_fl] / fault_join / er_owner_st) with the other die-placed frames (--astk-static)
ASTKX=
if [ "${OT_KV_ASTK_EXPAND:-1}" = 1 ] && [ "${OT_KV_STATIC_DIE:-0}" = 1 ]; then H14="$H14 --reserve-native-astk"; V14=$V14,reserve_native_astk; ASTKX=--astk-static; fi
python3 tools/qwen_kv_die/kv_die.py case --kv-wq-mirror --split $H14 --out $O/case_kv > $O/case.log
git rev-parse --short=9 HEAD > $O/case_kv/SOURCE_COMMIT
python3 tools/die_top_lint.py lint --die qwen_kv --variant kv_wq_mirror,split$V14 --out $O/lint > $O/lint.log 2>&1
# v1.2: the relays are REAL RTL generated from the die direction model (one flop a bit, per-bit direction) + its bench
python3 tools/qwen_kv_die/kv_relays.py --stubs $O/lint/qwen_kv_lint_top_stubs.sv --out $O/case_kv/qkd_kv_relays.sv \
  --json $O/relays.json --bench $O/tb_qkd_kv_relays.sv > $O/relays.log
for mu in 0 2; do
  python3 tools/qwen_kv_die/kv_relays.py --stubs $O/lint/qwen_kv_lint_top_stubs.sv --out $O/rly_mut$mu.sv --mut $mu > /dev/null
  iverilog -g2012 -o $O/rly_mut$mu.vvp $O/rly_mut$mu.sv $O/tb_qkd_kv_relays.sv && vvp -n $O/rly_mut$mu.vvp | grep -E 'RELAY_BENCH (PASS|FAIL)' | tail -1 > $O/relays_bench_mut$mu.txt   # Icarus 12 prints '$finish called' last
done
grep -q 'RELAY_BENCH PASS' $O/relays_bench_mut0.txt && grep -q 'RELAY_BENCH FAIL' $O/relays_bench_mut2.txt || { echo "relay bench gate FAILED"; exit 3; }
rm -f $O/rly_mut*.vvp $O/rly_mut*.sv
python3 tools/qwen_die_element_lib.py --stubs $O/lint/qwen_kv_lint_top_stubs.sv --lef $O/case_kv/elements.lef --out $O/libs > $O/libs.log
for c in tt ff ss; do cp physical/asap7_memory_macros_v2_ew/ot_hbm3e_phy/ot_hbm3e_phy_$c.lib $O/libs/ 2>/dev/null || true; done
python3 tools/qwen_kv_die/bind_views.py --split --case $O/case_kv --libs $O/libs \
  --view qkd_cdc_wleaf=physical/ref_tile/qkd_cdc_wleaf_ref/views/qkd_cdc_wleaf \
  --view qkd_kvwq_leaf_s_w129_m=physical/ref_tile/qkd_kvwq_leaf_s_w129_m/views/qkd_kvwq_leaf_s_w129_m \
  --view qkd_kvwq_ctl_bin=physical/ref_tile/qkd_kvwq_ctl_bin/views/qkd_kvwq_ctl_bin $BV \
  --out $O/libs/views.json > $O/bind.log
if [ -n "$D2DSV" ]; then python3 -c "import json,sys; d=json.load(open(sys.argv[1])); sys.exit(0 if 'qkd_d2ds' in d['bound'] else 1)" $O/libs/views.json \
  || { echo "OT_KV_D2DS_VIEW: qkd_d2ds view did not bind (bind.log)"; exit 7; }; echo "OT_KV_D2DS_VIEW: qkd_d2ds bound to $D2DSV"; fi
if [ -n "${HRV:-}" ] && [ -f $HRV/qkd_kvs_hroot.lef ]; then
  if python3 -c "import json,sys; d=json.load(open(sys.argv[1])); sys.exit(0 if 'qkd_kvs_hroot' in d['bound'] else 1)" $O/libs/views.json; then
    echo "OT_KV_HROOT_VIEW: qkd_kvs_hroot bound to $HRV (stand-in)"
  else echo "OT_KV_HROOT_VIEW: qkd_kvs_hroot view did NOT bind (bind.log) -- frame kept"; [ "${OT_KV_HROOT_VIEW:-auto}" = 1 ] && exit 7; fi
fi
# v1.3: DIE-PLACED LEAVES: wires-only parent frames -> their CLOSED leaves at the planned sub-slots, each on its own view
# (OT_KV_EXPAND = comma list of frame masters, default all that kv_expand.py knows; 'none' keeps the frames)
EXP=
if [ "${OT_KV_EXPAND:-all}" != none ]; then
  XO=${OT_KV_EXPAND:-all}; [ -n "$ASTKX" ] && [ "$XO" != all ] && XO=$XO,qkd_astk,qkd_astk_n
  python3 tools/qwen_kv_die/kv_expand.py --run $O $ASTKX $( [ "$XO" = all ] || echo --only $XO ) > $O/expand.log
  EXP="--expanded $O/expand.json"
fi
# KVPLAN 1815 (OT_KV_RST_REGIONAL=1, also read by kv_die.py): every reset / boot fan-out of the flattened die -> a local
# registered tree of closed qkd_rlys_1 stations through free space (kv_rst_regional.py; RUN/rst_regional.json)
if [ "${OT_KV_RST_REGIONAL:-0}" = 1 ]; then
  python3 tools/qwen_kv_die/kv_rst_regional.py --run $O > $O/rst_regional.log 2>&1 || { tail -5 $O/rst_regional.log; exit 6; }
  EXP="--expanded $O/expand.json"
fi
# Q-KVSYS-RLY 2026-10-16 (OT_KV_RLY_STD=1, also read by kv_die.py / kv_pin_repair.py for the frame size): every
# qkd_rly_<W> relay stage -> replicas of the closed relay standards qkd_rlys_1/36/296/528 (declared pads die.v.pads.json)
if [ "${OT_KV_RLY_STD:-0}" = 1 ]; then
  # OT_KV_RLY_STD_NETLIST_ONLY=1: port-bind checks before the standards' views close (never a physical die run)
  python3 tools/qwen_kv_die/kv_rly_std.py --run $O ${OT_KV_RLY_STD_NETLIST_ONLY:+--netlist-only} > $O/rly_std.log
  EXP="--expanded $O/expand.json"
fi
# KV-CLOCK 10-18 (OT_KV_FWD=1, landed-regions standard): every relay run that crosses core clock trees -> a forwarded
# half-cycle lane (hop-0 station on the source root, half-cycle stations, LANDING read on the receiving root);
# RUN/fwd_lanes.json.  OT_KV_FWD_NETLIST_ONLY=1: before the lane kits close (bind checks only, never a physical run)
if [ "${OT_KV_FWD:-0}" = 1 ]; then
  python3 tools/qwen_kv_die/kv_fwd_lanes.py --run $O ${OT_KV_FWD_NETLIST_ONLY:+--netlist-only} > $O/fwd_lanes.log 2>&1 || { tail -5 $O/fwd_lanes.log; exit 7; }
  EXP="--expanded $O/expand.json"
  # KVR-LANDLAG 10-19: every forwarded-clock landed crossing of the laned netlist (qkd_landsh* / qkd_landsh0*) checked
  # against its compiled age, FAIL CLOSED: lane traced on die.v == fwd_lanes.json row, K straps from the landing's own
  # tie cells == (E + cal + h0(n)) mod 8, the strap age inside the ring window, and the latency the hardware delivers
  # (E_hw + 1 + post) == the age the static compiler charges (ceil(landed - 1)) -> case_kv/land_lag.json.
  # OT_KV_LAND_LAG_DIAG=1 (explicit, never default): record, write RUN/LAND_LAG_DIAGNOSTIC and continue (NOT a die result).
  python3 tools/qwen_split/land_lag_sim.py kv-check --die-v $O/case_kv/die.v --lanes $O/fwd_lanes.json \
    $( [ -f $O/case_kv/relay_stages.json ] && echo --relay-stages $O/case_kv/relay_stages.json ) \
    $( [ -f $O/lane_stations.json ] && echo --lane-stations $O/lane_stations.json ) \
    --out $O/case_kv/land_lag.json > $O/land_lag.log 2>&1 || {
    if [ "${OT_KV_LAND_LAG_DIAG:-0}" = 1 ]; then tail -1 $O/land_lag.log > $O/LAND_LAG_DIAGNOSTIC
    else tail -4 $O/land_lag.log; echo "LAND_LAG_KV FAIL: landed crossings vs compiled ages ($O/case_kv/land_lag.json)"; exit 9; fi; }
  tail -1 $O/land_lag.log | cut -c1-400
fi
# v1.4: the host SerDes and the UCIe PHY bind their native ports (tx_up / tx_v / tx_flit / rx_v / rx_flit): SerDes <-> root core phy_*, UCIe <-> qkd_d2d_static fdi_* (583 b)
[ -n "$H14" ] && python3 tools/qwen_kv_die/kv_native_phy.py --case $O/case_kv > $O/native_phy.log \
  && python3 tools/qwen_kv_die/kv_native_phy.py --case $O/case_kv --libs $O/libs >> $O/native_phy.log
python3 tools/qwen_kv_die/kvsys_clocks.py --case $O/case_kv --views $O/libs/views.json --out $O/libs > $O/clocks.log
python3 tools/qwen_kv_die/die_port_bind_kv.py $O/case_kv/die.v --split --relay-rtl $O/case_kv/qkd_kv_relays.sv $EXP --out $O/port_bind.json > $O/port_bind.log
# Q-KVSYS-NETLIST 2026-10-16: the STRICT bit-level bind (die_port_bind v2 on the BINDINGS-bound netlist), recorded
bash tools/qwen_kv_die/kv_port_bind_v2.sh $O/case_kv/die.v $O/port_bind_v2 $O/case_kv/qkd_kv_relays.sv $O/expand.json > $O/port_bind_v2.log 2>&1 || true
# KV-CASE2 10-18: the stub / tie / open-input audit of the strict bind (0da classes, owner lane per gap) lands in the run
# dir every prep (stub_audit.json; the die_top_lint stub lint is $O/lint).  Recorded, never a prep failure.
[ -f $O/port_bind_v2/port_bind_v2.json ] && { python3 tools/qwen_kv_die/kvjg_gap_list.py --bind $O/port_bind_v2/port_bind_v2.json \
  --out $O/stub_audit.json > $O/stub_audit.log 2>&1 || echo "stub audit FAILED (stub_audit.log)" >> $O/stub_audit.log; }
# Q-KV 10-16: over-block capacity from each block's real top layer (post-expand elements.lef) -- the old die-layer-only
# capacity over-counted crossings over M5 tiles (kvs13i fine max 2.26 -> 1.48)
python3 tools/qwen_kv_die/kvsys_window.py --split $H14 --lef $O/case_kv/elements.lef $( [ -f $O/expand.json ] && echo --expand $O/expand.json ) --out $O/window.json > $O/window.log
echo "prep done: $(cat $O/case_kv/SOURCE_COMMIT) $(tail -1 $O/bind.log | head -c 300)"

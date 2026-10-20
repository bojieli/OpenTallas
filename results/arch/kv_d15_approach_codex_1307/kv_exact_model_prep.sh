#!/bin/bash
# qwen-split/kvsys v1.1 (2026-10-14): local prep of one KV/system die chain run, from a CLEAN committed tree.
#   case (kv_die.py plan --kv-wq-mirror --split) -> die_top_lint stubs -> ASSUMED element libs (frames, relays) -> closed
#   real views bound (bind_views.py) -> phi - R compensated die clocks (kvsys_clocks.py) -> NO-STUBS port bind
#   (die_port_bind_kv.py) -> per-bit 2-D window check (kvsys_window.py).  Then rsync OUT to the host and run
#   die_chain.sh kv with OT_STA_CLOCKS=<run>/libs/clocks_{corner}.tcl OT_CORNERS="tt ff ss" (SS = sensitivity only).
# usage: kvsys_prep.sh OUT
set -eu
O=$(readlink -f $1); S=$(cd $(dirname $0)/../../.. && pwd); cd $S
mkdir -p $O/libs
# Q-KV 2026-10-16 18:40: record the OT_KV_* build flags so die_chain.sh re-exports them for the strict bind
# (kv_port_bind_v2.sh / die_port_bind_kv.py re-import kv_die: without the flags they used the non-V144_R6 vport binding
# and reported 256 phantom undriven pvin epoch bits on kvs13h)
env | grep -E '^OT_KV_[A-Z0-9_]*=' | sed -E "s/^([^=]*)=(.*)$/export \1='\2'/" > $O/kv_flags.env
# KV-BIND8 10-20: the generated static tile RTL the die binds (kv_static_die.RTL_FILE for THESE flags) must exist and equal
# the producer's text: d11r bound a stale _mu_ba body (legacy boot/programme/ownership, sha df665451) and d11s selected an
# absent _hs_mu_ba.sv.  Fail closed before any GEN step (regenerate with kv_static_die.py --rtl and commit).
if [ "${OT_KV_STATIC_DIE:-0}" = 1 ]; then
  python3 tools/qwen_kv_die/kv_static_die.py --check > "$O/tile_rtl_check.log" 2>&1 || {
    tail -3 "$O/tile_rtl_check.log"; echo 'KV static tile RTL missing / STALE for the run flags: regenerate (--rtl) and commit'; exit 8; }
fi
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
  # KV-HEALTH 10-19 (OT_KV_RST_HOLD, default 273 = MU release): the health retirement reset contract needs every region
  # held >= 263 edges after a re-assert (source clear + plane depth + skew); qkd_rst_region_pr_h273 (9-bit hold) binds
  # when its CLOSED view audits PASS.  Absent view: HOLD128 _pr stays bound and RUN/RST_HOLD_DIAGNOSTIC marks the run.
  if [ "${OT_KV_RST_HOLD:-273}" = 273 ]; then
    # KV-BIND4 10-19: the native-pin successor qkd_rst_region_pr_h273b (dedicated b launch flop; h273's pin b launched
    # 223.8 > 220 ps) binds first when its CLOSED view audits PASS; h273 stays the fallback.
    HPV=physical/ref_tile/qkd_rst_region_pr_h273b/views/qkd_rst_region_pr_h273b
    HPV2=physical/ref_tile/qkd_rst_region_pr_h273/views/qkd_rst_region_pr_h273
    if python3 tools/qwen_kv_die/check_rst_pin_view.py --view "$HPV" --cell qkd_rst_region_pr_h273b > "$O/rst_hold_view_audit.json" 2>/dev/null; then
      RPV=$HPV; export OT_KV_RST_HOLD_CELL=qkd_rst_region_pr_h273b; echo "OT_KV_RST_HOLD=273: qkd_rst_region -> $HPV"
    elif python3 tools/qwen_kv_die/check_rst_pin_view.py --view "$HPV2" --cell qkd_rst_region_pr_h273 > "$O/rst_hold_view_audit.json" 2>/dev/null; then
      RPV=$HPV2; export OT_KV_RST_HOLD_CELL=qkd_rst_region_pr_h273; echo "OT_KV_RST_HOLD=273: qkd_rst_region -> $HPV2"
    else
      export OT_KV_RST_HOLD=128
      echo "qkd_rst_region_pr_h273b / _h273 views absent / not native PASS: HOLD128 bound, health reset contract (263) UNPROVEN" > "$O/RST_HOLD_DIAGNOSTIC"
      cat "$O/RST_HOLD_DIAGNOSTIC"
    fi
  fi
  export OT_KV_RST_HOLD=${OT_KV_RST_HOLD:-273}
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
   [ "${OT_KV_HROOT:-0}" = 1 ] && [ "${OT_KV_FANFOLD:-0}" = 1 ]; then
  # KV-BIND7 10-20: the k1 kit view is now the CLOSED pin-registered _hl view (qkd_kvs_hroot_k1-k1-da14c0bdf, own-R native
  # PASS spread 42.5/42.0) = the matching view under OT_KV_HROOT_LAND=1 (a same-port stand-in otherwise).  Under
  # OT_KV_HROOT_S32=1 the first CLOSED safe32 view (s32v4 / s32v4b, top qkd_kvs_hroot_safe32 = the _hs tile) binds; until
  # one closes the _hl view is the labelled same-port stand-in.
  HRN=qkd_kvs_hroot; HRV=physical/ref_tile/${OT_KV_HROOT_KIT:-qkd_kvs_hroot_k1}/views/qkd_kvs_hroot; HRWHY="stand-in (same ports)"
  [ "${OT_KV_HROOT_LAND:-0}" = 1 ] && [ "${OT_KV_HROOT_S32:-0}" != 1 ] && HRWHY="matching _hl view (CLOSED da14c0bdf)"
  if [ "${OT_KV_HROOT_S32:-0}" = 1 ]; then
    for k in qkd_kvs_hroot_s32v4 qkd_kvs_hroot_s32v4b; do
      v=physical/ref_tile/$k/views/qkd_kvs_hroot_safe32
      if [ -f $v/qkd_kvs_hroot_safe32.lef ] && [ -f $v/qkd_kvs_hroot_safe32_tt.lib ] && [ -f $v/qkd_kvs_hroot_safe32_ff.lib ]; then
        HRV=$v; HRN=qkd_kvs_hroot_safe32; HRWHY="matching safe32 view ($k CLOSED)"; break; fi
    done
  fi
  if [ -f $HRV/$HRN.lef ] && [ -f ${HRV}/${HRN}_tt.lib ] && [ -f ${HRV}/${HRN}_ff.lib ]; then
    BV="$BV --view qkd_kvs_hroot=$HRV"; echo "OT_KV_HROOT_VIEW: qkd_kvs_hroot -> $HRV ($HRWHY)"
  else echo "OT_KV_HROOT_VIEW: no closed view at $HRV (frame ASSUMED)"; fi
fi
if [ "${OT_KV_V143:-0}" = 1 ]; then H14="$H14 --v143"; V14=$V14,v143
  BV="$BV --view qkd_hgs=physical/ref_tile/qkh_head_gather_stage/views/qkh_head_gather_stage --view qkd_hss=physical/ref_tile/qkh_head_sstage/views/qkh_head_sstage"; fi
# OT_KV_DCAL=1 (Q-KVSYS-DIE 10-16): the link calendar sequencer qkd_d2d_cal_seq_pin on its CLOSED view (kv_die.py DCAL)
# KV-DCAL-MU 10-19: OT_KV_MU=1 binds the MU calendar kit qkd_d2d_cal_seq_pin_mu (ot_qwen_d2d_cal_seq_dies_mu.sv +
# d2d_cal_image_mu.svh, recompiled on the MU pair seam: TXDP lines = d2d_cal_image.svh 0x03030415; C RX / K TX +1 entry,
# SEG2 8 -> 9) once its view is recorded; until then the ep3 view (production image) stays a LABELLED STAND-IN.
if [ "${OT_KV_DCAL:-0}" = 1 ]; then
  DCV=physical/ref_tile/qkd_d2d_cal_seq_pin_ep3/views/qkd_d2d_cal_seq_pin
  if [ "${OT_KV_MU:-0}" = 1 ]; then MDCV=physical/ref_tile/${OT_KV_DCAL_MU_KIT:-qkd_d2d_cal_seq_pin_mu}/views/qkd_d2d_cal_seq_pin
    if [ -f $MDCV/qkd_d2d_cal_seq_pin.lef ] && [ -f $MDCV/qkd_d2d_cal_seq_pin_tt.lib ] && [ -f $MDCV/qkd_d2d_cal_seq_pin_ff.lib ]; then
      DCV=$MDCV; echo "OT_KV_DCAL MU: qkd_dcal -> $MDCV (MU calendar image)"
    else echo "OT_KV_DCAL STAND-IN: no MU view at $MDCV; qkd_dcal bound to qkd_d2d_cal_seq_pin_ep3 (production image)"; fi
  fi
  # KV-DCAL-BOOTCFG 10-19 (OT_KV_DCAL_BC=1, kv_die.DCAL_BC): the dcal slot is qkd_d2d_cal_seq_pin_bc (boot target 11 merged:
  # bcfg_* in, the D2D end's cfg port out); only its OWN view binds (the ep3 / _mu views have no bcfg pins): frame until then
  if [ "${OT_KV_DCAL_BC:-0}" = 1 ]; then BCV=physical/ref_tile/qkd_d2d_cal_seq_pin_bc/views/qkd_d2d_cal_seq_pin_bc; DCV=
    if [ -f $BCV/qkd_d2d_cal_seq_pin_bc.lef ] && [ -f $BCV/qkd_d2d_cal_seq_pin_bc_tt.lib ] && [ -f $BCV/qkd_d2d_cal_seq_pin_bc_ff.lib ]; then
      DCV=$BCV; echo "OT_KV_DCAL_BC: qkd_dcal -> $BCV (boot cfg merged)"
    else echo "OT_KV_DCAL_BC FRAME: no view at $BCV yet; qkd_dcal stays an ASSUMED frame (kit qkd_d2d_cal_seq_pin_bc not closed)"; fi
  fi
  # KV-DCAL 10-19 (OT_KV_DCAL_BC4=1 with OT_KV_DCAL_BC=1, kv_die.DCAL_BC4): the safe K22 successor qkd_d2d_cal_seq_pin_bc4
  # (kit OT_KV_DCAL_BC4_KIT, default qkd_d2d_cal_seq_pin_bc4; PARALLEL fallback qkd_d2d_cal_seq_pin_bc4w); own view only
  if [ "${OT_KV_DCAL_BC:-0}" = 1 ] && [ "${OT_KV_DCAL_BC4:-0}" = 1 ]; then
    B4K=${OT_KV_DCAL_BC4_KIT:-qkd_d2d_cal_seq_pin_bc4}; B4V=physical/ref_tile/$B4K/views/qkd_d2d_cal_seq_pin_bc4; DCV=
    if [ -f $B4V/qkd_d2d_cal_seq_pin_bc4.lef ] && [ -f $B4V/qkd_d2d_cal_seq_pin_bc4_tt.lib ] && [ -f $B4V/qkd_d2d_cal_seq_pin_bc4_ff.lib ]; then
      DCV=$B4V; echo "OT_KV_DCAL_BC4: qkd_dcal -> $B4V (safe K22)"
    else echo "OT_KV_DCAL_BC4 FRAME: no view at $B4V yet; qkd_dcal stays an ASSUMED frame (kit $B4K not closed)"; fi
  fi
  [ -z "$DCV" ] || BV="$BV --view qkd_dcal=$DCV"
fi
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
# KV-FACELAND-WIRE 10-19 (OT_KV_TILE_VIEWS = 1 default on the static kit die | 0): the generated control tiles qkd_kvs_attn /
# _ctl / _emb / _grp(_h) / _pc(_h) bind their CLOSED views (the _fl view when OT_KV_FACE_LAND selects the tile) ONLY when the
# view's tile RTL equals the die's tile file module, its other sources are unchanged, and the face edges it adds (pin
# registers, face-land landed buses) equal what the die schedule charges (kv_tile_views.py, RUN/tile_views.json); every
# other tile stays an ASSUMED frame with its reason.  A tile selected in OT_KV_FACE_LAND with no passing _fl view or no die
# instance (hr_core_queue: inside the qkd_host_rt frame) FAILS the prep (exit 10): the compiler would charge edges no netlist has.
if [ "${OT_KV_TILE_VIEWS:-1}" = 1 ] && [ "${OT_KV_STATIC_DIE:-0}" = 1 ] && [ "${OT_KV_TILE_KITS:-0}" = 1 ]; then
  TVB=$(python3 tools/qwen_kv_die/kv_tile_views.py select --out $O/tile_views.json 2> $O/tile_views.log) || {
    cat $O/tile_views.log; echo "KV_TILE_VIEWS FAIL (tile_views.json)"; exit 10; }
  BV="$BV $TVB"; echo "KV_TILE_VIEWS: bind [$TVB] assumed $(python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['assumed'])" $O/tile_views.json)"
fi
python3 tools/qwen_kv_die/kv_die.py plan --kv-wq-mirror --split $H14 --out $O/case_kv > $O/case.log

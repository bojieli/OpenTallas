# KV-INTEG2 10-18: design point of the KV die every qkd_kvs_* kit is built on = KV-PLAN3 m1 (kvj-g2-env.sh + the m1 placing
# flags + per-stack roots + folded fan) + the ONE kit flag OT_KV_TILE_KITS=1 (tile file qkd_kvs_tiles_hroot_ff_k.sv).
# Sourced by kvs_tile_bench.sh; re-kit with
#   source tools/qwen_kv_die/kvs_kits_env.sh && python3 tools/qwen_kv_die/kvs_tile_kits.py        (ctl / attn / emb)
#   source tools/qwen_kv_die/kvs_kits_env.sh && python3 tools/qwen_kv_die/kvs_tile_kits_rep.py specs  (grp / grp_h / pc / pc_h / hroot)
export OT_KV_PV_CTL_KIT=qkd_pv_ctl_rstpin_a72 OT_KV_HOST_V14=1 OT_KV_HOST_NORTH=1 OT_KV_TREES=1 OT_KV_V143=1 OT_KV_V143C=1 OT_KV_ECTL_H13=1 OT_KV_RLY_STD=1 OT_KV_DCAL=1 OT_KV_HOP=1 OT_KV_V144=1 OT_KV_V144_R6=1 OT_KV_PV_W=82 OT_KV_PV_AGE=96 OT_KV_SERDES_N=1 OT_KV_PV_PINY=1 OT_KV_KVNC=1 OT_KV_SEQ_STATIC=1 OT_KV_REACH=400 OT_KV_RST_REGIONAL=1 OT_KV_PHY_REG=1 OT_KV_REACH_W=36:400,296:370,100000:340 OT_KV_V144_DW=1814.4 OT_KV_V144_RLY_FIRST=krs_,kvn_ OT_KV_PV_T=1 OT_KV_PV_T_CTL_STANDIN=1 OT_KV_REACH_FIX=1 OT_KV_PVT_PINS=1 OT_KV_PVT_HDR_CTL=1 OT_KV_PVFORK_GAP=64.8 OT_KV_PVT_SOFT_SLACK=0 OT_KV_SEAM=1 OT_KV_STATIC_DIE=1
export OT_KV_HROOT=1 OT_KV_FANFOLD=1 OT_KV_V144_DW=2462.4 OT_KV_SN_LIFT=432 OT_KV_CTL_BAND=302.4 OT_KV_PVT_HUB_CLEAR=172.8 OT_KV_KV_CHAN_EXTRA=86.4 OT_KV_V144_RLY_FIRST=pvin_,krs_,kvn_,ap_,aq_,am_
export OT_KV_TILE_KITS=1
# KV-KITS-ATTN 10-18: the KV GEN source claude/qlb-kv-gsrc-1018 (64ce0504d) die chains (kvs14d / kvs14q) add these flags;
# the kit tile file qkd_kvs_tiles_hroot_ff_k.sv is byte-identical with or without them (checked), they are set so the kits
# and the benches see the die chain's design point.
export OT_KV_V144_RLY_FIRST=pvin_,krs_,kvn_,ap_,aq_,am_,ks_acal_,pve_ OT_KV_STATIC_DIE_DIAGNOSTIC=1
export OT_KV_EXPAND=qkd_rhead,qkd_rhead_ft,qkd_ectl,qkd_ctrl,qkd_ctrl_n,qkd_pvfork,qkd_pvtap2,qkd_pvtap3,qkd_pvtap4
export OT_KV_RST_PER_TREE=1 OT_KV_FWD=1 OT_KV_LANDSLOT=1 OT_KV_RST_PIN_REG=1 OT_KV_BUNDLE_EQ=1
# KV-ATTNKIT 10-18: registered kvs_attn boundary (kit qkd_kvs_attn-g1 EARLY_FAIL_SETUP); added edges K.tx_record / ks_prg /
# ks_arh +1 each (kv_static_die.ATTN_LAND_EDGES) -> the die design point adopts it with that pricing (KV-PLAN5).
export OT_KV_ATTN_LAND=1

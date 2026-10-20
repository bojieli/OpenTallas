#!/bin/bash
set -u
O=/srv/opentallas-scratch/claude/qw-gen3-takeover3-currentbind
S=/srv/opentallas-scratch/claude/mu-die-qw/dv2f19g2/src
D=/srv/opentallas-scratch/claude/mu-die-qw/dv2f19g2/out/case/die.v
python3 "$O/tools/die_port_bind.py" "$D" \
 --rtl-root "$S/rtl" \
 --rtl-file /srv/opentallas-scratch/claude/mu-die-qw/dv2f19g2/chain/port_bind/die_glue.sv \
 --rtl-file "$S/rtl/qwen_split/qfd_link_slots.sv" \
 --rtl-file "$S/rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_dies.sv" \
 --rtl-file "$S/physical/qwen_kv_die_phy/ot_qkvd_ucie_x64_phy/ot_qkvd_ucie_x64_phy_model.sv" \
 --rtl-file "$S/physical/qwen_missing_phy/tp8_1013/ot_qfd_ucie_x64_phy/ot_qfd_ucie_x64_phy_bb.v" \
 --rtl-file "$S/physical/qwen_missing_phy/ot_qfd_serdes_112g_x12_phy_s597/ot_qfd_serdes_112g_x12_phy_s597_bb.v" \
 --allow-model qfd_ckbump --allow-model qfd_sigbump --allow-model ot_qkvd_ucie_x64_phy --allow-model ot_qkvd_ucie_x64_phy_model \
 --allow-model ot_qfd_ucie_x64_phy --allow-model ot_qfd_serdes_112g_x12_phy_s597 \
 --lib-root "$S/physical/asap7_memory_macros" --define OT_QFD_UP4_CK_ENTRIES --ref-tile-prefer \
 --strap-file "$S/results/arch/qwen_split_compute_1014/q_slice_1017/straps_dv2f18mu.json" \
 --out "$O/result.json" > "$O/bind.log" 2>&1
rc=$?; printf '%s\n' "$rc" > "$O/result.rc"; exit "$rc"

#!/bin/bash
# Q-DIEPLAN6 10-17: strict die_port_bind v2 of the Qwen compute die dv2f9 full GEN (plan dv2f9-qdieplan6) on the run's
# own src tree (rtl/ incl. the slice face masters, qfd_native59_dv_service, qfd_tt_ctlm_dv, sys_face G8, the rr1
# embedding provider) + generated die relays + PHY models; chain-end ties = straps_dv2f8.json (rule c).
# Usage (src root): bash results/arch/qwen_split_compute_1014/q_dieplan6_1017/run_bind.sh DIE_V OUT_DIR
set -euo pipefail
DIE=$1; OUT=$2; mkdir -p "$OUT"
D=results/arch/qwen_split_compute_1014
P=physical/qwen_missing_phy/nface_tall_1017
python3 tools/qwen_split/gen_relay_rtl.py "$DIE" "$OUT/relays.sv" > "$OUT/relays.json"
python3 tools/die_port_bind.py "$DIE" --top qfd_die --strap-file $D/q_slice_1017/straps_dv2f8.json --rtl-file "$OUT/relays.sv" \
  --rtl-file physical/qwen_kv_die_phy/ot_qkvd_ucie_x64_phy/ot_qkvd_ucie_x64_phy_bb.v \
  --rtl-file $P/ot_qfd_serdes_112g_x12_phy_s597/ot_qfd_serdes_112g_x12_phy_s597_bb.v \
  --rtl-file $P/ot_qfd_ucie_x64_phy/ot_qfd_ucie_x64_phy_bb.v \
  --allow-model ot_qfd_serdes_112g_x12_phy_s597 --allow-model ot_qfd_ucie_x64_phy --allow-model ot_qkvd_ucie_x64_phy \
  --out "$OUT/port_bind.json" | tee "$OUT/port_bind.txt"

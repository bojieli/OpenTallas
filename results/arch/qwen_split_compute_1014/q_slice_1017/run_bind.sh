#!/bin/bash
# Q-BIND 10-17: strict die_port_bind v2 of the Qwen compute die dv2f7 full GEN (plan dv2f7-diag-r3-ad3209c7f,
# die.v sha256 f19ae6433b1fbc0f..., 926 instances) on this branch's rtl/ (c1r8 ROM-leaf parents + qfd_c_b16_dv vendored)
# + generated die relays + PHY models + the slice RTL (claude/qdv-slice-1016 35bf465bf rtl/qwen_dv/*.sv in $EXT).
# Usage (repo root): bash results/arch/qwen_split_compute_1014/q_bind_1017/run_bind.sh DIE_V EXT OUT_DIR
set -euo pipefail
DIE=$1; EXT=$2; OUT=$3; mkdir -p "$OUT"
D=results/arch/qwen_split_compute_1014/q_bind_1017
P=physical/qwen_missing_phy/nface_tall_1017
python3 tools/qwen_split/gen_relay_rtl.py "$DIE" "$OUT/relays.sv"
args=(); for f in "$EXT"/qfd_dv_*.sv; do args+=(--rtl-file "$f"); done
python3 tools/die_port_bind.py "$DIE" --top qfd_die --strap-file $D/../q_slice_1017/straps_dv2f8.json --rtl-file "$OUT/relays.sv" \
  --rtl-file "$EXT/ot_qkvd_ucie_x64_phy_bb.v" \
  --rtl-file $P/ot_qfd_serdes_112g_x12_phy_s597/ot_qfd_serdes_112g_x12_phy_s597_bb.v \
  --rtl-file $P/ot_qfd_ucie_x64_phy/ot_qfd_ucie_x64_phy_bb.v "${args[@]}" \
  --allow-model ot_qfd_serdes_112g_x12_phy_s597 --allow-model ot_qfd_ucie_x64_phy --allow-model ot_qkvd_ucie_x64_phy \
  --out "$OUT/port_bind.json" | tee "$OUT/port_bind.txt"

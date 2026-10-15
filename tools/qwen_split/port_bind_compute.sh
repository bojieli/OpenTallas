#!/bin/bash
# Owner no-stub gate for the Qwen split COMPUTE die: port-bind DIE_V against real RTL (compute-die lead r3, 2026-10-14).
# usage: tools/qwen_split/port_bind_compute.sh DIE_V OUTDIR     (exit 0 only when the die binds)
#   1. die relays / reset repeaters / the clock receiver of THIS build -> generated RTL (gen_relay_rtl.py)
#   2. tools/die_port_bind.py with the compute-die RTL (rtl/ tree + the link / clock / reset slots), the hard-macro
#      models allowed as such (UCIe PHY, forwarded-clock bump), the contract straps (straps.json)
set -u
D=$(readlink -f "$1"); O=$(mkdir -p "$2" && readlink -f "$2")
R=$(cd "$(dirname "$0")/../.." && pwd)
python3 $R/tools/qwen_split/gen_relay_rtl.py $D $O/die_glue.sv > $O/die_glue.json || exit 3
python3 $R/tools/die_port_bind.py $D --rtl-file $O/die_glue.sv --rtl-file $R/rtl/qwen_split/qfd_link_slots.sv --rtl-file $R/rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_dies.sv \
  --rtl-file $R/physical/qwen_kv_die_phy/ot_qkvd_ucie_x64_phy/ot_qkvd_ucie_x64_phy_model.sv \
  --rtl-file $R/physical/qwen_missing_phy/tp8_1013/ot_qfd_ucie_x64_phy/ot_qfd_ucie_x64_phy_bb.v \
  --rtl-file $R/physical/qwen_missing_phy/ot_qfd_serdes_112g_x12_phy_s597/ot_qfd_serdes_112g_x12_phy_s597_bb.v \
  --allow-model qfd_ckbump --allow-model qfd_sigbump --allow-model ot_qkvd_ucie_x64_phy --allow-model ot_qkvd_ucie_x64_phy_model \
  --allow-model ot_qfd_ucie_x64_phy --allow-model ot_qfd_serdes_112g_x12_phy_s597 \
  --define OT_QFD_UP4_CK_ENTRIES --strap-file $R/results/arch/qwen_split_compute_1014/straps.json --out $O/port_bind.json > $O/port_bind.txt 2>&1
rc=$?
tail -1 $O/port_bind.txt
exit $rc

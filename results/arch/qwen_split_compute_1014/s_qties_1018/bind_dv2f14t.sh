#!/bin/bash
S=/srv/opentallas-scratch/claude/qwen-split-compute/dv2f14t; cd $S/src
echo '{"straps": []}' > $S/no_straps.json
V=$S/out/case/die.v
OT_PORT_BIND_STRAPS=$S/src/results/arch/qwen_split_compute_1014/q_slice_1017/straps_dv2f8.json bash tools/qwen_split/port_bind_compute.sh $V $S/pb_manifest; echo "pb_manifest rc=$?"
OT_PORT_BIND_STRAPS=$S/no_straps.json bash tools/qwen_split/port_bind_compute.sh $V $S/pb_nostraps; echo "pb_nostraps rc=$?"
# RTL-internal tie scan over every die master's closure (same RTL args as port_bind_compute.sh)
MS=$(grep -oE '^  [A-Za-z_][A-Za-z0-9_]* [A-Za-z_][A-Za-z0-9_\\]*' $V | awk '{print $1}' | sort -u | grep -v '^module$' | sed 's/^/--closure /' | tr '\n' ' ')
R=$S/src; O=$S/pb_nostraps
python3 tools/die_port_bind.py $V --rtl-file $O/die_glue.sv --rtl-file $R/rtl/qwen_split/qfd_link_slots.sv --rtl-file $R/rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_dies.sv \
  --rtl-file $R/physical/qwen_kv_die_phy/ot_qkvd_ucie_x64_phy/ot_qkvd_ucie_x64_phy_model.sv \
  --rtl-file $R/physical/qwen_missing_phy/tp8_1013/ot_qfd_ucie_x64_phy/ot_qfd_ucie_x64_phy_bb.v \
  --rtl-file $R/physical/qwen_missing_phy/ot_qfd_serdes_112g_x12_phy_s597/ot_qfd_serdes_112g_x12_phy_s597_bb.v \
  --lib-root $R/physical/asap7_memory_macros --define OT_QFD_UP4_CK_ENTRIES $MS > $S/closure_files.txt 2> $S/closure.err
python3 tools/qwen_split/rtl_tie_scan.py $S/closure_files.txt $R --out $S/rtl_internal_ties.json; echo "tie_scan rc=$?"

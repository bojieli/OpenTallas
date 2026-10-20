#!/bin/bash
# KV-FUNC-OPENS 10-19: re-run ONLY the strict die_port_bind step of the GEN7 strict run (kv-exact-padgap-1019/gen7_strict,
# die SHA 7006cbd0) with the exact same RTL/strap/model inputs, using the binder + KV tools of THIS branch (TOOLS dir)
# over the GEN7 source tree (R), and a caller-supplied pad file (the GEN7 output_pads.pv.json, optionally augmented by
# this lane's provers). Never writes into the original run dir.
# usage: rebind.sh TOOLS_ROOT PAD_JSON OUTDIR
set -eu
T=$(readlink -f "$1"); PADS=$(readlink -f "$2"); O=$(mkdir -p "$3" && readlink -f "$3")
G=/srv/opentallas-scratch/claude/kv-exact-padgap-1019/gen7_strict
R=/srv/opentallas-scratch/claude/qwen-kvsys/wt-kvs14r-4db097403-codexmub
# run root: this branch's tools over the GEN7 source rtl/physical (symlinks, read-only use)
X=$O/root; mkdir -p $X; for d in rtl physical; do [ -e $X/$d ] || ln -s $R/$d $X/$d; done
rm -rf $X/tools; cp -r $T/tools $X/tools
cd $X
python3 $X/tools/die_port_bind.py $G/die_bound.v --rtl-root rtl \
  --prefer rtl/hdc/ot_hdc_fp32_add_lat.sv --prefer rtl/hdc/ot_hdc_fp32_mul_lat.sv \
  --prefer physical/qwen_kv_die_phy/ot_qkvd_ucie_x64_phy/ot_qkvd_ucie_x64_phy_bb.v \
  --prefer physical/qwen_missing_phy/ot_qfd_serdes_112g_x12_phy/ot_qfd_serdes_112g_x12_phy_bb.v \
  --lib-root physical/qkd_astk_strip/macros \
  --rtl-file $R/physical/qwen_kv_die_phy/ot_qkvd_ucie_x64_phy/ot_qkvd_ucie_x64_phy_bb.v \
  --rtl-file /srv/opentallas-scratch/claude/qwen-kvsys/kvs14r-4db097403-codexmub/case_kv/qkd_kv_relays.sv \
  --rtl-file $R/rtl/qwen_sys/kv_rly_std_20261016/qkd_rlys.sv \
  --rtl-file $R/rtl/qwen_sys/kv_fwd_lane_20261018/qkd_rlysh.sv --rtl-file $R/rtl/qwen_split/qfd_fwd_lane.sv --rtl-file $R/rtl/hdc/ot_hdc_cg.sv \
  --rtl-file $R/rtl/qwen_sys/static_kv_die_20261017/qkd_kvs_tiles_hroot_ff_k_mu_ba.sv \
  --rtl-file $G/kv_hard_models.sv --rtl-file $G/kv_relays_dir.sv \
  --rtl-file $R/physical/qwen_missing_phy/ot_qfd_serdes_112g_x12_phy/ot_qfd_serdes_112g_x12_phy_bb.v \
  --allow-model qkd_hbm3e_phy_pc --allow-model qkd_ckbump --allow-model qkd_fwdbump --allow-model ot_qkvd_ucie_x64_phy \
  --allow-model ot_qkvd_ucie_x64_phy_model \
  --allow-model ot_qfd_serdes_112g_x12_phy --allow-model qkd_pll_analog_model \
  --strap-file $G/straps.json --pad-file $PADS --out $O/port_bind_v2.json > $O/port_bind_v2.txt 2>&1 && rc=0 || rc=$?
tail -1 $O/port_bind_v2.txt
exit $rc

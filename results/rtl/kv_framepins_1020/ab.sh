#!/bin/bash
# KV-FRAMEPINS bind A/B: die_port_bind v2 on the KV-BIND3 bound gen9d netlist (bind_try4).
#  a = HOST master qkd_host_root_admission_obs (KV-BIND5 state)      b = OBSX: master _obsx + the 3 OBSX die buses
#  (the b buses are direct nets dcal/d2d_kv -> host; in the die they are kv_oneway relayed buses whose relay stations bind
#   as qkd_rlys_* separately -- connectivity of producer pin -> reader pin is identical)
set -u
D=/srv/opentallas-scratch/claude/kv-framepins-1019; S=$D/src; B=/srv/opentallas-scratch/claude/kv-bind3-1019; T=$B/bind_try4
F=$(python3 -c "
import json;d=json.load(open('$B/pass2_fixed.json'))
print(' '.join('--rtl-file '+f for f in d['rtl_files']))")
for V in a b; do
  O=$D/ab_$V; mkdir -p $O
  if [ $V = a ]; then
    sed "s/^  qkd_host_root_admission #(/  qkd_host_root_admission_obs #(/" $T/die_bound.v > $O/die_bound.v
  else
    python3 $D/patch_b.py $T/die_bound.v $O/die_bound.v || exit 3
  fi
  cd $S && python3 tools/die_port_bind.py $O/die_bound.v --rtl-root rtl \
    --prefer rtl/hdc/ot_hdc_fp32_add_lat.sv --prefer rtl/hdc/ot_hdc_fp32_mul_lat.sv \
    --prefer physical/qwen_kv_die_phy/ot_qkvd_ucie_x64_phy/ot_qkvd_ucie_x64_phy_bb.v \
    --prefer physical/qwen_missing_phy/ot_qfd_serdes_112g_x12_phy/ot_qfd_serdes_112g_x12_phy_bb.v \
    --lib-root physical/qkd_astk_strip/macros $F \
    --allow-model qkd_hbm3e_phy_pc --allow-model qkd_ckbump --allow-model qkd_fwdbump --allow-model ot_qkvd_ucie_x64_phy \
    --allow-model ot_qkvd_ucie_x64_phy_model --allow-model ot_qfd_serdes_112g_x12_phy --allow-model qkd_pll_analog_model \
    --strap-file $T/straps.json --out $O/port_bind_v2.json > $O/port_bind_v2.txt 2>&1
  echo "$V rc=$?"
  python3 $D/summ.py $V $O/port_bind_v2.json | tee $O/summary.txt
done

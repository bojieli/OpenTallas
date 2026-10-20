#!/bin/bash
# g2_bench.sh OUT [MUT=0] (KV-AHUB3 10-19, from tools/qwen_kv_die/ahub_safe/bench.sh): the LANDED-REGION hub qkd_ahub_static_dw_g2_lp
# (lp.py, 5 regions, 8 landings) on the HKV-DIE3 calendars with HUB_RECIP / HUB_PUB +6 (tb_qkd_ahub_static_dw_g2); MUT 13..16 expect FAIL too.
# FLAT=1 (env): the fallback flat parent with ZW_RLY = ZR_RLY = 3 relays (kit qkd_ahub_g2c); MUT 14 there = ZR_RLY 2.
# Original header: the KV die hub element qkd_ahub_static_dw at the die's binding
# Z_IN_STRIDE 4 AND the die's actual AP_OFS / FR_OFS (HKV-DIE3 OT_KV_AHUB_OFS) on the HKV-DIE3 production calendars,
# lockstep with the sealed hub at stride 4 (tb_qkd_ahub_static_dw_safe).  MUT 0 expects PASS; 1..10 expect FAIL (8 = a4 offsets) (5 = DUT at stride 16; 6 / 7 = slot_h / slot_k decode
# shifted by one: sed on a COPY of the DUT RTL under OUT, the repository file is untouched).  Fleet only (ot-run).
set -u
O=$1; M=${2:-0}
mkdir -p "$O"
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
DW=rtl/hdc/nearhbm/qkd_ahub_static_dw_safe.sv
if [ "$M" = 6 ] || [ "$M" = 7 ]; then
  cp "$DW" "$O/qkd_ahub_static_dw_m$M.sv"
  if [ "$M" = 6 ]; then
    old='slot_h[2*s+:2]=2'"'"'(dz[s][16:0]%Z_IN_STRIDE);'; new='slot_h[2*s+:2]=2'"'"'(dz[s][16:0]%Z_IN_STRIDE+1);'
  else
    old='slot_k[4*s+:4]=4'"'"'(dz[s][16:0]/Z_IN_STRIDE);'; new='slot_k[4*s+:4]=4'"'"'(dz[s][16:0]/Z_IN_STRIDE+1);'
  fi
  python3 - "$O/qkd_ahub_static_dw_m$M.sv" "$old" "$new" <<'PY' || { echo "AHUB_DW MUTANT NOT APPLIED mut=$M"; exit 1; }
import sys
p, o, n = sys.argv[1:4]
s = open(p).read()
if s.count(o) != 1:
    sys.exit(1)
open(p, 'w').write(s.replace(o, n))
PY
  DW="$O/qkd_ahub_static_dw_m$M.sv"
fi
SRC="rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fp32_add_lat.sv
rtl/hdc/ot_hdc_fp32_add_lat_nr.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_delay.sv
rtl/hdc/nearhbm/ot_qwen_nearhbm_sfu_p.sv rtl/lib/ot_rst_relay.sv rtl/lib/ot_rst_pipe.sv
rtl/hdc/nearhbm/ot_qkd_ahub_static_cal_gen.sv rtl/hdc/nearhbm/ot_qkd_ahub_core.sv rtl/hdc/nearhbm/ot_nhb_tiles.sv
rtl/hdc/nearhbm/ot_qkh_recip_leaf.sv rtl/hdc/nearhbm/ot_qwen_nearhbm_attn_hub_p.sv $DW
rtl/qwen_sys/split_20261014/qkd_attn_service_root.sv rtl/qwen_sys/split_20261014/qkd_pv_fin_s.sv
rtl/hdc/nearhbm/qkd_ahub_static_dw_g2.sv rtl/hdc/nearhbm/lp/qkd_ahub_static_dw_g2_lp.sv
rtl/common/landed_parent/ot_pl_land.sv rtl/common/landed_parent/ot_pl_land_field_copies.sv rtl/common/landed_parent/ot_pl_land_reset_forest.sv
rtl/test/qwen_kv_die/tb_qkd_ahub_static_dw_g2.sv"
sha256sum $SRC "$0" > "$O/source_m$M.sha256"
"$VL" --version
$VL --binary --timing -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -Wno-WIDTH --build-jobs 4 \
  --top-module tb_qkd_ahub_static_dw_g2 -GMUT=$M -GFLAT=${FLAT:-0} --Mdir "$O/obj_m$M" $SRC > "$O/build_m$M.log" 2>&1 \
  || { echo "AHUB_DW FAIL build"; grep -m8 '%Error' "$O/build_m$M.log"; exit 1; }
"$O/obj_m$M/Vtb_qkd_ahub_static_dw_g2" > "$O/run_m$M.log" 2>&1
grep -E '^AHUB_DW FAIL mut=[0-9]+ first' "$O/run_m$M.log" | head -2
line=$(grep -E '^AHUB_DW (PASS|FAIL mut=[0-9]+ errors)' "$O/run_m$M.log" | tail -1)
echo "${line:-AHUB_DW FAIL no verdict line}"
case "$line" in "AHUB_DW PASS"*) exit 0;; *) exit 1;; esac

#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
out="${1:?output directory}"
mkdir -p "$out"
variant="${WB_PIPELINE:-0}"
sources=(ot_hgi_dma_back_static.sv ot_hgi_b2_swap_disp_static.sv ot_hgi_b2_swap_grp_static.sv ot_hgi_b2_swap_wb_grp_static.sv ot_vms_bank_static.sv ot_hbm_svc_wb_block_cdc.sv ot_hbm_svc_wb_pipeline_cdc.sv ot_hbm_svc_phy_mux.sv ot_reset_sync.sv ot_async_fifo.sv ot_hbm_accel_cdc_fifo.sv ot_sram_1r1w_128x256_m1_r2c2.v ot_sram_1r1w_1024x256_m2_r2c2.v ot_hdc_v41x_idx_hbm.sv ot_hdc_hbm_model.sv ot_chip_v41x_hbm3e_phy.sv tb_dma_wb_phy_static.sv)
# A co-located source snapshot is used by remote gates. In a checkout,
# SERVICE_RTL may point to the service owner snapshot before serial collection.
if [[ ! -f ot_chip_v41x_hbm3e_phy.sv ]]; then
 repo="$(git rev-parse --show-toplevel)"
 service="${SERVICE_RTL:-$repo/rtl/hbm_accel/loader/service_native}"
 for i in "${!sources[@]}"; do
  name="${sources[i]}"
  if [[ -f "$name" ]]; then continue; fi
  if [[ -f "$service/$name" ]]; then sources[i]="$service/$name"; continue; fi
  path="$(rg --files "$repo/rtl" | awk -v n="$name" '$0 ~ ("/" n "$") && $0 !~ /\/pinned\// {print; exit}')"
  [[ -n "$path" ]] || { echo "missing dependency $name" >&2; exit 1; }
  sources[i]="$path"
 done
fi
for mut in 0 1;do
 /usr/bin/time -v -o "$out/build-$mut.time" verilator --binary --timing -j 4 -Wno-fatal --top-module tb_dma_wb_phy_static -GMUT="$mut" -GWB_PIPELINE="$variant" --Mdir "$out/obj-$mut" -o gate "${sources[@]}" > "$out/build-$mut.log" 2>&1
 set +e
 /usr/bin/time -v -o "$out/sim-$mut.time" "$out/obj-$mut/gate" > "$out/sim-$mut.log" 2>&1
 rc=$?
 set -e
 cat "$out/sim-$mut.log"
 if [ "$mut" -eq 0 ];then test "$rc" -eq 0;grep -q 'DMA_WB_PHY_FUNCTIONAL PASS' "$out/sim-$mut.log";else test "$rc" -ne 0;grep -q 'fence before actual HBM drain ACK' "$out/sim-$mut.log";fi
done
printf 'PASS full DMA-WB-PHY functional gate and premature posted-completion mutant; throughput verdict reported separately\n'

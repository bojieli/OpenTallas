#!/bin/bash
set -euo pipefail
mkdir -p price
for top in ot_s81sl_xr1 ot_s81sl_rstop; do
 for mode in baseline pair; do
  src=(--source rtl/lib/ot_rst_relay.sv)
  if [ "$mode" = pair ]; then src+=(--source tools/s81_rd_pair_size/selected.sv); else src+=(--source rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xr.sv --source rtl/dsrom_sys/s81_dv/slice/ot_s81sl_rstop.sv); fi
  python3 tools/run_abi3_physical.py --view asap7 --top "$top" "${src[@]}" --clock-period-ns 0.833333 --stages synth --synth-timeout-seconds unlimited --keep-workdir "price/${top}_${mode}" --output "price/${top}_${mode}.json" > "price/${top}_${mode}.log" 2>&1
  echo "SIZE_DONE $top $mode"
 done
done

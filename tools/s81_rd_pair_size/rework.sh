#!/bin/bash
set -euo pipefail
for top in ot_s81sl_xr1 ot_s81sl_rstop; do
 python3 tools/run_abi3_physical.py --view asap7 --top "$top" --source rtl/lib/ot_rst_relay.sv --source tools/s81_rd_pair_size/selected.sv --clock-period-ns 0.833333 --stages synth --synth-timeout-seconds unlimited --keep-workdir "price/${top}_loop" --output "price/${top}_loop.json" > "price/${top}_loop.log" 2>&1
 echo "SIZE_DONE $top loop"
done
python3 tools/s81_rd_pair_size/audit.py

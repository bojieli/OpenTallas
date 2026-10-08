#!/bin/bash
# route_cl.sh <label> (TT-VIEWS 2026-10-07): closure-loop TC re-route of the fused-head hardened SRAM lane
# ot_hdc_v41_fh_sram_lane_hardened (run.sh recipe unchanged; the view's route dir was deleted on every host) + the view
# export at SS/FF/TT (tools/w18/export_view.py, boundary.sdc, the SRAM macro's own _tt.lib) -> $W/view.  env OUT.
lab=$1; W=${OUT:?}/$lab; mkdir -p $W
M=physical/asap7_memory_macros/ot_sram_1r1w_512x128_m4_r2c2
OT_FH_ROUTE_TAG=lane_$lab bash physical/dsrom_fh_hardened_lane/run.sh $W > $W/run.log 2>&1
echo "rc=$?" > $W/exit
python3 tools/w18/corner_sta.py --macro $M --orfs-dir $W/work/orfs --post-sdc physical/dsrom_fh_hardened_lane/boundary.sdc --output $W/corner_sta.json > $W/corner.log 2>&1
echo "corner_rc=$?" >> $W/exit
python3 tools/w18/export_view.py --orfs-dir $W/work/orfs --name ot_hdc_v41_fh_sram_lane_hardened --post-sdc physical/dsrom_fh_hardened_lane/boundary.sdc \
  --macro $M --corners ss,ff,tt --out $W/view > $W/export.log 2>&1
echo "export_rc=$?" >> $W/exit

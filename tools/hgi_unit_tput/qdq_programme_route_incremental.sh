#!/bin/bash
# Continue retained actual CTS in a separate work copy. Original CTS baseline stays immutable.
set -euo pipefail
R=$1
SRC=$R/src
OUT=$R/native_route
mkdir -p "$OUT"
test ! -e "$OUT/work"
mkdir "$OUT/work"
cp -a "$R/routes/gate/work/orfs" "$OUT/work/orfs"
C=$OUT/work/orfs
export OT_CTS_MACRO_CLUSTER=
docker run --rm -e LEC_CHECK=0 -e OT_CTS_MACRO_CLUSTER -v "$SRC:/src:ro" -v "$C:/work" -w /OpenROAD-flow-scripts/flow openroad/orfs:latest bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; python3 /src/tools/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts >/dev/null && make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base finish' > "$OUT/flow.log" 2>&1
printf 'flow_rc=0\n' > "$OUT/status"
cd "$SRC"
python3 tools/w18/corner_sta_ref.py --orfs-dir "$C" --extra-sdc "$SRC/physical/ref_tile/hgi_qdq_program_sw125/signoff.sdc" --macro physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2 --output "$OUT/corner_sta.json" > "$OUT/sta.log" 2>&1
printf 'corner_rc=0\n' >> "$OUT/status"

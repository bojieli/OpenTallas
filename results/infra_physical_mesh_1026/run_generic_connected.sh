#!/bin/bash
set -eu
D=$(cd "$(dirname "$0")" && pwd);OR=/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad
python3 "$D/prepare_straps.py"
run() { docker run --rm -v "$D:/work" openroad/orfs:latest "$OR" "$@"; }
run -exit /work/build_straps.tcl > "$D/build_straps.log" 2>&1
run -python -exit /work/infra_mesh_connect.py --source /work/mesh_straps.odb --out /work/mesh_connected_tool.odb > "$D/generic_connect.log" 2>&1
run -python -exit /work/infra_clock_route.py --source /work/mesh_connected_tool.odb --sdc /work/mesh_straps.sdc --nets /work/all_nets.txt --preconnected /work/preconnected.txt --liberty "/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_*_RVT_TT_nldm_*.lib*" --out /work/shared_connected_r1 --signal-layers M1-M7 --clock-layers M1-M7 > "$D/shared_connected_r1.log" 2>&1

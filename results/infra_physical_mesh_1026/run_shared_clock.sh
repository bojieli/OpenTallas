#!/bin/bash
set -eu
D=$(cd "$(dirname "$0")" && pwd)
docker run --rm -v "$D:/work" openroad/orfs:latest /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -python -exit /work/infra_clock_route.py --source /work/mesh_before.odb --sdc /work/mesh.sdc --nets /work/all_nets.txt --preconnected /work/preconnected.txt --liberty "/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_*_RVT_TT_nldm_*.lib*" --out /work/shared_r1 --signal-layers M1-M7 --clock-layers M1-M7 > "$D/shared_r1.log" 2>&1

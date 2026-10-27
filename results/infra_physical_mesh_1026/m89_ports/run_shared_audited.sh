#!/bin/bash
set -eu
D=$(cd "$(dirname "$0")" && pwd)
docker run --rm -v "$D:/work" openroad/orfs:latest /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -python -exit /work/infra_clock_route.py --source /work/mesh_connected_sharedfit.odb --sdc /work/mesh.sdc --nets /work/all_nets.txt --preconnected /work/preconnected.txt --clock-nets /work/clock_nets.txt --access-regions /work/access_regions.json --liberty "/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_*_RVT_TT_nldm_*.lib*" --out /work/shared_audited_r1 > "$D/shared_audited_r1.log" 2>&1

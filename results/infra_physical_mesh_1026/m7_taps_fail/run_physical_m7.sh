#!/bin/bash
set -eu
D=$(cd "$(dirname "$0")" && pwd)
OR=/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad
docker run --rm -v "$D:/work" openroad/orfs:latest "$OR" -python -exit /work/infra_mesh_connect.py --source /work/mesh_straps.odb --out /work/mesh_connected_shared.odb --mesh ck_mesh --width-um 0.16 > "$D/connect_shared.log" 2>&1
docker run --rm -v "$D:/work" openroad/orfs:latest "$OR" -python -exit /work/infra_clock_route.py --source /work/mesh_connected_shared.odb --sdc /work/mesh.sdc --nets /work/all_nets.txt --preconnected /work/preconnected.txt --clock-nets /work/clock_nets.txt --access-regions /work/access_regions.json --liberty "/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_*_RVT_TT_nldm_*.lib*" --out /work/shared_audited_r1 > "$D/shared_audited_r1.log" 2>&1

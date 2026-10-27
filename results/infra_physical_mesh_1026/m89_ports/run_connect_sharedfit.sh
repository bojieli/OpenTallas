#!/bin/bash
set -eu
D=$(cd "$(dirname "$0")" && pwd)
docker run --rm -v "$D:/work" openroad/orfs:latest /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -python -exit /work/infra_mesh_connect.py --source /work/mesh_straps.odb --out /work/mesh_connected_sharedfit.odb --mesh ck_mesh --width-um 0.16 > "$D/connect_sharedfit.log" 2>&1

#!/bin/bash
set -euo pipefail
route="$1"
find "$route/work/orfs/results" -name 6_final.odb -exec sha256sum {} \; > odb.sha256
find "$route" -maxdepth 5 -name '*.lef' -type f -exec sha256sum {} \; > lef.sha256
docker image inspect openroad/orfs:asap7lock --format '{{.Id}} {{json .RepoDigests}}' > image.txt
docker run --rm -v "$PWD:/audit" -v "$route:/route:ro" --entrypoint /bin/bash openroad/orfs:asap7lock -lc '/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -exit /audit/audit.tcl'

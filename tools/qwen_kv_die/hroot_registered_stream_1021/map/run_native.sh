#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
image='openroad/orfs@sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29'
printf '%s\n' "$image" > tool_image.txt
docker run --rm --user "$(id -u):$(id -g)" -v "$PWD:/work" -w /work "$image" bash map.sh > map_docker.log 2>&1
sha=$(sha256sum original.v | cut -d' ' -f1)
python3 engine_native32.py --netlist original.v --parser textbook_lint.py --sha256 "$sha" --top qkd_host_native_engine_n32 --out qkd_host_native_engine_n32.sv > generate.log
python3 bind_copy_inputs.py --source qkd_host_native_engine_n32.sv --record qkd_host_native_engine_n32.json --out proof_only_bound.v > bind.log
python3 engine_copy_certificate.py --original original.v --mapped proof_only_bound.v --parser textbook_lint.py --record qkd_host_native_engine_n32.json --out copy_certificate.json > copy_certificate.log
python3 audit_physical_copy_cones.py --mapped proof_only_bound.v --record qkd_host_native_engine_n32.json --parser textbook_lint.py --out copy_cones.json > copy_cones.log
args=(python3 native_census.py --netlist qkd_host_native_engine_n32.sv --top qkd_host_native_engine_n32 --out native_raw.json)
for f in libs/*.lib;do args+=(--liberty "$f");done
"${args[@]}" > native_raw.log 2>&1
printf '%s\n' SOURCE_MAPPING_COPY_CERTIFICATE_CONES_AND_RAW_CENSUS_DONE

#!/bin/bash
set -euo pipefail
src=$PWD
out=$(realpath -m "${1:?OUT}")
mkdir -p "$out"
docker run --rm --user "$(id -u):$(id -g)" -v "$src:/src:ro" -v "$out:/out" -w /src openroad/orfs:asap7lock python3 results/rtl/hidx_link_safe_1019/mapped_census.py /out --spec results/rtl/hidx_link_safe_1019/census_spec.json

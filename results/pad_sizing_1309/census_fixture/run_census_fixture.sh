#!/bin/bash
set -e
R=$(cd "$(dirname "$0")" && pwd)
docker run --rm --cpus=1 --memory=2g --memory-swap=2g -v "$R":/out openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -exit /out/census_fixture.tcl" > "$R/census_fixture.log" 2>&1

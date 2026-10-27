#!/usr/bin/env bash
set -eu
cd "$(dirname "$0")"
docker run --rm -v "$PWD:/work" openroad/orfs:latest /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /work/coupon.tcl >coupon.log 2>&1

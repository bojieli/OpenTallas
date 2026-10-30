#!/bin/bash
set -euo pipefail
coupon_dir=$(pwd -P)
docker run --rm --cpus=2 --memory=4g --memory-swap=4g -v "$coupon_dir":/work openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; yosys -c /work/coupon.tcl > /work/coupon.log 2>&1'

#!/bin/bash
set -eu
here=$(cd "$(dirname "$0")" && pwd)
repo=${1:-$(git -C "$here" rev-parse --show-toplevel)}
out=${2:-$(mktemp -d /tmp/opentallas-hold-scope.XXXXXX)}
mkdir -p "$out"
cp "$here/tiny.v" "$here/fixture.sdc" "$here/test_flow_scope_fixed.tcl" "$out/"
cp "$repo/tools/orfs_hold_mm.tcl" "$out/flow_scope.tcl"
docker run --rm --memory=2g --cpus=1 -v "$out":/work openroad/orfs:asap7lock bash -lc '/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -exit /work/test_flow_scope_fixed.tcl' | tee "$out/test.log"

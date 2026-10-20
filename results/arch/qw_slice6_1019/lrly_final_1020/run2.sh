#!/usr/bin/env bash
set -euo pipefail
sha256sum lrly.odb lrlyb.odb native_pg_binding.tcl audit.tcl > source_sha256.txt
for leaf in lrly lrlyb;do
 docker run --rm -v "$PWD:/work" -w /work -e LEAF="$leaf" openroad/orfs:asap7lock /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit audit.tcl > "${leaf}_native_pg.log" 2>&1
done

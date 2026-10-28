#!/bin/bash
# Global-route parasitics for a design that has a 5_1_grt.odb but no detailed route
# (fallback for the top level when detail route fails):  odb -> <out>.v + <out>.spef
#   LIBS='a.lib b.lib ...' grt_spef.sh RESULTS_DIR OUT_PREFIX [mount dirs...]   (std-cell + macro/ETM libs)
# The SPEF comes from `estimate_parasitics -global_routing` with the platform layer RC
# (asap7 setRC.tcl); it is an estimate, label numbers made from it as such.
set -euo pipefail
R=$1; O=$2; shift 2
IMG=${ORFS_IMAGE:-openroad/orfs:asap7lock}
mounts=(-v "$R:$R" -v "$(dirname "$O"):$(dirname "$O")"); for m in "$@"; do mounts+=(-v "$m:$m"); done
{
  for f in ${LIBS:?set LIBS}; do echo "read_liberty $f"; done
  echo "read_db $R/5_1_grt.odb"
  echo "source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl"
  echo "estimate_parasitics -global_routing -spef_file $O.spef"
  echo "write_verilog $O.v"
} > "$O.tcl"
rc=0
docker run --rm --memory "${DOCKER_MEM:-8g}" --user "$(id -u):$(id -g)" "${mounts[@]}" "$IMG" \
  /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit "$O.tcl" > "$O.log" 2>&1 || rc=$?
echo "grt_spef rc=$rc $(grep -c ERROR "$O.log") errors"
exit $rc

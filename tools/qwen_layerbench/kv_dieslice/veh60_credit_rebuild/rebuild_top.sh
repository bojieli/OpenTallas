#!/bin/bash
# Launch only after ROOT reviews this packet; through ot-run128GB8CPU/disk20.
set -euo pipefail
D=$(cd "$(dirname "$0")" && pwd)
export PATH=/home/ubuntu/.local/opentallas-tools/bin:$PATH
cd "$D/b"
python3 "$D/guard_cache.py" pre
# --binary is deliberately decomposed into --main --exe: no automatic make.
/usr/bin/time -v verilator -f top_args.f > "$D/top_generate.log" 2>&1
python3 "$D/guard_cache.py" pre
mapfile -t LIBS < <(python3 -c 'import json,sys;print("\n".join(json.load(open(sys.argv[1]))))' "$D/child_libs.json")
OLDS=();for lib in "${LIBS[@]}";do OLDS+=(-o "$lib");done
# Never make a child archive/header/source. Inspect the dry plan before building.
make -n -C obj -f Vtb_kvslice.mk "${OLDS[@]}" -j8 > "$D/top_make_plan.log"
python3 "$D/guard_cache.py" make-plan
/usr/bin/time -v make -C obj -f Vtb_kvslice.mk "${OLDS[@]}" -j8 > "$D/top_make.log" 2>&1
python3 "$D/guard_cache.py" post
sha256sum obj/Vtb_kvslice > "$D/binary.sha256"
printf 'BUILD_ONLY_COMPLETE no_simulation_run\n' > "$D/status"

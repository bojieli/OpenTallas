#!/bin/bash
set -eu
bundle=${1:?absolute copied CFIFO bundle}
python3 "$bundle/cfifo_rd_drive_probe.py" "$bundle"
for corner in tt ff; do
    set +e
    docker run --rm --network none \
        -v "$bundle/work:/work:ro" -v "$bundle/src:/src:ro" \
        -v "$bundle/meas:/meas:ro" openroad/orfs:asap7lock \
        /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad \
        -exit "/meas/rd_drive_${corner}.tcl" > "$bundle/rd_drive_${corner}.log" 2>&1
    result=$?
    set -e
    echo "$result" > "$bundle/rd_drive_${corner}.exit"
    if [ "$result" -ne 0 ]; then exit "$result"; fi
done

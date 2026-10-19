#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch/claude/codex-pvm-mirror-census16
image=openroad/orfs@sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29
run(){ docker run --rm -v "$R/work:/work" -v "$R/src:/src:ro" -v "$R/region_mechanism.tcl:/probe.tcl:ro" -v "$R/$1:/macro_regions.tcl:ro" "$image" /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /probe.tcl; }
run macro_regions_group.tcl > "$R/region_group_roundtrip.log" 2>&1
docker run --rm -v "$R/work:/work" -v "$R/region_readback.tcl:/probe.tcl:ro" "$image" /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /probe.tcl >> "$R/region_group_roundtrip.log" 2>&1
grep 'REGION_READBACK PASS'  "$R/region_group_roundtrip.log"
if run macro_regions_unknownport_mut.tcl > "$R/region_group_unknownport_mut.log" 2>&1;then echo 'MUTANT_SURVIVED';exit 1;fi
grep 'unmodeled macro-cone boundary port tag_d' "$R/region_group_unknownport_mut.log"

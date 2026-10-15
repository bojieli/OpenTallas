#!/bin/bash
set -euo pipefail
PROOF=/srv/opentallas-scratch/codex/flow-prects-1103/proof
OLD=/srv/opentallas-scratch/claude/ref_gate/qfd_slab_pair_add-20261015-103006
SRC=/srv/opentallas-scratch/codex/flow-prects-1103/src
for CASE in original_pre fixed_pre original_post fixed_post; do
 docker run --rm -v "$OLD/src:/src:ro" -v "$OLD/routes/gate/work/orfs:/work:ro" -v "$PROOF:/proof" openroad/orfs:latest /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit "/proof/$CASE.tcl" > "$PROOF/$CASE.log" 2>&1
 python3 "$SRC/tools/preroute_gate.py" check "$PROOF/$CASE.json" --out "$PROOF/$CASE.judgement.json" > "$PROOF/$CASE.judgement.log" || test "$CASE" = original_pre
 done
cat > "$PROOF/openroad" <<'WRAPPER'
#!/bin/bash
exec docker run --rm -v "/srv/opentallas-scratch/codex/flow-prects-1103:/srv/opentallas-scratch/codex/flow-prects-1103" -v "$SRC_REPLAY:$SRC_REPLAY:ro" -v "$SRC_REPLAY:/src:ro" openroad/orfs:latest /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad "$@"
WRAPPER
chmod +x "$PROOF/openroad"
SRC_REPLAY="$SRC" OPENROAD="$PROOF/openroad" python3 "$SRC/tools/ref_tile/tests/test_tile_hybrid_raw_entries.py" --pre-cts-probe "$PROOF/raw-prects" > "$PROOF/raw-prects-suite.log" 2>&1

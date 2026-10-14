#!/usr/bin/env bash
set -euo pipefail
# Invoke this harness through ot-run --mem 2 --threads 1, never on a login host.
probe_dir=$(cd -- "$(dirname -- "$0")" && pwd)
probe_image=sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29
for probe_mode in ROUNDED DERIVED SHIFT100; do
  docker run --rm --network none -e PROBE_MODE="$probe_mode" -v "$probe_dir:/probe:ro" --entrypoint bash "$probe_image" -lc '/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -exit /probe/probe.tcl' > "$probe_mode.log" 2>&1
  cat "$probe_mode.log"
done

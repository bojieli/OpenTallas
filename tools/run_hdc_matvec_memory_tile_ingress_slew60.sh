#!/usr/bin/env bash
# Matched registered-ingress physical tile with stronger in-flow slew repair.
set -euo pipefail
cd "$(dirname "$0")/.."
tools/run_hdc_matvec_memory_tile_ingress.sh \
  --max-transition-ns --slew-margin-percent 60 \
  --nickname-tag hdc_mem_tile_ingress_slew60 \
  --output results/physical_hdc/asap7/matvec_memory_tile_ingress_slew60/physical.json "$@"

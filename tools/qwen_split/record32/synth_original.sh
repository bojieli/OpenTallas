#!/bin/bash
set -eu
cd "$(dirname "$0")/../../.."
docker run --rm -v "$PWD:/work" -w /work openroad/orfs:latest bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; yosys -Q -s tools/qwen_split/record32/synth_original.ys > original_synth.log 2>&1'

#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
tar -xzf source.tar.gz
docker run --rm --memory=96g --memory-swap=96g -v "$PWD:/work" -w /work openroad/orfs:latest bash -lc 'set -e; source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; python3 prepare.py; yosys -l yosys.log -s synth.ys; python3 tools/textbook_lint.py check --netlist mapped.v --top idxrg_native_top --out textbook.json --set hf_report=32 hf_max=32 hf_port_refuse=32 hf_reset_refuse=32 hf_refuse=32 reach_um=405' > native.log 2>&1
echo NATIVE_SYNTH_DONE

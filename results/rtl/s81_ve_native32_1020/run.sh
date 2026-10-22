#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
tar -xzf source.tar.gz
docker run --rm --memory=64g --memory-swap=64g -v "$PWD:/work" -w /work openroad/orfs:latest bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; python3 prepare.py; yosys -l yosys.log -s synth.ys; python3 mapped_census.py --tool tools/textbook_lint.py --netlist mapped.v --top ot_s81sl_ve --out census.json' > native.log 2>&1
echo NATIVE_SYNTH_DONE

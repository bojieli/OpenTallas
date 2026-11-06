#!/bin/bash
set -euo pipefail
iverilog -g2012 -s tb -o sim leaf.v tb.sv
vvp sim > sim.log
docker run --rm --network none -v "$PWD:/work" -w /work openroad/orfs:asap7lock bash map.sh
docker run --rm --network none -v "$PWD:/work" -w /work openroad/orfs:asap7lock python3 -I results.py

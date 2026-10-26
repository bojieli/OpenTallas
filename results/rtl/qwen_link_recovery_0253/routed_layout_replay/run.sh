#!/bin/bash
set -eu
for n in qfd_r4 qkd_r4sp; do docker run --rm -v "$PWD":/out openroad/orfs:latest /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -threads 1 -exit /out/$n.tcl > $n.log 2>&1; done

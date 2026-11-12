#!/bin/bash
# M2 face-pin probe runner (HBM-GEOM-2 11-12); $1 = pins per row
cd "$(dirname "$0")"
exec docker run --rm -m 6g --cpus 2 -e PPR=$1 -e STEP=${2:-1} -e DW=${3:-69.12} -v "$PWD":/w openroad/orfs:asap7lock /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -exit /w/probe.tcl

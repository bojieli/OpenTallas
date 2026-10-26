#!/bin/bash
set -eu
docker run --rm -v "$PWD":/out openroad/orfs:latest /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -threads 1 -exit /out/raw.tcl > raw_export.log 2>&1
sha256sum raw.lef

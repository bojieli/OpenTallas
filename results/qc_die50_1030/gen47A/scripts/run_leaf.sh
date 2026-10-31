#!/bin/bash
# DIE-QC-50/gen47A step 0: ot_clk leaf drivers on the gen47 provider (main tools/clk/leaf_drivers.py via ot_clk leaf-drivers)
set -euo pipefail
Q=/srv/opentallas-scratch2/claude; A=$Q/die-qc-50/gen47A; W=$Q/wt/die-qc-50-gen47A
docker run --rm --name dqc50g47A-leaf-$$ --memory=32g --memory-swap=32g --cpus=2 -v $Q:$Q -w $W/tools/clk python:3.12 bash -c "pip -q install pyyaml shapely numpy jsonschema >/dev/null 2>&1; python ot_clk.py leaf-drivers $W/results/qc_die50_1030/gen47A/leaf/qc_leaf_gen47.yaml --out $A/leaf > $A/leaf/run.log 2>&1; r=\$?; chown -R 1000:1000 $A/leaf; exit \$r"

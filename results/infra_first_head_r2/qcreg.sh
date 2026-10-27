#!/bin/sh
# INFRA-FIRST-HEAD-2 QC regression: qc_clk_mesh3 plan with the R17 d43b args; the R17 tool and the generalised tool are
# each mounted at /w/tools and write /w/out (same argv), outputs moved aside -> must be byte-identical.
# usage (host): for v in old new; do docker run ... -v $Q/tools_$v:/w/tools:ro ... sh /w/qcreg.sh $v; done
cd /w
A="--r2 inputs/d43/r2_plan_d43.json --stage inputs/stage_table.json --lanes vss --islands type --feed periodic --island-edge-sym --row-at 10471.68=10445.76,5227.2=5218.56 --lift-lane deepest --row-slots holder --centre-channel 43.2 --centre-split 30.24"
rm -rf out; PYTHONPATH=/w/tools python3 /w/tools/qc_clk_mesh3.py plan $A --no-render --out out > log.txt 2>&1; echo "$1 rc=$?"
rm -rf res_$1; mkdir res_$1; mv out log.txt res_$1/

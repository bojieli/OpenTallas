#!/bin/bash
# usage: mk50.sh GEN_PART_DIR OUT_DIR : copy a generated g2 part probe, 50 congestion iterations (HBM die GRT judge rule >=50), dhbm39 names
set -e; rm -rf $2; cp -r $1 $2; cd $2
sed -i "s/-congestion_iterations 30/-congestion_iterations 50/" probe.tcl
sed -i "s/--name g2part-/--name dhbm39-g2-/; s/--memory=32g --memory-swap=32g/--memory=56g --memory-swap=56g/" run.sh
grep -c "congestion_iterations 50" probe.tcl; grep -o "dhbm39-g2-" run.sh; grep -o "memory=56g" run.sh

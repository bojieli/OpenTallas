#!/bin/bash
# usage: mkq0.sh GEN_DIR OUT_DIR : copy a generated g2 part probe, 0 congestion iterations (first-pass trend), dhbm38 names
set -e; rm -rf $2; cp -r $1 $2; cd $2
sed -i "s/-congestion_iterations 30/-congestion_iterations 0/" probe.tcl
sed -i "s/--name g2part-/--name dhbm38-g2-/; s/--memory=32g --memory-swap=32g/--memory=48g --memory-swap=48g/" run.sh
grep -c "congestion_iterations 0" probe.tcl; grep -o "dhbm38-g2-" run.sh

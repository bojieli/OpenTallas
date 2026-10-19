#!/bin/bash
# usage: run_census.sh HOST GATE_DIR OUT
H=$1; R=$2; O=$3
scp -q /home/ubuntu/scratch/c199-fanout/data_census.tcl $H:$R/routes/gate/work/orfs/data_census.tcl
ssh $H "docker run --rm -v $R/routes/gate/work/orfs:/work openroad/orfs:latest /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /work/data_census.tcl" > $O 2>&1

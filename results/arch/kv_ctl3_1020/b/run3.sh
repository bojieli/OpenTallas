#!/bin/bash
cd "$(dirname "$(readlink -f "$0")")"
docker run --rm --network none -v $PWD:/work -w /work openroad/orfs:asap7lock bash -c '
export PATH=/OpenROAD-flow-scripts/tools/install/yosys/bin:$PATH
TOP=dcfg_wrap PARAMS="S32 1" TAG=dw1 yosys -q -l syn_dw1.log -c syn.tcl >/dev/null 2>&1 & TOP=qkd_kv_die_cfg PARAMS="NRST 43 CAP 1 PCOPIES 1 S32 1" TAG=dcfg1 yosys -q -l syn_dcfg1.log -c syn.tcl >/dev/null 2>&1 & wait'
echo SYN_DONE

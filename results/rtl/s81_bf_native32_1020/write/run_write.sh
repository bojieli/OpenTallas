#!/bin/bash
set -eu
cd src
export PATH=/opt/verilator-5.050/bin:$PATH
verilator --version
F=OT_BMUL_RSPLIT+OT_BF_TAGREP+OT_BF_TILE_FREECLK+OT_BF_RSTPART+OT_BF_FOREP+OT_BF_FOREP32+OT_BF_HELD_SRAM+OT_BF_QUEUE32
set +e
python3 tools/s81/bf_forep_bench.py --variant recut --params QZE=1,TCG=1,BXST=2,FXST=2,PINLAT=1,HCOL=1 --jobs 4 --prep "$PWD"/results/rtl/s81_bf_compact_20261010/compact199_pinreg_1018/bench_5050/prep --no-default-mutants --positive-define write32=$F --mutant wptr_mut=$F+OT_BF_QUEUE32_MUT_WRITE --mutant addr_mut=$F+OT_BF_HELD_SRAM_MUT_ADDR --work ../out --only write32 wptr_mut addr_mut
rc=$?
set -e
echo DRIVER_RC=$rc
python3 ../check.py ../out write32 wptr_mut addr_mut

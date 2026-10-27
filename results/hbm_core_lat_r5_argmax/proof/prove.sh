#!/bin/bash
# HBM-CORE-LAT-R5 argmax proofs (P1 FSM range, P2 res_id load-before-observe, P3 sign identity); docker, 8 GB cap
set -uo pipefail
R=$(cd "$(dirname "$0")" && pwd)
python3 -I $R/mkproof.py $R/kit/rtl/ot_hbm_argmax_static_sw_vm_r2.sv $R/proof_core.sv
cat > $R/prove.ys <<'YS'
read_verilog -sv -formal -DOT_PROOF /r/proof_core.sv
read_verilog -sv /r/kit/rtl/ot_rst_relay.sv
read_verilog -sv -lib /r/kit/rtl/ot_hgi_argmax18_m.sv
hierarchy -top ot_hbm_argmax_static_sw_vm_r2__rtl
proc; flatten; delete t:ot_hgi_argmax18_m; setundef -undriven -expose; opt_clean; async2sync; dffunmap; opt -fast
stat
sat -tempinduct -prove-asserts -set-init-zero -maxsteps 20 -show-regs -verify
YS
cat > $R/prove3.ys <<'YS'
read_verilog /r/comb.v
prep -top p3
sat -prove ok 1 -prove eq_hi 1 -verify -show-inputs
YS
docker run --rm --memory=8g --memory-swap=8g --cpus=2 -v $R:/r openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; yosys -q -l /r/prove3.log /r/prove3.ys; echo P3 rc $?; yosys -l /r/prove.log /r/prove.ys > /dev/null; echo P12 rc $?'

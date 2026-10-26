#!/bin/bash
set -uo pipefail
cd "$(dirname "$0")"
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
run(){ local name=$1; shift; mkdir -p "$name"; "$V" --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD --build-jobs 2 -MAKEFLAGS "OPT_FAST=-O1 OPT_SLOW=-O0 OPT_GLOBAL=-O0" -Mdir "$name/obj" "$@" > "$name/build.log" 2>&1 && "$name/obj/"V* > "$name/run.log" 2>&1; echo "$name $?" > "$name/rc"; }
run base --top-module tb_s81sl_rstd_release ot_rst_relay.sv ot_s81sl_xrt.sv tb_s81sl_rstd_release.sv &
run mutant +define+OT_S81SL_QREL_MUT_RELEASE --top-module tb_s81sl_rstd_release ot_rst_relay.sv ot_s81sl_xrt.sv tb_s81sl_rstd_release.sv &
for h in 0 1;do for q in 0 1;do run eq${h}q${q} --top-module tb_s81sl_xrt_qrel_eq -GHB=$h -GQEN=$q -GLAND=0 -GNC=20000 ot_rst_relay.sv ot_s81sl_xrt.sv ref_s81sl_xrt.sv tb_s81sl_xrt_qrel_eq.sv & done;done
wait
cat */rc
cat */run.log
if grep -q '^PASS QREL' base/run.log && grep -q '^FAIL QREL' mutant/run.log && grep -q '^PASS' eq0q0/run.log && grep -q '^PASS' eq1q0/run.log && grep -q '^PASS' eq0q1/run.log && grep -q '^PASS' eq1q1/run.log;then echo QUALIFIED;else echo FAILED;exit 1;fi

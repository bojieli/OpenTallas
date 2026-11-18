#!/bin/bash
set -eu
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
cd /tmp/token_ds_followthrough1116/gb_component
V=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator
/usr/bin/time -v -o frontend.time "$V" --cc --exe --main --timing -O1 --output-split 10000 --output-split-cfuncs 1000 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -Wno-lint -Wno-style -Wno-PINMISSING -Wno-MULTIDRIVEN --top-module tb_native_go_split -Mdir obj -f sources.f > frontend.log 2>&1
/usr/bin/time -v -o backend.time make -C obj -f Vtb_native_go_split.mk -j2 OPT_FAST=-O1 OPT_SLOW=-O0 OPT_GLOBAL=-O0 > backend.log 2>&1
sha256sum obj/Vtb_native_go_split > binary.sha256

#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
m=${1:?}
case "$m" in original|or|bypass|reset_early|reset_missing) ;; *) exit 2;; esac
python3 make_mutants.py
src=coupon.sv
[ "$m" = original ] || src=mut_$m.sv
V=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator
"$V" --binary --timing --top-module tb -Wno-fatal -j 4 --Mdir obj_one_$m "$src" tb.sv
exec ./obj_one_$m/Vtb

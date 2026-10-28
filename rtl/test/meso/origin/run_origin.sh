#!/bin/bash
# MESO-COUNT-2: exhaustive start-sync check of ot_dp_landing_origin (every phase at 1 ps, both metastable outcomes).
set -u
here=$(cd "$(dirname "$0")" && pwd); repo=$(git -C "$here" rev-parse --show-toplevel)
out=${1:?usage: run_origin.sh OUT}; mkdir -p "$out"; cd "$out"
export PATH="$HOME/.local/opentallas-tools/bin:$PATH"
rc=0
for P in 0 2; do for E in 0 1; do
  verilator --cc --exe --build -j 8 -Wno-fatal -Wno-lint -CFLAGS "-DPADV=$P -DEF=$E" -GPAD=$P -GEDGE_FALL=$E \
    --top-module tb_origin "$here"/tb_origin.sv "$repo"/rtl/common/ot_dp_clk_landing_ca.sv "$here"/tb_origin.cpp \
    --Mdir o_p${P}e$E > b_p${P}e$E.log 2>&1 || { echo "BUILD FAIL p$P e$E"; rc=1; continue; }
  for D in 0 40; do o_p${P}e$E/Vtb_origin $D || rc=1; done
done; done
exit $rc

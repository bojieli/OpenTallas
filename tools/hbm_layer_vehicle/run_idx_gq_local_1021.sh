#!/usr/bin/env bash
set -euo pipefail
v="$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator"
"$v" --version
sha256sum rtl/hbm_accel/generic/collective/p2p/ot_hgi_coll_gq.sv rtl/hbm_accel/generic/collective/p2p/ot_hgi_coll_ring_ag.sv rtl/hbm_accel/generic/collective/p2p/tb_hgi_coll_gq_local_rf_1021.sv > sources.sha256
"$v" --binary --timing -O1 -j 4 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -DOT_COLL_GQ_LOCAL_READ --top-module tb --Mdir obj_local -f incdirs.f -f files.f rtl/hbm_accel/generic/collective/p2p/tb_hgi_coll_gq_local_rf_1021.sv > build.log 2>&1
./obj_local/Vtb | tee run.log

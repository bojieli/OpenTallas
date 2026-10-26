#!/usr/bin/env bash
set -euo pipefail
O=${1:?};mkdir -p "$O"
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
source tools/s81_dv/svc_rs/rs_files.sh
P=rtl/dsrom_sys/s81_dv/pv_so
EXTRA=("$P/dsdv_pv_half_join.sv" "$P/dsdv_pv_so_ingress.sv" "$P/dsdv_pv_so_program.sv" "$P/dsdv_svc_rs_pvso_entry.sv")
"$V" --lint-only --timing -Wno-fatal -Wno-WIDTH --unroll-count 4 -fno-dfg -I"$D" -DOT_SVC_ALLQ -DSVCQ_ENG_FG3 "${RS_DEF[@]}" --top-module dsdv_svc_rs_pvso_entry -GPVSO_ENABLE=1 "${RS_SRC[@]}" "${RS_LIB[@]}" "${EXTRA[@]}" > "$O/lint.log" 2>&1
sha256sum "${RS_SRC[@]}" "${EXTRA[@]}" "$D/dsdv_svc_rs_roles.svh" "$D/dsdv_svc_sx_roles.svh" rtl/dsrom_sys/s81_ph/svc/dsfd_svc_c.sv tools/s81_dv/svc_rs/rs_files.sh > "$O/sources.sha256"
echo PVSO_CURRENT_COMPOSED_HIERARCHY_PASS

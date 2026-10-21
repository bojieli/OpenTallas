#!/usr/bin/env bash
set -euo pipefail
O=${1:?outdir};mkdir -p "$O"
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
source tools/s81_dv/svc_rs/rs_files.sh
"$V" --lint-only --top-module dsdv_svc_rs_pvso_entry -GPVSO_ENABLE=1 -GNTP=1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD \
 -I"$D" -DSVCQ_ENG_FG3 "${RS_DEF[@]}" "${RS_SRC[@]}" "${RS_LIB[@]}" \
 rtl/dsrom_sys/s81_dv/pv_so/dsdv_pv_so_ingress.sv rtl/dsrom_sys/s81_dv/pv_so/dsdv_svc_rs_pvso_entry.sv > "$O/hierarchy.log" 2>&1
echo 'PVSO_HIERARCHY_PASS actual current service entry NTP1 PVSO_ENABLE1'

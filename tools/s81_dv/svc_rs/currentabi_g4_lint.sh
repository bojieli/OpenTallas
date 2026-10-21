#!/usr/bin/env bash
# Run on the fleet from a source-pinned archive. No simulator build on localhost.
set -euo pipefail
out=$1
mkdir -p "$out"
source tools/s81_dv/svc_rs/rs_files.sh
vl=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
for variant in dsdv_svc_att:0 dsdv_svc_att:1 dsdv_svc_rs:1 dsdv_svc_rs_entry:1; do
  top=${variant%:*}; ntp=${variant#*:}
  "$vl" --lint-only --top-module "$top" -GNTP="$ntp" -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD \
    -I"$D" -DSVCQ_ENG_FG3 "${RS_DEF[@]}" "${RS_SRC[@]}" "${RS_LIB[@]}" \
    > "$out/${top}_ntp${ntp}.log" 2>&1
  echo "CURRENTABI_G4_LINT PASS $top NTP=$ntp"
done

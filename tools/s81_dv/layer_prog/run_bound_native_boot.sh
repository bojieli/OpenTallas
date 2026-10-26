#!/bin/bash
# Current bound die + explicit measured local stages; emits an unsealed prototype.
set -euo pipefail
W=$(cd "$(dirname "$0")/../../.." && pwd)
: "${BOUND:?current strict bind out/ required}"
: "${INVENTORY:?current extended source inventory required}"
: "${ENTRY_PROGRAM:?actual native entry norm programme required}"
: "${ENTRY_ROWS:?actual native entry writes required}"
: "${OUT:?fresh output directory required}"
SOURCE_ROOT=${SOURCE_ROOT:-$W}
MANIFEST=${MANIFEST:-physical/die_plan/s81/bind/asbuilt_b178_coll.json}
export OT_S81_SELECTED_CHILD_FILES=rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xs.sv,rtl/dsrom_sys/s81_dv/slice/ot_s81sl_rstop.sv
python3 "$W/tools/s81_dv/dv_layer_compile.py" --layer L14 --out "$OUT" \
 --bound-control-only --bound "$BOUND" --bound-inventory "$INVENTORY" \
 --bound-source-root "$SOURCE_ROOT" --bound-asbuilt-manifest "$MANIFEST" \
 --bound-local-timing "$W/results/token_pass/bound_control_1026/timing_all_v2.json" \
 --native-entry-program "$ENTRY_PROGRAM" --retime-native-entry --compose-native-boot \
 --native-entry-rows "$ENTRY_ROWS" \
 --native-boot-cadence "$W/results/token_pass/seqhost_local_1026/host_csr_cadence.json" \
 --native-boot-seqhost-timing "$W/results/token_pass/bound_control_1026/seqhost_bk_timing.json"

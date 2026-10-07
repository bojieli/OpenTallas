#!/bin/bash
# One component bench per invocation; immutable build directory in a pinned snapshot.
set -euo pipefail
O=$(realpath -m "$1"); mode=${2:-gold}
R=$(cd "$(dirname "$0")/../../../.." && pwd)
mkdir -p "$O"
opts=(); margin=1
case "$mode" in
 gold) ;;
 legacy) margin=0 ;;
 noatom) opts+=(+define+S81PH_SVC_MUT_NOATOM) ;;
 skid) opts+=(+define+S81PH_SVC_MUT_SKID) ;;
 *) exit 2 ;;
esac
verilator --binary --timing -j 8 -Wno-fatal -Wno-lint -Wno-style -Wno-WIDTH \
 --top-module tb_s81ph_svc_od_margin +define+SVCIO_TILED -GMARGIN=$margin "${opts[@]}" \
 -Mdir "$O/obj" -o sim \
 "$R/rtl/dsrom_sys/s81_ph/svc/ot_s81ph_svc_io.sv" \
 "$R/rtl/dsrom_sys/s81_ph/svc/ot_s81ph_svc_io_tiles.sv" \
 "$R/rtl/dsrom_sys/s81_ph/svc/ot_s81ph_svc_od_margin.sv" \
 "$R/rtl/common/ot_fwd_link_stage.sv" \
 "$R/rtl/dsrom_sys/s81_ph/svc/tb_s81ph_svc_od_margin.sv" > "$O/build.log" 2>&1
for seed in 1 2 3; do
 "$O/obj/sim" +SEED=$seed +N=300 > "$O/seed$seed.log" 2>&1 || true
 grep -E 'SUMMARY|RESULT' "$O/seed$seed.log"
 grep -q 'RESULT PASS' "$O/seed$seed.log" || exit 1
done

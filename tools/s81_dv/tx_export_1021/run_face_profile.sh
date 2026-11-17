#!/bin/bash
# Run via ot-run. One production-sized native transmitter, same-score/control
# streams: FACE2 DLY-3 keeps the old reserved grid; staleDLY is a negative control.
set -euo pipefail
ulimit -c 0
R=$(cd "$(dirname "$0")/../../.." && pwd)
O=$(realpath -m "${1:?new output directory}")
[ ! -e "$O" ] || { echo "refuse to overwrite output $O"; exit 2; }
mkdir -p "$O"
for f in rtl/lib/ot_rst_relay.sv rtl/dsrom_sys/s81_dv/idx/dsdv_idx_tree.sv rtl/dsrom_sys/s81_dv/idx/dsdv_idx_l20s.sv physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v; do
 cp "$R/$f" "$O/"
done
cp "$R/tools/s81_dv/tx_export_1021/tb_tx_face_profile.sv" "$O/tb.sv"
cd "$O"
sha256sum ./*.sv ./*.v > source.sha256
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
/usr/bin/time -f 'elapsed %e maxrss_kb %M' -o build.time "$VL" --binary --timing -j "${JOBS:-4}" -Wno-fatal -Wno-lint -Wno-style -Wno-WIDTH -Wno-MULTIDRIVEN -Wno-UNOPTFLAT -Wno-PINMISSING -Wno-IMPLICIT -Wno-SELRANGE -Wno-LATCH -Wno-COMBDLY --top-module tb_tx_miter -GRDL=1 -GWDL=1 -GWDC=1 -GSCS=1 -GRIL=1 -GRHP=1 --Mdir obj ot_rst_relay.sv dsdv_idx_tree.sv dsdv_idx_l20s.sv ot_sram_1r1w_1024x256_m2_r2c2.v tb.sv > build.log 2>&1
./obj/Vtb_tx_miter > nominal.log 2>&1
grep -q TX_FACE2_PROFILE_PASS nominal.log
set +e
./obj/Vtb_tx_miter +STALE > stale.log 2>&1
rc=$?
set -e
[ "$rc" != 0 ] && grep -q TX_MITER_FAIL stale.log
cat nominal.log
grep -m2 TX_MISMATCH stale.log
echo TX_FACE2_PROFILE_GATE_PASS

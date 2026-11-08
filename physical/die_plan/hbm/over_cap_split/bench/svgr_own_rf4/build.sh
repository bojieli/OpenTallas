#!/bin/bash
# Lock-step bench: RF3 reference ot_svgr_own (REF = pre-RF4 ot_svgr_split.sv, e.g. git show 685b58b8:<file>) vs the
# RF4 owner extracted from NEW (the RF4 ot_svgr_split.sv) by make_rf4x.py.  Same inputs, every output compared per cycle.
#   build.sh NAME MUTB REF_SPLIT NEW_SPLIT REPO_ROOT     then  obj_NAME/ls_NAME SEED CYCLES
#   MUTB 0 = RF4; 17 = no tail select (must mismatch); 18 = no push while a pop is pending (must mismatch).
set -e; D=$(cd "$(dirname "$0")" && pwd); N=$1; M=$2; REF=$3; NEW=$4; R=$5
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
W=${OUT:-$PWD}; cd "$W"; rm -rf obj_$N
python3 -I "$D/make_rf4x.py" "$NEW" rf4_only.sv
$V --cc --exe --build -j 8 -O2 --x-assign fast --x-initial fast -Wno-fatal -Wno-lint -Wno-style -Wno-WIDTH \
 +define+SYNTHESIS +define+OT_SVGR_OWN_RF1 +define+OT_SVGR_OWN_RF2 +define+OT_SVGR_OWN_RF3 +define+OT_SVGR_OWN_RF4 \
 -GMUTB=$M --top-module ls_top --Mdir obj_$N -o ls_$N \
 "$D/ls_top.sv" "$REF" rf4_only.sv "$R/rtl/hbm_accel/loader/service_native/ot_hbm_svc_async_fifo.sv" "$R/rtl/lib/ot_reset_sync.sv" "$D/tb.cpp" > build_$N.log 2>&1
echo "built $N"

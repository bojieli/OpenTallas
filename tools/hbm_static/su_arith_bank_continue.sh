#!/usr/bin/env bash
# Continue the immutable native bank CTS database; no remap or source edits.
set -euo pipefail
run=$(realpath "$1")
src="$run/src"
flow="$run/routes/gate/work/orfs"
export PATH="$run/bin:$PATH"
cd "$src"
sha256sum "$flow/config.mk" "$flow"/results/asap7/*/base/4_cts.sdc "$flow"/results/asap7/*/base/4_1_cts.odb > "$run/continue_inputs.sha256"
docker run --rm -v "$src:/src:ro" -v "$flow:/work" -w /OpenROAD-flow-scripts/flow openroad/orfs:latest bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; python3 /src/tools/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts >/dev/null; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base finish' > "$run/finish.log" 2>&1
python3 tools/w18/corner_sta_ref.py --orfs-dir "$flow" --extra-sdc physical/ref_tile/hbm_su_static_bank6_1015/signoff.sdc --macro physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2 --output "$run/continued_corner_sta.json" > "$run/continued_sta.log" 2>&1
printf '%s\n' 'SU_BANK_NATIVE_CONTINUE terminal0; inspect actual TT/FF/DRC before acceptance'

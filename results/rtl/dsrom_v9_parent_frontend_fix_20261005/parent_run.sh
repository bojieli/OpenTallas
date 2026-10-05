#!/bin/bash
set -eu
B=/srv/opentallas-scratch2/codex/fspine-v9-parent-context-20261005
R="$B/pq0_fault_parent_retained_r2"
bash "$R/pre_guard.sh"
sha256sum "$R"/*.sv "$B/source-r3/rtl/v41die/ot_v41_retn_w17w10.sv" "$B/source-r3/rtl/v41rom/ot_v41_ret.sv" "$B/source-r3/rtl/v41rom/ot_v41_kreg.sv" "$B/source-r3/rtl/hdc/ot_hdc_cg.sv" "$B/source-r3/rtl/hdc/ot_hdc_delay.sv" "$B/source-r3/rtl/proto/ot_fp32_add_rne_pipe.sv" > "$R/source.sha256"
docker run --rm --cpus=1 -v "$B/source-r3":/src:ro -v "$R":/out --entrypoint /OpenROAD-flow-scripts/tools/install/yosys/bin/yosys openroad/orfs:latest -Q -T -s /out/canonical.ys > "$R/canonical.log" 2>&1
printf '0
' > "$R/terminal.exit"

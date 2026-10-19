#!/bin/bash
set -euo pipefail
root=/srv/opentallas-scratch/claude/ref_gate/qkd_hr_core_guard_frc-20261019-122000
mkdir -p provenance
for f in physical/qwen_die_masters/post_plain.tcl physical/qwen_die_masters/pre_cts.tcl physical/common_flow/protect_clocks.tcl physical/ref_tile/qkd_hr_core_guard_frc/post_cts.tcl physical/ref_tile/qkd_hr_core_guard_frc/pre_grt.tcl physical/ref_tile/qkd_hr_core_guard_frc/post_grt.tcl; do
 if [ -f "$root/src/$f" ]; then cp "$root/src/$f" "provenance/$(basename "$f")"; fi
done
sha256sum "$root/src/rtl/qwen_sys/host_20261013/qkd_host_service_guard.sv" "$root/src/rtl/qwen_sys/host_20261013/qkd_host_guard_fifo.sv" "$root/src/rtl/qwen_sys/mu_qwen_20261018/host_cluster_mu/qkd_hr_core_guard.v" > provenance/frozen_source.sha256
docker run --rm --network none -v "$PWD/provenance:/out" openroad/orfs:asap7lock bash -lc 'cp /OpenROAD-flow-scripts/flow/scripts/cts.tcl /OpenROAD-flow-scripts/flow/scripts/global_route.tcl /OpenROAD-flow-scripts/flow/scripts/load.tcl /out/; cp /OpenROAD-flow-scripts/flow/platforms/asap7/global_connect.tcl /out/platform_global_connect.tcl; true'

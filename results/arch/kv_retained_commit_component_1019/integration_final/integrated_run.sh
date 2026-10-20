#!/bin/bash
set -euo pipefail
sha256sum integrated_*.sv > inputs.sha256
verilator --version
verilator --binary --timing --top-module integrated_bench -Wno-fatal -j 8 --Mdir obj integrated_bench.sv integrated_ot_host_if_pb2_observed_rc.sv integrated_qkd_host_axi_packet_rc.sv integrated_qkd_host_native_token_endpoint_cancel_rc.sv integrated_ot_qwen_host_ctl.sv integrated_qkd_host_ctl_service_pins.sv integrated_ot_qfd_pkgctl.sv > compile.log 2>&1
for n in 0 1 2 3 4; do obj/Vintegrated_bench +CASE=$n > case${n}.log 2>&1; done

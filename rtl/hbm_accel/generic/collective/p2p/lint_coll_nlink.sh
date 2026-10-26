#!/usr/bin/env bash
# H-NETLIST D4F 2026-10-16: lint the COLL q2/q3 host_v4 masters at every NLINK used (q3: 3 default, 2 d4f; q2: 2 default,
# 1 d4f).  Prints COLL_NLINK_LINT <top> NLINK=<n> ok|FAIL.
set -uo pipefail
ROOT=${HCOLL_ROOT:-$(cd "$(dirname "$0")/../../../../.." && pwd)}
p=$ROOT/rtl/hbm_accel/generic/collective/p2p; t=$ROOT/rtl/hbm_accel/generic/collective/tkm
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}; [ -x "$V" ] || V=verilator
src=("$p/ot_hfd_coll_q_static_v4.sv" "$p/ot_hfd_coll_q3_static_host_v4.sv" "$p/ot_hfd_coll_q2_static_host_v4.sv"
 "$p/ot_hgi_coll_static_program_target.sv" "$p/ot_hgi_coll_static_issuer.sv" "$p/ot_hgi_coll_qslots.sv"
 "$p/ot_hgi_coll_pring_static.sv" "$p/ot_hgi_coll_pring_captured_static.sv" "$p/ot_hgi_coll_pring_static_state_capture.sv"
 "$p/ot_hgi_coll_reduce_static.sv" "$p/ot_hgi_coll_argmax_static.sv" "$ROOT/rtl/hbm_accel/generic/collective/ot_hgi_coll_amerge.sv"
 "$p/ot_hgi_coll_static_vmwrite.sv" "$p/ot_hgi_coll_static_link_capture.sv" "$p/ot_hgi_coll_static_capture_ctl.sv"
 "$p/ot_hgi_coll_static_pinreg_ctl.sv" "$p/ot_hgi_coll_static_pinreg_store.sv" "$p/ot_hgi_coll_static_seq_ctl.sv"
 "$t/ot_hgi_coll_tkm_static.sv" "$t/ot_hgi_coll_tkm.sv" "$t/ot_hgi_coll_tkm_buffer.sv" "$ROOT/rtl/lib/ot_rst_relay.sv"
 "$ROOT/rtl/qwen_sys/split_20261014/ot_qkvd_d2d_llr.sv" "$ROOT/rtl/qwen_sys/split_20261014/ot_qwen_crc_parallel.sv"
 "$ROOT/rtl/hdc/ot_hdc_fp32_add_lat.sv" "$ROOT/rtl/hdc/ot_hdc_prefix.sv" "$ROOT/rtl/hdc/ot_hdc_fastfp.sv"
 "$ROOT/physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v"
 "$ROOT/physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v")
fail=0
CASES=${LINT_CASES:-"ot_hfd_coll_q3_static_host_v4:3 ot_hfd_coll_q3_static_host_v4:2 ot_hfd_coll_q2_static_host_v4:2 ot_hfd_coll_q2_static_host_v4:1"}
for tc in $CASES; do tc=${tc/:/ }
 set -- $tc; q=0; [ $1 = ot_hfd_coll_q2_static_host_v4 ] && q=2
 if "$V" --lint-only -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN --top-module "$1" -GNLINK=$2 -GQID=$q "${src[@]}" > /tmp/coll_nlink_$1_$2.log 2>&1 \
    && ! grep -q '%Error' /tmp/coll_nlink_$1_$2.log; then echo "COLL_NLINK_LINT $1 NLINK=$2 ok"
 else echo "COLL_NLINK_LINT $1 NLINK=$2 FAIL"; grep '%Error' /tmp/coll_nlink_$1_$2.log | head -5; fail=1; fi
done
exit $fail

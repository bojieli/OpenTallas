#!/bin/bash
set -euo pipefail
export AHUB_NATIVE_SOURCE=${AHUB_NATIVE_SOURCE:-rtl/hdc/nearhbm/qkd_ahub_static_dw_safe_face_native.v}
exec bash tools/qwen_kv_die/ahub_safe/native_bench.sh "$@"

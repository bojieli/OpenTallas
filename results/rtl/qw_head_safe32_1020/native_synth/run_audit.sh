#!/bin/bash
set -eu
O="$PWD/safe32_native_synth_out/${MAPPED_TAG:-safe32r5b}/work/orfs"
docker run --rm -v "$PWD:/src:ro" -v "$O:/out" openroad/orfs:latest python3 /src/results/rtl/qw_head_safe32_1020/native_synth/audit_current.py > "$O/audit_current.log" 2>&1

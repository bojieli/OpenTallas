#!/bin/bash
set -eu
O="$PWD/safe32_native_synth_out/${MAPPED_TAG:-safe32r5b}/work/orfs"
docker run --rm -v "$PWD:/src:ro" -v "$O:/out" openroad/orfs:latest python3 /src/results/rtl/qw_head_safe32_1020/native_synth/emit_roles.py
python3 results/rtl/qw_head_safe32_1020/native_synth/summarize.py

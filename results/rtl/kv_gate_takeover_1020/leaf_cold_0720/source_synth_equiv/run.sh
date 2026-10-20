#!/bin/bash
set -euo pipefail
lane=$PWD
run=/srv/opentallas-scratch/claude/closure-loop/qkd_kvs_hroot_s32v4-v4a-295504c93
base=$(ls -d "$run"/routes/*/work/orfs/results/asap7/*/base)
mkdir -p out
sha256sum "$base/1_2_yosys.v" "$base/ot_rst_land_wrapper.v" core.sv gold_inner.sv miter.sv > out/inputs.sha256
docker run --rm -v "$run:/route:ro" -v "$lane:/audit" -w /audit openroad/orfs:latest bash /audit/inside.sh "${base/$run/\/route}"

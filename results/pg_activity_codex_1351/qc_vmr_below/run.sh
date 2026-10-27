#!/usr/bin/env bash
set -eu
D=/srv/opentallas-scratch2/claude/codex-pg-act2-1351/qc_vmr_below
K=/srv/opentallas-scratch2/claude/autopilot/closed/qwen_compute/qfd_dv_s8x_vmr__f4kfinal__77013e5059/base
M=/srv/opentallas-scratch2/claude/codex-qc-cores-0815/vmr_f4k_final/macros
docker run --rm --name codex-qc-vmr-below-1351 -m 32g --cpus 4 -u $(id -u):$(id -g) -v "$K":/old:ro -v "$M":/macros:ro -v "$D":/out openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; /usr/bin/time -v openroad -no_init -threads 4 -exit /out/below.tcl' > "$D/run.log" 2>&1

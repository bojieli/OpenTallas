#!/bin/bash
set -euo pipefail
K=$(cd "$1" && pwd); GOAL=${2:-route}; MEM=${3:-12}; THR=${4:-8}
python3 "$K/post_grt_gate.py" "$K"
python3 "$K/sdc_lint.py" "$K" > "$K/pre_resume_lint.log" 2>&1
IMAGE=openroad/orfs:asap7lock
B=/work/run/results/asap7/kq_qfd_dv_s8_crh_rp1_f57/base
echo "resume post-GRT $(date -Is) host $(hostname) image $(docker image inspect --format '{{.Id}}' "$IMAGE")" >> "$K/image.txt"
docker run --rm --name codex-rp1-postgrt-$$ --cpus="$THR" --memory="${MEM}g" --memory-swap="${MEM}g" -v "$K":/work -w /OpenROAD-flow-scripts/flow "$IMAGE" bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; set -e; for t in do-5_2_route do-5_3_fillcell do-5_route do-5_route.sdc do-finish do-generate_abstract; do make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=$THR \$t; done; for c in TT FF; do MC=\$c ODB=$B/6_final.odb SPEF=$B/6_final.spef SDC=$B/6_final.sdc openroad -no_init -exit /work/macro_rcx.tcl > /work/macro_rcx_\$c.log 2>&1; done" > "$K/run_resume.log" 2>&1
rc=$?
docker run --rm -v "$K":/work "$IMAGE" chown -R "$(id -u):$(id -g)" /work
[ "$rc" = 0 ] || exit "$rc"
SIGNOFF_DOCKER=docker python3 -I "$K/signoff.py" run --run-dir "$K/run" --kit "$K" --corners tt,ff --ff-vclk auto --out "$K/signoff_resume" --image "$IMAGE" > "$K/signoff_resume.log" 2>&1
cat "$K/signoff_resume.log"

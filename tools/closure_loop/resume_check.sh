#!/bin/bash
# resume_check.sh <work/orfs dir> <src dir>: ORFS `make -n finish` on the moved work dir -> which stage targets
# would run.  Prints RESUME_FROM=<first stage to run> and RESUME_OK=1 when no stage before global route re-runs.
O=$1; S=$2
out=$(docker run --rm -v $S:/src:ro -v $O:/work -w /OpenROAD-flow-scripts/flow openroad/orfs:latest bash -lc \
  "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; make -n DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base finish 2>&1" )
st=$(echo "$out" | grep -oE "do-[0-9]_[0-9]_[a-z_]+|[0-9]_[0-9]_[a-z_]+\.(log|tmp\.log)" | grep -oE "^(do-)?[0-9]_[0-9]_[a-z_]+" | sed 's/^do-//' | sort -u | tr '\n' ' ')
echo "STAGES_TO_RUN: $st"
first=$(echo $st | tr ' ' '\n' | sort | head -1); echo "RESUME_FROM=$first"
case "$first" in 1_*|2_*|3_*|4_*) echo RESUME_OK=0;; *) echo RESUME_OK=1;; esac

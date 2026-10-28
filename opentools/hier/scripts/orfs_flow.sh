#!/bin/bash
# Run the ORFS side of an ohier plan inside the ORFS docker image.
#   orfs_flow.sh GEN WORK blocks   # every partition -> generate_abstract, in parallel
#   orfs_flow.sh GEN WORK top      # top assembly on the abstracts (needs blocks)
#   orfs_flow.sh GEN WORK flat     # flat baseline on the identical netlist and die
# GEN = `ohier plan --out` dir; WORK = ORFS WORK_HOME.  Paths must be visible
# inside the container at the same location (the caller mounts them).
# Env: ORFS_IMAGE (default openroad/orfs:asap7lock), CPUS_PER_RUN (default 4),
#      DOCKER_MEM (default 16g).
set -uo pipefail
GEN=$1; WORK=$2; WHAT=$3
IMG=${ORFS_IMAGE:-openroad/orfs:asap7lock}
CPUS=${CPUS_PER_RUN:-4}
MEM=${DOCKER_MEM:-16g}
mkdir -p "$WORK"

orfs() {  # orfs NAME DESIGN_CONFIG TARGET
  local name=$1 cfg=$2 tgt=$3
  docker run --rm --name "ohier_${name}_$$" --memory "$MEM" --cpus "$CPUS" \
    --user "$(id -u):$(id -g)" -e HOME="$WORK" -v "$GEN:$GEN" -v "$WORK:$WORK" "$IMG" \
    bash -c "source /OpenROAD-flow-scripts/env.sh >/dev/null; cd /OpenROAD-flow-scripts/flow && \
             make WORK_HOME=$WORK DESIGN_CONFIG=$cfg NUM_CORES=$CPUS $tgt" > "$WORK/$name.log" 2>&1
  local rc=$?
  echo "$(date '+%F %T') $name $tgt rc=$rc" | tee -a "$WORK/flow_status.txt"
  return $rc
}

case $WHAT in
  blocks)
    pids=()
    for cfg in "$GEN"/*/config.mk; do
      d=$(basename "$(dirname "$cfg")")
      [ "$d" = flat ] && continue
      orfs "$d" "$cfg" generate_abstract & pids+=($!)
    done
    rc=0; for p in "${pids[@]}"; do wait "$p" || rc=1; done; exit $rc ;;
  top)   orfs top "$GEN/config.mk" "" ;;
  flat)  orfs flat "$GEN/flat/config.mk" "" ;;
  *) echo "unknown stage $WHAT" >&2; exit 2 ;;
esac

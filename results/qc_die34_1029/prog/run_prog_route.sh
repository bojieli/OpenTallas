#!/bin/bash
# DIE-QC-34 PROG QC-020 candidate 2: prep (PG hook + strip) -> ORFS do-grt (50 congestion iterations, overflow -> stop)
# -> DRT -> fill/report/abstract -> main signoff.py (tt,ff).  run_prog_route.sh KIT [THREADS] [MEM_GB]
set -uo pipefail
K=$(cd "$1" && pwd); C=${2:-16}; M=${3:-32}; IMAGE=openroad/orfs:asap7lock
echo "image $IMAGE $(docker image inspect --format '{{.Id}}' $IMAGE) host $(hostname) start $(date -Is)" > "$K/image.txt"
docker run --rm --name dqc34-prog-$$ --cpus=$C --memory=${M}g --memory-swap=${M}g -v "$K":/work -e HUID=$(id -u) -e HGID=$(id -g) \
  -w /OpenROAD-flow-scripts/flow $IMAGE bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; rc=0; \
  openroad -exit /work/prep_prog.tcl > /work/prep.log 2>&1 || { echo PREP_FAIL; rc=7; }; grep -E '^PREP|OT_PG' /work/prep.log; \
  if [ \$rc = 0 ]; then for t in do-grt do-5_2_route do-5_3_fillcell do-5_route do-5_route.sdc do-6_1_fill do-6_1_fill.sdc do-6_report do-generate_abstract; do \
    make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=$C \$t || { rc=\$?; echo STAGE_FAIL \$t rc \$rc; break; }; done; fi; \
  chown -R \$HUID:\$HGID /work; exit \$rc" > "$K/run_route.log" 2>&1
rc=$?
echo "end $(date -Is) rc $rc" >> "$K/image.txt"; tail -3 "$K/run_route.log"
[ $rc = 0 ] || exit $rc
SIGNOFF_DOCKER=docker python3 -I "$K/signoff.py" run --run-dir "$K/run" --kit "$K" --corners tt,ff --out "$K/signoff" --image "$IMAGE" > "$K/signoff.log" 2>&1
src=$?; grep -E '^SIGNOFF|^  - ' "$K/signoff.log" | head -12; exit $src

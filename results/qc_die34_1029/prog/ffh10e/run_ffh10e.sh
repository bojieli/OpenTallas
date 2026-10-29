#!/bin/bash
# DIE-QC-35 PROG QC-020 ffh10e: FF-only post-route hold ECO. KIT = kit_ffh10e (4_cts.odb = kit_ffh10 5_1_grt.odb sha
# 402d414a.., + its routed 6_final.spef). kit_modes eco check (FF-only, vclk ff) -> ORFS do-grt (POST hook eco_ffh10.tcl)
# -> DRT -> fill/report/abstract -> kit signoff.py (tt,ff).   run_ffh10e.sh KIT [THREADS] [MEM_GB]
set -uo pipefail
K=$(cd "$1" && pwd); C=${2:-16}; M=${3:-32}; IMAGE=openroad/orfs:asap7lock
echo "image $IMAGE $(docker image inspect --format '{{.Id}}' $IMAGE) host $(hostname) start $(date -Is)" > "$K/image.txt"
docker run --rm --name dqc35-proge-$$ --cpus=$C --memory=${M}g --memory-swap=${M}g -v "$K":/work -e HUID=$(id -u) -e HGID=$(id -g) \
  -e OT_VCLK_CORNER=ff -w /OpenROAD-flow-scripts/flow $IMAGE bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; rc=0; \
  python3 -I /work/kit_modes.py check /work --step eco --session bc --vclk-corner ff --hold-repair || rc=9; \
  if [ \$rc = 0 ]; then for t in do-grt do-5_2_route do-5_3_fillcell do-5_route do-5_route.sdc do-6_1_fill do-6_1_fill.sdc do-6_report do-generate_abstract; do \
    make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=$C \$t || { rc=\$?; echo STAGE_FAIL \$t rc \$rc; break; }; done; fi; \
  chown -R \$HUID:\$HGID /work; exit \$rc" > "$K/run_route.log" 2>&1
rc=$?
echo "end $(date -Is) rc $rc" >> "$K/image.txt"; tail -3 "$K/run_route.log"
[ $rc = 0 ] || exit $rc
SIGNOFF_DOCKER=docker python3 -I "$K/signoff.py" run --run-dir "$K/run" --kit "$K" --corners tt,ff --out "$K/signoff" --image "$IMAGE" > "$K/signoff.log" 2>&1
src=$?; grep -E "^SIGNOFF|^  - " "$K/signoff.log" | head -12; exit $src

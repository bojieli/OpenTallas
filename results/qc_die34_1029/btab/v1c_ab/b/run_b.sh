#!/bin/bash
# DIE-QC-36 KITS BTAB QC-014 (B) (V1d run form): KIT = copy of V1c kit (no run/) + results/4_cts.odb = V1c 5_2_route.odb, 4_cts.sdc = V1c,
# v1c_routed.spef = V1c 6_final.spef.  FF-only kit_modes eco check (bc, vclk ff) -> do-grt (PRE pre_v1d.tcl,
# POST eco_v1d.tcl) -> DRT -> fill/report/abstract -> kit signoff.py tt,ff.     run_b.sh KIT [THREADS] [MEM_GB]
set -uo pipefail
K=$(cd "$1" && pwd); C=${2:-16}; M=${3:-48}; IMAGE=openroad/orfs:asap7lock
echo "image $IMAGE $(docker image inspect --format '{{.Id}}' $IMAGE) host $(hostname) start $(date -Is)" > "$K/image.txt"
docker run --rm --name dqc36-btab-b-$$ --cpus=$C --memory=${M}g --memory-swap=${M}g -v "$K":/work -e HUID=$(id -u) -e HGID=$(id -g) \
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

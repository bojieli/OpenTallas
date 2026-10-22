#!/bin/bash
# ROOT14 10-20 die IR-drop step (tools/die_safety/ir_drop.py): dump -> generate -> solve windows -> record.
#   ir_step.sh ODB OUTDIR [GRT_LOG]          env: OT_IR_DESIGN, OT_IR_DENSITY (json), OT_IR_LIMIT_MV (35),
#                                                 OT_IR_WINDOWS (3), OT_IR_M8_USAGE, CPUS (8), MEMG (32)
# Exit 0 = PASS; 1 = FAIL / NOT_RUN (the record step prints an OWNER_REPORT line: the coordinator tells the owner).
set -u
ODB=$(readlink -f "$1"); OUT=$(mkdir -p "$2" && cd "$2" && pwd); LOG=${3:-}
H=$(cd "$(dirname "$0")" && pwd); PY=$H/ir_drop.py
IMG=${OT_IR_IMAGE:-openroad/orfs:asap7lock}
[ -s "$ODB" ] || { echo "DIE_IR_DROP NOT_RUN: no odb $ODB"; echo "OWNER_REPORT die IR-drop NOT_RUN: no odb $ODB"; exit 1; }
python3 "$PY" dump-tcl --out /work/insts.tsv > "$OUT/dump.tcl"
printf 'read_db /in/%s\nsource /work/dump.tcl\n' "$(basename "$ODB")" > "$OUT/dump_run.tcl"
docker run --rm --name otir-dump-$$ --cpus=${CPUS:-8} --memory=${MEMG:-32}g -v "$(dirname "$ODB")":/in:ro -v "$OUT":/work \
  "$IMG" bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -exit /work/dump_run.tcl > /work/dump.log 2>&1; chmod -R a+rwX /work"
[ -s "$OUT/insts.tsv" ] || { echo "DIE_IR_DROP NOT_RUN: instance dump failed ($OUT/dump.log)"; echo "OWNER_REPORT die IR-drop NOT_RUN: dump failed $OUT/dump.log"; exit 1; }
GA=(--insts "$OUT/insts.tsv" --out "$OUT" --windows "${OT_IR_WINDOWS:-3}" --limit-mv "${OT_IR_LIMIT_MV:-35}")
[ -n "${OT_IR_DESIGN:-}" ] && GA+=(--design "$OT_IR_DESIGN")
[ -n "${OT_IR_DENSITY:-}" ] && GA+=(--density "$OT_IR_DENSITY")
[ -n "${OT_IR_M8_USAGE:-}" ] && GA+=(--m8-usage "$OT_IR_M8_USAGE")
[ -n "$LOG" ] && [ -s "$LOG" ] && GA+=(--grt-log "$LOG")
python3 "$PY" generate "${GA[@]}" || { python3 "$PY" record --out "$OUT"; exit 1; }
for W in "$OUT"/w*/; do
  W=${W%/}
  docker run --rm --name otir-$(basename "$W")-$$ --cpus=${CPUS:-8} --memory=${MEMG:-32}g -v "$W":/work "$IMG" \
    bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -threads ${CPUS:-8} -no_init -exit /work/run.tcl > /work/run.log 2>&1; echo \$? > /work/run.exit; chmod -R a+rwX /work"
done
python3 "$PY" record --out "$OUT"

#!/bin/bash
# run one hbm_b2_ir.py case dir in the pinned ORFS image:  ir_run.sh CASE_DIR [THREADS=16] [MEM_GB=64]
set -u
D=$(cd "$1" && pwd); N=${2:-16}; M=${3:-64}
DK=docker; $DK info >/dev/null 2>&1 || DK="sudo docker"
date -Is > "$D/run.start"
$DK run --rm --name thbm_ir_$(basename $D)_$$ --cpus=$N --memory=${M}g --memory-swap=${M}g -v "$D":/work openroad/orfs:asap7lock bash -lc \
  "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; /usr/bin/time -v openroad -threads $N -no_init -exit /work/run.tcl > /work/run.log 2>&1; echo \$? > /work/run.exit; chmod -R a+rwX /work"
date -Is > "$D/run.end"
grep -E "OT_|Maximum resident|Elapsed" "$D/run.log" | tail -12

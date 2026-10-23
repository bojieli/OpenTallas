#!/bin/bash
# Apply a die_eco.tcl to a die ODB in openroad/orfs:asap7lock and report the ECO checks (validation; writes
# OUT/eco.odb only with WRITE=1).  STAND_IN=1 clones missing relay widths as pin-only abstracts.
#   tools/die_feedthrough/eco_apply.sh DIE.odb ECO_DIR OUTDIR [MEM_GB=64]
set -euo pipefail
ODB=$(readlink -f "$1"); ECO=$(readlink -f "$2"); OUT=$3; MEM=${4:-64}
mkdir -p "$OUT"; OUT=$(readlink -f "$OUT"); rm -f "$OUT/eco.exit"
cat > "$OUT/apply.tcl" <<TCL
read_db /in/in.odb
set ft_stand_in ${STAND_IN:-0}
set t0 [clock seconds]
source /eco/die_eco.tcl
puts "OT_ECO_SECONDS [expr {[clock seconds] - \$t0}]"
if {${WRITE:-0}} { write_db /work/eco.odb }
TCL
docker run --rm --name ftecoapply-$$ --cpus=2 --memory=${MEM}g --memory-swap=${MEM}g \
  -v "$OUT":/work -v "$ODB":/in/in.odb:ro -v "$ECO":/eco:ro -w /work openroad/orfs:asap7lock \
  bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -exit /work/apply.tcl > /work/eco.log 2>&1; echo EXIT \$? > /work/eco.exit; chmod -R a+rwX /work"
cat "$OUT/eco.exit"; grep -E "OT_ECO|FT_ECO|Error|ERROR" "$OUT/eco.log" | tail -n 25

#!/bin/bash
# Run odb_dump.py on a die ODB inside openroad/orfs:asap7lock (read-only ODB mount).
#   tools/die_feedthrough/dump.sh DIE.odb OUTDIR [MEM_GB=80]
# Short diagnostic: plain docker run with --memory=--memory-swap (owner 10-23); keep >=64 GB host headroom.
set -euo pipefail
ODB=$(readlink -f "$1"); OUT=$2; MEM=${3:-80}
HERE=$(cd "$(dirname "$0")" && pwd)
mkdir -p "$OUT"; OUT=$(readlink -f "$OUT")
cp "$HERE/odb_dump.py" "$OUT/odb_dump.py"
docker run --rm --name ftdump-$$ --cpus=2 --memory=${MEM}g --memory-swap=${MEM}g \
  -e FT_ODB=/in/in.odb -e FT_OUT=/work -v "$OUT":/work -v "$ODB":/in/in.odb:ro -w /work \
  openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; \
  openroad -python -exit /work/odb_dump.py > /work/dump.log 2>&1; echo EXIT \$? > /work/dump.exit"
sed -i "s|/in/in.odb|$ODB|" "$OUT/die.json" 2>/dev/null || true
cat "$OUT/dump.exit"

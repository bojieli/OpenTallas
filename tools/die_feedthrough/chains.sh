#!/bin/bash
# Bit-exact relay chains of a plan's pushed lanes (chains_odb.py in openroad/orfs:asap7lock; read-only ODB).
#   tools/die_feedthrough/chains.sh DIE.odb PLAN.json OUTDIR DIE [MEM_GB=80]      DIE = s81|kv|qc|hbm (dies.py regexes)
set -euo pipefail
ODB=$(readlink -f "$1"); PLAN=$(readlink -f "$2"); OUT=$3; DIE=$4; MEM=${5:-80}
HERE=$(cd "$(dirname "$0")" && pwd)
mkdir -p "$OUT"; OUT=$(readlink -f "$OUT")
rm -f "$OUT/chains.exit"; cp "$HERE/chains_odb.py" "$OUT/chains_odb.py"
read DROP RELAY < <(cd "$HERE" && python3 -c "import dies; c=dies.get('$DIE'); print(c['drop_re'], c['relay_re'])")
docker run --rm --name ftchains-$$ --cpus=2 --memory=${MEM}g --memory-swap=${MEM}g \
  -e FT_ODB=/in/in.odb -e FT_PLAN=/in/plan.json -e FT_OUT=/work -e "FT_DROP_RE=$DROP" -e "FT_RELAY_RE=$RELAY" \
  -v "$OUT":/work -v "$ODB":/in/in.odb:ro -v "$PLAN":/in/plan.json:ro -w /work openroad/orfs:asap7lock \
  bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -python -exit /work/chains_odb.py > /work/chains.log 2>&1; echo EXIT \$? > /work/chains.exit; chmod -R a+rwX /work"
cat "$OUT/chains.exit"; tail -n 2 "$OUT/chains.log"

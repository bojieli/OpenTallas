#!/bin/bash
# DIE-S81-80 standalone kit LEC (same image/entry as lec_async unit form). $1 kit dir, $2 container name, $3 netlist (/work path), $4 mem GB
K=$1; N=$2; NET=$3; M=${4:-48}
docker run --rm --name "$N" ${OTE:+-e $OTE} --cpus=4 --memory=${M}g --memory-swap=${M}g -v "$K:/work" -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock \
  bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; python3 -I /work/legacy_gate.py /work lec --netlist $NET; r=\$?; chown -R $(id -u):$(id -g) /work/lec /work/lec_run.log 2>/dev/null; exit \$r"
r=$?; echo "LEC64_RC $N $r"; tail -n 2 "$K/lec_run.log"; exit $r

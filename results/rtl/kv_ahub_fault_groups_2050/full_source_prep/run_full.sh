#!/bin/bash
set -uo pipefail
D=/srv/opentallas-scratch2/claude/codex-kv-ahub-fault-full-2055
DK=docker; docker ps >/dev/null 2>&1 || DK='sudo docker'
for v in normal mutant; do
 mkdir -p "$D/proof/$v"
 $DK run --rm --name "codex-kv-ahub-fault-$v-2055" --memory=16g --memory-swap=16g --cpus=2 \
  -v "$D/$v":/work:ro -v "$D/reference.v":/source/reference.v:ro -v "$D/tools":/m:ro -v "$D/proof/$v":/out \
  openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; python3 -I /m/lec.py /work --netlist /source/reference.v --out /out' > "$D/proof/$v/client.log" 2>&1
 rc=$?; printf '%s\n' "$rc" > "$D/proof/$v/rc"
 $DK run --rm -v "$D/proof/$v":/out openroad/orfs:asap7lock chown -R "$(id -u):$(id -g)" /out >/dev/null 2>&1
 echo "fullsource $v rc=$rc $(date)"
done

#!/bin/bash
# usage: run_rst.sh <placed odb> <outdir name>   (Codex reset_tree.py --apply: balanced BUFx24 4-way native reset trees, 0 cycles)
D=$(cd $(dirname $1) && pwd); R=/srv/opentallas-scratch2/claude/die-kv-47-hr/rst
docker run --rm --cpus 2 --memory 8g --memory-swap 8g -v $D:/db:ro -v $R:/work openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -python -exit /work/reset_tree.py /db/$(basename $1) /work/$2 --apply" > $R/$2.log 2>&1

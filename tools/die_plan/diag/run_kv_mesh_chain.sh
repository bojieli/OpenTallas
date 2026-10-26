#!/bin/bash
# PATH-KV-R2: full KV 8-region mesh chain against a given PG grid: build -> (combo+post, balance) x3 -> stubtrim -> combo+post.
# usage: run_kv_mesh_chain.sh OUTBASE PG_JSON   (plan/kit = codex-kv-mesh-1026 inputs; tools = this checkout)
set -e
O=$1; PG=$2; T=$(cd $(dirname $0)/.. && pwd)
IN=/srv/opentallas-scratch2/claude/codex-kv-mesh-1026; PL=$IN/plan.json; K=$IN/kit
export PYTHONPATH=$IN/pylib
SPEC=/srv/opentallas-scratch2/claude/path-kv-clk-1026/spec_c3.json
mkdir -p $O
measure() { python3 $T/die_clock_mesh.py combo $1 --kit $K --plan $PL; MEM=24 bash $1/run_combo.sh; grep -H EXIT $1/combo_TT.log $1/combo_FF.log
            bash $T/die_clock_mesh_post.sh $1 $PL; }
python3 $T/die_clock_mesh.py build $PL --out $O/b0 --nx 32 --ny 64 --m 2 --rep-um 450 --ndr 4w --sites any \
  --region-spec $SPEC --reserve-cell-sites --pg-json $PG --track-file $K/grt/tracks.tcl \
  --trunk-repeaters --driver-pair-span 700 --split-yfirst --max-move ${MAXMOVE:-250} --delta-id D-KV-CLKMESH-PROTO
measure $O/b0
python3 $T/die_clock_mesh.py balance $O/b0 --out $O/b1 --plan $PL --tag a; measure $O/b1
python3 $T/die_clock_mesh.py balance $O/b1 --out $O/b2 --plan $PL --tag b; measure $O/b2
python3 $T/die_clock_mesh.py balance $O/b2 --out $O/b3 --plan $PL --tag c --fine-lib BUFx6f_ASAP7_75t_R; measure $O/b3
python3 $T/die_clock_mesh.py stubtrim $O/b3 --out $O/t --plan $PL --tag t --fine-lib BUFx6f_ASAP7_75t_R; measure $O/t
python3 $T/die_clock_mesh.py render $O/t --plan $PL --out $O/t/t.png || true
echo CHAIN_DONE

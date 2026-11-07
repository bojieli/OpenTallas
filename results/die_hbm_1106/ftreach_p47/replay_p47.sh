#!/bin/bash
# DIE-HBM-82-G0C d44v part 47 replay from the repo root of the base commit (part 43 applied):
#   results/die_hbm_1106/ftreach_p47/replay_p47.sh [JOBS]
# ft_s0_resite.py once per type of types_p47.txt (the types with a G0C 'stations' row on the base), in parallel, then
# mk_p47.py takes only the re-sited slots + regenerates latency.lanes.  Needs ~16 GB per job; takes ~1-2 h at 16 jobs.
set -e; export PYTHONDONTWRITEBYTECODE=1
P=results/die_hbm_1106/ftreach_p47; J=${1:-16}
T=$(mktemp -d); trap 'rm -rf $T' EXIT
POR=$(python3 -I results/die_hbm_1106/street_p43/mat_por.py . $T)
mkdir -p $T/run
xargs -P $J -I{} sh -c "python3 -I tools/die_plan/ft_s0_resite.py $POR $T/run/{}.plan.json $T/run/{}.ledger.json --types {} > $T/run/{}.log 2>&1" < $P/types_p47.txt
python3 -I $P/mk_p47.py $POR physical/die_plan/hbm/plan_of_record/d44v $T/run $P/ledger_p47.json
python3 -I $P/fin_p47.py .

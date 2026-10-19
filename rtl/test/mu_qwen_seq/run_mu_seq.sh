#!/bin/bash
# MU-QWEN-SEQ benches (Verilator 5.050, the closure daemon's version): mutant 0 must PASS, mutants 4 5 11..15 must FAIL.
# usage: run_mu_seq.sh WORK [mut ...]     (default: 0 11 12 13 14 15).  Logs: WORK/m<M>.out, WORK/m<M>/summary_m<M>.json
set -u
D=$(cd "$(dirname "$0")" && pwd); W=${1:?WORK}; shift; mkdir -p "$W"; rc=0
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$VL" --version
M=${*:-0 4 5 11 12 13 14 15 33}
for m in $M; do
    python3 -I "$D/mu_seq_bench.py" --work "$W/m$m" --mut "$m" --verilator "$VL" --jobs 8 > "$W/m$m.out" 2>&1
    L=$(head -1 "$W/m$m.out"); echo "$L"
    if [ "$m" = 0 ]; then case "$L" in MU_SEQ_PASS*) ;; *) rc=1;; esac; else case "$L" in MU_SEQ_FAIL*) ;; *) rc=1;; esac; fi
done
[ $rc = 0 ] && echo "MU_SEQ BENCHES: PASS" || echo "MU_SEQ BENCHES: FAIL"
exit $rc

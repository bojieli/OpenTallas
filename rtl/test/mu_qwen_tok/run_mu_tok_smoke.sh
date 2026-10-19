#!/bin/bash
# MU-ADOPT-TOK smoke (Verilator 5.050, the closure daemon's version): mutant 0 must PASS, every listed mutant must FAIL.
# usage: run_mu_tok_smoke.sh WORK [mut ...]   (default: 0 cal11 amax1 glue1 glue2; amax2 is equivalent under the
# station-exclusive calendar rule cp.stn, kept runnable as a diagnostic).  Logs WORK/<mut>.out,
# WORK/<mut>/summary_<mut>.json.  Fleet: ot-run --mem 8 --threads 8 --dir <synced src> -- bash rtl/test/mu_qwen_tok/run_mu_tok_smoke.sh WORK
set -u
D=$(cd "$(dirname "$0")" && pwd); W=${1:?WORK}; shift; mkdir -p "$W"; rc=0
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$VL" --version
M=${*:-0 cal11 amax1 glue1 glue2}
for m in $M; do
    python3 "$D/mu_tok_smoke.py" --work "$W/$m" --mut "$m" --verilator "$VL" --jobs 8 > "$W/$m.out" 2>&1
    L=$(head -1 "$W/$m.out"); echo "$L"
    if [ "$m" = 0 ]; then case "$L" in MU_TOK_SMOKE_PASS*) ;; *) rc=1;; esac
    else case "$L" in MU_TOK_SMOKE_FAIL*) ;; *) rc=1;; esac; fi
done
[ $rc = 0 ] && echo "MU_TOK_SMOKE BENCHES: PASS" || echo "MU_TOK_SMOKE BENCHES: FAIL"
exit $rc

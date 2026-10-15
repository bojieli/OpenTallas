#!/bin/bash
# Production NG256 return-leaf qualification; explicit active parameter probes.
set -euo pipefail
out=$1; tile=${2:-}; ntree=${HC_NTREE:-0}; pipe=1
for c in "${S81_SU_CASES:-}" /srv/opentallas-scratch/claude/s81-suhc/su_cases_v2_ildr.pkl /srv/opentallas-scratch2/claude/s81-suhc/su_cases_v2_ildr.pkl "$HOME/s81-suhc/su_cases_v2_ildr.pkl"; do
    [ -n "$c" ] && [ -s "$c" ] && { pkl=$c; break; }
done
[ -n "${pkl:-}" ] || { echo fixture-not-found; exit 97; }
[ "$(sha256sum "$pkl" | cut -c1-16)" = 8c18c0655ccf6a14 ] || exit 97
export PATH="$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH"
mkdir -p "$out"
python3 tools/s81_suhc/hc_gate.py prep --cases "$pkl" --out "$out" --ng 256
python3 tools/s81_suhc/hc_gate.py run --out "$out" --ng 256 --hier 3 --cnl-pin 1 --chain-step 6 --lane-specialize 1 --ntree "$ntree" --nt-k 67 --pipe "$pipe" --pipe-pd 40 --mut 0 --tile-probe ot_s81_hc_ctra,ot_s81_hc_ctrb ${tile:+--tile-mut $tile} --tmax 30000

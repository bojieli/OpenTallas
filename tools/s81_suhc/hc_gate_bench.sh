#!/bin/bash
# S81 HC composition gate as a closure-loop bench (s81hc-1013).  Every HC ref_tile job carries it, so a CLOSED HC tile
# is bound to a bit-exact whole-HC run of its OWN source commit: the production shape of the physical master
# (HIER 3 = half-octet tiles + split column roots + chain-tail split, CNL_PIN 1, CHAIN_STEP 6, LANE_SPECIALIZE 1) at
# NG 64, against the CPU golden of the 1M token (golden_L0_L2) plus two stress runs.
#   hc_gate_bench.sh <out dir> <mut>      mut 0: exact, must print "RUN <tag> pass"; mut 3: must print "RUN <tag> fail"
# The su_cases pickle is the per-host fixture (same file on EPYC1 / EPYC4 / AGIdock, sha256 checked).
set -euo pipefail
out=$1; mut=${2:-0}
PKL_SHA=8c18c0655ccf6a14
for c in "${S81_SU_CASES:-}" tools/s81_suhc/fixtures/su_cases_v2_ildr.pkl /srv/opentallas-scratch/claude/s81-suhc/su_cases_v2_ildr.pkl \
         /srv/opentallas-scratch2/claude/s81-suhc/su_cases_v2_ildr.pkl "$HOME/s81-suhc/su_cases_v2_ildr.pkl"; do
    [ -n "$c" ] && [ -s "$c" ] && { pkl=$c; break; }
done
[ -n "${pkl:-}" ] || { echo "hc_gate_bench: su_cases_v2_ildr.pkl fixture not found on $(hostname)"; exit 97; }
got=$(sha256sum "$pkl" | cut -c1-${#PKL_SHA})
[ "$got" = "$PKL_SHA" ] || { echo "hc_gate_bench: fixture $pkl sha256 $got != $PKL_SHA"; exit 97; }
[ -x "$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator" ] && export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
mkdir -p "$out"
python3 tools/s81_suhc/hc_gate.py prep --cases "$pkl" --out "$out" --ng 64
python3 tools/s81_suhc/hc_gate.py run --out "$out" --ng 64 --hier 3 --cnl-pin 1 --chain-step 6 --lane-specialize 1 --mut "$mut"

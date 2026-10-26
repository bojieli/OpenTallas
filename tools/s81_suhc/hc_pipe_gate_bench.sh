#!/bin/bash
# Production-width ordered-POST gate for a cseq RTL successor. The mutation removes
# the local write-back guard, so dependent jobs overtake write-back and must fail.
set -euo pipefail
out=$1
mode=${2:-exact}
case "$mode" in exact) pd=40 ;; guard_mut) pd=0 ;; *) exit 64 ;; esac
for c in "${S81_SU_CASES:-}" tools/s81_suhc/fixtures/su_cases_v2_ildr.pkl /srv/opentallas-scratch/claude/s81-suhc/su_cases_v2_ildr.pkl /srv/opentallas-scratch2/claude/s81-suhc/su_cases_v2_ildr.pkl "$HOME/s81-suhc/su_cases_v2_ildr.pkl"; do
    [ -n "$c" ] && [ -s "$c" ] && { pkl=$c; break; }
done
[ -n "${pkl:-}" ] || { echo "hc_pipe_gate: fixture missing"; exit 97; }
expected=8c18c0655ccf6a147cde5e8a65e709ad5ccfd62ba9024e2644019289cd8d2108
[ "$(sha256sum "$pkl" | cut -d' ' -f1)" = "$expected" ] || { echo "hc_pipe_gate: fixture checksum mismatch"; exit 97; }
[ -x "$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator" ] && export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
mkdir -p "$out"
python3 tools/s81_suhc/hc_gate.py prep --cases "$pkl" --out "$out" --ng 256
python3 tools/s81_suhc/hc_gate.py run --out "$out" --ng 256 --hier 3 --cnl-pin 1 --chain-step 6 --lane-specialize 1 --pipe 1 --pipe-pd "$pd" --tmax 20000

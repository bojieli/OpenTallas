#!/bin/bash
set -euo pipefail
mode=$1
mkdir -p "$2"
out=$(realpath "$2")
fixture=''
for candidate in /srv/opentallas-scratch/claude/s81-suhc/su_cases_v2_ildr.pkl /srv/opentallas-scratch2/claude/s81-suhc/su_cases_v2_ildr.pkl "$HOME/s81-suhc/su_cases_v2_ildr.pkl"; do
    if [ -s "$candidate" ]; then fixture=$candidate; break; fi
done
[ -n "$fixture" ] || { echo 'production fixture missing'; exit 97; }
[ "$(sha256sum "$fixture" | cut -c1-16)" = 8c18c0655ccf6a14 ] || exit 97
export PATH="$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH"
python3 tools/s81_suhc/hc_gate.py prep --cases "$fixture" --out "$out" --ng 256
python3 tools/s81_suhc/native_comb_gate.py run --native-mode "$mode" --out "$out" --ng 256 --hier 3 --cnl-pin 1 --chain-step 6 --lane-specialize 1 --pad-hard 1 --tmax 40000

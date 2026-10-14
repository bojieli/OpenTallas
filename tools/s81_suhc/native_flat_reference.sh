#!/bin/bash
# Independent production flat RTL reference against exactly the native corpus.
set -euo pipefail
mut=$1
mkdir -p "$2"
out=$(realpath "$2")
fixture=''
for candidate in /srv/opentallas-scratch/claude/s81-suhc/su_cases_v2_ildr.pkl /srv/opentallas-scratch2/claude/s81-suhc/su_cases_v2_ildr.pkl "$HOME/s81-suhc/su_cases_v2_ildr.pkl"; do
    if [ -s "$candidate" ]; then fixture=$candidate; break; fi
done
[ -n "$fixture" ] || exit 97
[ "$(sha256sum "$fixture" | cut -c1-16)" = 8c18c0655ccf6a14 ] || exit 97
export PATH="$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH"
python3 tools/s81_suhc/hc_gate.py prep --cases "$fixture" --out "$out" --ng 256
python3 tools/s81_suhc/hc_gate.py run --out "$out" --ng 256 --fp dpi --hier 0 --mut "$mut" --tmax 40000

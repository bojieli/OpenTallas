#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch/claude/codex-s81-rtlgap-2140-1022
D=/srv/opentallas-scratch/claude/stw-s81c-cap30/gen-main
cd "$R"
sha256sum "$D/bind/bind/die.v" "$D/bind/bind/port_bind.json" "$D/bind/bind/bind_case.json" > cap30_input.sha256
python3 tools/s81_dv/dv_rtl_kit.py --repo /srv/opentallas-scratch/claude/git-mirror/OpenTallas.git --ref 528fc3c9f --port-bind "$D/bind/bind/port_bind.json" --bind-case "$D/bind/bind/bind_case.json" --bind-snapshot-bytes --top-v "$R/producer_top.sv" --top producer_top --out "$R/K_producer2" > prep2.log 2>&1
cat prep2.log

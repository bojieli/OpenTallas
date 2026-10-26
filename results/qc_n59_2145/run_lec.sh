#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch2/claude/codex-n59-2145-current
sudo python3 "$R/tool/lec.py" "$R/kit" --out "$R/lec" --mem 32 --jobs 4

#!/bin/bash
set -euo pipefail
: "${TYPE:?}" "${OUT:?}" "${PLAN:?}"
python3 -I tools/s81_head/head_wave_kit_rtl.py export --plan "$PLAN" --out "$OUT" --type "$TYPE"

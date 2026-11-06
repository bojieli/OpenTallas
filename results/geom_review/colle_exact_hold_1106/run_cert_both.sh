#!/bin/bash
set -euo pipefail
r=/srv/opentallas-scratch2/claude/codex-colle-exact-hold-1106
for side in ${COLLE_CERT_SIDES:-e w}; do
 python3 "$r/run_cert_context.py" "$side"
 done

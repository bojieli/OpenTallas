#!/bin/bash
set -euo pipefail
cd /srv/opentallas-scratch2/claude/codex-s81-rcx-1351/field
exec /srv/opentallas-scratch2/claude/codex-infra-tool-1026/venv/bin/python -u rcx_width_rules.py write stock.rules cal.json physical_multi.rules --widths 1.60,1.68,1.76

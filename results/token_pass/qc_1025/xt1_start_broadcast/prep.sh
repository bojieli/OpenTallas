#!/bin/bash
set -euo pipefail
export CAL_SMOKE_CACHE_ROOT=/srv/opentallas-scratch2/claude/qc-tok-start-1025/cache
cd /srv/opentallas-scratch2/claude/qc-tok-start-1025
python3 /srv/opentallas-scratch2/claude/qc-tok-start-1025/tool/tools/die_plan/bind_smoke.py --die qwen_compute --bound /srv/opentallas-scratch2/claude/clock-reset/start/qc_bind   --constants /srv/opentallas-scratch2/claude/codex-qc-wavefront-run-1025/constants_meth.json   --asbuilt /srv/opentallas-scratch2/claude/clock-reset/start/qc_recipe.json --src-rev bc11ef2db --repo /home/ubuntu/OpenTallas   --clusters both --inputs /srv/opentallas-scratch2/claude/codex-qc-wavefront-run-1025/inputs_cache   --work /srv/opentallas-scratch2/claude/qc-tok-start-1025/both --start-at 200 --no-report

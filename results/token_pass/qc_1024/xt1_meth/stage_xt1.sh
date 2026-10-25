#!/bin/bash
export CAL_SMOKE_CACHE_ROOT=/srv/opentallas-scratch2/claude/qc-tok/cap_eq/srccache
python3 /srv/opentallas-scratch2/claude/wt/qc-tok-meth/tools/die_plan/bind_smoke.py --die qwen_compute --bound /srv/opentallas-scratch2/claude/qc/bind_meth_cb16   --asbuilt /srv/opentallas-scratch2/claude/qc/bind_meth_cb16/recipe.json --constants /srv/opentallas-scratch2/claude/qc-tok/meth/constants_meth.json   --src-rev 2ece7f9a79 --clusters both --work /srv/opentallas-scratch2/claude/qc-tok/meth/xt1_meth_both --inputs /srv/opentallas-scratch2/claude/qc-tok/cap_eq/xt1_inputs --no-report
echo STAGE_RC=$?

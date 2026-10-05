#!/usr/bin/env bash
set -uo pipefail
source "$HOME/.opentallas-env"
cd /srv/opentallas-scratch/codex/dsrom-wf-ctrl/wt-local-115e40246
/srv/opentallas-scratch/admit.sh 12 -- bash tools/dsrom_wfc_reset_reference_recipe.sh /srv/opentallas-scratch/codex/dsrom-wf-ctrl/local_control1_s0/case -DOT_WFC_LOCAL_CONTROL=1 -GSOURCE=0 -GMAXU=866 -GUSERS=866 -GSEED=13 -GNJOBS=20000 -GXWORDS=46 -GRXWORDS=41
rc=$?
printf '%s\n' "$rc" > /srv/opentallas-scratch/codex/dsrom-wf-ctrl/local_control1_s0/exit_code
exit "$rc"

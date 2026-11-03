#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch2/claude/codex-ahub-drv-0158
OT_PRD_FROM=route OT_PRD_TARGETED=1 OT_SETUP_MARGIN='' OT_HOLD_ALLOW_SETUP=0 bash "$R/source/tools/die_plan/post_route_drv/prd_mk.sh" "$R/seed" "$R/driver_only" m10 "$R/source"
. "$R/driver_only/variant.env"
test -z "$OT_SETUP_MARGIN"
test "$OT_HOLD_ALLOW_SETUP" = 0

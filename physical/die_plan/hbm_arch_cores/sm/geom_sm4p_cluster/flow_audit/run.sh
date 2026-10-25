#!/bin/bash
docker run --rm --cpus=4 --memory=24g --memory-swap=24g -v /srv/opentallas-scratch2/claude/path-hbm-sm/audit:/a openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; for h in n s; do /OpenROAD-flow-scripts/tools/install/yosys/bin/yosys -q -l /a/conn_\$h.log -s /a/conn_\$h.ys; echo rc_\$h \$?; done; chown -R $(id -u):$(id -g) /a"

#!/bin/bash
set -u
D=/srv/opentallas-scratch/codex/hbm-router-dr3-02b165495
W=/srv/opentallas-scratch/claude/die-evidence/hbm_r25/grt3
# 47GiB rounds up the measured same-run peak48401148KiB; no wall/address-space cap.
/srv/opentallas-scratch/admit.sh 47 -- docker run --rm --name codex_dr3_dump_02b165495 -v "$W:/work:ro" -v "$D:/rb" openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; /usr/bin/time -v openroad -threads 16 -no_init -exit /rb/run_rb.tcl > /rb/rb.log 2>&1; rc=\$?; echo \$rc > /rb/exit.rc; chmod -R a+rwX /rb; exit \$rc"
echo "$?" > "$D/guard.rc"

#!/bin/bash
Q=/srv/opentallas-scratch2/claude
docker run --rm --name dieqc44-rcx-$$ --memory=160g --memory-swap=160g --cpus=8 -v $Q:/s openroad/orfs:asap7lock bash -c "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -threads 8 -exit /s/die-qc-44/grt/rcx_clock.tcl > /s/die-qc-44/grt/rcx.log 2>&1; rc=\$?; chown 1000:1000 /s/die-qc-44/grt/*; exit \$rc"
rc=$?; [ $rc = 0 ] && grep -q QC44_RCX_DONE $Q/die-qc-44/grt/rcx.log && touch $Q/die-qc-44/grt/clock.spef.done; echo "rcx rc=$rc $(date)" > $Q/die-qc-44/grt/rcx.status

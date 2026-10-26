#!/bin/bash
# DIE-PROTO 2325: combined QC die GRT (batch 1+2 signals M4-M7 + die clock M8-M9) TT/FF; A = old ctree (FROZEN 54a1aeb5 recipe), B = Codex combo_legal legal-site 4W/8W NDR clock
O=/srv/opentallas-scratch2/claude/die-proto-2325/qc_b12
for v in A B; do for c in TT FF; do
 docker run --rm --name dieproto-qcb12-$v-$c --cpus=16 --memory=48g --memory-swap=48g -e CORNER=$c -e LIBDIR=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM \
   -v $O/kit:/work:ro -v $O/out$v:/out openroad/orfs:latest bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -threads 16 -exit /out/combo.tcl > /out/combo_$c.log 2>&1; echo EXIT \$? >> /out/combo_$c.log; chown -R $(id -u):$(id -g) /out" &
done; done; wait; echo ALL_DONE $(date)

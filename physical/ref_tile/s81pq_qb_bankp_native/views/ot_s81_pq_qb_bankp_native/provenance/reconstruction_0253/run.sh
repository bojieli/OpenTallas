#!/bin/bash
set -eu
for item in vmb9 bankp; do
 docker run --rm -v /srv/opentallas-scratch2/claude/closure-loop/s81coll_vm_boundary_b9-b9-81f67e112/routes/s81coll_vm_boundary_b9_b9_81f67e112/work/orfs:/work:ro -v /srv/opentallas-scratch/codex/s81-raw-recovery-0253/$item:/out openroad/orfs:latest /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -threads 1 -exit /out/raw.tcl > /srv/opentallas-scratch/codex/s81-raw-recovery-0253/$item/raw_export.log 2>&1
 sha256sum /srv/opentallas-scratch/codex/s81-raw-recovery-0253/$item/raw.lef
 python3 /srv/opentallas-scratch/codex/s81-raw-recovery-0253/$item/abstract_pin_stub.py /srv/opentallas-scratch/codex/s81-raw-recovery-0253/$item/raw.lef /srv/opentallas-scratch/codex/s81-raw-recovery-0253/$item/replayed.lef
 done

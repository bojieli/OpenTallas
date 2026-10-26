#!/bin/bash
# PATH-QC-N59-5 stage A: released kit runner (gen/run_kit.sh from 1d335f9d99 flow) to GOAL=floorplan: sdc/rtl lint, selrange,
# synth (n59 keep + ot_rst_copies canonicalize), port_bind, face_guard, reg_fanout, face_guard_odb, floorplan.
# lec.py is run as its own parallel job (stageL.sh) on the same 1_2_yosys.v, then restored into the kit.
set -uo pipefail
bash /srv/opentallas-scratch2/claude/path-qc-n59-5/gen/run_kit.sh /srv/opentallas-scratch2/claude/path-qc-n59-5/gen/native59 floorplan 32 16

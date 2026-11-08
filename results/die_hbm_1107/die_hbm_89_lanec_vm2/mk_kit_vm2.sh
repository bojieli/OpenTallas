#!/bin/bash
# DIE-HBM-89 11-07: lanec_vM2 kit = lanec_vM1 kit inputs (epyc2 /srv/opentallas-scratch2/claude/die-hbm-87/kits/lanec_vM1,
# base kit PROVENANCE 308530375d + DIE-HBM-86 vM1 edits: fshell e_hv[3:1] kept, M4 macro ring) with the files of this
# directory copied over.  KIT_SHA256.txt = sha256 of every vM2 kit file (except PROVENANCE.json) as built.
#   mk_kit_vm2.sh VM1_KIT NEW_KIT
set -euo pipefail
S=$1; K=$2; H=$(cd "$(dirname "$0")" && pwd)
mkdir -p "$K"
rsync -a --exclude run/ --exclude signoff/ --exclude 'signoff_2*' --exclude views/ --exclude lec/ --exclude __pycache__/ \
  --exclude '*.log' --exclude placed.csv --exclude hold_census.txt --exclude ot_face_flops.txt --exclude 'postcts_gate_*' \
  --exclude pin_audit.json --exclude dtap.txt --exclude prd_result.json --exclude vclk_measured_band.json \
  --exclude face_guard.json --exclude port_bind.json --exclude rtl_lint.json --exclude selrange.json --exclude selrange.rc "$S/" "$K/"
for f in config.mk face_flops.tcl macro_placement.tcl max_fanout.tcl hold_pad_struct.tcl hpad_list_insert.tcl hpad_list.txt hpad_probe.tcl FORM_VM2.json; do
  cp "$H/$f" "$K/$f"; done
(cd "$K" && find . -type f ! -name PROVENANCE.json -print0 | sort -z | xargs -0 sha256sum) | diff - "$H/KIT_SHA256.txt" && echo "vM2 kit matches KIT_SHA256.txt"

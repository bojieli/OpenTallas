#!/bin/bash
K=/srv/opentallas-scratch3/claude/die-s81-81/kits/ot_s81ph_hq_pk2_pk
mv "$K/signoff" "$K/signoff_prelec_1246"
SIGNOFF_DOCKER=docker python3 -I "$K/signoff.py" run --run-dir "$K/run" --kit "$K" --corners tt,ff --out "$K/signoff" --image openroad/orfs:asap7lock > "$K/signoff.log" 2>&1
rc=$?; grep -E '^SIGNOFF|^  - ' "$K/signoff.log" | cut -c1-260; echo RESIGN_RC $rc; exit $rc

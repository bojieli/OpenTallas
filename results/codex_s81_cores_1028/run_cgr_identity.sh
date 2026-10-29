#!/bin/bash
set -euo pipefail
r=/srv/opentallas-scratch2/claude/codex-s81-cores-1028
src=/srv/opentallas-scratch2/claude/wt/codex-s81-cores-1028
mode="$1"
gate="$src"
if test "$mode" = mutant; then gate="$r/cgr_mutant"; fi
python3 "$src/tools/dsrom_qelem_cl/qxpq_cgr_lec.py" "$gate" "$src" "$r/cgr_${mode}" --yosys "$HOME/.local/opentallas-tools/bin/yosys" --top ot_v41_rom_elem_q_qxpq_w10_gb --gold-top ot_v41_rom_elem_q_qxpq_w10_gb --gate-param CGR=8 --merge-enables --state-points

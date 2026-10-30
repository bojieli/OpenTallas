#!/bin/bash
set -eu
W=/srv/opentallas-scratch2/claude/wt/codex-s81vec-model
O=/srv/opentallas-scratch2/claude/codex-s81vec-1848
LIB=/srv/opentallas-scratch2/claude/die-s81-28/d1cmp/lib
cd "$W"
python3 tools/die_plan/core_family_slice.py run --family "$O/families_vsw.json" --core ot_s81sl_vsw --kit "$O/vsw_snapshot" --work "$O/vsw_replan" --libtt "$LIB/invbuf_tt.lib" --libff "$LIB/invbuf_ff.lib" --fit "$W/results/model_refit3_1026/uf_phys3_v1.json" --libdir "$LIB"

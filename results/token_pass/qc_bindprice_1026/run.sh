#!/bin/bash
# QC-BINDPRICE 10-26: price the FINAL strict QC bind (landing +3 x 65 + fresh R8 + CB16/sle_ctl phase classes) with the
# TOK-QK chain of codex/qc-land-price-1026@63f4e17f63 (results/token_pass/qc_v7_1025): roots.py -> rederive_edges_ext.py -> compose_edges.py.
# The bind already contains the landings and the D-QC-FE-REACH stations, so NO --add / --cb-add / --hop-add / --l9-add model adds.
# 1. CB16 x-in/root/rs path on the final bind (epyc1 ot-run unit oth-ubuntu-1911193-1793019894):
#    python3 results/token_pass/qc_bindprice_1026/roots.py <final bind dir> physical/die_plan/qwen_compute/bind/land_r8_1026/base_r8.json roots_final.json physical/die_plan/qwen_compute/bind
#    -> cb16_path.json binds.final (max_root 1, max_root_plus_rs 7)
# 2. die edges + lane ages (light python):
python3 rederive_edges_ext.py bus_groups_final.json.gz final --hop-ext --l9-stb --cb-bind final --out out
#    control (bus_groups_v7.json.gz from the 63f4e17f63 packet): ... bus_groups_v7.json.gz v7ctl_ext --hop-ext --l9-stb --cb-bind v7 --out out
# 3. compose (intel2, light; QCE engine tree + QCL S8 ages):
#    C=/srv/opentallas-scratch2/claude/claude-qc-bindprice-1026/compose (compose_edges.py, src/tree -> tok-qk-qce/compose); Q=/srv/opentallas-scratch2/claude/tok-qk-qcl/r1/die
#    python3 compose_edges.py $C q_<n> $Q/build/slice_ages.json $Q/build/vec_ages.json $Q/cal_mat/stn_ages.json "$(cat $Q/vflags.txt)" --replace out/edges_<n>_rederived.json out/lane_ages_<n>_rederived.json

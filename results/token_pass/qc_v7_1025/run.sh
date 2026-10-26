#!/bin/bash
# TOK-QK-QCV7: recompose the QCL measured-age token with/without the bind-derived v7-vs-441 CB16 path edge
cd /srv/opentallas-scratch2/claude/tok-qk-qcv7/compose; VF="$(cat /srv/opentallas-scratch2/claude/tok-qk-qcl/r1/die/vflags.txt)"
for n in none v7_vs_441; do python3 compose_edges.py /srv/opentallas-scratch2/claude/tok-qk-qcv7/compose q_$n /srv/opentallas-scratch2/claude/tok-qk-qcl/r1/die/build/slice_ages.json /srv/opentallas-scratch2/claude/tok-qk-qcl/r1/die/build/vec_ages.json /srv/opentallas-scratch2/claude/tok-qk-qcl/r1/die/cal_mat/stn_ages.json "$VF" /srv/opentallas-scratch2/claude/tok-qk-qcv7/compose/edges_$n.json; done

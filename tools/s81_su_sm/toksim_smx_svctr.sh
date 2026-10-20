#!/usr/bin/env bash
# TOKSIM-S81B/SMX: traced run (+trace=1) of the RELEASE svc_rs 16-slice bench exe (TOKSIM-S81/SU build, 19bf4121e, ST0) on full1m
X=/srv/opentallas-scratch/claude/toksim-s81-su/out_svc/base_d0s0/obj_m40000/Vtb_dsdv_svc_rs
O=/srv/opentallas-scratch/claude/toksim-s81b-smx/svctr; mkdir -p $O; sha256sum $X > $O/exe.sha256
echo HOST $(hostname) $(date)
for C in full1m short300; do ( $X +dir=/srv/opentallas-scratch/claude/toksim-s81-su/vec/$C +seed=1 +trace=1 > $O/run_${C}_s1.log 2>&1; echo EXIT $? >> $O/run_${C}_s1.log ) & done
wait; grep -h '^SVCRS ' $O/*.log

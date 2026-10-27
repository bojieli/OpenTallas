#!/bin/bash
# HBM-MU-QUAD-4 keybuf: SBY k-induction proof of the serialised wrapper (inner cut), full 8792-bit width, NB = 2 3 4
WT=/srv/opentallas-scratch2/claude/wt/hbm-mu-quad-4-1027; F=$WT/results/hbm_mu_quad_4/keybuf/formal
cp $WT/rtl/hbm_next/idxn/ot_hnx_idxn_keybuf_ser.sv $F/
for nb in ${NBS:-2 3 4}; do
 docker run --rm --memory=16g --memory-swap=16g --cpus=2 -u $(id -u):$(id -g) -v $F:/w -w /w openroad/orfs:asap7lock \
  bash -c "sby -f fv_nb$nb.sby > fv_nb$nb.log 2>&1; tail -3 fv_nb$nb.log"
done

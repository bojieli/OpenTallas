#!/bin/bash
# S81-ROMOPT-A: frame images for CFG (o1o2|o1) x 4 layers x 4 frames + golden tie per layer
set -u; D=/srv/opentallas-scratch/claude/s81-romopt-a; cd $D/root; export PYTHONDONTWRITEBYTECODE=1
CFG=$1; case $CFG in o1) export OT_XS_QPAIRS=10 OT_XS_COMPACT_TAILS=0;; o1o2nc) export OT_XS_COMPACT_TAILS=0;; esac
O=$D/out/images_$CFG; mkdir -p $O
for L in L0 L2 L14 L20; do
  timeout 3600 python3 tools/s81_dv/layer_prog/xs_place.py tie --fixtures /srv/opentallas-scratch/claude/s81-calpipe/fixtures/$L --layer $L --out $O/tie_$L.json > $O/tie_$L.log 2>&1; echo "TIE $CFG $L rc=$? $(grep -c 'bad 0' $O/tie_$L.log) ok-lines"
  for F in u_f_0L00 u_f_2L00 u_f_3L01 u_f_3L02; do
    ( timeout 7200 python3 $D/imagesa.py $O $L $F > $O/${L}_$F.log 2>&1; echo "IMG $CFG $L $F rc=$? $(grep -E 'IMAGESA|Error' $O/${L}_$F.log | tail -1 | cut -c1-300)" ) &
  done
done; wait; echo IMAGESA_DONE $CFG

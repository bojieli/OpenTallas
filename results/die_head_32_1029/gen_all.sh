#!/bin/bash
# DIE-HEAD-32: face-flop re-kit gen of 4 HEAD types on the 25-type source + hk5m delta (src25m)
W=/srv/opentallas-scratch2/claude/wt/die-head-32; B=/srv/opentallas-scratch2/claude/die-head-32
for T in hd_host_n hd_mesh_e hd_spn hd_spn_end; do
  python3 $B/head_rekit_hk5m.py $W $B/src25m $B/rekit/$T $T > $B/rekit/$T.gen.log 2>&1; echo "$T rc=$?" >> $B/rekit/gen_rc.txt
done

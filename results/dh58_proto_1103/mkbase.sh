#!/bin/bash
# DH58-PROTO: tap-arrival proof (both-edge) of a combo GRT run.  usage: mkbase.sh V   (kit_V, out_V_<C> -> base_V)
set -u; P=/srv/opentallas-scratch2/claude/dh58/proto; cd $P; V=$1; TL=$P/wt/tools/die_plan
rm -rf base_$V; mkdir -p base_$V; cp /srv/opentallas-scratch2/claude/die-head-48/sta/proof_l48c/mesh.json base_$V/
for c in TT FF; do O=out_${V}_$c; python3 - $O $c <<"PY"
import sys
O, c = sys.argv[1:3]
E = open(f"{O}/edges_{c}.txt").read().splitlines(); A = open(f"{O}/arr_{c}.txt").read().splitlines()
at = [l for l in A if l.startswith("T ")]
open(f"{O}/both_{c}.txt", "w").write("\n".join([E[0]] + at + [l for l in E[1:] if l[:2] in ("F ", "N ", "M ")]) + "\n")
PY
python3 $TL/trial_tap_arrivals.py kit_$V/kit/clock/tree.json $O/both_$c.txt $c base_$V/tap_arrivals_$c.json | /usr/bin/tail -n 1; done

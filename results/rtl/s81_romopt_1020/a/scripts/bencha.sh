#!/bin/bash
set -u; D=/srv/opentallas-scratch/claude/s81-romopt-a; cd $D/root; export PYTHONDONTWRITEBYTECODE=1
for CFG in o1o2 o1; do ( if [ $CFG = o1 ]; then export OT_XS_QPAIRS=10; fi
  rm -rf $D/out/bench_$CFG; timeout 5400 python3 $D/bencha.py $D/out/bench_$CFG > $D/out/bench_$CFG.log 2>&1; echo "BENCHA $CFG rc=$? $(grep -E 'VERDICT|Error' $D/out/bench_$CFG.log|tail -2)" ) & done; wait
for B in v_h9nx_e5 v_h10_e2 v_h9MX_e1; do echo "SRCCHK $B $(sha256sum -c /srv/opentallas-scratch/claude/toksim-s81c-fseq/$B/sources.sha256 2>&1 | grep -vc ': OK$') not-ok"; done
echo "SRCCHK romcap_bench $(sha256sum -c /srv/opentallas-scratch/claude/s81-romcap/out/bench/sources.sha256 2>&1 | grep -vc ': OK$') not-ok"

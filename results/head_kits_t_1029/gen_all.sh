#!/bin/bash
cd /srv/opentallas-scratch2/claude/head-kits-t
for T in "$@"; do
  /usr/bin/time -f "%e s %M KB" python3 head_rekit_hk5m.py /srv/opentallas-scratch2/claude/wt/head-kits-t src25m_kt rekit/$T $T > rekit/$T.gen.log 2>&1; echo "$T rc $?" >> gen_rc.txt
done

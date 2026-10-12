#!/bin/bash
export PATH=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin:$PATH
cd /srv/opentallas-scratch/claude/s81-suhc/src_3ef72f846
P=/srv/opentallas-scratch/claude/s81-suhc/su_cases_v2_ildr.pkl
for h in 1 2; do
  H=/srv/opentallas-scratch/claude/s81-suhc/hc64_h${h}_3ef72f846
  python3 tools/s81_suhc/hc_gate.py prep --cases $P --out $H --ng 64 || exit 1
  for m in 0 1 3; do ot-heavy --mem 24 -- python3 tools/s81_suhc/hc_gate.py run --out $H --ng 64 --hier $h --mut $m > $H.m$m.log 2>&1 & done
done
H=/srv/opentallas-scratch/claude/s81-suhc/hc256_h1_3ef72f846
(python3 tools/s81_suhc/hc_gate.py prep --cases $P --out $H --ng 256 && ot-heavy --mem 30 -- python3 tools/s81_suhc/hc_gate.py run --out $H --ng 256 --hier 1 --mut 0 > $H.m0.log 2>&1) &
wait; echo ALLDONE

#!/bin/bash
# HBM-R15 C16 plan delta on Codex pin6_bundle (C15 3a73d67be12d + XQ 362.88 + HC pair E pins). data intel2:/srv/opentallas-scratch2/claude/hbm-r15-1027
set -euo pipefail
R=/srv/opentallas-scratch2/claude/hbm-r15-1027; Q=/srv/opentallas-scratch2/claude/hbm-mu-quad-7-1027
cd $R
rm -rf c16 && rsync -aL --exclude gates /srv/opentallas-scratch2/claude/codex-hbm-plan-1351/pin6_bundle/ c16/
sha256sum c16/die_plan.json > c16/basis.sha256
python3 tools/c16_delta.py c16 ep_wesplit_pins_5a4807c8.json
python3 $Q/epall.py c16 > c16/epall_before.log
python3 $Q/epall.py c16 --fix --only 'u_hb_coll_Q_edge__q[01]|u_ep_N0|u_ep_N2|u_ep_S0|u_ep_S1|u_host_ep|u_xq_Q_p[01]_eg' > c16/epall_fix.log
python3 $Q/epall.py c16 > c16/epall_after.log
python3 $Q/relax_route.py c16 400 405 --noadd > c16/relax_route.log
python3 $Q/relax_hop.py c16 400 405 > c16/relax_hop.log
python3 $Q/pg_adopt.py c16 > c16/pg_adopt.log
sha256sum c16/die_plan.json | tee c16/die_plan.sha256
bash $Q/gates.sh $R/c16

#!/bin/bash
# HBM-MU-QUAD-8 plan event c15 on c14 (claude/hbm-mu-quad-7-1027@e41772821a). data intel2:/srv/opentallas-scratch2/claude/hbm-mu-quad-7-1027
set -euo pipefail
cd /srv/opentallas-scratch2/claude/hbm-mu-quad-7-1027
rm -rf c15 && rsync -a --exclude gates c14/ c15/
python3 pretree_clk.py c15                       # pretree clk_ctl = actual centre BPin
python3 fixtrack.py c15 --snap-pins              # pins back on tracks after the 8.64 snap (offsets), stray pins snapped
python3 xq_split.py c15 1296                     # xq E->W/S by partner side
python3 epall.py c15 --fix --only 'u_xq_Q_p[01]_eg' # xq chain endpoints onto the moved pins (global endpoint truth: REPORT only, see epall_c14)
python3 epall.py c15                             # re-measure
python3 relax_route.py c15 400 405 --noadd       # street route re-place, count kept
python3 relax_hop.py c15 400 405                 # min-hop (wire over cores M6/M7), count kept else +1
# 2 chains still need +2 because their launch endpoint is a stale interior point of body_n2__q1 (actual pins on its S face beside reduce/vm)
python3 epall.py c15 --fix --only 'u_hb_coll_Q_body_n2__q1' --conns 'qout_8_g2_w_o_u_out_u_dst_d\|u_hb_coll_Q_reduce|qout_13_g2_w_o_u_out_u_dst_d\|u_hb_coll_Q_vm' | head -1
cp c15/relax_route_report.json c15/relax_route_report_pass1.json
python3 relax_route.py c15 400 405 --noadd | tail -1
python3 relax_hop.py c15 400 405 | tail -2
python3 entry_fix.py c15                        # GEOM-30: 3 resized types' clock entries to the new centres
python3 pg_adopt.py c15                         # one-grid rule: G12 PG grid + edge-fill C4 lattice sidecar
sha256sum c15/die_plan.json | tee c15/die_plan.sha256

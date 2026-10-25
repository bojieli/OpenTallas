#!/bin/bash
# HBM-BIND: regenerate the B2 wiring delta, the B2 die top and its port-bind report (epyc2 scratch)
cd /srv/opentallas-scratch2/claude/hbm-bind/top || exit 2
B=/srv/opentallas-scratch2/claude/tokd-hbm2/r18h5_src
python3 make_wiring.py --die die_r18h5.v.gz --asbuilt asbuilt.json "$@" --out wiring.json > mw.log 2>&1 || { cat mw.log; exit 3; }
python3 b2_top.py --die die_r18h5.v.gz --asbuilt asbuilt.json --delta wiring.json --out outw > b2.log 2>&1; echo "b2_top rc=$?"
rm -f pb_w.json pb_w.log
python3 die_port_bind.py outw/die_b2.v --top hbm_b2_die --rtl-root $B/rtl --rtl-root $B/physical -f files_abs.f $EXTRA --out pb_w.json > pb_w.log 2>&1; echo "port_bind rc=$?"
grep -E 'WIDTH|UNPARSED|STUB|child|UNDRIVEN|OPEN|NOT_IN|DIE_PORT' pb_w.log | cut -c1-300

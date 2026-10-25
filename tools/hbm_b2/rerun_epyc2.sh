#!/bin/bash
# HBM-BIND: regenerate the B2 wiring delta, the B2 die top and its port-bind report (epyc2 scratch).
# OVL (default ./ovl): branch RTL files that are new or changed vs the r18h5 bundle; each one is indexed and preferred.
cd /srv/opentallas-scratch2/claude/hbm-bind/top || exit 2
B=/srv/opentallas-scratch2/claude/tokd-hbm2/r18h5_src
OVL=${OVL:-$PWD/ovl}
X=""; for f in $(find $OVL -name '*.sv' -o -name '*.v' 2>/dev/null | sort); do X="$X --rtl-file $f --prefer $f"; done
# the bundle file list, with every overlaid path pointing at the overlay copy
while read rel; do if [ -f "$OVL/$rel" ]; then echo "$OVL/$rel"; else echo "$B/$rel"; fi; done < $B/files.f > files_abs.f
python3 make_wiring.py --die die_r18h5.v.gz --asbuilt asbuilt.json "$@" --out wiring.json > mw.log 2>&1 || { cat mw.log; exit 3; }
python3 b2_top.py --die die_r18h5.v.gz --asbuilt asbuilt.json --delta wiring.json --out outw > b2.log 2>&1; echo "b2_top rc=$?"
rm -f pb_w.json pb_w.log
python3 die_port_bind.py outw/die_b2.v --top hbm_b2_die --rtl-root $B/rtl --rtl-root $B/physical -f files_abs.f $X --out pb_w.json > pb_w.log 2>&1; echo "port_bind rc=$?"
grep -E 'WIDTH|UNPARSED|STUB|child|UNDRIVEN|OPEN|NOT_IN|AMBIG|DIE_PORT' pb_w.log | cut -c1-300

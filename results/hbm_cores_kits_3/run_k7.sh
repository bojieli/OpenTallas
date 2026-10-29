#!/bin/bash
set -u
echo "$(date) start src $(git -C /srv/opentallas-scratch2/claude/wt/hbm-cores-kits-3 rev-parse --short=10 HEAD)"
python3 /srv/opentallas-scratch2/claude/wt/hbm-cores-kits-3/results/die_hbm_kits_1027/mk_c20.py /srv/opentallas-scratch2/claude/die-hbm-10/c24 /srv/opentallas-scratch2/claude/hbm-cores-kits-1/k1/views.json /srv/opentallas-scratch2/claude/hbm-cores-kits-3/k7/slices /srv/opentallas-scratch2/claude/hbm-cores-kits-3/k7/kits /srv/opentallas-scratch2/claude/wt/hbm-cores-kits-3 ot_pdie_serdes --tag _k7 --gen-args "--macro-placement /srv/opentallas-scratch2/claude/wt/hbm-cores-kits-3/results/hbm_cores_kits_3/mp/ot_pdie_serdes.json --macro-inst-fmt {k}" > /srv/opentallas-scratch2/claude/hbm-cores-kits-3/k7/mk.log 2>&1
for k in /srv/opentallas-scratch2/claude/hbm-cores-kits-3/k7/kits/*/; do k=${k%/}; n=$(basename $k); [ -f $k/freeze.json ] || continue
  ( cd /srv/opentallas-scratch2/claude/wt/hbm-cores-kits-3/tools/die_plan && timeout 1800 python3 kit_preflight.py --contract --plan-dir /srv/opentallas-scratch2/claude/die-hbm-10/c24 --out /srv/opentallas-scratch2/claude/hbm-cores-kits-3/k7/preflight/$n.json $k > /srv/opentallas-scratch2/claude/hbm-cores-kits-3/k7/preflight/$n.txt 2>&1 ) ; done
echo "$(date) done"; touch /srv/opentallas-scratch2/claude/hbm-cores-kits-3/k7/RUN_DONE

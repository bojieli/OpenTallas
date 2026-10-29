#!/bin/bash
# DIE-HBM-21: AUTO-GEOM (geom_check.sh, GRT 50 it) on a probe kit 3_place.odb.  review.sh KITDIR OUTDIR ID
K=$(cd $1 && pwd); O=$2; mkdir -p $O; O=$(cd $O && pwd)
ODB=$(ls $K/run/results/asap7/*/base/3_place.odb); W=$(sed -nE "s/^export DIE_AREA = 0 0 (\S+) (\S+)/\1x\2/p" $K/config.mk | sed -E "s/\.?0+x/x/; s/(\.[0-9]*[1-9])0+$/\1/; s/\.0+$//")
python3 -c "import json,sys;json.dump(dict(odb=sys.argv[1],image=\"openroad/orfs:asap7lock\",id=sys.argv[2],mem_gb=16,grt=True,grt_iter=50,rules_args=[\"--all-kits\",\"--outline\",sys.argv[3],\"--odb\",sys.argv[1]]),open(sys.argv[4],\"w\"))" "$ODB" "$3" "$W" "$O/check.json"
bash /srv/opentallas-scratch2/claude/die-hbm-21/epS/tools/geom_check.sh $O > $O/review.log 2>&1; echo "rc $?" >> $O/review.log

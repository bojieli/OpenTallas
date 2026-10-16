#!/bin/bash
# run2.sh <candidate> <tag> <ME extra stages> <other extra stages (-1 = unbounded)> [critweight]
set -e
c=$1;tag=$2;x=$3;ox=$4;w=${5:-1.0};G=/home/ubuntu/artifacts/globalfp/qwen/structural-1417/upper-specialized-routing-capacity-source.json
cd /home/ubuntu/artifacts/globalfp/qwen/fpq-1705
if [ ! -f r-$c/all-bus-route-costs.json ]; then
 python3 router/prepare_route.py $G $c-homes.json r-$c 62.5 0.5 actual_bound_io >/dev/null
 router/route r-$c/route.in r-$c/route.out 12 1.0 2>/dev/null
 python3 router/audit_route.py r-$c $G $c-homes.json 0.6 > r-$c/audit.log
 python3 router/me_detour.py r-$c r-$c/route.out $G $c-homes.json > /dev/null
fi
t=r-$c/$tag;mkdir -p $t;ln -sf ../route.in $t/route.in;ln -sf ../route-metadata.json $t/route-metadata.json
python3 router/crit.py r-$c r-$c/all-bus-route-costs.json 1.0 $x $ox $t/crit.txt ${ADD:-2} ${MEADD:-0} > $t/crit.log
router/route2 r-$c/route.in $t/route.out ${PASSES:-15} 1.0 $t/crit.txt $w ${MAXADD:-0}
python3 router/audit_route.py $t $G $c-homes.json 0.6 > $t/audit.log
python3 router/me_detour.py r-$c $t/route.out $G $c-homes.json > /dev/null
python3 router/hot.py r-$c $t/route.out 8 > $t/hot.log
python3 - $t <<'P'
import json,sys
t=sys.argv[1];a=json.load(open(t+'/route-audit.json'));m=json.load(open(t+'/me-detour.json'))
print(t,'cut',round(a['worst_grid_cut_util'],4),'ME pp',m['pin_pair']['me_loop'],'routed',m['routed_detour']['me_loop'],'exposed',m['routed_detour']['exposed_stage_cycles_per_token'],'relayFF',m['routed_detour']['relay_ff'],'mm2',m['routed_detour']['relay_area_mm2'],'regressed',m['stage_regressed_buses'])
P

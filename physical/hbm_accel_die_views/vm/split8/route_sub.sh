#!/bin/bash
# route_sub.sh <label> <master> <top-source> [args]: common/route_view.sh for an 8-way VM sub-tile BEFORE the generator knows
# it (r23v): the outline + pins come from vm/split8/ports/<master> (make_vm_split8.py) instead of tools/hbm_die_views.py,
# and the LEF check compares the exported LEF pins with that io_place.tcl.  Same env as route_view.sh.
set -u
S=physical/hbm_accel_die_views/vm/split8; R=physical/hbm_accel_die_views/common/route_view.sh
# the ports line is matched whole (route_view.sh 1ad3621a6 added ${VARIANT:+--variant $VARIANT} and an rc=ports guard)
sed -e "s#^python3 tools/hbm_die_views.py .*ports --master \$master --out \$W/ports .*#mkdir -p \$W/ports \&\& cp -r $S/ports/\$master \$W/ports/#" \
    -e '/hbm_die_views.py .*check --master/d' -e '/^echo "check_rc/d' $R > $S/.route_view_sub.sh
grep -q "cp -r $S/ports" $S/.route_view_sub.sh || { echo "route_sub.sh: route_view.sh ports line not found" >&2; exit 3; }
bash $S/.route_view_sub.sh "$@"
lab=$1; master=$2; W=$OUT/$lab
python3 - "$W/view/$master.lef" "$S/ports/$master/io_place.tcl" > $W/check.json <<'PY'
import json, re, sys
try:
    lef = set(re.findall(r'^\s*PIN (\S+)', open(sys.argv[1]).read(), re.M))
except OSError as e:
    print(json.dumps({'verdict': 'NO_LEF', 'error': str(e)})); sys.exit(0)
want = set(re.findall(r'-pin_name \{(\S+)\}', open(sys.argv[2]).read()))
lef = {p.replace('\\', '') for p in lef} - {'VDD', 'VSS'}
print(json.dumps({'verdict': 'MATCH' if lef == want else 'MISMATCH', 'lef_pins': len(lef), 'io_pins': len(want),
                  'missing': sorted(want - lef)[:20], 'extra': sorted(lef - want)[:20]}))
PY
echo "check_rc=$?" >> $W/exit

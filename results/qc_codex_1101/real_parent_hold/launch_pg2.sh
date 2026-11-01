#!/bin/bash
set -eu
B=/srv/opentallas-scratch2/claude/codex-parent-hold/r3
P=$B/hold_parent_pg2
mkdir -p "$P"
cp "$B/hold_parent/"*.{tcl,mk,sdc,v,json} "$P/" 2>/dev/null || true
cp -r "$B/hold_parent/macros" "$P/"
python3 - "$P/pdn.tcl" <<'PY'
import sys
p=sys.argv[1];s=open(p).read();s=s[:s.index('define_pdn_grid -macro')];s+='''add_pdn_stripe -grid stdcell -layer M8 -width 0.288 -pitch 8.64 -offset 4.128
add_pdn_connect -grid stdcell -layers {M7 M8}
define_pdn_grid -macro -name core_pg_M7 -instances {u_send u_r0.u_bs0 u_other} -voltage_domains {CORE} -halo {0}
add_pdn_connect -grid core_pg_M7 -layers {M7 M8}
''';open(p,'w').write(s)
PY
bash "$B/run_route.sh" "$P"

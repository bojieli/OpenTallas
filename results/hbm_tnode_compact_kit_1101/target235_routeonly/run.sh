#!/bin/bash
set -uo pipefail
R=/srv/opentallas-scratch2/claude/codex-hbm-tnode-target235-routeonly-0010
K=$R/kit
base=(sudo docker run --rm --cpus 2 --memory 8g --memory-swap 8g -v "$K":/work -v "$R":/out -w /out -e HUID="$(id -u)" -e HGID="$(id -g)")
"${base[@]}" --name "codex-tnode235-routeonly-$$" -e OT_CORNER=TT -e ODB=/work/run/results/asap7/hbc_ot_hnx_fused_tnode/base/4_cts.odb openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit /out/route_only.tcl > /out/route.log 2>&1; rc=$?; chown $HUID:$HGID /out/*.json /out/*.tcl /out/route.log /out/cong.rpt /work/route_only.odb 2>/dev/null || true; exit $rc'
route_rc=$?
if [ "$route_rc" != 0 ]; then exit "$route_rc"; fi
"${base[@]}" --name "codex-tnode235-routeonly-pgaudit-$$" -e OT_PG_AUDIT_ODB=/work/route_only.odb -e OT_PG_AUDIT_REPORT=/out/saved_pg.json openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit /out/tools/audit_native_pg.tcl > /out/saved_pg.log 2>&1; rc=$?; chown $HUID:$HGID /out/saved_pg*; exit $rc'
saved_rc=$?
if [ "$saved_rc" != 0 ]; then exit "$saved_rc"; fi
rc=0
for corner in TT FF; do
 "${base[@]}" --name "codex-tnode235-routeonly-gate-${corner}-$$" -e OT_CORNER="$corner" -e OT_POSTCTS_GRT=1 -e ODB=/work/route_only.odb openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit /work/postcts_gate.tcl > /work/postcts_gate_${OT_CORNER}.log 2>&1; rc=$?; chown $HUID:$HGID /work/postcts_gate*; exit $rc'
 one=$?
 [ "$one" = 0 ] || rc="$one"
done
python3 - "$R" <<'PY'
import json,pathlib,re,sys
r=pathlib.Path(sys.argv[1]);k=r/'kit';corners={c:json.loads((k/('postcts_gate_'+c+'.json')).read_text()) for c in ['tt','ff']}
if any(x.get('parasitics')!='global_routing' for x in corners.values()):raise RuntimeError('fresh global-routing RC missing')
log=(r/'route.log').read_text();totals=re.findall(r'^Total\s+\d+\s+\d+\s+[\d.]+%\s+\d+\s*/\s*\d+\s*/\s*(\d+)',log,re.M)
if not totals:raise RuntimeError('native raw congestion result missing')
pg={name:json.loads((r/(name+'.json')).read_text()) for name in ['before_pg','after_pg','saved_pg']}
result=dict(scope='ROOT authorized235 fullCLOCK+SIGNAL50 route-only diagnostic; NOT production repair/SIGNED',raw_overflow=int(totals[-1]),clock_signal_route=True,iterations=50,repair=False,new_cells=False,structural_guard_equal=(r/'before_guard.tcl').read_bytes()==(r/'after_guard.tcl').read_bytes(),PG={name:dict(status=x.get('status'),checked=x.get('checked'),failure_count=x.get('failure_count')) for name,x in pg.items()},corners=corners,SIGNED=False)
(r/'RESULT.json').write_text(json.dumps(result,indent=1)+'\n')
print('ROUTE_ONLY_RESULT',json.dumps(result))
PY
summary_rc=$?
[ "$summary_rc" = 0 ] || rc="$summary_rc"
exit "$rc"

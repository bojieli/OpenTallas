import json,sys,tempfile
from pathlib import Path
from layer_prog.emitted_rstd_return import collect
R=Path('/srv/opentallas-scratch2/claude/codex-ds-norm-event3-1030')
args=[Path('/srv/opentallas-scratch2/claude/codex-s81-inventory-1030/inventory.json'),Path('/srv/opentallas-scratch2/claude/die-s81-34/ev3bind/out/bind_latency.json'),R/'producer_params.json']
r=collect(*args);assert len(r['leaves'])==80 and not r['advertised_lane_counts_are_qualified_relative_dates']
with tempfile.TemporaryDirectory(prefix='rstd_native_',dir=R)as temp:
 p=Path(temp)/'bad_native.json';raw=json.loads(args[2].read_text());a,b=raw['leaves'][:2]
 for key in('native_file','native_sha256','native_master'):a[key]=b[key]
 p.write_text(json.dumps(raw))
 try:collect(*args[:2],p)
 except ValueError as exc:r['wrong_native_receiver_control']=str(exc)
 else:raise ValueError('wrong receiver/top association escaped')
(R/'rstd_return.json').write_text(json.dumps(r,indent=1)+'\n');print(r['status'],80,'mappingonly,phaseauthorityheld')

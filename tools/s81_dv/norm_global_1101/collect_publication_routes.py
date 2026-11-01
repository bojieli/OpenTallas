from pathlib import Path
import json,sys
r=Path('/srv/opentallas-scratch2/claude/codex-ds-norm-1101');sys.path.insert(0,str(r/'code'))
from layer_prog.emitted_nx_routes import collect
m={'ri_w':list(range(1045)),'ri_e':list(range(1045)),'vi':list(range(276))}
x=collect(r/'norm_ece/inventory.json','/srv/opentallas-scratch2/claude/codex-s81-1101/bind_t48_pg/out/bind_latency.json',m)
x['packet_active_contract']={'ri_w':'all21header+1024BF16payload bits0..1044','ri_e':'all21header+1024BF16payload bits0..1044','vi':'all276literalfragmentbits'};x['schema']='opentallas.s81.current_publication_transport.v1';x['source_scope']='actualcurrentt48PG boundary source/header/payload only, fullVbridges composed separately';x['global_calendar_qualified']=False
out=r/'publication_current';out.mkdir(exist_ok=False);(out/'.keep').write_text('criticalactualpublication source transport\n');(out/'routes.json').write_text(json.dumps(x,indent=1)+'\n');print('CURRENT_PUBLICATION_BOUNDARIES direct',x['direct_paths'],'ring',len(x['ring']),'source',x['source_top_sha256']);print('UNRESOLVED',[(a['slice'],a['input'],a.get('reason'))for a in x['ring']if a['status']!='PASS_DIRECT_NX'])

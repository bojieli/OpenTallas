"""Read selected canonical leaf interfaces only; no diagnostic output waivers."""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--receipt',type=Path,required=True);p.add_argument('--parser-tree',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
sys.path.insert(0,str(a.parser_tree/'tools'));import die_port_bind as P
r=json.loads(a.receipt.read_text());cache={};sources={};unknown=[];named=[];opens=[]
thermal=re.compile(r'therm|temp|telemetr|sensor',re.I)
for master,rec in r['masters'].items():
    path=Path(rec['rtl'])
    if path not in cache:
        data=path.read_bytes();sources[str(path)]=hashlib.sha256(data).hexdigest();cache[path]=P.parse_modules(data.decode(errors='replace'),str(path))
    matches=[m for m in cache[path] if m.name==master]
    if len(matches)!=1:unknown.append(dict(master=master,file=str(path),definitions=len(matches)));continue
    mod=matches[0]
    if getattr(mod,'port_parse_errors',None):unknown.append(dict(master=master,file=str(path),port_parse_errors=mod.port_parse_errors))
    named += [dict(master=master,port=pn,direction=direction,file=str(path)) for pn,(direction,_) in mod.ports.items() if thermal.search(pn)]
    for pn in rec['output_open']:
        safety=bool(re.search(r'fault|abort|ready|permission|auth|consensus|irq|ack',pn))
        opens.append(dict(master=master,port=pn,file=str(path),role='FUNCTIONAL_SAFETY_OR_CONTROL_NO_WAIVER' if safety else 'ROLE_UNRESOLVED_NO_WAIVER'))
doc=dict(status='NAMED_INTERFACE_INVENTORY_ONLY_NO_WAIVERS',receipt_sha256=hashlib.sha256(a.receipt.read_bytes()).hexdigest(),
         master_count=len(r['masters']),summary_open_output_types=r['summary']['output_open_ports'],listed_receipt_open_output_types=len(opens),named_thermal_telemetry_ports=named,unresolved_interfaces=unknown,source_sha256=sources,open_outputs=opens,
         limits='Per-master receipt open-output lists are capped and are examples, not complete counts. No standalone named thermal/temperature/telemetry/sensor ports found is not a statement about encoded opaque bundle fields. Existing diagnostics and faults remain functional/unresolved until separately source-qualified.')
a.out.write_text(json.dumps(doc,indent=1)+'\n');print(json.dumps(dict(masters=len(r['masters']),matches=named,unresolved=unknown,open_port_types=len(opens))))

#!/usr/bin/env python3
"""Bind mapped provider ports to actual native endpoint ITerms in a fresh ODB.
Reuses the retained legal R0 clock body pack, without changing clock cells,
connections or topology. This source needs new loaded routed timing.
"""
import argparse,hashlib,json
from pathlib import Path
import odb
p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--packed-tree',required=True);p.add_argument('--mapped',required=True);p.add_argument('--clock-bindings',required=True);p.add_argument('--endpoints',required=True);p.add_argument('--out',required=True);a=p.parse_args();o=Path(a.out);o.mkdir(parents=True,exist_ok=True);d=odb.dbDatabase.create();odb.read_db(d,a.source);b=d.getChip().getBlock();D=b.getDbUnitsPerMicron();tree=json.load(open(a.packed_tree));sites=tree['sites'];changed=0
clocks=[i for i in b.getInsts() if i.getName().startswith('ck_')];assert len(clocks)==len(sites)==15296
before={i.getName():sorted((t.getMTerm().getName(),t.getNet().getName() if t.getNet() else None) for t in i.getITerms()) for i in clocks}
for i in clocks:
 name=i.getName()[3:];assert name in sites;x,y=sites[name];old=tuple(i.getOrigin());i.setOrient('R0');i.setOrigin(round(x*D),round(y*D));i.setPlacementStatus('FIRM');changed+=tuple(i.getOrigin())!=old
assert before=={i.getName():sorted((t.getMTerm().getName(),t.getNet().getName() if t.getNet() else None) for t in i.getITerms()) for i in clocks}
ports=json.load(open(a.mapped))['modules']['ot_die_start_stages']['ports'];bindings=json.load(open(a.clock_bindings))['ports'];by={q['net']:q for q in json.load(open(a.endpoints))['uses']};details=[]
for name,q in ports.items():
 if name in bindings:
  net=b.findNet(bindings[name]['net']);assert net,name;continue
 assert name in by,name;u=by[name];i=b.findInst(u['part']);assert i,u['part'];it=i.findITerm(u['pin']);assert it,(u['part'],u['pin']);net=it.getNet();assert net and net.getName()==name,(name,net.getName() if net else None)
 expect='INPUT' if q['direction']=='output' else 'OUTPUT';assert str(it.getMTerm().getIoType())==expect,(name,expect)
 drivers=[t for t in net.getITerms() if str(t.getMTerm().getIoType())=='OUTPUT'];assert len(drivers)==(1 if q['direction']=='input' else 0),(name,len(drivers))
 bindings[name]=dict(net=name,role='reset' if name.startswith('rraw_') else 'start',native_endpoints=[dict(inst=u['part'],pin=u['pin'])]);details.append(dict(port=name,inst=u['part'],pin=u['pin'],direction=q['direction']))
assert set(bindings)==set(ports);odb.write_db(d,str(o/'native_source.odb'));digest=hashlib.sha256((o/'native_source.odb').read_bytes()).hexdigest();json.dump(dict(schema='ot_provider_boundary_bindings/1',source_odb_sha256=digest,ports=bindings),open(o/'bindings_native.json','w'),indent=1);receipt=dict(verdict='NATIVE_SOURCE_ENDPOINTS_BOUND',clock_cells=len(clocks),clock_cells_moved=changed,clock_topology_connections_preserved=True,native_boundary_ports=len(details),clock_ports=len(ports)-len(details),source_odb_sha256=digest,scope='Native abstract endpoints and legal packed clock bodies; new routed clock/load/reset timing still required',endpoints=details);json.dump(receipt,open(o/'native_binding_receipt.json','w'),indent=1);print(json.dumps({k:v for k,v in receipt.items() if k!='endpoints'}))

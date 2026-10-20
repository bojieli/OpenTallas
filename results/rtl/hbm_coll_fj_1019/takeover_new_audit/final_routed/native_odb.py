import pathlib,sys,csv,json,collections,hashlib
base=pathlib.Path('/audit');sys.path[:0]=[str(base/'current_audit/tools'),str(base/'current_audit/tools/ref_tile')]
import native_census as N
import textbook_lint as T
q=sys.argv[1];libs=sys.argv[2:];roles,receipts=N.liberty_roles(libs);g=T.Graph();cells={}
for master,name,pin,net in csv.reader((base/f'fj{q}_native_graph_cells.tsv').open(),delimiter='\t'):
 if name not in cells:cells[name]=[master,name,{}]
 if pin in cells[name][2]:raise ValueError('duplicate actual ITerm')
 cells[name][2][pin]=[g.net(net)]
g.cells=[tuple(x) for x in cells.values()]
for direction,name,net in csv.reader((base/f'fj{q}_native_graph_ports.tsv').open(),delimiter='\t'):g.ports[name]=(direction.lower(),g.net(net))
d=N.census(g,roles);d.update(schema='opentallas.native_odb_census.v1',graph_authority='actual5_1GRT ODB ITerms/BTerms, noVerilogexport',liberty=receipts,cells=len(g.cells),ports=len(g.ports),graph_sha256={x.name:hashlib.sha256(x.read_bytes()).hexdigest() for x in [base/f'fj{q}_native_graph_cells.tsv',base/f'fj{q}_native_graph_ports.tsv']})
(base/f'fj{q}_native_postgrt.json').write_text(json.dumps(d,indent=2)+'\n');print(q,d['status'],d['roots_examined'],d['max_dynamic_loads'],'errors',len(d['role_errors']),'violations',len(d['violations']))
if d['role_errors']:print(d['role_errors'][:3])
if d['violations']:print(d['violations'][:3])
raise SystemExit(d['status']!='PASS')

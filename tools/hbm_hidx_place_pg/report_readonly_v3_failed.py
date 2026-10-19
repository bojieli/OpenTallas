"""Same-checkpoint geometry and exact full signal-network identity; no mutation."""
import json,gzip,collections,re,hashlib,math
from pathlib import Path
p=Path('/work');o=p/'output';raw=json.loads((o/'native/raw.json').read_text());m=next(iter(raw['modules'].values()))
orig=json.load(gzip.open(p/'input/netlist.json.gz','rt'))['modules']['hidx_coupon1']; metadata={n:c for n,c in orig['cells'].items() if c['type']=='$scopeinfo'};assert all(not c['connections'] for c in metadata.values());orig['cells']={n:c for n,c in orig['cells'].items() if c['type']!='$scopeinfo'};pos=json.loads((o/'native/positions.json').read_text());u=pos['units']
mapping={n:re.sub(r'\\(.)',r'\1',n) for n in m['cells']}
assert len(set(mapping.values()))==11145 and set(mapping.values())==set(orig['cells'])
def networks(module,native=False):
 nets=collections.defaultdict(list)
 for n,c in module['cells'].items():
  for pin,bits in c['connections'].items():
   if native and c['pin_signal_types'][pin] in ['POWER','GROUND']:continue
   assert len(bits)==1,(n,pin,bits)
   nets[bits[0]].append(('cell',mapping[n] if native else n,c['type'],pin))
 for n,port in module['ports'].items():
  if native and port['signal_type'] in ['POWER','GROUND']:continue
  for idx,bit in enumerate(port['bits']):
   dest=(n if len(port['bits'])==1 and n=='clk' else f'{n}[{idx}]') if not native else n
   nets[bit].append(('port',dest,port['direction']))
 return sorted([sorted(ends) for ends in nets.values()])
a=networks(orig);b=networks(m,True);assert a==b,'FULL_NATIVE_ENDPOINT_NETWORK_MISMATCH'
identity=dict(verdict='PASS',nonphysical_scopeinfo_records=len(metadata),scopeinfo_signal_contacts=0,cells=11145,canonical_cells=8265,added_cells=2880,networks=len(a),signal_network_sha256=hashlib.sha256(json.dumps(a).encode()).hexdigest(),identifier_decode='one native OpenDB escape layer; complete injective exact-name-map required',PG_roles='native master MTerm -> ITerm inventory, all22290 bound separately')
(o/'source_placement_identity.json').write_text(json.dumps(identity,indent=2)+'\n')
rows=pos['rows'];assert len(rows)==504
boxes=[z['bbox'] for z in pos['insts'].values()];assert all(y0>=56.16*u-1 and y1<=84.24*u+1 for x0,y0,x1,y1 in boxes)
pinmodel=json.loads((p/'input/pin_geometry_model.json').read_text());actual=pos['bterms'];faces=collections.defaultdict(list);errors=[]
for pin in pinmodel['pins']:
 boxes=actual[pin['port']];assert len(boxes)==1 and len(boxes[0]['boxes'])==1
 shape=boxes[0]['boxes'][0];expect=[round(z*u) for z in pin['rect_um']];assert shape==[pin['layer']]+expect
 coord=(expect[1]+expect[3])/2/u if pin['face'] in 'WE' else (expect[0]+expect[2])/2/u
 if abs((coord-.024)/.048-round((coord-.024)/.048))>1e-6:errors.append(pin['port'])
 assert abs((expect[2]-expect[0])*(expect[3]-expect[1])/u**2-.002304)<1e-8
 faces[pin['face']].append(coord)
counts={}
for face,coords in faces.items():
 coords.sort();counts[face]=max(sum(x<=v<x+1-1e-8 for v in coords) for x in coords);assert counts[face]<=6
assert not errors,errors
summary=dict(verdict='GEOMETRY_PASS_ROUTE_ACCESS_OPEN',outline_um=[140.4,140.4],all_legal_rows=504,actual_occupied_band_um=[min(z[1] for z in boxes)/u,max(z[3] for z in boxes)/u],central_rows=104,cells=11145,area_um2=sum((z[2]-z[0])*(z[3]-z[1]) for z in boxes)/u**2,contacts=2609,fullface_counts={k:len(v) for k,v in faces.items()},max_contacts_per_1um=counts,actual_track_center_alignment_errors=errors,pin_area_um2=.002304,min_area_um2=.002,manhattan_outline_bound_um=280.8,routed_access='OPEN: no route authorized; grid/rectangle/density are actual native geometry only',cts='NOT RUN',clock_sinks=2904,reset_endpoints=0,cold_priming_edges=2,all_signal_network_identity='PASS')
(o/'geometry_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(identity));print(json.dumps(summary))

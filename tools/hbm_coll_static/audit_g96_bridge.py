#!/usr/bin/env python3
"""Independent actual bridge command, identity and registered-edge audit."""
import argparse,collections,json,pathlib
RING=[0,1,3,2]
p=argparse.ArgumentParser();p.add_argument('directory',type=pathlib.Path);a=p.parse_args()
v=json.loads((a.directory/'calendar.json').read_text());words={}
for line in (a.directory/'expanded_bridge.jsonl').open():
 x=json.loads(line);key=(x['owner'],x['cycle']);assert key not in words;words[key]=int(x['word'],16)
bridge={};input_identity={};checks=collections.Counter()
for x in v['bridge']:
 o,c,s,d,identity=x['owner'],x['cycle'],x['source'],x['out'],x['identity'];q=int(o.split('q')[1]);npt=3 if q==0 else 2;ns=npt+2;nd=2*npt+2;sw=3 if npt==3 else 2
 k=(o,c,d)
 if d is not None:
  if k in bridge:assert bridge[k]==(s,identity)
  bridge[k]=(s,identity)
 ik=(o,c,s)
 if ik in input_identity:assert input_identity[ik]==identity
 input_identity[ik]=identity
 w=words[(o,c)];assert w>>s&1
 if d is not None:assert w>>(ns+d)&1 and (w>>(ns+nd+sw*d))&((1<<sw)-1)==s
 checks['bridge_command_checks']+=1
routes={(x['owner'],x['capture'],x['sink']):x['identity'] for x in v['qroutes']}
for (o,c,s),identity in input_identity.items():
 rank,q=map(int,o[1:].split('q'));npt=3 if q==0 else 2
 if s<npt:
  assert routes[(o,c-3,s)]==identity
  checks['qslot_to_bridge_registered_edges']+=1
 else:
  direction=s-npt;prev=RING[(RING.index(q)+(-1 if direction==0 else 1))%4];pn=3 if prev==0 else 2
  producer=(f'd{rank}q{prev}',c-2-v['relay_edges_per_quarter_link'],2*pn+direction)
  assert bridge[producer][1]==identity
  checks['quarter_wire_registered_edges']+=1
arrivals={(e['dst'],e['q'],e['dst_rail'],e['receive'],e['id']) for e in v['transport_hops']}
for x in v['rx_faces']:
 o,c,port,b,identity=x['owner'],x['cycle'],x['port'],x['bridge'],x['identity'];npt=3 if o.endswith('q0') else 2;shift=(37 if npt==3 else 22)+4*port
 assert words[(o,c)]>>shift&15==int(not b)|(int(b)<<1)|4|(int(b)<<3)
 if b:assert bridge[(o,c-2,npt+port)][1]==identity
 else:
  rank,q=map(int,o[1:].split('q'))
  assert (rank,q,port,c-1,identity) in arrivals
 checks['rx_face_command_and_arrival_checks']+=1
# Every reserved endpoint write must be driven by the actual bridge output.
for e in v['transport_hops']:
 o=f'd{e["src"]}q{e["q"]}'
 assert bridge[(o,e['write']-2,e['rail'])][1]==e['id']
 checks['native_endpoint_write_drivers']+=1
result=dict(status='PASS: independent actual49/30-bit bridge control and full545 identity/edge audit',checks=dict(checks),cycles=v['cycles'],ratio=v['ratio'],qualification='Component calendar only; extra program catalog/issuer, physical relay placement and FEC/board contracts remain unqualified')
(a.directory/'independent_bridge_audit.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))

#!/usr/bin/env python3
"""Evidence only: exact GEN7 open ports and unread output source references."""
import collections, gzip, hashlib, importlib.util, json, pathlib, re
P=pathlib.Path('/srv/opentallas-scratch/claude/kv-exact-padgap-1019/gen7_strict')
W=pathlib.Path('/srv/opentallas-scratch/claude/qwen-kvsys/wt-kvs14r-4db097403-codexmub')
O=pathlib.Path(__file__).parent
spec=importlib.util.spec_from_file_location('bind',W/'tools/die_port_bind.py'); b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
pb=json.loads((P/'port_bind_v2.json').read_text()); die=P/'die_bound.v'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(die)=='7006cbd0d11ffb755902c588eec474a1a7c27d7ad77212cebe3be1fcae5aae7e'
mods={}; sources={}
for mst,rec in pb['masters'].items():
 p=pathlib.Path(rec['rtl']); p=p if p.is_absolute() else W/p
 if p not in sources:
  t=p.read_text();sources[p]=t
 mods[mst]=next(m for m in b.parse_modules(sources[p],str(p)) if m.name==mst)
nets,ti,to,insts=b.parse_die(die)
readers=collections.defaultdict(list)
for mst,inst,params,cm in insts:
 if mst not in mods:continue
 for pn,e in cm.items():
  if pn in mods[mst].ports and mods[mst].ports[pn][0] in ('input','inout'):
   for bit in b.expr_bits(e,nets) or []:readers[tuple(bit)].append([inst,pn])
openrows=[]; unreadrows=[]
for mst,inst,params,cm in insts:
 if mst not in mods:continue
 m=mods[mst];env=m.env(params)
 for pn,(direction,rng) in m.ports.items():
  if direction!='output':continue
  e=cm.get(pn,''); bits=b.expr_bits(e,nets) or []; width=m.width(pn,env)
  refs=[{'line':i,'text':line.strip()} for i,line in enumerate(pathlib.Path(m.path).read_text().splitlines(),1) if re.search(r'\b'+re.escape(pn)+r'\b',line)]
  row=dict(master=mst,instance=inst,port=pn,width=width,expression=e,parameters=params,rtl=m.path,rtl_sha256=sha(pathlib.Path(m.path)),source_references=refs,clock_reset_pins={k:v for k,v in cm.items() if re.search(r'(^ck|^clk|^rst|^por|rst_n$)',k)},classification='UNREVIEWED_STRICT_FAILURE')
  if not e:openrows.append(row)
  else:
   missing=[{'port_bit':len(bits)-1-i,'net':bit[0],'net_bit':bit[1]} for i,bit in enumerate(bits) if bit[0] in nets and tuple(bit) not in readers]
   if missing:
    row['unread_bit_count']=len(missing)
    groups=collections.defaultdict(list)
    for z in missing:groups[z['net']].append([z['port_bit'],z['net_bit']])
    row['unread_bit_pairs_by_net']=dict(groups); unreadrows.append(row)
types=sorted(set((r['master'],r['port']) for r in openrows))
assert len(types)==pb['summary']['output_open_ports']==69
manifest={str(p):sha(p) for p in sources}
out=dict(schema='opentallas.kv_functional_fault_inventory.v1',evidence_only=True,qualified=False,die_sha256=sha(die),port_bind_sha256=sha(P/'port_bind_v2.json'),strict_summary=pb['summary'],strict_failing=pb['failing'],open_types=[{'master':m,'port':p,'instances':sum(r['master']==m and r['port']==p for r in openrows)} for m,p in types],open_instances=openrows,source_manifest=manifest)
(O/'open_ports.json').write_text(json.dumps(out,indent=2)+'\n')
with gzip.open(O/'unread_outputs.json.gz','wt') as f:json.dump(dict(note='ALL raw no-reader output bits, including declared spare subranges; NOT a strict failure recount or waiver. Use original strict binder counts. Original unread_nets is truncated to200 entries; this recomputes whole-die raw readers.',outputs=unreadrows),f)
(O/'unread_classes.json').write_text(json.dumps(pb['unread_classes'],indent=2)+'\n')
print(json.dumps({'open_types':len(types),'open_instances':len(openrows),'unread_output_records':len(unreadrows),'strict_unread_bits':pb['summary']['unread_net_bits']}))

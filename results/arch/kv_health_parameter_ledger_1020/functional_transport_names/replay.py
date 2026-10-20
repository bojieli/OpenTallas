import sys,json,re,hashlib,types
from pathlib import Path
from collections import defaultdict,Counter
D=Path.cwd();B=D.parent/'diagnostic_run/port_bind_v2';S=Path('/srv/opentallas-scratch/claude/qwen-kvsys/wt-kvs14r-54e9d9c39-gen9d5p');R=Path('/srv/opentallas-scratch/claude/qwen-kvsys/kvs14r-54e9d9c39-gen9d5p')
sys.path.insert(0,str(D.parent));import kv_health_plane as H;import die_port_bind as P;import kv_output_pads as O
src=B/'die_bound.v';nets,_,_,insts=P.parse_die(str(src));cells={i:(m,pr,c) for m,i,pr,c in insts};die=types.SimpleNamespace(nets=nets,cells=cells,bits=lambda x:P.expr_bits(x,nets))
free=defaultdict(lambda:defaultdict(set));h=json.loads((R/'health_plane.json').read_text())
for t in h['plan']['transports']:
 for i in t['stations']:free[i]['a'].add(t['payload_bit']);free[i]['b'].add(t['payload_bit'])
existing=json.loads((R/'case_kv/die.v.pads.json').read_text())
try:O.derive(src,S,existing)
except ValueError as e:original_error=str(e)
else:raise AssertionError('original guard unexpectedly passes')
assert 'private spare output has a dynamic/nonzero input' in original_error,original_error
edits=defaultdict(dict);rename=H.name_functional_transport(die,edits,free,{})
assert rename,'no renames';newlines=[];seen=set()
pattern=re.compile(r'^(\s*\w+(?:\s*#\(.*\))?\s+)(\S+)\s*\((.*)\);\s*$')
for line in src.read_text().splitlines():
 m=pattern.match(line)
 if m and m[2] in edits:
  inst=m[2];cm=cells[inst][2]
  body=', '.join('.'+p+'('+H.pack_msb(edits[inst][p])+')' if p in edits[inst] else '.'+p+'('+v+')' for p,v in cm.items())
  line=m[1]+inst+' ('+body+');';seen.add(inst)
 if line.strip()=='endmodule':newlines += ['wire [0:0] '+n+';' for n,k in rename.values()]
 newlines.append(line)
assert seen==set(edits),(set(edits)-seen)
out=D/'die_bound_functional_names.v';out.write_text('\n'.join(newlines)+'\n')
n2,_,_,i2=P.parse_die(str(out));c2={i:(m,pr,c) for m,i,pr,c in i2};assert set(c2)==set(cells)
ports=bits=0
for i,(m,pr,cm) in cells.items():
 mm,pp,cc=c2[i];assert m==mm and pr==pp and set(cm)==set(cc),(i,'header')
 for p,e in cm.items():
  a=P.expr_bits(e,nets);b=P.expr_bits(cc[p],n2)
  if a is None:assert e==cc[p],(i,p,'unparsedchanged');continue
  assert [rename.get(x,x) for x in a]==b,(i,p,'graphchanged');ports+=1;bits+=len(a)
doc=O.derive(out,S,existing);(D/'output_pads.json').write_text(json.dumps(doc,indent=1)+'\n')
for i,ps in free.items():
 row=doc.get('instances',{}).get(i,{})
 for k in ps['b']:
  ranges=row.get('ports',{}).get('b',[]);assert not any(a<=k<=b for a,b in ranges),(i,k,'functionalpadclaim')
identity=dict(qualified=False,source_commit='54e9d9c39',original_guard_error=original_error,unchanged_guard_after='PASS',renamed_bits=len(rename),edited_instances=len(edits),identical_instances=len(cells),compared_ports=ports,compared_bit_connections=bits,all_master_parameters_unchanged=True,graph_isomorphism='PASS modulo explicit bijective functional renames',no_functional_pad_claims=True,rename=[dict(old=list(a),new=list(b)) for a,b in rename.items()],files={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [src,out,D.parent/'kv_health_plane.py',D.parent/'kv_output_pads.py',D/'output_pads.json']})
(D/'identity.json').write_text(json.dumps(identity,indent=2)+'\n');print(json.dumps({k:identity[k] for k in ['original_guard_error','unchanged_guard_after','renamed_bits','edited_instances','identical_instances','compared_ports','compared_bit_connections','no_functional_pad_claims']}),flush=True)

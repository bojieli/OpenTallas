from pathlib import Path
import json,re,hashlib,gzip,tarfile,io
b=Path('/srv/opentallas-scratch2/claude/codex-sc974-alias-1030');i=b/'input';o=b/'candidate';o.mkdir(exist_ok=True);src=o/'source';src.mkdir(exist_ok=True)
F=json.load((i/'frontier.json').open());I=json.load((i/'port_interface.json').open());core=(i/'qfd_dv_s5_sc2_k79.sv').read_text();leaf=(i/'qfd_dv_s5_sc2_leaf.sv').read_text();helpers=(i/'qfd_dv_s5_sc2_k79_helpers.sv').read_text()
ports={p['name']:p for p in I['ports']}
def bits(expr):
 expr=expr.strip()
 if expr.startswith('{'):
  assert expr.endswith('}');return sum((bits(x) for x in reversed(expr[1:-1].split(','))),[])
 m=re.fullmatch(r'(\w+)\[(\d+):(\d+)\]',expr)
 if m:return [f'{m[1]}[{k}]' for k in range(int(m[3]),int(m[2])+1)]
 assert re.fullmatch(r'\w+(?:\[\d+\])?',expr),expr
 return [expr]
connections={p['name']:bits(p['parent_net']) for p in I['ports'] if p['direction']=='input'}
assert all(len(connections[n])==ports[n]['bits'] for n in connections)
rx=re.compile(r'(?P<master>qfd_s2_bmath_dff_p(?:n0)?)\s*#\(\.ID\((?P<id>\d+)\)\)\s*(?P<instance>u_\d+)\s*\((?P<pins>[^;]*?)\);')
ff={m['instance']:m for m in rx.finditer(core)};assert len(ff)==43058
pindict=lambda m:dict(re.findall(r'\.(\w+)\(([^)]+)\)',m['pins']))
endpoint=[];aliases=[];changes=[]
for bit,rec in F['inputs'].items():
 m=re.fullmatch(r'(\w+)\[(\d+)\]',bit);assert m,bit;bus,k=m[1],int(m[2]);targets=rec['immediate_data_ff_sinks'];assert not rec['immediate_comb_sinks']
 for r,inst in enumerate(targets):
  cell=ff[inst];ps=pindict(cell);assert ps['D']==rec['net'],(bit,inst,ps)
  alias=None if r==0 else f'alias_{bus}_{k}_r{r}'
  row=dict(source_bit=bit,leaf_port=bus,bit=k,instance=inst,source_master=cell['master'],source_id=int(cell['id']),original_D=ps['D'],Q=ps['Q'],C=ps['C'],R=ps.get('R'),private_port=alias or (bus if ports[bus]['bits']==1 else bit),new_alias=bool(alias),actual_parent_net=connections[bus][k])
  endpoint.append(row)
  if alias:
   pm=re.search(r'\.D\(([^)]+)\)',cell['pins']);a=cell.start('pins')+pm.start(1);z=cell.start('pins')+pm.end(1);changes.append((a,z,alias));aliases.append(row)
assert len(endpoint)==757 and len(aliases)==402
new=core
for a,z,t in sorted(changes,reverse=True):new=new[:a]+t+new[z:]
oldmod='qfd_dv_s5_sc2_k79';newmod=oldmod+'_alias974';new=new.replace('module '+oldmod+'(','module '+newmod+'(',1);end=new.index(');',new.index('module '));new=new[:end]+','+','.join(r['private_port'] for r in aliases)+new[end:];end=new.index(');',new.index('module '))+2;new=new[:end]+'\n'+'\n'.join('input wire [0:0] '+r['private_port']+';' for r in aliases)+new[end:]
newleaf=leaf.replace('module qfd_dv_s5_sc2_leaf (','module qfd_dv_s5_sc2_leaf_alias974 (',1).replace(oldmod+' u (',newmod+' u (',1)
end=newleaf.index('\n);',newleaf.index('module '));newleaf=newleaf[:end]+',\n'+',\n'.join('    input wire '+r['private_port'] for r in aliases)+newleaf[end:]
call=newleaf.rindex('.fault(fault)');newleaf=newleaf[:call]+'.fault(fault),\n        '+',\n        '.join('.'+r['private_port']+'('+r['private_port']+')' for r in aliases)+newleaf[call+len('.fault(fault)'):]
newff={m['instance']:m for m in rx.finditer(new)};assert set(newff)==set(ff)
for n,m in ff.items():
 a,z=pindict(m),pindict(newff[n]);assert m['master']==newff[n]['master'] and m['id']==newff[n]['id'];assert all(a[x]==z[x] for x in a if x!='D')
 # Actual parent composition returns every old D net, with no state or helper deletion.
 if a['D']!=z['D']:
  r=next(t for t in aliases if t['instance']==n);assert z['D']==r['private_port'] and a['D']==r['original_D']
# Per-alias source ties are exact copies of the original child-bit parent expression.
(o/'parent_alias_connections.svh').write_text(',\n'.join('.'+r['private_port']+'('+r['actual_parent_net']+')' for r in aliases)+'\n')
(src/(newmod+'.sv')).write_text(new);(src/'qfd_dv_s5_sc2_leaf_alias974.sv').write_text(newleaf);(src/'qfd_dv_s5_sc2_k79_helpers.sv').write_text(helpers)
# Preserve a total arbitrary-state bijection: every old helper instance/master/ID/C/R/Q is the same.
(o/'state_bijection.json').write_text(json.dumps(dict(count=len(ff),mapping=[dict(instance=n,master=m['master'],ID=int(m['id']),C=pindict(m)['C'],R=pindict(m).get('R'),Q=pindict(m)['Q']) for n,m in ff.items()],assumption='NONE: old/new state variables identified one-to-one, arbitrary initial bits; no reset/cold restriction'),indent=2)+'\n')
(o/'endpoint_map.json').write_text(json.dumps(dict(original_data_bits=355,new_data_pins=757,outputs=215,controls=2,total_private_bits=974,extra_aliases=402,endpoints=endpoint),indent=2)+'\n')
# One read-only pass over the original mapped native child, no new SYNTH.
wanted={r['instance'] for r in endpoint};mapped={};nr=re.compile(r'^\s+(\w*ASAP7\w*)\s+\\?u_bound\.u_core\.u\.(u_\d+)/Q\$_DFF')
with (i/'original_parent_native.v').open() as f:
 for line in f:
  m=nr.match(line)
  if m and m[2] in wanted:mapped[m[2]]=m[1]
(o/'frontier_native_masters.json').write_text(json.dumps(dict(source='existing original full-parent native, read-only; no new build',found=len(mapped),expected=757,missing=sorted(wanted-set(mapped)),masters=mapped),indent=2)+'\n')
manifest=dict(status='SOURCE PREP ONLY; no activation/P&R/native qualification',source_state=43058,candidate_state=43058,new_ff=0,new_cycles=0,private_input_bits=759,private_output_bits=215,total=974,parent_public_unchanged=True,original572packet_preserved=True,files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in src.glob('*.sv')},alias_parent_binding='parent_alias_connections.svh',state_identity='state_bijection.json',native_frontier_found=len(mapped))
(o/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps(manifest,indent=2))

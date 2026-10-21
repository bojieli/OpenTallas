#!/usr/bin/env python3
"""Extract actual shipping aggregate members and current aligned ownership.

Read-only source/inventory operation. No RTL replacement, phase assumption,
synthetic work assignment, golden producer or simulation is created here.
"""
import argparse,ast,hashlib,json,os,re
from pathlib import Path
from types import SimpleNamespace

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--shipping-root',type=Path,required=True);p.add_argument('--fixture-meta',type=Path,required=True);p.add_argument('--lower-xs',type=Path,required=True);p.add_argument('--slice',default='u_s_0N');p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 root=a.shipping_root;raw=(root/'bind/bind/die.v').read_text();plan=json.loads((root/'plan_routed_g8.json').read_text());land=json.loads((root/'land_plan_g8.json').read_text());source_manifest=json.loads((root/'original_source_manifest.json').read_text())
 pat=re.compile(r'^\s*(\w+)\s+(?:#\((.*?)\)\s+)?(\w+)\s*\((.*)\);\s*(?://.*)?$')
 inst={m[3]:dict(master=m[1],params=m[2] or '',conns={p:e.strip() for p,e in re.findall(r'\.(\w+)\(([^()]*)\)',m[4])}) for line in raw.splitlines() if (m:=pat.match(line)) and m[1] not in ('module','wire','input','output','assign','reg')}
 blocks={b['name']:b for b in plan['blocks']}
 class Inventory:
  def slices(self):return {n:dict(sid=self.strap(n,'sid')) for n,i in inst.items() if n.startswith('u_s_') and 'slice' in i['master']}
  def frames_of(self,n):return sorted('u_'+b['name'] for b in plan['blocks'] if b['kind']=='frame' and b.get('group')==blocks[n[2:]].get('group') and 'u_'+b['name'] in inst)
  def strap(self,n,p):
   x=re.fullmatch(r"(\d+)'([dh])([0-9a-fA-F]+)",inst[n]['conns'].get(p,''));assert x,(n,p);return int(x[3],16 if x[2]=='h' else 10)
 inv=Inventory();inv.inst=inst
 # Execute the unmodified canonical placement function definitions; fixtures
 # supply real tensor shapes, and every frame comes from the actual die/plan.
 names={'slice_index','aproj_topology_enabled','aproj_rank_tags_enabled','dense_split2','dense_split2_rows','placement'}
 parsed=ast.parse(a.lower_xs.read_text());defs=[n for n in parsed.body if isinstance(n,ast.FunctionDef) and n.name in names]
 assert {n.name for n in defs}==names
 constants={'NSEG','NPAIRS','ROWS_PER_FRAME','ROWS_PER_SLICE'}
 assignments=[n for n in parsed.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in constants for t in n.targets)]
 scope=dict(os=os)
 exec(compile(ast.Module(body=assignments+defs,type_ignores=[]),str(a.lower_xs),'exec'),scope)
 meta=json.loads(a.fixture_meta.read_text());rank=meta['rank'];ranges=meta['tp_split'];fx=dict(meta=meta,w={k:[SimpleNamespace(shape=(v[1]-v[0],5120))] for k,v in [('wq_a',ranges['a_proj.wq_a_rows'][rank]),('wkv',ranges['a_proj.wkv_rows'][rank])]})
 total=sum(item[0].shape[0] for item in fx['w'].values());assert total%2==0
 os.environ.update(OT_XS_APROJ_TOPO='1',OT_XS_APROJ_RANK_TAGS='1',OT_XS_APROJ_ALIGN4='1',OT_XS_DENSE_SPLIT2_ROWS=str(total//2))
 ownership={}
 for half in ('A','B'):
  os.environ['OT_XS_DENSE_SPLIT2']=half
  ownership[half]={s:scope['placement'](inv,s,fx)[1] for s in inv.slices()}
 selected=a.slice;members=inv.frames_of(selected);assert members
 assert any(f['rows'] for half in ownership.values() for f in half[selected]),'chosen slice idle in both real halves'
 identities={selected:inst[selected],**{f:inst[f] for f in members}}
 wires=set();clock_nets=set()
 for item in identities.values():
  for port,expression in item['conns'].items():
   wires.update(re.findall(r'\b(w_\w+?)_(?:src|lnd|dst)\b',expression))
   if port.startswith('ck') or port in ('clk','xk','xok'):clock_nets.update(re.findall(r'\b[A-Za-z_]\w*\b',expression))
 wire_rx=re.compile(r'\b(?:'+'|'.join(map(re.escape,wires))+r')_(?:src|lnd|dst)\b')
 linked={n:i for n,i in inst.items() if wire_rx.search(str(i['conns'])) and n not in identities}
 base='rtl/dsrom_sys/s81_dv/slice'
 wrapper=base+'/landed/c1x_k8_cap5r/ot_s81sl_slice_c1x_k8_cap5r_lp.sv'
 cap_text=(root/'src'/wrapper).read_text()
 xg=re.search(r'(?m)^\s*(ot_s81sl_xg\w*)\s+u_xg\s*\(',cap_text).group(1)
 xgpath=base+'/'+xg+'.sv';xg_text=(root/'src'/xgpath).read_text()
 ring=re.search(r'(?m)^\s*(ot_s81sl_\w+)\s+u_r\s*\(',xg_text).group(1)
 streamer=re.search(r'(?m)^\s*(ot_s81sl_xs\w*)\s+u_s\s*\(',xg_text).group(1)
 paths=[base+'/mu72/'+inst[selected]['master']+'.sv',wrapper,xgpath,base+'/'+ring+'.sv',base+'/'+streamer+'.sv',base+'/ot_s81sl_xrt.sv',base+'/lp/ot_s81sl_capc5r.sv','rtl/dsrom_sys/s81_dv/frame_lp/col_h9_l4_lp.sv','rtl/dsrom_sys/s81_dv/land/dsfd_cfifo_crs4.sv']

 sources={}
 for name in paths:
  path=root/'src'/name;actual=sha(path);text=path.read_text()
  sources[name]=dict(sha256=actual,manifest_sha256=source_manifest.get(name),matches_manifest=actual==source_manifest.get(name),binding_lines=[line.strip() for line in text.splitlines() if re.search(r'\bu_(?:sl|xg|xr|cap|r|s)\s*\(',line) and not line.lstrip().startswith('//')])
 clock_nets={n for n in clock_nets if n not in ('d','h')};clock_rx=re.compile(r'\b(?:'+'|'.join(map(re.escape,clock_nets))+r')\b')
 clock_statements=[line.strip() for line in raw.splitlines() if clock_rx.search(line) and line.strip().startswith(('assign','BUFx','INVx','ICGx','dsfd_dvrlyh'))]
 out=dict(clock_source_statements=clock_statements,clock_cone_qualified=False,schema='opentallas.s81.aggregate_shipping_source_path.v1',status='SOURCE_PATH_ONLY_NOT_QUALIFIED',shipping_root=str(root),placement_environment=dict(OT_XS_APROJ_TOPO='1',OT_XS_APROJ_RANK_TAGS='1',OT_XS_APROJ_ALIGN4='1',OT_XS_DENSE_SPLIT2_ROWS=str(total//2),OT_XS_DENSE_SPLIT2=['A','B']),actual_chain=dict(xg=xg,ring=ring,streamer=streamer),source_manifest_sha256=sha(root/'original_source_manifest.json'),die_sha256=hashlib.sha256(raw.encode()).hexdigest(),plan_sha256=sha(root/'plan_routed_g8.json'),land_sha256=sha(root/'land_plan_g8.json'),fixture_meta_sha256=sha(a.fixture_meta),lower_xs_sha256=sha(a.lower_xs),selected_slice=selected,selected_instances=identities,related_transport_instances=linked,selected_ownership={half:rows[selected] for half,rows in ownership.items()},all_cap5r_endpoint_ownership={half:{s:rows[s] for s in ['u_s_0S','u_s_0N','u_s_7S','u_s_7N']} for half,rows in ownership.items()},sources=sources,physical_phase_qualified=False,aggregate_programme_qualified=False)
 a.out.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(dict(selected=selected,frames=members,rows={h:[f['rows'] for f in ownership[h][selected]] for h in ownership},die_sha256=out['die_sha256']),indent=2))
if __name__=='__main__':main()

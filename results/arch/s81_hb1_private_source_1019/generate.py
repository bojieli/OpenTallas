#!/usr/bin/env python3
"""Exact endpoint-ledger structural source, no synthesis or logic guessing."""
import argparse,gzip,json,hashlib,pathlib,re
P=pathlib.Path(__file__).resolve().parent
A=P.parent/'s81_hb1_diagnostic_census_1019'
M=P.parent/'s81_hb1_fixedpoint_model_1019'
def load(p):return json.load(gzip.open(p) if str(p).endswith('.gz') else open(p))
def norm(s):return s.replace('\\','')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def generate(out):
 out.mkdir(exist_ok=False,parents=True)
 model=load(M/'correspondence.json.gz'); census=load(A/'receipt/native_census.json.gz'); mapped=load(A/'receipt/mapped.json.gz')['modules']['ot_s81sl_xr3']
 assert sha(A/'bundle/rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xr.sv')==model['source_sha256']
 cells=mapped['cells']; native={norm(r['instance']):r['instance'] for r in census['pin_inventory']}
 assert set(cells)==set(native), (len(cells),len(native))
 rows={r['driver']:r for r in model['rows']}; root={r['driver']:r for r in census['records'] if r['driver']!='PORT'}
 dirs={(norm(r['instance']),r['pin']):r['direction'] for r in census['pin_inventory'] if r['signal'] not in ('POWER','GROUND')}
 assignment={(d,dc,p):(s,sc,iv) for s,sc,d,dc,p,iv in model['endpoint_assignments']}
 assert len(assignment)==len(model['endpoint_assignments'])
 copies={n:rows.get(native[n],{}).get('copies',1) for n in cells}
 allbits={b for c in cells.values() for v in c['connections'].values() for b in v if isinstance(b,int)}
 allbits|={b for p in mapped['ports'].values() for b in p['bits'] if isinstance(b,int)}
 def bit(b):return 'n'+str(b) if isinstance(b,int) else "1'b"+b
 indices={n:i for i,n in enumerate(cells)}
 def ow(n,c,p):
  b=cells[n]['connections'][p];assert len(b)==1
  return bit(b[0]) if c==0 else f'cp_{indices[n]}_{c}_{p}'
 def redirect(n,c,p,old):
  k=(native[n],c,p)
  if k not in assignment:return old
  s,sc,iv=assignment[k]; rr=root[s]; sn=norm(s)
  assert sc<copies[sn]
  return ('~' if iv else '')+ow(sn,sc,rr['pin'])
 lines=['// Generated from exact frozen HB1 mapped graph and complete fixedpoint ledger.', '// No initialization; physical timing/PG/mapping retention remains unqualified.','module ot_s81sl_xr3_hb1_graph_1019 ('+', '.join(mapped['ports'])+');']
 for pn,p in mapped['ports'].items():
  w=len(p['bits']);lines.append(f"  {p['direction']} wire "+(f'[{w-1}:0] ' if w>1 else '')+pn+';')
 lines.append('  wire '+', '.join('n'+str(b) for b in sorted(allbits))+';')
 for pn,p in mapped['ports'].items():
  for j,b in enumerate(p['bits']):
   port=pn+(f'[{j}]' if len(p['bits'])>1 else '')
   if p['direction']=='input':lines.append(f'  assign {bit(b)} = {port};')
   else:
    a=assignment.get(('PORT',0,port));expr=bit(b)
    if a:
     s,sc,iv=a;expr=('~' if iv else '')+ow(norm(s),sc,root[s]['pin'])
    lines.append(f'  assign {port} = {expr};')
 for n,cell in cells.items():
  for ci in range(copies[n]):
   con=[]
   for pin,b in cell['connections'].items():
    assert len(b)==1
    if dirs[n,pin]=='OUTPUT':
     expr=ow(n,ci,pin)
     if ci:lines.append(f'  (* keep *) wire {expr};')
    else:expr=redirect(n,ci,pin,bit(b[0]))
    con.append(f'.{pin}({expr})')
   lines.append(f'  (* keep, dont_touch *) {cell["type"]} u_{indices[n]}_{ci} ('+', '.join(con)+');')
 lines.append('endmodule')
 (out/'retained_graph.sv').write_text('\n'.join(lines)+'\n')
 # Preserve source snapshots byte-for-byte; private compilation renames modules by a recorded textual projection.
 for fname,src in [('anchor.sv',A/'bundle/rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xr.sv'),('reset.sv',A/'bundle/rtl/lib/ot_rst_relay.sv')]:
  (out/fname).write_bytes(src.read_bytes())
 wrapper=(A/'receipt/ot_rst_land_wrapper.v').read_text().replace('module ot_s81sl_xr3 (','module ot_s81sl_xr3_hb1_anchor_1019 (').replace('ot_s81sl_xr3__ot_pr_core u_ot_pr_core','ot_s81sl_xr3_hb1_anchorcore_1019 u_ot_pr_core')
 (out/'anchor_wrapper.sv').write_text(wrapper)
 anchor=(out/'anchor.sv').read_text();anchor=anchor.replace('module ot_s81sl_xr #(','module ot_s81sl_xr_hb1_snapshot_1019 #(')
 # Source includes original C1/C3 wrappers; retain them privately too.
 anchor=re.sub(r'\bot_s81sl_xr3\b','ot_s81sl_xr3_hb1_originalwrapper_1019',anchor)
 anchor=re.sub(r'\bot_s81sl_xr1\b','ot_s81sl_xr1_hb1_originalwrapper_1019',anchor)
 anchor=re.sub(r'\bot_s81sl_xr\b','ot_s81sl_xr_hb1_snapshot_1019',anchor)
 # Generated pin landing core is simply the original production HB1 wrapper.
 core=wrapper.replace('module ot_s81sl_xr3_hb1_anchor_1019 (','module ot_s81sl_xr3_hb1_anchorcore_1019 (')
 core=core[:core.index('  (* keep *) reg')]+core[core.index('  input [3:0] sid;'):]
 ports=', '.join(f'.{p}({p})' for p in mapped['ports'])
 core=re.sub(r'  ot_s81sl_xr3_hb1_anchorcore_1019 u_ot_pr_core .*?;', '  ot_s81sl_xr_hb1_snapshot_1019 #(.HB(1), .W(1104), .V(276)) u ('+ports+');',core)
 (out/'anchor_private.sv').write_text(anchor+'\n'+wrapper+'\n'+core)
 decl=lines[2].replace('ot_s81sl_xr3_hb1_graph_1019','ot_s81sl_xr3_hb1_retained_1019 #(parameter RETAINED=0)')
 declarations=lines[3:3+len(mapped['ports'])]
 (out/'select.sv').write_text('\n'.join([decl,*declarations,'generate if (RETAINED) begin : retained',f'ot_s81sl_xr3_hb1_graph_1019 u ({ports});','end else begin : identity',f'ot_s81sl_xr3_hb1_anchor_1019 u ({ports});','end endgenerate','endmodule'])+'\n')
 manifest={'scope':'GENERATED SOURCE ONLY; no executed equivalence or native retention claim','anchor_sha256':model['source_sha256'],'model_sha256':sha(M/'correspondence.json.gz'),'mapped_sha256':sha(A/'receipt/mapped.json.gz'),'original_cells':len(cells),'new_cells':sum(copies.values()),'added':model['added'],'endpoint_assignments':len(assignment),'files':{f.name:sha(f) for f in out.iterdir() if f.is_file()}}
 (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
 print(json.dumps({k:v for k,v in manifest.items() if k!='files'},indent=2))
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('out',type=pathlib.Path);generate(ap.parse_args().out)

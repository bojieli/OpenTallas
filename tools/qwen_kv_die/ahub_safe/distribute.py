#!/usr/bin/env python3
"""Emit a fixed-profile native AHUB source with same-edge distributed drivers.
No cell truth table, FF D/reset/clock/priority, or hard child is changed.
Transparent INV/BUF cones are represented by canonical root plus polarity.
Copies are solved to a fixed point including the extra D/reset input loads.
"""
import argparse,collections,copy,hashlib,json,math,re
from pathlib import Path
TOP='qkd_ahub_static_dw_safe'
SUPPORTED_MAPPED_SHA256='1256f2546a0985710857f13bf72269408c07e355349c7a3f2385e1992203f3da'
PROFILE={'AP_OFS':'ffd9ffdaffd8ffd8','FR_OFS':-7,'Z_IN_STRIDE':4,'RS_RLY':1,'RX_RLY':1,'RY_RLY':2,'WF_RLY':1}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def transparent(c):return c['type'].startswith(('INV','BUF','HB'))
def ident(s):return '\\'+s+' '
def emit(inp,out,limit=24):
 if sha(inp)!=SUPPORTED_MAPPED_SHA256:raise ValueError('unsupported AHUB mapped source/profile hash')
 j=json.loads(Path(inp).read_text());m=j['modules'][TOP];cells=m['cells'];drivers={};init={}
 for n,w in m['netnames'].items():
  if 'init' in w.get('attributes',{}):
   for b,x in zip(w['bits'],w['attributes']['init'][::-1]):
    if b in init and init[b]!=x:raise ValueError('conflicting init')
    init[b]=x
 for n,c in cells.items():
  for p,bs in c['connections'].items():
   if c['port_directions'][p]=='output':
    for b in bs:
     if b in drivers:raise ValueError('multiple driver')
     drivers[b]=(n,p)
 def canonical(b,seen=()):
  if not isinstance(b,int) or b not in drivers:return (b,0)
  n,p=drivers[b];c=cells[n]
  if not transparent(c):return (b,0)
  if n in seen:raise ValueError('transparent cycle')
  ins=[x for q,bs in c['connections'].items() if c['port_directions'][q]=='input' for x in bs]
  if len(ins)!=1:raise ValueError('unsupported transparent cell')
  root,pol=canonical(ins[0],seen+(n,));return (root,pol^int(c['type'].startswith('INV')))
 base={n:copy.deepcopy(c) for n,c in cells.items() if not transparent(c) and c['type']!='$scopeinfo'}
 roots={}
 for n,c in base.items():
  for p,bs in c['connections'].items():
   if c['port_directions'][p]=='output':
    for bi,b in enumerate(bs):roots[b]=(n,p,bi)
 clockbits=set(m['ports']['ck']['bits'])
 # Literal aliases normalize every transparent cone without changing polarity.
 refs={n:{p:[canonical(b) for b in bs] for p,bs in c['connections'].items() if c['port_directions'][p]=='input'} for n,c in base.items()}
 copies={n:1 for n in base}
 def targets():
  t=collections.defaultdict(list)
  for n in sorted(base):
   for k in range(copies[n]):
    for p,rs in refs[n].items():
     for bi,(b,pol) in enumerate(rs):t[b].append(('cell',n,k,p,bi,pol))
  for p,v in m['ports'].items():
   if v['direction']=='output':
    for bi,b in enumerate(v['bits']):
     rt,pol=canonical(b);t[rt].append(('port',p,0,'',bi,pol))
  return t
 iterations=[]
 for iteration in range(10000):
  ts=targets();changes={}
  for b,ds in ts.items():
   if not isinstance(b,int) or b in clockbits:continue
   need=math.ceil(len(ds)/limit)
   if need<=1:continue
   if b not in roots:
    if len(ds)>32:raise ValueError(f'primary input root {b} has {len(ds)} consumers')
    continue
   n,p,bi=roots[b];c=base[n]
   outs=[q for q,di in c['port_directions'].items() if di=='output']
   if len(outs)!=1 or len(c['connections'][p])!=1 or c['type'] in ('ot_nhb_zh','ot_qkh_recip_leaf'):
    raise ValueError(f'hard/multioutput source {n} requires replication')
   if need>copies[n]:changes[n]=need
  iterations.append({'iteration':iteration,'cells':sum(copies.values()),'changed_roots':len(changes)})
  if not changes:break
  copies.update(changes)
 else:raise RuntimeError('replication fixed point did not converge')
 ts=targets();assigned={};outbit={};serial=0
 for n in sorted(base):
  for k in range(copies[n]):
   for p,bs in base[n]['connections'].items():
    if base[n]['port_directions'][p]=='output':
     for bi,b in enumerate(bs):outbit[(n,k,p,bi)]=f'w{serial}';serial+=1
 def source(b,k=0):
  if not isinstance(b,int):return "1'b"+b
  if b in roots:
   n,p,bi=roots[b];return outbit[n,k,p,bi]
  for p,v in m['ports'].items():
   if v['direction']=='input' and b in v['bits']:
    return ident(p)+(f'[{v["bits"].index(b)}]' if len(v['bits'])>1 else '')
  raise ValueError(f'undriven root {b}')
 inv={};partition=[]
 for b,ds in sorted(ts.items(),key=lambda x:str(x[0])):
  for i,t in enumerate(ds):
   k=i//limit if b in roots and b not in clockbits else 0
   sig=source(b,k)
   if t[-1]:
    key=(b,k)
    if key not in inv:inv[key]=(f'w{serial}',sig);serial+=1
    sig=inv[key][0]
   assigned[t[:-1]]=sig
  partition.append({'root':b,'targets':len(ds),'copies':math.ceil(len(ds)/limit) if b in roots and b not in clockbits else 1})
 out=Path(out);out.mkdir(parents=True,exist_ok=True)
 lines=['// GENERATED fixed GEN7 profile; no timing/physical qualification.',f'module {TOP}_native (',',\n'.join('  '+ident(p) for p in m['ports']),');']
 for p,v in m['ports'].items():lines.append(f'  {v["direction"]} wire '+(f'[{len(v["bits"])-1}:0] ' if len(v['bits'])>1 else '')+ident(p)+';')
 lines.append('  wire '+', '.join(f'w{x}' for x in range(serial))+';')
 emitted=[]
 for n in sorted(base):
  c=base[n]
  if c['parameters']:raise ValueError('unsupported unresolved native cell parameters')
  for k in range(copies[n]):
   en=f'safe_c{len(emitted)}';cn={}
   for p,bs in c['connections'].items():
    cn[p]=[assigned[('cell',n,k,p,bi)] if c['port_directions'][p]=='input' else outbit[n,k,p,bi] for bi in range(len(bs))]
   args=[]
   for p,bs in cn.items():args.append('.'+ident(p)+'('+('{'+','.join(reversed(bs))+'}' if len(bs)>1 else bs[0])+')')
   lines.append('  (* keep = "true", dont_touch = "true" *) '+ident(c['type'])+' '+en+' ('+', '.join(args)+');')
   emitted.append({'emitted':en,'origin':n,'copy':k,'master':c['type'],'ports':cn,'parameters':c['parameters']})
 for (b,k),(wire,src) in inv.items():lines.append(f'  INVx1_ASAP7_75t_R safe_inv_{wire} (.A({src}), .Y({wire}));')
 for p,v in m['ports'].items():
  if v['direction']=='output':
   bs=[assigned[('port',p,0,'',bi)] for bi in range(len(v['bits']))]
   lines.append('  assign '+ident(p)+'= '+('{'+','.join(reversed(bs))+'}' if len(bs)>1 else bs[0])+';')
 lines.append('endmodule')
 path=out/'qkd_ahub_static_dw_safe_native.v';path.write_text('\n'.join(lines)+'\n')
 proof={'schema':'opentallas.ahub.sameedge_distribution.v1','input_sha256':sha(inp),'output_sha256':sha(path),'profile':PROFILE,'limit':limit,'original_cells':len(cells),'original_nontransparent_cells':len(base),'emitted_cells':len(emitted),'additional_copies':sum(copies.values())-len(base),'copies':copies,'iterations':iterations,'canonical':{str(b):canonical(b) for b in drivers},'state_init_by_original_bit':init,'emitted':emitted,'partitions':partition,'native_qualified':False}
 (out/'distribution.json').write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps({k:proof[k] for k in ('original_cells','original_nontransparent_cells','emitted_cells','additional_copies','iterations')}))
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('input');a.add_argument('output');a.add_argument('--profile',required=True);args=a.parse_args()
 if args.profile!='GEN7_AP_-40_-40_-38_-39_FR_-7':raise SystemExit('unsupported AHUB native parameter profile')
 emit(args.input,args.output)

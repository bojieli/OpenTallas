#!/usr/bin/env python3
"""Inventory actual mapped provider cells, LEF bodies and exact output Q drivers.
Placement is intentionally left to the source-DB owner; no FF-only area claim.
"""
import argparse,json,re,collections
from pathlib import Path

def inventory(mapped,stages,lef):
 m=mapped['modules']['ot_die_start_stages'];ss={s['id']:s for s in stages['stages']};sizes={}
 for name,body in re.findall(r'\bMACRO\s+(\S+)\s+(.*?)\bEND\s+\1\b',lef,re.S):
  sz=re.search(r'\bSIZE\s+([\d.eE+-]+)\s+BY\s+([\d.eE+-]+)',body)
  if sz:sizes[name]=list(map(float,sz.groups()))
 rows=[];groups=collections.defaultdict(list);drivers=collections.defaultdict(list)
 metadata_cells=0
 for name,c in m['cells'].items():
  if c['type']=='$scopeinfo':
   metadata_cells+=1
   continue
  h=re.match(r'^(?:\$flatten\\+)?u_(st|rst)_([^.]+)\.',name)
  matches=[h[2]] if h and h[2] in ss else []
  if len(matches)!=1:raise ValueError(f'mapped cell lacks unique stage hierarchy: {name}')
  sid=matches[0];master=c['type']
  if master not in sizes:raise ValueError(f'mapped cell master lacks actual LEF footprint: {master}')
  row=dict(inst=name,stage=sid,role='reset' if h[1]=='rst' else 'origin',master=master,wh_um=sizes[master],area_um2=sizes[master][0]*sizes[master][1],
           sequential=master.startswith('DFF'),connections=c['connections'],directions=c['port_directions'])
  rows.append(row);groups[sid].append(row)
  for port,direction in c['port_directions'].items():
   if direction=='output':
    for bit in c['connections'][port]:drivers[bit].append((name,port))
 outputs=[]
 for e in stages['die_outputs']:
  bits=m['ports'][e['net']]['bits']
  if len(bits)!=1 or len(drivers[bits[0]])!=1:raise ValueError(f'provider output lacks unique mapped driver: {e}')
  name,pin=drivers[bits[0]][0];cell=next(r for r in rows if r['inst']==name)
  driver=cell;driver_pin=pin;path=[];seen=set()
  while not cell['sequential']:
   if cell['inst'] in seen or cell['master']!='INVx1_ASAP7_75t_R' or cell['stage']!=e['stage']:
    raise ValueError(f'provider output has non-inverter or cross-stage launch cone: {e}')
   seen.add(cell['inst']);path.append(dict(inst=cell['inst'],master=cell['master'],pin=pin))
   ins=[v for p,v in cell['connections'].items() if cell['directions'][p]=='input']
   if len(ins)!=1 or len(ins[0])!=1 or len(drivers[ins[0][0]])!=1:
    raise ValueError(f'provider inverter lacks unique scalar launch: {e}')
   name,pin=drivers[ins[0][0]][0];cell=next(r for r in rows if r['inst']==name)
  if cell['stage']!=e['stage']:raise ValueError(f'provider START output not launched by declared stage FF: {e}')
  outputs.append(dict(**e,source_inst=driver['inst'],source_pin=driver_pin,master=driver['master'],
    launch_inst=cell['inst'],launch_pin=pin,launch_master=cell['master'],output_inverters=path))
 # Visible RTL state aliases only; Yosys may remove internal names. Missing
 # aliases remain unknown, never reconstructed from cell ordering or placement.
 byname={r['inst']:r for r in rows}
 for n,v in m.get('netnames',{}).items():
  a=re.fullmatch(r'u_(st|rst)_([^.]+)\.(s[012]|g_fall.sf|g_pad.pd|n|start|r[01]|g_fall.rf)',n)
  if not a or a[2] not in ss:continue
  for k,bit in enumerate(v['bits']):
   path=[];seen=set()
   while len(drivers[bit])==1:
    inst,pin=drivers[bit][0];c=byname[inst]
    if c['stage']!=a[2]:raise ValueError('cross-stage state alias '+n)
    if c['sequential']:
     c.setdefault('state_aliases',[]).append(dict(net=n,bit_index=k,launch_pin=pin,
       inverters=path,inversion_parity=len(path)%2))
     break
    if inst in seen or c['master']!='INVx1_ASAP7_75t_R':break
    seen.add(inst);path.append(inst)
    ins=[b for p,b in c['connections'].items() if c['directions'][p]=='input']
    if len(ins)!=1 or len(ins[0])!=1:break
    bit=ins[0][0]
 perstage=[]
 for sid,s in ss.items():
  rs=groups[sid]
  actual_ff=sum(r['sequential'] for r in rs)
  actual_reset_ff=sum(r['sequential'] and r['role']=='reset' for r in rs)
  declared_ff=s.get('flops');declared_reset=s.get('reset_flops',0)
  if not isinstance(declared_ff,int) or actual_ff!=declared_ff or actual_reset_ff!=declared_reset:
   raise ValueError(f'provider FF census mismatch {sid}: actual {actual_ff}/reset {actual_reset_ff}, declared {declared_ff}/reset {declared_reset}')
  perstage.append(dict(stage=sid,clock_net=s['clock_net'],clock_port=s['clock_port'],node_cell=s['node_cell'],
    node_xy_um=s['node_xy_um'],provisional_ff_rect_um=s['rect_um'],cells=len(rs),flops=sum(r['sequential'] for r in rs),
    comb=sum(not r['sequential'] for r in rs),mapped_area_um2=sum(r['area_um2'] for r in rs)))
 return dict(schema='ot_start_provider_cells/1',physical_qualified=False,
  scope='actual technology-mapped cells and LEF bodies; source DB still must place ALL cells and time actual added clock loads',
  counts=dict(stages=len(ss),cells=len(rows),metadata_cells_skipped=metadata_cells,state_named_flops=sum(bool(r.get('state_aliases')) for r in rows),flops=sum(r['sequential'] for r in rows),comb=sum(not r['sequential'] for r in rows),
  mapped_area_um2=sum(r['area_um2'] for r in rows),outputs=len(outputs)),stages=perstage,cells=rows,outputs=outputs)

def main():
 a=argparse.ArgumentParser();a.add_argument('mapped');a.add_argument('stages');a.add_argument('lef');a.add_argument('--out',required=True);a=a.parse_args()
 d=inventory(json.load(open(a.mapped)),json.load(open(a.stages)),Path(a.lef).read_text());Path(a.out).write_text(json.dumps(d,indent=1));print(json.dumps(d['counts']))
if __name__=='__main__':main()

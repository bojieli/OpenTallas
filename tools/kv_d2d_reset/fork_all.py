#!/usr/bin/env python3
"""Exact-source ATTN mapped control fork; no inserted clock or data edge."""
import argparse,copy,hashlib,importlib.util,json,pathlib,collections
p=argparse.ArgumentParser();p.add_argument('source');p.add_argument('--out',required=True);p.add_argument('--limit',type=int,default=24);p.add_argument('--emit',action='store_true');p.add_argument('--size',action='store_true');a=p.parse_args()
root=pathlib.Path(__file__).resolve().parents[2]
parser=root/'tools/textbook_lint.py'; assert hashlib.sha256(parser.read_bytes()).hexdigest()=='1199c260157d377ac824853a7e22829c753312414e5951257df911aa99631677','use frozen textbook_lint from evidence/remote allfork package'
spec=importlib.util.spec_from_file_location('lint',parser);T=importlib.util.module_from_spec(spec);spec.loader.exec_module(T)
source=pathlib.Path(a.source);raw=source.read_text();assert hashlib.sha256(raw.encode()).hexdigest() in ('86bcd2bbfd5033b593db9d9fda74619646e14de6e5d5e88d947a0fa4e87c6c98', '1d215ceb9017c03ef0564d8afe6a892eb2f66f8cb6a84e9808e0af5a984b2006'),'unsupported source hash';mods=T.parse_verilog(raw);g,top=T.flatten(mods,None);macro_dump={'macros':[{'name':n,'master':t,'pins':[(pn,0,0,'OUTPUT' if pn=='rd_out' else 'INPUT') for pn in pins]} for t,n,pins in g.cells if t=='ot_sram_1r1w_64x512_m1_r2c2']}; A=T.build(g,macro_dump)
assert top in ('qkd_d2d_static_reset24','qkd_d2d_static_ovl_reset24'),('unsupported profile',top)
assert len(g.cells) in (40736,40738),('unsupported source inventory',len(g.cells))
assert 'icg' not in A['kind']; assert A['kind'].count('macro')==4; assert all(t=='ot_sram_1r1w_64x512_m1_r2c2' for (t,n,p),k in zip(g.cells,A['kind']) if k=='macro')
clock={x for b,(d,x) in g.ports.items() if b=='ck'}
base=copy.deepcopy(g.cells);origin=list(range(len(base)));proof=[]
def census():
 B=T.build(g,macro_dump)
 const={x for x,(ci,pn) in B['driver'].items() if ci>=0 and B['kind'][ci]=='tie'}
 changed=True
 while changed:
  changed=False
  for x in tuple(const):
   for ci,pn,bit in B['loads'].get(x,[]):
    if B['kind'][ci]=='buf':
     for op,bs in g.cells[ci][2].items():
      if B['pin_dir'][ci][op]=='out':
       for y in bs:
        if y not in const:const.add(y);changed=True
 rows=[]
 for x,ls in B['loads'].items():
  if x in clock or x<4 or x in const:continue
  ci,pn=B['driver'].get(x,(-2,'UNKNOWN'))
  rows.append({'net':x,'label':g.net_name[x],'loads':len(ls),'driver':ci,'pin':pn,'master':g.cells[ci][0] if ci>=0 else 'PORT','kind':B['kind'][ci] if ci>=0 else 'port'})
 return B,sorted(rows,key=lambda r:(-r['loads'],r['net']))
B,before=census()
if a.emit or a.size:
 for iteration in range(200):
  B,rows=census();bad=[r for r in rows if r['loads']>(1 if r['kind']=='buf' else a.limit) and r['driver']>=0]
  if not bad:break
  counts={x:len(v) for x,v in B['loads'].items()}
  aliases={}
  for ci,(typ,nm,pins) in enumerate(g.cells):
   for pn,bs in pins.items():
    if B['pin_dir'][ci][pn]=='out' and len(bs)==1:aliases.setdefault((origin[ci],pn),[]).append((ci,bs[0]))
  def move(load,y,x):
   li,pn,bit=load;at=len(g.cells[li][2][pn])-1-bit
   assert g.cells[li][2][pn][at]==x
   g.cells[li][2][pn][at]=y;counts[x]-=1;counts[y]=counts.get(y,0)+1
  for row in bad:
   x=row['net'];ci=row['driver'];typ,nm,pins=g.cells[ci];outpins=B['pin_dir'][ci];cap=1 if row['kind']=='buf' else a.limit
   loads=[l for l in B['loads'][x] if g.cells[l[0]][2][l[1]][len(g.cells[l[0]][2][l[1]])-1-l[2]]==x]
   overflow=loads[cap:]
   op=next(pn for pn,bs in pins.items() if outpins[pn]=='out' and bs==[x])
   # Reuse capacity in proven same-origin peers before adding new state.
   # This closes enable/hold feedback cones without endlessly creating a new
   # FF->D-mux->FF copy on each fixed-point pass.
   for peer,y in aliases.get((origin[ci],op),[]):
    if y==x:continue
    room=cap-counts.get(y,0)
    while room>0 and overflow:
     move(overflow.pop(),y,x);room-=1
   assert B['kind'][ci]!='macro',(nm,'immutable macro fanout failure')
   assert all(len(v)==1 for v in pins.values()),(nm,'non scalar source driver')
   while overflow:
    np=copy.deepcopy(pins);mapped={}
    for pn,bs in pins.items():
     if outpins[pn]=='out':
      nn=g.net(f'copy_{len(g.cells)}_{pn}');np[pn]=[nn];mapped[bs[0]]=nn
    ni=len(g.cells);g.cells.append((typ,f'safe_copy_{ni}',np));origin.append(origin[ci])
    for pn,bs in np.items():
     if outpins[pn]=='in':
      for y in bs:counts[y]=counts.get(y,0)+1
     else:aliases.setdefault((origin[ci],pn),[]).append((ni,bs[0]))
    chosen=overflow[:cap];overflow=overflow[cap:]
    for l in chosen:move(l,mapped[x],x)
    proof.append({'copy':ni,'parent':ci,'origin':origin[ci],'split_net':x,'output':mapped[x],'loads':[list(l) for l in chosen]})
 else:raise AssertionError('no fixedpoint')
B,after=census()
collapsed=[]
for row in after:
 if row['driver']>=0 and B['kind'][row['driver']]=='buf':continue
 stack=[row['net']];ends=set();visited=set()
 while stack:
  x=stack.pop()
  if x in visited:continue
  visited.add(x)
  for ci,pn,bit in B['loads'].get(x,[]):
   if B['kind'][ci]=='buf':
    stack.extend(v for op,bs in g.cells[ci][2].items() if B['pin_dir'][ci][op]=='out' for v in bs)
   else:ends.add((ci,pn,bit))
 collapsed.append(dict(row,first_logic_loads=len(ends)))
out=pathlib.Path(a.out);out.mkdir(parents=True,exist_ok=True)
info={'source_sha256':hashlib.sha256(raw.encode()).hexdigest(),'top':top,'limit':a.limit,'before_cells':len(base),'after_cells':len(g.cells),'before_ff':sum(T.FLOP_RE.match(t)!=None for t,n,p in base),'after_ff':sum(k=='ff' for k in B['kind']),'new_cells':len(g.cells)-len(base),'clock_loads':sum(len(B['loads'].get(x,[])) for x in clock),'before_violations':[r for r in before if r['loads']>32],'after_violations':[r for r in after if r['loads']>32],'before':before,'after':after,'collapsed':collapsed,'collapsed_violations':[r for r in collapsed if r['first_logic_loads']>32],'iterations':iteration+1 if (a.emit or a.size) else 0,'qualified':False}
(out/'census.json').write_text(json.dumps(info,indent=2)+'\n')
if a.emit:
 # Every original/copy retains the exact master equation and pin polarity. Its
 # input equivalence classes and clock/reset pins must be identical to source.
 equivalence={i:i for i in range(len(g.net_name))}
 for item in proof:equivalence[item['output']]=item['split_net']
 def eq(x):
  seen=set()
  while equivalence[x]!=x:
   assert x not in seen;seen.add(x);x=equivalence[x]
  return x
 for ci,(typ,nm,pins) in enumerate(g.cells):
  bt,bn,bp=base[origin[ci]];assert typ==bt;assert set(pins)==set(bp)
  for pn,bs in pins.items():assert [eq(x) for x in bs]==bp[pn],(ci,pn,bs,bp[pn])
 # New cells are source-equivalent, not buffers hiding broad FF sources.
 (out/'correspondence.json').write_text(json.dumps({'source_sha256':info['source_sha256'],'origins':origin,'copies':proof,'all_cell_equations_preserved':True,'same_clock_reset_polarity_priority':True,'initialization':'original mapped source contains no initial blocks; no new initialized state; copied flops converge on identical first active edge or matching reset','qualified':False},indent=2)+'\n')
 tm=mods[top];lines=['// Generated by fork.py. Opt-in frozen D2D NTX3 PR1 SAFE_RC1 TXDP.16 exact-source profile only.','module '+top.replace('_reset24','_safe24')+' ('+', '.join(tm.ports)+');']
 for pn in tm.ports:
  w=tm.widths.get(pn);width=f'[{w[0]}:{w[1]}] ' if w else '';lines.append(f'  {tm.dirs[pn]} wire {width}{pn};')
 used=sorted({x for _,_,pins in g.cells for bs in pins.values() for x in bs}|{x for d,x in g.ports.values()})
 def net(x):return ["1'b0","1'b1","1'bx","1'bz"][x] if x<4 else f'n{x}'
 lines += [f'  wire {net(x)};' for x in used if x>=4]
 for pn,(d,x) in g.ports.items():lines.append(f'  assign {net(x)} = {pn};' if d=='input' else f'  assign {pn} = {net(x)};')
 for ci,(typ,nm,pins) in enumerate(g.cells):
  lines.append('  (* keep = 1, dont_touch = 1 *) '+typ+f' c{ci} ('+', '.join(f'.{pn}('+ (net(bs[0]) if len(bs)==1 else '{'+', '.join(net(x) for x in bs)+'}') +')' for pn,bs in pins.items())+');')
 lines.append('endmodule');(out/(top.replace('_reset24','_safe24')+'.v')).write_text('\n'.join(lines)+'\n')
print(json.dumps({k:info[k] for k in ('source_sha256','before_cells','after_cells','before_ff','after_ff','clock_loads','new_cells','iterations')}));print('remaining>32',info['after_violations']);print('collapsed>32',info['collapsed_violations'])

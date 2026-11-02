# Companion executed in the existing live-db native anchor pass: no second ODB load.
import re,json
skip={i.getId()for i in block.getInsts()if re.match(r'^(TAPCELL|FILLER|FILL|DECAP)',i.getMaster().getName())}
pk={p.getName():j for j,p in enumerate(block.getBTerms())};net_index={};outdir=output.parent
with(outdir/'actual_geom.tsv').open('w')as out:
 b=block.getDieArea();c=block.getCoreArea()
 out.write('D\t'+'\t'.join(str(v/u)for v in(b.xMin(),b.yMin(),b.xMax(),b.yMax()))+'\n')
 out.write('R\t'+'\t'.join(str(v/u)for v in(c.xMin(),c.yMin(),c.xMax(),c.yMax()))+'\n')
 for i in block.getInsts():
  if i.getId()in skip:continue
  m=i.getMaster();n=m.getName();k='M'if m.isBlock()else'S'if n.startswith(('DFFHQN','DFFASRHQN'))else'B'if n.startswith(('BUF','INV','HB'))else'L';b=i.getBBox()
  out.write('C\t%d\t%s\t%s\t%s\t%s\n'%(i.getId(),k,n,'\t'.join(str(v/u)for v in(b.xMin(),b.yMin(),b.xMax(),b.yMax())),i.getName()))
 for p in block.getBTerms():
  boxes=[b for bp in p.getBPins()for b in bp.getBoxes()if b.getTechLayer()]
  if not boxes:continue
  b=boxes[0];out.write('P\t%d\t%s\t%s\t%s\t%s\t%g\t%g\n'%(pk[p.getName()],p.getName(),str(p.getIoType()),str(p.getSigType()),b.getTechLayer().getName(),(b.xMin()+b.xMax())/(2*u),(b.yMin()+b.yMax())/(2*u)))
 ni=0
 for n in block.getNets():
  sig=str(n.getSigType())
  if sig in('POWER','GROUND'):continue
  drv='-';sinks=[];extra=[]
  for t in n.getITerms():
   i=t.getInst();cid=i.getId()
   if cid in skip:continue
   if t.isOutputSignal():
    if drv=='-':drv='i'+str(cid)
    else:extra.append('i'+str(cid))
    continue
   mt=t.getMTerm();clock=str(mt.getSigType())=='CLOCK'or bool(re.match(r'^(CLK|CK|GCLK)$',mt.getName()))
   sinks.append('i'+str(cid)+('c'if clock else''))
  for t in n.getBTerms():
   ref='p'+str(pk[t.getName()])
   if str(t.getIoType())=='INPUT'and drv=='-':drv=ref
   else:sinks.append(ref)
  if not sinks:continue
  out.write('N\t'+sig+'\t'+drv+'\t'+'\t'.join(sinks)+'\n')
  for d in extra:out.write('ND\t'+d+'\n')
  net_index[n.getId()]=ni;ni+=1
macros={}
for i in block.getInsts():
 if not i.getMaster().isBlock():continue
 b=i.getBBox();ports=[]
 for t in i.getITerms():
  mt=t.getMTerm()
  if str(mt.getSigType())in('POWER','GROUND'):continue
  v=t.getAvgXY()
  if len(v)==3:
   ok,x,y=v;assert ok,(i.getName(),mt.getName())
  else:x,y=v
  n=t.getNet();ports.append(dict(port=mt.getName(),io=str(mt.getIoType()),xy=[x/u,y/u],geom_net_index=net_index.get(n.getId())if n else None))
 macros[i.getName()]=dict(cid=i.getId(),master=i.getMaster().getName(),orient=str(i.getOrient()),bbox_um=[v/u for v in(b.xMin(),b.yMin(),b.xMax(),b.yMax())],ports=ports)
(outdir/'actual_macro_ports.json').write_text(json.dumps(dict(macros=macros)))
print('NATIVE_GEOM exported',ni,'actual signal nets',len(macros),'macros; no extra ODB load')

import json,re,collections,sys,math
pl=sys.argv[1]; P=json.load(open(pl+'/die_plan.json'))
rows=[]
for t,v in P['partition_types'].items():
  hc={h['inst']:h for h in v.get('hard_cores') or []}
  org=v.get('origin_um')
  pins={}
  def pinpos(inst,port):
    h=hc[inst]; f=h['pins_file']
    if f not in pins: pins[f]=json.load(open(pl+'/'+f))
    pts=[p for p in pins[f] if p['name']==port or p['name'].startswith(port+'[')]
    if not pts: return None
    W,H=h['outline_um']; o=h.get('orient','R0'); ox,oy=h['origin_um']
    xs=[(W-p['x'] if o in('MY','R180') else p['x']) for p in pts]; ys=[(H-p['y'] if o in('MX','R180') else p['y']) for p in pts]
    return ox+sum(xs)/len(xs),oy+sum(ys)/len(ys)
  for st in v.get('internal_stations') or []:
    for end,key,chain in (('launch','from_um',0),('capture','to_um',-1)):
      e=st.get(end)
      if not isinstance(e,str) or not re.match(r'u_svg_\w+__[tob]\d?(\.|$)',e): continue
      inst,_,port=e.partition('.')
      if not port: continue
      q=pinpos(inst,port)
      if q is None: rows.append((t,e,'NOPIN',0,0)); continue
      r=st.get('regs_um') or []
      nb=(r[0] if chain==0 else r[-1]) if r else st['from_um' if chain else 'to_um']
      d=abs(q[0]-nb[0])+abs(q[1]-nb[1]); old=abs(st[key][0]-nb[0])+abs(st[key][1]-nb[1])
      rows.append((t,e,round(d),round(old),st.get('bits')))
print(len(rows),'ends; NOPIN',sum(1 for r in rows if r[2]=='NOPIN'))
ok=[r for r in rows if r[2]!='NOPIN']; ok.sort(key=lambda r:-r[2])
print('hop >450:',sum(r[2]>450 for r in ok),'>360:',sum(r[2]>360 for r in ok),'old >450',sum(r[3]>450 for r in ok))
for r in ok[:14]: print(r)
c=collections.Counter(re.sub(r'u_svg_\w+__','',r[1]) for r in ok if r[2]>450); print(c.most_common(16))

import json,sys,re,collections
p=json.load(open(sys.argv[1])); H=4.32
for tn in ['q_hub_nw','q_hub_ne']:
  t=p['partition_types'][tn]; R=[]
  for c in t['hard_cores']:
    (x,y),(w,h)=c['origin_um'],c['outline_um']
    if c.get('orient','R0') in ('R90','R270','MXR90','MYR90'): w,h=h,w
    R.append((c['inst'],x-H,y-H,x+w+H,y+h+H,x,y,x+w,y+h))
  n=0;tot=0;bysrc=collections.Counter();bycore=collections.Counter();deep=0;bits=0;legs=set()
  for i,s in enumerate(t['internal_stations']):
    src=re.split(r'[ (,|]',s.get('note','?').strip())[0][:40]
    for r in s.get('regs_um',[]):
      tot+=1
      for (nm,a,b,c2,d,X0,Y0,X1,Y1) in R:
        if a<r[0]<c2 and b<r[1]<d:
          n+=1;bysrc[src]+=1;bycore[nm]+=1;bits+=s.get('bits',0);legs.add(i)
          if X0<r[0]<X1 and Y0<r[1]<Y1: deep+=1
          break
  print(tn,'regs',tot,'in body+halo',n,'strictly in body',deep,'legs',len(legs),'of',len(t['internal_stations']),'bitFF',bits)
  print('  by note-src',bysrc.most_common(8)); print('  by core',bycore.most_common(8))

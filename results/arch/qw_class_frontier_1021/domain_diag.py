import pickle,json,sys
D=pickle.load(open(sys.argv[1],'rb'));by={n:(ms,x,y,w,h) for n,ms,x,y,w,h in D['insts']};n=sys.argv[2]
print('TARGET',n,by[n]);UL=VL=-1e99;UH=VH=1e99
for bid,width,a,b in D['incident'][n]:
 own,peer=(a,b) if a[0]==n else(b,a);j=by[peer[0]];rows=[]
 for k,(qa,qb) in enumerate(zip(D['local'][tuple(own)+(width,)],D['local'][tuple(peer)+(width,)])):
  cx,cy=j[1]+qb[0]-qa[0],j[2]+qb[1]-qa[1]
  rows.append((cx+cy,cx-cy,k,cx,cy))
 ul=max(z[0]-405 for z in rows);uh=min(z[0]+405 for z in rows);vl=max(z[1]-405 for z in rows);vh=min(z[1]+405 for z in rows)
 UL=max(UL,ul);UH=min(UH,uh);VL=max(VL,vl);VH=min(VH,vh)
 print('PAIR',bid,width,own,peer,'PEER',j,'class?',peer[0]in D['names'],'uv',[ul,uh,vl,vh], 'constraints',min(rows),max(rows))
print('ALL_DOMAIN',UL,UH,VL,VH,'yl',(UL-VH)/2,'yh',(UH-VL)/2)
print('SRCFRAME',D['src'].get(next(r['source_instance']for r in D['receipts'] if r['instance']==n)))

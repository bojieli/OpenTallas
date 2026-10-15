import json,re,pathlib,collections,itertools
r=pathlib.Path('/home/ubuntu/wt/hbm-smcompact-1014');d=json.load(open(r/'results/arch/hbm_native_1013/sm/component.json')); C={c['instance']:c for c in d['children']};pins={};dims={}
for n,c in C.items():
 if not n.startswith('g_fd.u_fc') or n.endswith(('.u_bc','.u_is')):continue
 t=(r/c['view_lef']).read_text();dims[n]=tuple(map(float,re.search(r'SIZE\s+(\S+) BY (\S+)',t).groups()));pins[n]={}
 for name,b in re.findall(r'  PIN (\S+)\n(.*?)  END \S+\n',t,re.S):
  m=re.search(r'RECT\s+(\S+) (\S+) (\S+) (\S+)',b)
  if m:
   x0,y0,x1,y1=map(float,m.groups());pins[n][name]=((x0+x1)/2,(y0+y1)/2)
names=['g_fd.u_fc.u_'+s for s in ['te','be','re','tw','xl','rw','bw']]; xpos={};x=2000
for n in names:xpos[n]=x;x+=dims[n][0]+20
fr={'be':.25,'bw':.5,'re':.91,'rw':0,'te':1,'tw':1,'xl':.05};ors={'be':'MY','bw':'MX','re':'R180','rw':'R0','te':'R0','tw':'R0','xl':'MY'}
ys={n:(322.4-dims[n][1])*fr[n.split('u_')[-1]]for n in names}
for n in names:C[n]['orientation']=ors[n.split('u_')[-1]]
rows=[]
def xy(n,p):
 x,y=pins[n][p];w,h=dims[n];o=C[n]['orientation']
 if o in('MY','R180'):x=w-x
 if o in('MX','R180'):y=h-y
 return xpos[n]+x,ys[n]+y
for e in d['connections']:
 ep=e['endpoints']
 if len(ep)!=2 or not all(v['instance']in pins for v in ep)or e.get('kind')in('clock','reset'):continue
 a,b=ep
 for bit in range(a['width']):
  def pn(v):return v['port'] if v['width']==1 else f"{v['port']}[{v['lsb']+bit}]"
  pa,pb=pn(a),pn(b)
  if pa not in pins[a['instance']]or pb not in pins[b['instance']]:continue
  ax,ay=xy(a['instance'],pa);bx,by=xy(b['instance'],pb)
  rows.append(dict(net=e['net'],bit=bit,a=[a['instance'],pa,ax,ay],b=[b['instance'],pb,bx,by],reach=abs(ax-bx)+abs(ay-by)))
by=collections.defaultdict(list)
for t in rows:by[(t['a'][0],t['b'][0])].append(t['reach'])
for p,v in by.items():print(p,len(v),max(v),sum(x>500for x in v))
json.dump(dict(origins={n:[xpos[n],ys[n]]for n in names},rows=rows),open('results/hbm_sm_dense_pack/legacy_strip_probe.json','w'),indent=2)

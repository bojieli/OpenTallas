import json,re,itertools,pathlib
r=pathlib.Path('/home/ubuntu/wt/hbm-smcompact-1014');g=json.load(open('results/hbm_sm_dense_pack/split18_east_canonical.json'));B={b['name']:b for b in g['blocks']};gate=json.load(open('/home/ubuntu/wt/sm-dense-pack-1015/results/hbm_sm_dense_pack/split18_east_gate.json'));M=json.load(open('/home/ubuntu/wt/sm-dense-pack-1015/results/hbm_sm_dense_pack/plan.json'))['source_models'];P={}
for k in ['row_w','row_e','beat_e']:
 p=r/f'physical/ref_tile/smh_tr_group_{k}_ref/views'/f'ot_smh_tr_group_{k}'/f'ot_smh_tr_group_{k}.lef';t=p.read_text();P[k]={}
 for n,b in re.findall(r'  PIN (\S+)\n(.*?)  END \S+\n',t,re.S):
  m=re.search(r'RECT\s+(\S+) (\S+) (\S+) (\S+)',b)
  if m:
   x0,y0,x1,y1=map(float,m.groups());P[k][n]=[(x0+x1)/2,(y0+y1)/2]
def xy(n,p,o,k):
 b=B[n];x,y=P[k][p] if k in P else [M[k]['pins'][p]['x'],M[k]['pins'][p]['y']]
 if o in('MY','R180'):x=b['w']-x
 if o in('MX','R180'):y=b['h']-y
 return[b['x']+x,b['y']+y]
for lf in range(2):
 os=gate['compute_and_landing'][str(lf)]['orientations']['xs'];best=None
 for ow,oe in itertools.product(['R0','MX','MY','R180'],repeat=2):
  v=[]
  for i in range(818):
   a=xy(f'{lf}_rowW',f'first[{i}]',ow,'row_w');b=xy(f'{lf}_xs',f'rl1[{i}]',os,'xs');c=xy(f'{lf}_rowW',f'last[{i}]',ow,'row_w');d=xy(f'{lf}_rowE',f'd[{i}]',oe,'row_e');v.extend([abs(a[0]-b[0])+abs(a[1]-b[1]),abs(c[0]-d[0])+abs(c[1]-d[1])])
  q=(sum(x>500for x in v),max(v),ow,oe)
  if best is None or q<best:best=q
 print(lf,best)

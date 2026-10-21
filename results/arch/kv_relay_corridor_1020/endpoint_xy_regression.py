"""Execute the real nested _spot and refinement AST on the captured A failure."""
import ast,json,math,sys
from pathlib import Path
source=Path(sys.argv[1]); fixture=Path(sys.argv[2])
tree=ast.parse(source.read_text()); nodes=list(ast.walk(tree))
spot=next(n for n in nodes if isinstance(n,ast.FunctionDef) and n.name=='_spot')
chain=next(n for n in nodes if isinstance(n,ast.FunctionDef) and n.name=='chain_')
fine_assign=next(n for n in ast.walk(chain) if isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id=='fine_' for x in n.targets))
xy=next(n for n in ast.walk(chain) if isinstance(n,ast.If) and isinstance(n.test,ast.Name) and n.test.id=='RLY_FINE_XY')
d=json.loads(fixture.read_text());state=d['state'];insts=d['insts'];dst=next(i for i in insts if i['name']=='d2d_kv')
points=d['endpoint_view'][4];fw,fh=45.38,82.10;GX,GY,G=.432,2.16,21.6
up=lambda x,g: math.ceil(x/g)*g
far=lambda p:max(abs(p[0]-dst['x']-x)+abs(p[1]-dst['y']-y) for x,y in points)
def free(x,y,w,h,*unused):
 for i in insts:
  gap=4.32 if i['kind']=='relay' else 21.6
  extra=.02 if i['kind']=='relay' else 0
  if i['x']<x+w+gap and x-gap<i['x']+i['w']+extra and i['y']<y+h+gap and y-gap<i['y']+i['h']+extra:return False
 return True
ns=dict(st_=state,up=up,GX=GX,GY=GY,fw=fw,fh=fh,TG=(),free=free,
 d_ep=lambda pt,*_:far(pt),a=d['src'][0],pa=d['src'][1],b=d['dst'][0],pb=d['dst'][1],remaining_=lambda:far(state['prev_pt']))
exec(compile(ast.Module(body=[spot],type_ignores=[]),str(source),'exec'),ns)
offs=[(0,0)]+[(i*G,j*G) for r in range(1,7) for i in range(-r,r+1) for j in range(-r,r+1) if max(abs(i),abs(j))==r]
ns.update(offl_=offs,RLY_FINE_STEPS=(10.8,-10.8,21.6,-21.6,32.4,-32.4))
refine=compile(ast.Module(body=[fine_assign,xy],type_ignores=[]),str(source),'exec')
args=([len(state['path'])-1],None,state['prev_pt'],340,False,True)
for enabled in [False,True]:
 ns['RLY_FINE_XY']=enabled;exec(refine,ns)
 got=ns['_spot'](args[0],ns['fine_'],*args[2:])
 if not enabled:
  assert got is None,got
  print('LEGACY_Y_ONLY_EXPECTED_FAIL')
 else:
  assert got is not None
  x,y,idx=got;din=abs(x-state['prev_pt'][0])+abs(y+fh/2-state['prev_pt'][1]);dout=far((x+fw,y+fh/2))
  assert max(din,dout)<=340 and free(x,y,fw,fh)
  print(json.dumps(dict(XY='PASS',x=x,y=y,path_index=idx,previous_um=din,farthest_pin_um=dout)))
# Reach is never waived: moving the previous stage out of reach must refuse.
assert ns['_spot'](args[0],ns['fine_'],(-10000,-10000),340,False,True) is None
print('UNREACHABLE_PREDECESSOR_EXPECTED_FAIL')

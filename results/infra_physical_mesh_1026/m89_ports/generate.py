from pathlib import Path
import json
p=Path(__file__).parent
xs=[18.414,78.408];ys=[19.98,79.92];cells=[]
for j,y in enumerate(ys):
 for i,x in enumerate(xs):
  k=j*2+i;cells.extend([(f'drv{k}',x,y),(f'stub{k}',x+4.05,y)])
u=lambda x:int(round(x*1000))
h=['VERSION 5.8 ;','DIVIDERCHAR "/" ;','BUSBITCHARS "[]" ;','DESIGN mesh2 ;','UNITS DISTANCE MICRONS 1000 ;','DIEAREA ( 0 0 ) ( 100000 100000 ) ;']
for j in range(370):h.append(f'ROW core{j} asap7sc7p5t 0 {j*270} N DO 1851 BY 1 STEP 54 0 ;')
h+=['COMPONENTS 8 ;']+[f'- {n} BUFx24_ASAP7_75t_R + FIXED ( {u(x)} {u(y)} ) N ;' for n,x,y in cells]+['END COMPONENTS']
ports=[('clk','clk','INPUT','CLOCK','M9',50,95),('vdd','VDD','INOUT','POWER','M2',10,5),('vss','VSS','INOUT','GROUND','M2',90,5)]
for k in range(4):ports.append((f'o{k}',f'o{k}','OUTPUT','SIGNAL','M9',30 if k%2==0 else 90,25 if k<2 else 85))
ports=[(n,net,dr,use,l,.116+round((x-.116)/.080)*.080,.116+round((y-.116)/.080)*.080) if l=='M9' else (n,net,dr,use,l,x,y) for n,net,dr,use,l,x,y in ports]
h+=['PINS 7 ;']+[f'- {n} + NET {net} + DIRECTION {dr} + USE {use} + PORT + LAYER {l} ( -80 -80 ) ( 80 80 ) + FIXED ( {u(x)} {u(y)} ) N ;' for n,net,dr,use,l,x,y in ports]+['END PINS']
h+=['NETS 5 ;','- clk ( PIN clk ) '+' '.join(f'( drv{k} A )' for k in range(4))+' + USE CLOCK ;']
h += [f'- o{k} ( stub{k} Y ) ( PIN o{k} ) ;' for k in range(4)]+['END NETS']
sp=['SPECIALNETS 3 ;','- ck_mesh '+' '.join(f'( drv{k} Y ) ( stub{k} A )' for k in range(4))+' + USE CLOCK']
mx=[x+1.593 for x in xs];my=[y+.135 for y in ys];first=True
def path(layer,width,a,b=None,vias=()):
 global first
 s=f'  {"+ FIXED" if first else "NEW"} {layer} {u(width)} ( {u(a[0])} {u(a[1])} )'
 if b is not None:s+=f' ( {u(b[0])} {u(b[1])} )'
 s+=''.join(' '+v for v in vias);sp.append(s);first=False
for y in my:path('M8',.16,(mx[0]-.2,y),(xs[1]+4.05+.027+.2,y))
for x in mx:path('M9',.16,(x,my[0]-.2),(x,my[1]+.2))
for y in my:
 for x in mx:path('M8',.16,(x,y),vias=['VIA89'])
for k in range(4):
 x=xs[k%2];y=ys[k//2]
 path('M1',.018,(x+1.593,y+.135),vias=[f'VIA{i}{i+1}' for i in range(1,8)])
 path('M1',.018,(x+4.05+.027,y+.135),vias=[f'VIA{i}{i+1}' for i in range(1,8)])
sp[-1]+=' ;'
for net,trunk,kind,pin,offset in [('VDD',10,'POWER','vdd',.27),('VSS',90,'GROUND','vss',0)]:
 sp+=['- '+net+f' ( PIN {pin} ) '+' '.join(f'( {n} {net} )' for n,x,y in cells)+f' + USE {kind}'];first=True
 path('M2',.018,(trunk,5),(trunk,85))
 for y in ys:
  path('M1',.018,(5,y+offset),(95,y+offset))
  path('M1',.018,(trunk,y+offset),vias=['VIA12'])
 sp[-1]+=' ;'
h+=sp+['END SPECIALNETS','END DESIGN'];(p/'mesh.def').write_text('\n'.join(h)+'\n')
v=['module mesh2(input clk, output o0,o1,o2,o3);','wire ck_mesh;']
for k in range(4):v += [f'BUFx24_ASAP7_75t_R drv{k}(.A(clk),.Y(ck_mesh));',f'BUFx24_ASAP7_75t_R stub{k}(.A(ck_mesh),.Y(o{k}));']
v+=['endmodule'];(p/'mesh.v').write_text('\n'.join(v)+'\n')
(p/'geometry.json').write_text(json.dumps({'cells':cells,'mesh_x':mx,'mesh_y':my,'pg_trunks':{'VDD':10,'VSS':90},'cell_master':'BUFx24_ASAP7_75t_R','mesh_width_um':.16,'mesh_intersection_vias':4,'pin_access_stacks':8,'pin_access_vias_per_stack':7,'ports':ports},indent=2)+'\n')

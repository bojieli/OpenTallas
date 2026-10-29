import sys,json,re,math,collections
from pathlib import Path
sys.path.insert(0,'/home/ubuntu/OpenTallas/tools/autopilot');import geom_rules as G
p=Path(__file__).parent/'astk_actual';D=G.Design(p/'geom.tsv');orig=dict(D.cells);moves=[]
for i,c in D.cells.items():
 if c[0]!='B' or not re.fullmatch('input[0-9]+',c[6]):continue
 ins=[D.nets[n] for n,ck in D.cell_in[i] if not ck and D.nets[n][1] and D.nets[n][1][0]=='p']
 if len(ins)!=1:continue
 pin=D.pin_by_k[ins[0][1][1]]
 if re.search('ck|clk|rst|reset',pin['name'],re.I):continue
 loads=[s[1] for ni in D.drives[i] for s in D.nets[ni][2] if s[0]=='i' and D.cells[s[1]][0]=='S']
 if len(loads)!=1:continue
 face=D.cells[loads[0]];fx,fy=G.ctr(face);px,py=pin['x'],pin['y']
 if abs(px-fx)+abs(py-fy)>30:continue
 if abs(G.ctr(c)[0]-px)+abs(G.ctr(c)[1]-py)<12:continue
 moves.append({'id':i,'name':c[6],'pin':pin['name'],'pinxy':[px,py],'ff':face[6],'ffxy':[fx,fy]})
print('SOURCE_BUFFER_MOVES',len(moves));moving={x['name'] for x in moves};x0=y0=4.32;sw=.054;sh=.27;nx=3360;ny=640;rows=[bytearray(nx) for _ in range(ny)]
for ln in (p/'sites.txt').read_text().splitlines():
 f=ln.split()
 if f[:1]!=['FIXED'] or f[1] in moving:continue
 x,y,xx,yy=map(float,f[3:7]);a=max(0,int(math.floor((x-x0)/sw+1e-5)));b=min(nx,int(math.ceil((xx-x0)/sw-1e-5)));j0=max(0,int(math.floor((y-y0)/sh+1e-5)));j1=min(ny,int(math.ceil((yy-y0)/sh-1e-5)))
 for j in range(j0,j1):rows[j][a:b]=b'\1'*(b-a)
for a in sorted(moves,key=lambda z:z['ffxy'][1]):
 c=D.cells[a['id']];w,h=c[4]-c[2],c[5]-c[3];nw=round(w/sw);px,py=a['pinxy'];fx,fy=a['ffxy'];cx=(min(max(px,4.32+w/2),185.76-w/2)+fx)/2;cy=(min(max(py,4.32+h/2),177.12-h/2)+fy)/2;ix=round((cx-w/2-x0)/sw);iy=round((cy-h/2-y0)/sh)
 candidates=[]
 for dy in range(-20,21):
  j=iy+dy
  if not 0<=j<ny:continue
  for dx in range(-160,161,2):
   k=ix+dx
   if k<0 or k+nw>nx or any(rows[j][k:k+nw]):continue
   xx=x0+k*sw;yy=y0+j*sh;mx,my=xx+w/2,yy+h/2;cost=abs(mx-px)+abs(my-py)+abs(mx-fx)+abs(my-fy)
   candidates.append((cost,abs(dy),j,k,xx,yy))
 if not candidates:raise RuntimeError(('NO_SITE',a))
 _,_,j,k,xx,yy=min(candidates);rows[j][k:k+nw]=b'\1'*nw;box=(xx,yy,xx+w,yy+h);D.cells[a['id']]=c[:2]+box+c[6:];a.update(origin=[xx,yy],box=box,oldbox=list(c[2:6]))
metrics=G.demand_metrics(D);r2r=G.r2r_metrics(D);print('PLANNED_COLUMN',metrics['col_v_max'],metrics['col_v_at'],'R2R',r2r['r2r_max']);report={'moves':moves,'new_demand':metrics,'r2r':r2r,'clock_and_all_FFs_unchanged':True,'cycles_added':0};(p/'input_buffer_plan.json').write_text(json.dumps(report,indent=1)+'\n')
t=['# Move only source-identified data input buffers beside their own fixed face FFs.','set b [ord::get_db_block]','set u [[ord::get_db_tech] getDbUnitsPerMicron]','foreach i [$b getInsts] {$i setPlacementStatus FIRM}']
for a in moves:
 t+=['set c [$b findInst {'+a['name']+'}]','if {$c eq "NULL"} {error "missing exact input buffer"}','$c setPlacementStatus PLACED',f'$c setLocation [expr {{round({a["origin"][0]:.6f} * $u)}}] [expr {{round({a["origin"][1]:.6f} * $u)}}]','$c setPlacementStatus FIRM']
(p/'input_buffer_anchors.tcl').write_text('\n'.join(t)+'\n')

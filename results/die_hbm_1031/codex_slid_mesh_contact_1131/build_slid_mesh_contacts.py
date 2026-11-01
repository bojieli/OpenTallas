from pathlib import Path
import sys,json,re,shutil,subprocess,math
r=Path(__file__).resolve().parent
sys.path.insert(0,'/srv/opentallas-scratch/claude/wt/codex-hbm-mesh-core-union-1131/tools/die_plan')
import clock_routed as C
p=json.load(open(r/'union600/NW.json'));g=p['geom'];names=['M0_0','M0_1'];base=r/'slid_contact_base.def'
subprocess.run([sys.executable,str(r/'crop2.py'),str(r/'union600/NW.def'),str(base),'230','100','340','450'],check=True)
def section(s,name,lines):return re.sub(rf'(?ms)^{name} \d+ ;.*?^END {name}',f'{name} {len(lines)} ;\n'+'\n'.join(lines)+f'\nEND {name}',s)
for form,delta in [('near',0),('east',4.32)]:
 o=r/f'slid_mesh_contact_{form}';o.mkdir(exist_ok=True)
 cells={n:dict(x=p['cells'][n]['x'],y=p['cells'][n]['y'],lib=p['cells'][n]['master'],orient='MX' if round(p['cells'][n]['y']/.27)%2 else 'R0')for n in names}
 s=section(base.read_text(),'COMPONENTS',[f'- {n} {c["lib"]} + FIXED ( {round(c["x"]*1000)} {round(c["y"]*1000)} ) '+('FS' if c['orient']=='MX' else 'N')+' ;' for n,c in cells.items()])
 pins=[];nets=[]
 for i,(n,c) in enumerate(cells.items()):
  # Actual A boundary uses a separate PG-gap track, not a point on the mesh dogleg.
  x=round((round((c['x']-3.0)/4.32-.5)+.5)*4.32,4)+.004
  pins.append(f'- drive{i} + NET input{i} + DIRECTION INPUT + USE CLOCK + LAYER M9 ( -20 -40 ) ( 20 40 ) + FIXED ( {round(x*1000)} {round(c["y"]*1000)} ) N ;')
  nets.append(f'- input{i} ( PIN drive{i} ) ( {n} A ) + USE CLOCK ;')
 pins.append('- mesh_contact + NET ck_mesh + DIRECTION OUTPUT + USE CLOCK + LAYER M9 ( -20 -40 ) ( 20 40 ) + FIXED ( 257040 270000 ) N ;')
 s=s.replace('COMPONENTS',f'PINS {len(pins)} ;\n'+'\n'.join(pins)+'\nEND PINS\nCOMPONENTS',1)
 s=section(s,'NETS',nets);s=s.replace('- ck_mesh + ROUTED','- ck_mesh '+' '.join(f'( {n} Y )' for n in names)+' ( PIN mesh_contact ) + ROUTED')
 # Keep native hard-core blockages and reserve lower-layer metal except bounded driver access windows.
 existing=re.search(r'(?ms)^BLOCKAGES \d+ ;\n(.*?)^END BLOCKAGES',s)[1].splitlines()
 cores=[c for c in g['cores'] if c['rect'][0]<340 and c['rect'][2]>230 and c['rect'][1]<450 and c['rect'][3]>100]
 windows=[(c['x']-4,c['y']-2,c['x']+7.2,c['y']+2.27) for c in cells.values()]
 ys=sorted({100,450}|{q for a,b,c,d in windows for q in(b,d)});blocks=[]
 for ya,yb in zip(ys,ys[1:]):
  xx=230
  for a,b in sorted((max(230,a),min(340,c)) for a,b,c,d in windows if b<(ya+yb)/2<d)+[(340,340)]:
   if a>xx:
    blocks += [f'- LAYER M{l} RECT ( {round(xx*1000)} {round(ya*1000)} ) ( {round(a*1000)} {round(yb*1000)} ) ;' for l in range(2,8)]
   xx=max(xx,b)
 for core in cores:
  a,b,c,d=core['rect']
  blocks += [f'- LAYER M{l} RECT ( {round(max(230,a)*1000)} {round(max(100,b)*1000)} ) ( {round(min(340,c)*1000)} {round(min(450,d)*1000)} ) ;' for l in range(1,6)]
 s=section(s,'BLOCKAGES',blocks);(o/'pilot.def').write_text(s)
 ys=sorted({100,135,136.08,270,403.92,405,450});edges=[[['M9',257.04,a],['M9',257.04,b]]for a,b in zip(ys,ys[1:])]
 for y in [136.08,403.92]:edges += [[['M8',230,y],['M8',257.04,y]],[['M8',257.04,y],['M8',340,y]],[['M8',257.04,y],['M9',257.04,y]]]
 drivers=[];legs=[]
 for n,c in cells.items():
  ax,ay=g['drv_anchor'][n];px,py=C.pin_point(cells,n,'Y',c['lib']);sx=round((round(px/4.32-.5)+.5)*4.32+delta,4)
  pts=[['M9',ax,ay],['M8',ax,ay],['M8',sx,ay],['M9',sx,ay],['M9',sx,py]]
  edges += [[a,b]for a,b in zip(pts,pts[1:]) if a!=b];drivers.append(dict(anchor=pts[-1],units=[n]));legs.append(dict(cell=n,vertices=pts))
 graph=dict(edges=edges,vias=sum(a[0]!=b[0]for a,b in edges),drivers=drivers,taps=[dict(port_node=['M9',257.04,270],port='mesh_contact')])
 wire=dict(name='ck_mesh',explicit_mesh=True,ndr='4w',mesh_graph=graph)
 lines,rec=C.routed_tcl([wire],cells,{'mesh_contact':dict(layer='M9',xy=[257.04,270])},'BUFx24_ASAP7_75t_R','CONTACT')
 (o/'fixed_mesh.tcl').write_text('set blk [ord::get_db_block]\nset tech [ord::get_db_tech]\nforeach sw [[$blk findNet ck_mesh] getSWires] {odb::dbSWire_destroy $sw}\n'+'\n'.join(lines)+'\n')
 for f in ['mesh_contact_route.tcl','rcx.tcl','ndr.tcl','run.sh']:shutil.copy2(r/'mesh_contact_fixed_r3'/f,o/f)
 (o/'scope.json').write_text(json.dumps(dict(variant=form,cells=cells,cores=cores,graph=graph,legs=legs,record=rec,scope='Two actual union-sited relocated mesh drivers to original strap anchors via explicit PG-gap M8/M9 doglegs; diagnostic physical contact only, not full current event',release_qualified=False),indent=2))
print('Two actual relocated mesh contacts built')

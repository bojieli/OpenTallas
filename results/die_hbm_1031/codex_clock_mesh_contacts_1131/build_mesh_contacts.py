from pathlib import Path
import json,re,sys,subprocess
r=Path(__file__).resolve().parent;sys.path.insert(0,'/srv/opentallas-scratch/claude/wt/codex-hbm-clock-sparse/tools/die_plan');import schema as S,die_trial as DT
P=S.Plan(S.load(r/'current_C11E_plan.json'));sm=DT.SiteMap(P)
base=r/'contact_base.def';subprocess.run([sys.executable,str(r/'crop2.py'),str(r/'NW_pilot.def'),str(base),'220','3000','300','3450'],check=True)
s=base.read_text();cells=json.load(open(r/'NW_pilot.json'))['cells'];names=['M0_11','M0_12'];pos={n:[cells[n]['x'],cells[n]['y']] for n in names}
def section(text,name,lines):return re.sub(rf'(?ms)^{name} \d+ ;.*?^END {name}',f'{name} {len(lines)} ;\n'+'\n'.join(lines)+f'\nEND {name}',text)
cs=[]
for n in names:
 c=cells[n];x,y=pos[n];assert all(sm.legal((5140.8+x+dx,6065.28+y+dy)) for dx,dy in [(0,0),(1.62,.27)])
 cs.append(f'- {n} {c["master"]} + FIXED ( {round(x*1000)} {round(y*1000)} ) '+('FS' if round(y/.27)%2 else 'N')+' ;')
s=section(s,'COMPONENTS',cs);pins=[];nets=[]
for i,n in enumerate(names):
 x,y=pos[n];pins.append(f'- drive{i} + NET input{i} + DIRECTION INPUT + USE CLOCK + LAYER M9 ( -20 -40 ) ( 20 40 ) + FIXED ( {round((x-1)*1000)} {round(y*1000)} ) N ;');nets.append(f'- input{i} ( PIN drive{i} ) ( {n} A ) + USE CLOCK ;')
pins.append('- mesh_contact + NET ck_mesh + DIRECTION OUTPUT + USE CLOCK + LAYER M9 ( -20 -40 ) ( 20 40 ) + FIXED ( 257036 3244320 ) N ;')
s=s.replace('COMPONENTS',f'PINS {len(pins)} ;\n'+'\n'.join(pins)+'\nEND PINS\nCOMPONENTS',1)
s=section(s,'NETS',nets);s=s.replace('- ck_mesh + ROUTED','- ck_mesh '+' '.join(f'( {n} Y )' for n in names)+' ( PIN mesh_contact ) + ROUTED')
# Current actual hard-core obstacles; other lower metal reserved except local M4/via access around both drivers.
win=[(x-1.5,y-1.5,x+3.12,y+1.77) for x,y in pos.values()];ys=sorted({3000,3450}|{q for a,b,c,d in win for q in (b,d)});bl=[]
for ya,yb in zip(ys,ys[1:]):
 cuts=[(max(220,a),min(300,c)) for a,b,c,d in win if b<(ya+yb)/2<d];cuts.sort();xx=220
 for a,b in cuts+[(300,300)]:
  if a>xx:
   for l in range(2,8):bl.append(f'- LAYER M{l} RECT ( {round(xx*1000)} {round(ya*1000)} ) ( {round(a*1000)} {round(yb*1000)} ) ;')
  xx=max(xx,b)
cores=[]
for h in P.types[P.parts['NW_hub']['type']]['hard_cores']:
 x,y=h['origin_um'];w,hh=h['outline_um'];box=[x,y,x+w,y+hh]
 if box[2]<220 or x>300 or box[3]<3000 or y>3450:continue
 cores.append(dict(inst=h['inst'],rect_um=box))
 for l in range(1,6):bl.append(f'- LAYER M{l} RECT ( {round(max(220,x)*1000)} {round(max(3000,y)*1000)} ) ( {round(min(300,x+w)*1000)} {round(min(3450,y+hh)*1000)} ) ;')
s=section(s,'BLOCKAGES',bl)
for v in ['narrow','wide']:
 o=r/f'mesh_contact_{v}';o.mkdir(exist_ok=True);(o/'pilot.def').write_text(s);(o/'scope.json').write_text(json.dumps(dict(scope='Actual two BUFx24 Y pins to retained physical clock mesh/PG stripes; no whole mesh phase claim',positions=pos,cores=cores,contact=[257.036,3244.32],variant=v,net='ck_mesh',change='Unmark special clock net for actual DRT pin-to-mesh wiring; retain same net and fixed SWires; no metal short between aliased nets',G4='HELD nativecore+wholeclock+newtaps'),indent=2))
print('CONTACT_READY',len(cs),'cells',len(nets),'input nets; one common mesh net,',len(cores),'current macro obstacles')

from pathlib import Path
import json,re,subprocess,sys
r=Path(__file__).resolve().parent;sys.path.insert(0,'/srv/opentallas-scratch/claude/wt/codex-hbm-clock-sparse/tools/die_plan');import schema as S,die_trial as DT
P=S.Plan(S.load(r/'current_C11E_plan.json'));sm=DT.SiteMap(P);j=json.load(open(r/'NW_pilot.json'));origin=[5140.8,6065.28];base=r/'joint_nw_base.def';subprocess.run([sys.executable,str(r/'crop2.py'),str(r/'NW_pilot.def'),str(base),'4000','1300','4700','2200'],check=True)
def body(s,name):return re.search(rf'(?ms)^{name} \d+ ;\n(.*?)^END {name}',s)[1].strip().splitlines()
def repl(s,name,rows):return re.sub(rf'(?ms)^{name} \d+ ;.*?^END {name}',f'{name} {len(rows)} ;\n'+'\n'.join(rows)+f'\nEND {name}',s)
for v in ['a','b']:
 src=(r/f'feed_nw_actual_{v}_new_r2/pilot.def').read_text();o=r/f'joint_NW_{v.upper()}';o.mkdir(exist_ok=True);s=base.read_text();cs=body(src,'COMPONENTS');pos={}
 for ln in cs:
  z=re.match(r'- (\S+) (\S+).*?\( (\d+) (\d+) \)',ln);pos[z[1]]=[int(z[3])/1000,int(z[4])/1000]
 prefix=['R','P1','P2','N255']+[f'XI{i}'for i in range(8)]
 for n in prefix:
  c=j['cells'][n];x,y=c['x'],c['y'];pos[n]=[x,y];cs.append(f'- {n} {c["master"]} + FIXED ( {round(x*1000)} {round(y*1000)} ) '+('FS'if round(y/.27)%2 else'N')+' ;')
 s=repl(s,'COMPONENTS',cs);pins=[ln for ln in body(src,'PINS') if not ln.startswith('- mesh_root ')];s=s.replace('COMPONENTS',f'PINS {len(pins)} ;\n'+'\n'.join(pins)+'\nEND PINS\nCOMPONENTS',1)
 ns=[ln.replace('( PIN mesh_root )','( R A )')for ln in body(src,'NETS')]
 for nn in ['n_R','n_P1','n_P2']:
  net=j['nets'][nn];ns.append(f'- {nn} ( {net["drv"]} Y ) '+' '.join(f'( {ld} A )'for ld in net['loads'])+' + USE CLOCK ;')
 s=repl(s,'NETS',ns);windows=[(x-1.5,y-1.5,x+3.12,y+1.77) for x,y in pos.values()];ys=sorted({1300,2200}|{z for a,b,c,d in windows for z in(b,d)});bl=[]
 for ya,yb in zip(ys,ys[1:]):
  spans=sorted((max(4000,a),min(4700,c))for a,b,c,d in windows if b<(ya+yb)/2<d);xx=4000
  for a,b in spans+[(4700,4700)]:
   if a>xx:
    for layer in range(2,8):bl.append(f'- LAYER M{layer} RECT ( {round(xx*1000)} {round(ya*1000)} ) ( {round(a*1000)} {round(yb*1000)} ) ;')
   xx=max(xx,b)
 cores=[]
 for h in P.types[P.parts['NW_hub']['type']]['hard_cores']:
  x,y=h['origin_um'];w,hh=h['outline_um'];box=[x,y,x+w,y+hh]
  if box[2]<4000 or x>4700 or box[3]<1300 or y>2200:continue
  cores.append(dict(inst=h['inst'],rect_um=box))
  for layer in range(1,6):bl.append(f'- LAYER M{layer} RECT ( {round(max(4000,x)*1000)} {round(max(1300,y)*1000)} ) ( {round(min(4700,x+w)*1000)} {round(min(2200,y+hh)*1000)} ) ;')
 s=repl(s,'BLOCKAGES',bl);illegal=[n for n,(x,y)in pos.items()if not all(sm.legal((origin[0]+x+dx,origin[1]+y+dy))for dx,dy in[(0,0),(1.62,.27)])];assert not illegal,illegal
 (o/'pilot.def').write_text(s);legs=[dict(src=net['drv'],dst=ld,length_um=abs(pos[net['drv']][0]-pos[ld][0])+abs(pos[net['drv']][1]-pos[ld][1]))for nn,net in j['nets'].items()if nn in['n_R','n_P1','n_P2']for ld in net['loads']]
 (o/'scope.json').write_text(json.dumps(dict(variant=v,positions=pos,cores=cores,legs=legs,native_START_added=0,scope='Actual calibrated die-source fanout + actual R/A->P1->P2 shared prefix; no artificial3fFrootBTerm. Original immediate fanout Aloads retained. Wholemesh/currenttaps/nativecoresG4HELD.'),indent=2));print(v,len(cs),'cells',len(ns),'nets','maxleg',max(z['length_um']for z in legs))

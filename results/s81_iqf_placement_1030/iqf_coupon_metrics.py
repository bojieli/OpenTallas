import sys,json,re,math,pathlib
sys.path.insert(0,sys.argv[1]);import geom_rules as G
r=pathlib.Path('/srv/opentallas-scratch2/claude/codex-s81types-1030');D=G.Design(str(r/'iqf_coupon_movable/geom.tsv'),None,False);P={p['name']:p for p in D.pins};C={c[6]:ci for ci,c in D.cells.items()};pos={};pins=[]
for row in json.load(open(r/'iqf_ft0_targets.json'))['targets']:
 j,b=row['stage'],row['bit'];pos[j,b]=G.ctr(D.cells[C[row['name']]])
 if j in(0,5):
  p=P[f'ft0_{"i" if j==0 else "o"}[{b}]'];x,y=pos[j,b];pins.append(abs(x-p['x'])+abs(y-p['y']))
hops=sorted([(abs(pos[j,b][0]-pos[j-1,b][0])+abs(pos[j,b][1]-pos[j-1,b][1]),j,b) for j in range(1,6) for b in range(1121)],reverse=True);pins.sort()
m=dict(FT0=dict(max_hop=hops[0],over405=sum(h[0]>405 for h in hops),pinp90=pins[math.ceil(.9*len(pins))-1],pinmax=max(pins),worst=hops[:12]),r2r=G.r2r_metrics(D),pinreg=G.pin_reg_metrics(D,re.compile(G.STRAP_RE_DEFAULT)))
(r/'iqf_coupon_movable/metrics.json').write_text(json.dumps(m,indent=1));print(json.dumps(m,indent=1)[:6000])

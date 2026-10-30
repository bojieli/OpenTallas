import json,math,collections
from pathlib import Path
B=Path('/srv/opentallas-scratch2/claude/die-hbm-33/plan/d33s');O=Path('/srv/opentallas-scratch2/claude/codex-hbm-1030/est')
r=json.load(open(B/'die_plan.json'));parts={p['name']:p for p in r['partitions']};T=r['partition_types'];ports={p['id']:p for p in r['ports']}
old=sorted([n for n,p in parts.items() if n.startswith('NW_') and p['origin_um'][1]==4510.08],key=lambda n:parts[n]['origin_um'][0]);C=sorted([n for n,p in parts.items() if n.startswith('NW_') and p['origin_um'][1]==10385.28],key=lambda n:parts[n]['origin_um'][0]);print('BASE',old)
variants={'pairmid2':['b111','spu1','su20','su21','b102','b103','su30','su31','b110','b100','b101'],'pairmid':['b111','su20','su21','spu1','b102','b103','su30','su31','b110','b100','b101'],'paireast':['b111','su20','su21','spu1','su30','b102','b103','su31','b110','b100','b101'],'eastgroup':['su30','su31','spu1','su20','su21','b102','b103','b111','b110','b100','b101'],'midgroup':['su20','su21','spu1','b102','b103','b111','su30','su31','b110','b100','b101']}
def rect(n,orig):
 p=parts[n];w,h=T[p['type']]['outline_um'];x,y=orig.get(n,p['origin_um']);return x,y,x+w,y+h
rows=json.load(open(O/'rows81.json'))['rows'];edges=[]
for ln in r['lanes']:
 pp=[ports[q] for q in ln['ports']];a=pp[0]['src']['part'];b=pp[-1]['dst']['part'];edges.append((a,b,pp[0]['width'],'old:'+ln['id']))
for x in rows:
 a,b=x['src'],x['dst'];bits=x['unplanned_bits'];
 if a.endswith('b100') and b.endswith('b102'):a=a[:3]+'hub';bits=2746
 edges.append((a,b,bits,'gap'))
report={}
for name,order in [('base',[n[3:] for n in old])]+list(variants.items()):
 orig={};x=0
 for k in order:
  n='NW_'+k;p=parts[n];w=T[p['type']]['outline_um'][0];orig[n]=[x,4510.08];orig['NE_'+k]=[r['die']['outline_um'][0]-x-w,4510.08];x+=w
 score=0;newfar=[];breaks=[]
 for a,b,bits,kind in edges:
  A=rect(a,orig);D=rect(b,orig);gap=max(0,A[0]-D[2],D[0]-A[2])+max(0,A[1]-D[3],D[1]-A[3]);score+=gap*bits
  if kind=='gap' and bits>=1000:newfar.append([a,b,bits,round(gap,2),math.ceil(gap/405)])
 for p in r['ports']:
  if p['src']['part'] not in orig and p['dst']['part'] not in orig:continue
  a,b=p['src']['part'],p['dst']['part'];A=rect(a,orig);D=rect(b,orig)
  vert=(abs(A[2]-D[0])<.001 or abs(D[2]-A[0])<.001) and min(A[3],D[3])-max(A[1],D[1])>0
  horiz=(abs(A[3]-D[1])<.001 or abs(D[3]-A[1])<.001) and min(A[2],D[2])-max(A[0],D[0])>0
  if not(vert or horiz):breaks.append(p['id'])
 report[name]={'variant':{'name':name,'A':['NW_'+q for q in order],'C':C},'weighted_gap_bit_um':round(score,2),'moved':sum(any(abs(v-u)>.001 for v,u in zip(orig[n],parts[n]['origin_um'])) for n in orig),'broken_ports':len(breaks),'big_unplanned':newfar}
 if name!='base':json.dump(report[name]['variant'],open(O/(name+'.json'),'w'),indent=1)
 print(name,'weighted_gap',round(score),'moved',report[name]['moved'],'broken_ports',len(breaks),'biggaps',newfar)
json.dump(report,open(O/'row_event_estimate.json','w'),indent=1)

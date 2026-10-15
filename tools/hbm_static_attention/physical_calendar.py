#!/usr/bin/env python3
"""Exact32-pair ATT profile: H16 D512 TD32 NL2 FPL6 FML8 PWORDS2.

Each QK beat covers2 rows ×16heads ×16featuretiles ×32terms=16,384MACs.
Each PV beat likewise covers32physicaltiles ×16heads ×32rows=16,384MACs.
No terms are skipped, every result preserves the source chunk8 reduction order.
"""
import argparse,json,math
from pathlib import Path

def schedule(T,mode):
 H,D,TD,NL,PW,FPL,NB=16,512,32,2,2,6,5
 R=TD//H;FC=TD//NL;DPT=TD//NL;events={}
 def put(c,e):events.setdefault(c,[]).append(e)
 put(0,'job')
 for c in range(math.ceil(T/NL)):put(1+c,'kv')
 if mode=='qk':
  for h in range(H):put(1+h,'q')
  for c in range(math.ceil(T/NL)):put(H+1+c,'qk')
  last=H+math.ceil(T/NL)
 else:
  GP=1+max(max(0,FPL*((R*g+j)%8-1))-g//PW for g in range(H) for j in range(R))
  plast=0;flast=0;lasts=[]
  for b in range(math.ceil(T/TD)):
   nw=math.ceil(math.ceil(min(T-b*TD,TD)/R)/PW)
   start=max(plast+1,lasts[b-NB]+GP if b>=NB else 1)
   for c in range(nw):put(start+c,'p')
   plast=start+nw-1
   fs=max(flast+1,2,lasts[b-2] if b>=2 else 2)
   for c in range(FC):put(fs+c,'fill')
   flast=fs+FC-1
   first=max(flast+2,plast+1,lasts[-1]+1 if lasts else 1)
   for c in range(DPT):put(first+c,'pv')
   lasts.append(first+DPT-1)
  last=lasts[-1]
 bits={'job':0,'q':1,'kv':2,'p':3,'fill':4,'qk':5,'pv':6}
 words=[sum(1<<bits[e] for e in events.get(c,[])) for c in range(last+1)]
 return dict(T=T,mode=mode,H=H,D=D,TD=TD,NL=NL,PWORDS=PW,FPL=FPL,FML=8,NBANK=NB,physical_pairs=32,word_count=len(words),words=words,MACs_per_record_per_QK_or_PV=H*D*T,terms_per_beat=16384,expected_issue_beats=T//NL)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
 for T in (128,640):
  for m in ('qk','pv'):
   s=schedule(T,m);(a.out/f'{m}{T}.json').write_text(json.dumps(s,indent=2)+'\n');(a.out/f'{m}{T}.hex').write_text(''.join(f'{w:02x}\n' for w in s['words']+[0]*(512-len(s['words']))))

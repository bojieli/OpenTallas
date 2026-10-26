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
   # RTL p_ready: a new block's first P word needs pl_blk < iss_blk + LA (LA = NBANK-1), and iss_blk
   # advances the edge after block b-LA's last PV beat; bank reuse (b-NB) also needs the drain gap GP.
   LA=NB-1
   start=max(plast+1,lasts[b-LA]+1 if b>=LA else 1,lasts[b-NB]+GP if b>=NB else 1)
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

def resident_event_frames():
 """Four exact physical-profile calendars in one actual1024x256 macro."""
 profiles=[schedule(T,m) for T in (128,640) for m in ('qk','pv')]
 n=max(p['word_count'] for p in profiles)
 words=[sum((p['words'][c] if c<len(p['words']) else 0)<<(7*i) for i,p in enumerate(profiles)) for c in range(n)]
 return profiles,[1|(a<<4)|(w<<14) for a,w in enumerate(words)]

def launch_instruction(profile,epoch=0):
 profiles,_=resident_event_frames();p=profiles[profile]
 return 2|(profile<<4)|((p['word_count']-1)<<6)|(p['T']<<16)|((p['mode']=='pv')<<32)|(epoch<<33)

def outer_record(profile,epoch=0,query_base_sector=0,P_base_sector=4096,P_head_stride_sectors=80):
 profiles,_=resident_event_frames();p=profiles[profile];words=[]
 if p['mode']=='qk':
  for head in range(16):
   for burst in range(8):
    src=query_base_sector+head*64+burst*8
    words.append(4|(epoch<<4)|(head<<5)|(burst<<9)|(src<<12))
 else:
  if P_head_stride_sectors<p['T']//8 or P_head_stride_sectors%8:raise ValueError('nativePheadstride')
  for head in range(16):
   for burst in range(p['T']//64):
    src=P_base_sector+head*P_head_stride_sectors+burst*8
    if src<0 or src+7>65535:raise ValueError('nativePsectoraperture')
    words.append(4|(epoch<<4)|(head<<5)|((burst&7)<<9)|(src<<12)|(1<<28)|((burst>>3)<<29)|((p['T']==640)<<30))
 words += [8]*9
 words.append(launch_instruction(profile,epoch))
 return words

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
 for T in (128,640):
  for m in ('qk','pv'):
   s=schedule(T,m);(a.out/f'{m}{T}.json').write_text(json.dumps(s,indent=2)+'\n');(a.out/f'{m}{T}.hex').write_text(''.join(f'{w:02x}\n' for w in s['words']+[0]*(512-len(s['words']))))

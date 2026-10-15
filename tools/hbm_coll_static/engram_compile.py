#!/usr/bin/env python3
"""Explicit typed238-bit Engram node control -> actual native256 catalogue.

This is the registeredtarget120 extension, not unchanged G25A/HBM programme.
The two-rate calendar remains preliminary until actual crossing RTL proof.
"""
import argparse,hashlib,json,pathlib,sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from uarch_model_hcoll_rowgather import compile_calendar
FIELDS={'capture':(0,10),'sink':(10,16),'select':(26,64),'wr':(90,1),'wrseq':(91,16),'rd':(107,1),'rdseq':(108,16),'rx':(124,1),'rxseq':(125,16),'bridge':(141,49),'srcread':(190,1),'srcrow':(191,5),'srcsector':(196,4),'pkt_expect':(200,1),'pkt_low':(201,1),'pkt_pub':(202,1),'pkt_row':(203,5),'pkt_pair':(208,3),'asm_expect':(211,1),'asm_row':(212,5),'asm_pair':(217,3),'asm_home':(220,8),'consumer_read':(228,1),'consumer_row':(229,5),'consumer_sector':(234,4)}
FIRST=406;LAUNCH=399;BANKS=19

def lower(cal):
    if cal.get('local_slot_schedule'):
        raise ValueError('160-slot successor needs its own native packet/assembler lowering; selected120 ABI cannot encode it')
    return _lower(cal,BANKS,False)

def lower_local_slots(cal):
    if not cal.get('local_slot_schedule'):
        raise ValueError('local-slot lower requires the160-reservation typed successor')
    return _lower(cal,21,True)

def _lower(cal,banks,slots):
    limit=max(x['cycle'] for x in cal['consumer_reads'])-FIRST+1+(5 if slots else 0)
    assert limit<=banks*128
    words=[[0]*(banks*128) for _ in range(9)]
    def put(node,cycle,field,value,offset=0,width=None,merge=False):
        bit,w=FIELDS[field];w=width or w;bit+=offset
        if not 0<=value<1<<w:raise ValueError('fieldoverflow '+field)
        i=cycle-FIRST
        if i<0:raise ValueError('control beforeprogramme '+field)
        mask=((1<<w)-1)<<bit;old=words[node][i]&mask
        if merge:words[node][i]|=value<<bit
        else:
            if old and old!=value<<bit:raise ValueError(f'wordconflict {node}/{cycle}/{field}')
            words[node][i]=(words[node][i]&~mask)|(value<<bit)
    for r in cal['requests']:
        n,c,row,s=r['home'],r['cycle'],r['local_slot'] if slots else r['row'],r['sector']
        put(n,c,'srcread',1);put(n,c,'srcrow',row);put(n,c,'srcsector',s)
        c+=4;put(n,c,'pkt_expect',1)
        if s<8 and s%2==0:put(n,c,'pkt_low',1)
        else:
            put(n,c,'pkt_pub',1);put(n,c,'pkt_row',row);put(n,c,'pkt_pair',s//2)
    for h in cal['hops']:
        n,c=h['link'],h['capture'];source=0 if n==h['home'] else 3
        put(n,c,'capture',1<<source,merge=True);put(n,c+1,'sink',1,merge=True);put(n,c+1,'select',source,0,4)
        put(n,c+3,'bridge',(1<<0)|(1<<5),merge=True)
        put(n,h['write'],'wr',1);put(n,h['write'],'wrseq',h['seq'])
        put(n,h['read'],'rd',1);put(n,h['read'],'rdseq',h['seq'])
        put(n+1,h['receive']-2,'rx',1);put(n+1,h['receive']-2,'rxseq',h['seq'])
        put(n+1,h['receive']+1,'bridge',5<<41,merge=True)
    for p in cal['packets_calendar']:
        c=p['consumer_capture'];row,pair,home=p['local_slot'] if slots else p['row'],p['pair'],p['home']
        put(8,c-3,'capture',1<<3,merge=True);put(8,c-2,'sink',1<<3,merge=True);put(8,c-2,'select',3,12,4)
        put(8,c,'asm_expect',1);put(8,c,'asm_row',row);put(8,c,'asm_pair',pair);put(8,c,'asm_home',cal['home_ranks'][home])
    for r in cal['consumer_reads']:
        put(8,r['cycle'],'consumer_read',1);put(8,r['cycle'],'consumer_row',r['row']);put(8,r['cycle'],'consumer_sector',r['sector'])
    assert all(w>>238==0 for code in words for w in code)
    return words,limit

def audit(cal,words,local_slots=False):
    assert bool(cal.get('local_slot_schedule'))==local_slots
    def get(n,c,f,shift=0,width=None):
        bit,w=FIELDS[f];return words[n][c-FIRST]>>(bit+shift)&((1<<(width or w))-1)
    for h in cal['hops']:
        n,c=h['link'],h['capture'];source=0 if n==h['home'] else 3
        assert get(n,c,'capture')>>source&1
        assert get(n,c+1,'sink')&1 and get(n,c+1,'select',0,4)==source
        assert get(n,c+3,'bridge')&33==33
        assert get(n,h['write'],'wr') and get(n,h['write'],'wrseq')==h['seq']
        assert get(n,h['read'],'rd') and get(n,h['read'],'rdseq')==h['seq']
        assert get(n+1,h['receive']-2,'rx') and get(n+1,h['receive']-2,'rxseq')==h['seq']
        assert get(n+1,h['receive']+1,'bridge')>>41&15==5
    for p in cal['packets_calendar']:
        c=p['consumer_capture'];assert get(8,c,'asm_expect')
        assert get(8,c,'asm_row')==(p['local_slot'] if local_slots else p['row']) and get(8,c,'asm_pair')==p['pair'] and get(8,c,'asm_home')==cal['home_ranks'][p['home']]
    return dict(status='PASS compiledtypedfieldaudit',hops=len(cal['hops']),packets=len(cal['packets_calendar']),sectors=len(cal['consumer_writes']))

def main():
    p=argparse.ArgumentParser();p.add_argument('receipt',type=pathlib.Path);p.add_argument('out',type=pathlib.Path);a=p.parse_args();v=json.loads(a.receipt.read_text());a.out.mkdir(parents=True,exist_ok=True)
    for layer in [1,14]:
        cal=compile_calendar(v,layer,two_rate=True);words,limit=lower(cal);checks=audit(cal,words);d=a.out/f'layer{layer}';d.mkdir(exist_ok=True)
        for n,code in enumerate(words):(d/f'n{n}.hex').write_text(''.join(f'{w:064x}\n' for w in code))
        (d/'calendar.json').write_text(json.dumps(cal,indent=2)+'\n')
        r=dict(status='PRELIMINARY_TYPED_EXTENSION',layer=layer,target=120,version='Engramcontrol256',banks=BANKS,operations_per_word=2,launch=LAUNCH,first_consumer=FIRST,limit=limit,cycles=cal['done'],checks=checks,fields={k:dict(lsb=b,width=w) for k,(b,w) in FIELDS.items()},source_sha256=hashlib.sha256(a.receipt.read_bytes()).hexdigest(),qualification='Actual two-rate crossing proof and native8source/1consumer chain run pending; not unchangedG25A/HBM join or physical qualification')
        (d/'manifest.json').write_text(json.dumps(r,indent=2)+'\n');print(layer,limit,cal['done'],checks)
if __name__=='__main__':main()

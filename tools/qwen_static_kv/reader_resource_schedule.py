#!/usr/bin/env python3
"""Independent, deterministic source-constrained read-only controller compiler.

No RTL discovery traces are inputs. This models the actual PC0 scheduler's
registered refresh/ACT/PRE decisions and JEDEC counters. Static HOST/writer
requests are currently unsupported and fail closed; a read schedule does not
prove their persistent full-token join.
"""
import hashlib,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
RTL='rtl/qwen_sys/static_kv_20261014/ot_qkd_static_kv_timing.sv'

def constants():
    text=(ROOT/RTL).read_text().split(')(\n',1)[0]
    return {k:int(v) for k,v in re.findall(r'\b(T_\w+)\s*=\s*(\d+)',text)}

class ReadResources:
    """Read-only SROW/WR_EN=1, no queued static/write requests, REF_MODE1 PC0."""
    def __init__(self):
        self.t=constants()
        expected=dict(T_RCD=19,T_RP=16,T_RAS=28,T_RTP=6,T_CCDL=3,T_RRDS=3,T_RRDL=4,T_FAW=15,T_RFCPB=196,T_REFIPB=118,T_RREFD=8)
        if any(self.t.get(k)!=v for k,v in expected.items()):raise ValueError('unsupported changed JEDEC resource constants')
        header=(ROOT/RTL).read_text().split(')(\n',1)[0]
        idle={int(k):int(v) for k,v in re.findall(r'\bIDLE(\d)\s*=\s*(\d+)',header)}
        if [idle.get(k) for k in range(8)]!=[3,4,2,5,1,6,0,7]:raise ValueError('unsupported changed idle refresh priorities')
        self.bank=[dict(rcd=0,ras=0,aok=0,rtp=0) for _ in range(32)]
        self.bg=[dict(rrdl=0,ccdl=0,faw=0) for _ in range(4)]
        self.open=set();self.done=set();self.stale=set();self.refreshed=set()
        self.block=None;self.rb=0;self.refpend=False;self.ref=118;self.phase=0
        self.keypipe=[[127]*32 for _ in range(3)];self.bsel=0
        self.rowcmd=None;self.streaming=False;self.running=False;self.j=0;self.last=0
        self.nm1=0;self.row=0;self.rrds=0;self.noact=0;self.vorder=False
        self.reads=[];self.rows=[];self.cycle=0
    def keys(self):
        result=[];k=self.j>>7;idle=[3,4,2,5,1,6,0,7]
        for b in range(32):
            s=b>>2;d=(s-k)&7;opened=b in self.open
            if s==self.last and not opened:base=20 # WR_EN1 source priority, even with empty write queue
            elif not self.streaming:base=idle.index(s)+(32 if opened else 0)
            elif opened:base=24 if b in self.done or b in self.stale else 32
            elif s>=k and s<=self.last:base=16+2-d if d<=2 else d
            else:base=8+s
            result.append(127 if b in self.refreshed else base+(64 if not opened and self.bank[b]['aok']>48 else 0))
        return result
    def legal_read(self):
        b=((self.j>>7)<<2)|(self.j&3)
        return (self.streaming and self.running and b in self.open and b not in self.stale
                and b!=self.block and self.bank[b]['rcd']==0 and self.bg[b&3]['ccdl']==0)
    def tick(self,*,descriptor=None,go=False,reserve=False):
        t=self.t;now=self.cycle;self.cycle+=1
        keys=self.keys();old_bsel=self.bsel
        self.bsel=min(range(32),key=lambda b:(self.keypipe[0][b],b))
        self.keypipe=self.keypipe[1:]+[keys]
        refnext=117 if self.ref==0 else self.ref-1
        actblock=0<refnext<8
        k=self.j>>7
        act=[b for b in range(32) if b>>2 in (k,k+1) and b>>2<=self.last
             and b not in self.open and b not in self.done and b!=self.block
             and self.bank[b]['aok']==0 and self.bg[b&3]['rrdl']==0]
        pre=[b for b in self.open if b in self.done or b in self.stale]
        pre=[b for b in pre if b!=self.block and self.bank[b]['ras']==0 and self.bank[b]['rtp']==0]
        forced=self.refpend and self.rb in self.open and self.bank[self.rb]['ras']==0 and self.bank[self.rb]['rtp']==0
        decision=None
        if refnext==0 and self.refpend:decision=('REF',self.rb)
        elif forced:decision=('PRE',self.rb)
        elif self.streaming and not actblock and self.noact==0 and self.rrds==0 and any(b['faw']==0 for b in self.bg) and act:
            decision=('ACT',min(act))
        elif pre:decision=('PRE',min(pre))
        fire=self.rowcmd;nextcmd=decision if self.phase else None
        if reserve and not self.legal_read():raise ValueError(f'illegal resource reservation {now} j{self.j}')
        if self.ref==0:
            if not fire or fire[0]!='REF' or self.rb in self.open or self.bank[self.rb]['aok']:
                raise ValueError(f'source refresh cannot issue at {now}, bank{self.rb}')
        readbank=((self.j>>7)<<2)|(self.j&3)
        oldj=self.j;oldopen=set(self.open);oldstream=self.streaming
        if fire:self.rows.append((now,*fire,self.row))
        # Timing state follows physical operations, independent of expected outputs.
        free_faw=next((g for g in range(4) if self.bg[g]['faw']==0),None)
        for b,state in enumerate(self.bank):
            act_e=fire==('ACT',b);pre_e=fire==('PRE',b);ref_e=fire==('REF',b)
            state['rcd']=18 if act_e else max(0,state['rcd']-1)
            state['ras']=27 if act_e else max(0,state['ras']-1)
            state['rtp']=5 if reserve and b==readbank else max(0,state['rtp']-1)
            state['aok']=(43 if act_e else 195 if ref_e else 15 if pre_e and state['aok']<16 else max(0,state['aok']-1))
        for g,state in enumerate(self.bg):
            act_g=fire is not None and fire[0]=='ACT' and fire[1]&3==g
            take=fire is not None and fire[0]=='ACT' and g==free_faw
            state['rrdl']=3 if act_g else max(0,state['rrdl']-1)
            state['ccdl']=2 if reserve and readbank&3==g else max(0,state['ccdl']-1)
            state['faw']=14 if take else max(0,state['faw']-1)
        self.rrds=max(0,self.rrds-1);self.noact=max(0,self.noact-1)
        self.ref=refnext;self.phase^=1;self.rowcmd=nextcmd
        # ref_c tested before decrement, and registered bsel tested before its update.
        if (118 if refnext==117 else refnext+1)==48:
            self.refpend=True;self.rb=old_bsel;self.block=old_bsel
        if reserve:
            self.reads.append((now,self.row,self.j))
            if self.j==self.nm1:self.streaming=False
            if (self.j>>2)&31==31:self.done.add(readbank)
            if self.vorder:
                ordinal=((self.j>>3)&15)*16+((self.j>>7)&1)*8+(self.j&7)
                o=(ordinal+1)&255;self.j=512+((o&8)<<4)+((o>>4)<<3)+(o&7)
            else:self.j+=1
        if fire:
            op,b=fire
            if op=='ACT':self.open.add(b);self.rrds=2
            elif op=='PRE':self.open.discard(b);self.stale.discard(b)
            else:
                self.noact=7;self.refpend=False;self.block=None
                self.refreshed.add(self.rb)
                if len(self.refreshed)==32:self.refreshed=set()
        if go and oldstream:self.running=True
        if descriptor is not None:
            if oldstream:raise ValueError('descriptor overlaps live native read range')
            first,n,row=descriptor
            if not 0<=first<n<=1024:raise ValueError('invalid source range')
            self.j=first;self.nm1=n-1;self.row=row;self.last=(n-1)>>7
            self.vorder=(first,n)==(512,768);self.done=set();self.running=False
            self.streaming=True;self.stale=set(self.open)
        return reserve


def compile_reader(stages=36,period=1782,host_requests=(),v_period=1):
    if host_requests:raise ValueError('actual persistent host/write arbitration contracts unsupported; never silently omit')
    if stages not in (1,36):raise ValueError('only actual one-layer or all36 native shape')
    if period<512 or v_period<1:raise ValueError('source resource frame violates read capacity')
    core=ReadResources();events=[];commands=[];stages_out=[]
    # Leaf-origin cycle0: source wrapper PC0 hgo releases after this interval.
    core.cycle=1
    for stage in range(1,stages+1):
        base=(stage-1)*period;row=64+stage-1
        desc={base+14:(0,256,row)}
        gos={base+44}
        v_start=None
        commands += [dict(cycle=base+10,first=0,n=256,row=row,kind='descriptor'),
                     dict(cycle=base+40,kind='go')]
        start=len(events)
        while core.cycle<base+period:
            c=core.cycle
            request=core.legal_read() and c>=base+63 and (core.j<512 or (c-v_start)%v_period==0)
            if request:
                events.append(dict(cycle=c-3,sector=core.j,stage=stage,row=row))
                if len(events)-start==256:
                    v_desc=c-2;v_start=v_desc+33
                    desc[v_desc+4]=(512,768,row);gos.add(v_desc+34)
                    commands.extend([dict(cycle=v_desc,first=512,n=768,row=row,kind='descriptor'),dict(cycle=v_desc+30,kind='go')])
            core.tick(descriptor=desc.get(c),go=c in gos,reserve=request)
        stage_events=events[start:]
        if len(stage_events)!=512 or core.streaming:raise ValueError('512-sector source frame did not finish')
        if [e['sector'] for e in stage_events[:256]]!=list(range(256)):raise ValueError('K sector coverage')
        if sorted(e['sector'] for e in stage_events[256:])!=list(range(512,768)):raise ValueError('V sector coverage')
        stages_out.append(dict(stage=stage,row=row,first=stage_events[0]['cycle'],last=stage_events[-1]['cycle']))
    return dict(schema='opentallas.qwen-kv-resource-reader.v1',scope='SOURCE_CONSTRAINED_READ_ONLY_PROGRAMME',
      source_sha256={RTL:hashlib.sha256((ROOT/RTL).read_bytes()).hexdigest()},
      events=events,commands=commands,stages=stages_out,period=period,v_period=v_period,stop=stages*period,
      production_installable=False,missing=['actual HOST/writer persistent service calendar',
        'actual native PC11 start/consumer and phi-R/route profiles','physical calendar storage/bootloader and die join','next-token persistent refresh/open-row initial state'])

"""Independent fixed-edge compiler for the real compressed calendar leaf.

Input edges name output PIN edges relative to captured go. Every field has an
explicit width; >16 run descriptors or crossing the frame deadline is refused.
This does not infer JEDEC permission or certify an absent integrated schedule.
"""
from dataclasses import dataclass

@dataclass(frozen=True)
class Run:
    edge:int
    count:int=1
    burst:int=1
    gap:int=0
    command:int=0
    mask:int=0
    layer_row:bool=False
    static_read:bool=False
    context_mode:int=0 # 0 literal,1 K count,2 V count; CONTEXT_DESC opt-in only
    context_descriptor:bool=False

    def events(self,count=None):
        return [self.edge+i+(i//self.burst)*self.gap for i in range(self.count if count is None else count)]

    def word(self):
        if not (2<=self.edge<=65535 and 1<=self.count<=1023 and 1<=self.burst<=16 and 0<=self.gap<=255):
            raise ValueError('run exceeds hardware width or pin-capture latency')
        if not (0<=self.command<2**43 and self.mask in (0,1,2,4)):
            raise ValueError('invalid command or multiple column reservations')
        if self.static_read and self.mask!=2:
            raise ValueError('static_read needs static column reservation')
        if self.context_mode not in (0,1,2) or (self.context_descriptor and (not self.context_mode or self.count!=1 or self.mask!=0)):
            raise ValueError('invalid context descriptor/count mode')
        return (self.context_mode<<86)|(int(self.context_descriptor)<<88)|(self.edge-2)|(self.count<<16)|((self.burst-1)<<26)|(self.gap<<30)|(self.command<<38)|(self.mask<<81)|(int(self.layer_row)<<84)|(int(self.static_read)<<85)

def compile_image(runs,deadline=65535,capacity=16,context=None):
    if type(capacity)is not int or not 1<=capacity<=16:raise ValueError('actual hardware supports capacity 1..16')
    if len(runs)>capacity:raise ValueError('run image exceeds real leaf capacity')
    if any(r.context_mode for r in runs) and context is None:
        raise ValueError('context descriptors require explicit T/stack/group collision proof')
    if context is not None:
        T,stack,group=context
        if not (1<=T<=8192 and 0<=stack<4 and 0<=group<8):raise ValueError('invalid context')
        # Enumerate the logical token rows independently of the hardware count.
        k0=sum(1 for t in range(T) if (t>>7)&3==stack and t&7==group and not(t&64))
        kb=sum(1 for t in range(T) if (t>>7)&3==stack)>1024
        counts={1:sum(1 for t in range(T) if (t>>7)&3==stack and t&7==group),
                2:sum(1 for t in range(T) if (t>>7)&3==stack and (((t>>4)&3)<<1|t&1)==group)}
    events={}
    for r in runs:
        word=r.word()
        edges=r.events(counts[r.context_mode] if r.context_mode and not r.context_descriptor else None)
        if r.context_mode==1 and not r.context_descriptor and kb and 0<k0<len(edges):
            gap_needed=max(0,3-(k0%4)) if k0%4 else 0
            existing_gap=edges[k0]-edges[k0-1]-1
            padding=max(0,gap_needed-existing_gap)
            edges=[e+(padding if i>=k0 else 0)for i,e in enumerate(edges)]
        for edge in edges:
            if edge>deadline:raise ValueError('event exceeds fixed frame deadline')
            if edge in events:raise ValueError('calendar output collision')
            events[edge]=dict(command=r.command,mask=r.mask,layer_row=r.layer_row,static_read=r.static_read)
    return dict(words=[r.word() for r in runs]+[0]*(capacity-len(runs)),events=events,
                storage_bits=capacity*128,descriptor_count=len(runs),full_native_qualified=False)

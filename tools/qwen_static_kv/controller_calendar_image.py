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

    def events(self):
        return [self.edge+i+(i//self.burst)*self.gap for i in range(self.count)]

    def word(self):
        if not (2<=self.edge<=65535 and 1<=self.count<=1023 and 1<=self.burst<=16 and 0<=self.gap<=255):
            raise ValueError('run exceeds hardware width or pin-capture latency')
        if not (0<=self.command<2**43 and self.mask in (0,1,2,4)):
            raise ValueError('invalid command or multiple column reservations')
        if self.static_read and self.mask!=2:
            raise ValueError('static_read needs static column reservation')
        return (self.edge-2)|(self.count<<16)|((self.burst-1)<<26)|(self.gap<<30)|(self.command<<38)|(self.mask<<81)|(int(self.layer_row)<<84)|(int(self.static_read)<<85)

def compile_image(runs,deadline=65535,capacity=16):
    if len(runs)>capacity:raise ValueError('run image exceeds real leaf capacity')
    events={}
    for r in runs:
        word=r.word()
        for edge in r.events():
            if edge>deadline:raise ValueError('event exceeds fixed frame deadline')
            if edge in events:raise ValueError('calendar output collision')
            events[edge]=dict(command=r.command,mask=r.mask,layer_row=r.layer_row,static_read=r.static_read)
    return dict(words=[r.word() for r in runs]+[0]*(capacity-len(runs)),events=events,
                storage_bits=capacity*128,descriptor_count=len(runs),full_native_qualified=False)

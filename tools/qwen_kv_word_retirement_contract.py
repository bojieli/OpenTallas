#!/usr/bin/env python3
"""Source-addressed perbeat capture/visibility/reader/ACK guard; model only."""
from uarch_model_qwen_kv_beat_retirement import fragments, A

class WordRetirement:
    def __init__(self,layer,base,length,epoch,tag):
        A.burst_group(base,length)
        if not 0<=tag<4096 or len(epoch)!=2 or not 0<=epoch[0]<2**64 or not 0<=epoch[1]<2**32:raise ValueError('source tag/epoch')
        self.layer=layer;self.base=base;self.length=length;self.epoch=epoch;self.tag=tag
        self.required={};self.beat_words={};self.captured={};self.visible=set();self.acked=set();self.readers={};self.remaining_PC={};self.released=False
        for st in range(4):
            self.remaining_PC[st]=set(A.pc_of(base+b) for b in range(length))
            for b in range(length):
                key=st,b;parts=fragments(layer,st,base+b);self.beat_words[key]={w for w,q in parts}
                for off,(w,q) in enumerate(parts):
                    if q in self.required.setdefault(w,{}):raise ValueError('duplicate source quarter')
                    self.required[w][q]=(key,off)
        if any(set(q)!=set(range(4)) for q in self.required.values()):raise ValueError('complete four source quarters')
        self.readers=dict.fromkeys(self.required,0)
    def valid(self,epoch):
        if epoch!=self.epoch or self.released:raise ValueError('stale epoch/reused tag')
    def capture(self,epoch,stack,beat,sector,pc,payload,accepted):
        self.valid(epoch);key=stack,beat
        if key not in self.beat_words or sector!=self.base+beat or pc!=A.pc_of(sector) or key in self.captured:raise ValueError('immutable identity/duplicate')
        if not isinstance(payload,bytes) or len(payload)!=32:raise ValueError('actual32B payload')
        if accepted:
            self.captured[key]=payload
            same_pc={k for k in self.beat_words if k[0]==stack and A.pc_of(self.base+k[1])==pc}
            if same_pc<=self.captured.keys():self.remaining_PC[stack].remove(pc)
    def commit(self,epoch,word,masked_write_accepted):
        self.valid(epoch)
        if word not in self.required or word in self.visible or any(key not in self.captured for key,off in self.required[word].values()):raise ValueError('not source-ready word')
        payload=b''.join(self.captured[key][off*16:off*16+16] for key,off in (self.required[word][q] for q in range(4)))
        if masked_write_accepted:self.visible.add(word)
        return payload
    def borrow(self,epoch,word):
        self.valid(epoch)
        if word not in self.visible or self.readers[word]>=3:raise ValueError('visibility or finite two-bit reader debt')
        self.readers[word]+=1
    def drain(self,epoch,word):
        self.valid(epoch)
        if word not in self.readers or not self.readers[word]:raise ValueError('unowned reader')
        self.readers[word]-=1
    def ack(self,epoch,key,reverse_accepted):
        self.valid(epoch)
        if key not in self.captured or key in self.acked or any(w not in self.visible or self.readers[w] for w in self.beat_words[key]):raise ValueError('capture/visibility/reader/duplicate ACK')
        if reverse_accepted:self.acked.add(key)
    def release(self,epoch,readers_drained):
        self.valid(epoch)
        if readers_drained is not True or self.acked!=self.beat_words.keys() or any(self.readers.values()) or any(self.remaining_PC.values()):raise ValueError('ACK/context/reader quarantine')
        self.released=True

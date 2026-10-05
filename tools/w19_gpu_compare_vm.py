"""Typed CPU execution of lowered standardGPU compare instructions, not RTL."""
import numpy as np
import w19_norm_opcode_proof as N
from w19_attention_typed_vm import Machine as Base,constants
import w19_gpu_compare_lowering as L


class Machine(Base):
    def __init__(self,program,memory,attn_scale,active_lanes=32):
        self.admission=L.calendar(program,active_lanes);self.program=program;self.memory=memory
        self.constants=constants(attn_scale)
        self.constants.update({k:N.Value('U32',np.asarray(v,np.uint32)) for k,v in L.CONST.items()})
        self.regs={};self.trace=[];self.stores=[]

    def run(self):
        original=self.program
        for pc,i in enumerate(original):
            code=i['op'];dst=i['dst'];args=[self.read(s) for s in i['src']];old=self.regs.get(dst)
            if code in ['IEQ','INE','OR'] or code.startswith('FCMP'):
                if code.startswith('FCMP'):
                    a,b=[x.f32() for x in args]
                    with np.errstate(invalid='ignore'):result=(a>b) if code=='FCMP_GT' else (a<b)
                else:
                    a,b=[x.u32() for x in args];result=(a==b) if code=='IEQ' else (a!=b) if code=='INE' else a|b
                value=N.Value('U32',np.asarray(result,np.uint32))
                pred=i['attributes'].get('predicate')
                if pred:
                    import re
                    match=re.fullmatch(r'lane\s*%\s*(\d+)\s*==\s*0',pred)
                    if not match or old is None:raise ValueError('predicateddestination')
                    mask=np.arange(value.data.shape[-1])%int(match[1])==0
                    value=N.Value('U32',np.where(mask,value.data,old.u32()).astype(np.uint32))
                self.regs[dst]=value
                self.trace.append(dict(pc=pc,op=code,dst=dst,src=i['src'],kind=value.kind,
                    shape=list(value.data.shape),sha256=N.sha(value.data.tobytes()),value=value))
            else:
                self.program=[i];Base.run(self);self.trace[-1]['pc']=pc
        self.program=original
        return self

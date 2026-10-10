#!/usr/bin/env python3
"""Actual native690 ROM compiler for four N256/M64 c12 quarters.

Default-off consumers; identical immutable words may replay four query slots.
Finite softmax windows use real dispatcher NIN clipping, not host-generated
outputs. All inter-op dependencies conservatively wait for real engine idle.
"""
import argparse,hashlib,importlib,json,sys
from pathlib import Path
N,M,CAP=256,64,8224
SCORES,EXP,PUB=0,65792,131584
MP,MX,ZP,Z,T1,T2=210000,210064,210080,210144,210160,210192
ZERO=262143

def model():
    return dict(schema='opentallas.qwen.native690.quarters.v1',status='CANDIDATE_NOT_ADOPTED',
        quarters=4,lanes_per_quarter=N,sfu_lanes_per_quarter=M,rom_bits=4*4096*690,
        metadata_bits=4096*42,rom_ECC=False,rom_read_bits_per_request=2760,
        vm_words=1<<18,score_capacity_rows=CAP,query_slots=4,query_execution='serial replay; one score/exp/publication slot',
        rmsnorm=dict(exact_sum_replicas=4,square_elements=4*4096,extra_square_elements=3*4096,
            rsqrt_replicas=4,output_elements=4096,order='full chunk8/padded tree duplicated; no cross-quarter sum'),
        softmax=dict(heads_per_quarter=2,full_windows=4,window_rows=2048,tail_rows=32,
            max_lv_span=5,partial_tree='8 leaves:four complete2048 trees, tail chunk8,3zero leaves; explicit pairwise adds',
            empty_tail='prezero sums/exp/publication; finite minimum initializes maxpartials'),
        clock='actual c12 production constraints unchanged; no new timing claim',
        latency_cycles=None,area='uses existing four-quarter/ROM/provider design; no synthesized area claim',
        boundary='native690×4+metadata42; VMword24; dispatcherROM_PC12',
        adoption='requires actual quarter arithmetic/finite-provider RTL gate and physical qualification')

def load(tools):
    sys.path.insert(0,str(Path(tools).resolve()))
    S=importlib.import_module('qwen_r25_su_programs')
    R=importlib.import_module('qwen_r25_su_stage')
    return S,R,S.C,S.I

class Compiler:
    def __init__(self,S,R,C,I):
        self.S,self.R,self.C,self.I=S,R,C,I;self.entries=[];self.stages={}
    def op(self,**f):
        x=self.C.op_defaults();x.update(f);x['w_idle']=1
        self.C.encode(x);return x
    def emit(self,name,words,window=False,row0=0,rows=0):
        if len(words)!=4:raise ValueError('four independently compiled quarter words')
        mask=sum(1<<q for q,w in enumerate(words) if w is not None)
        if not mask:raise ValueError('empty immutable instruction')
        for w in words:
            if w is not None:
                self.C.encode(w)
                if self.C.layout(w,N,M)['bad']:raise ValueError('actual N256/M64 LV6 failure: '+name)
                if w['w_idle']!=1:raise ValueError('unsafe sequence linkage')
        if window and not 0<rows<=CAP-row0:raise ValueError('window extent')
        meta=(1<<41)|(mask<<37)|(int(window)<<36)|(row0<<16)|rows
        self.entries.append(dict(pc=len(self.entries),name=name,fields=words,mask=mask,
            window=window,row0=row0,rows=rows,metadata=meta,
            words=[0 if w is None else self.C.encode(w) for w in words]))
    def begin(self,name):self.stages[name]=dict(pc=len(self.entries))
    def end(self,name):self.stages[name]['count']=len(self.entries)-self.stages[name]['pc']
    def rms(self):
        self.begin('rmsnorm4096')
        qs=[]
        for q in range(4):
            ops=self.S.norm_program(1,4096,x=229376,gain=237568,scalar=220000+q,y=0)
            ops=[dict(x,w_idle=1) for x in ops]
            ops[2].update(nin=1024,abase=229376+q*1024,cbase=237568+q*1024,obase=q*1024)
            qs.append(ops)
        for j in range(3):self.emit('rms'+str(j),[x[j] for x in qs])
        self.emit('rms_bf16',[self.op(nout=1,nin=1024,abase=q*1024,asi=1,rnd=1,dst=self.I.DST_VM,obase=q*1024,osi=1) for q in range(4)])
        self.end('rmsnorm4096')
    def qk(self):
        self.begin('qknorm128');qs=[]
        for q in range(4):
            ops=self.S.norm_program(2,128,x=q*256,gain=8192,scalar=220016+q*4,y=16384+q*256)
            qs.append([dict(x,w_idle=1) for x in ops])
        for j in range(3):self.emit('qnorm'+str(j),[x[j] for x in qs])
        ks=[]
        for q in range(2):
            ops=self.S.norm_program(1,128,x=1024+q*128,gain=8320,scalar=220018+q*4,y=17408+q*128)
            ks.append([dict(x,w_idle=1) for x in ops])
        for j in range(3):self.emit('knorm'+str(j),[ks[0][j],ks[1][j],None,None])
        self.end('qknorm128')
    def rope(self):
        self.begin('rope128');base=self.R.program();qs=[]
        for q in range(4):
            heads=[2*q,2*q+1]+([8+q] if q<2 else [])
            ops=[]
            for h in heads:
                for f in base[2*h:2*h+2]:
                    f=dict(f,w_idle=1);f['abase']+=16384;f['cbase']+=16384;f['obase']-=8192;ops.append(f)
            qs.append(ops)
        for j in range(6):self.emit('rope'+str(j),[x[j] if j<len(x) else None for x in qs])
        self.emit('q_bf16',[self.op(nout=1,nin=256,abase=q*256,asi=1,rnd=1,dst=self.I.DST_VM,obase=q*256,osi=1) for q in range(4)])
        self.end('rope128')
    def swiglu(self):
        self.begin('swiglu3072')
        self.emit('swiglu',[self.op(nout=1,nin=768,abase=q*768,asi=1,cbase=4096+q*768,csi=1,sfu=self.I.SFU_SILU,e1=self.I.E1_MULC,dst=self.I.DST_VM,obase=8192+q*768,osi=1) for q in range(4)])
        self.emit('swiglu_bf16',[self.op(nout=1,nin=768,abase=8192+q*768,asi=1,rnd=1,dst=self.I.DST_VM,obase=8192+q*768,osi=1) for q in range(4)])
        self.end('swiglu3072')
    def softmax(self):
        self.begin('softmax8x8224')
        self.emit('max_neutral',[self.op(nout=1,nin=16,abase=ZERO,ad=self.I.AD_IMM,imm2=0xff7fffff,dst=self.I.DST_VM,obase=MP+q*16,osi=1) for q in range(4)])
        self.emit('sum_zero',[self.op(nout=1,nin=16,abase=ZERO,dst=self.I.DST_VM,obase=ZP+q*16,osi=1) for q in range(4)])
        for dest in (EXP,PUB):
            self.emit('tail_zero'+str(dest),[self.op(nout=2,nin=32,abase=ZERO,dst=self.I.DST_VM,obase=dest+q*2*CAP+8192,oso=CAP,osi=1) for q in range(4)])
        for k,(row,rows) in enumerate([(i*2048,2048) for i in range(4)]+[(8192,32)]):
            self.emit('max_window'+str(k),[self.op(nout=2,nin=rows,abase=SCORES+q*2*CAP+row,aso=CAP,asi=1,red=self.I.RED_MAX,rbase=MP+q*16+k,rso=8) for q in range(4)],True,row,rows)
        self.emit('max_merge',[self.op(nout=2,nin=8,abase=MP+q*16,aso=8,asi=1,red=self.I.RED_MAX,rbase=MX+q*2,rso=1) for q in range(4)])
        for k,(row,rows) in enumerate([(i*2048,2048) for i in range(4)]+[(8192,32)]):
            self.emit('exp_window'+str(k),[self.op(nout=2,nin=rows,abase=SCORES+q*2*CAP+row,aso=CAP,asi=1,bbase=MX+q*2,bso=1,ad=self.I.AD_NEGB,sfu=self.I.SFU_EXP,red=self.I.RED_SUM,rbase=ZP+q*16+k,rso=8,dst=self.I.DST_VM,obase=EXP+q*2*CAP+row,oso=CAP,osi=1) for q in range(4)],True,row,rows)
        for src,dst,width in ((ZP,T1,4),(T1,T2,2),(T2,Z,1)):
            self.emit('den_tree'+str(width),[self.op(nout=2,nin=width,abase=src+q*4*width,aso=2*width,asi=2,cbase=src+q*4*width+1,cso=2*width,csi=2,ad=self.I.AD_C,dst=self.I.DST_VM,obase=dst+q*2*width,oso=width,osi=1) for q in range(4)])
        for k,(row,rows) in enumerate([(i*2048,2048) for i in range(4)]+[(8192,32)]):
            self.emit('bf16_window'+str(k),[self.op(nout=2,nin=rows,abase=EXP+q*2*CAP+row,aso=CAP,asi=1,rnd=1,dst=self.I.DST_VM,obase=PUB+q*2*CAP+row,oso=CAP,osi=1) for q in range(4)],True,row,rows)
        self.end('softmax8x8224')
    def build(self):
        self.rms();self.qk();self.rope();self.swiglu();self.softmax()
        if len(self.entries)>4096:raise ValueError('ROM_PC12 extent')
        return self
    def write(self,out):
        out.mkdir(parents=True,exist_ok=False)
        for q in range(4):
            (out/f'Q{q}.hex').write_text(''.join(f'{e["words"][q]:0173x}\n' for e in self.entries))
        (out/'META.hex').write_text(''.join(f'{e["metadata"]:011x}\n' for e in self.entries))
        sources=[Path(__file__),Path(self.S.__file__),Path(self.R.__file__),Path(self.C.__file__),Path(self.I.__file__)]
        manifest=dict(schema='opentallas.qwen.native690.rom.v1',N=N,M=M,word_bits=self.C.PW,
            slots=len(self.entries),stages=self.stages,entries=[{k:v for k,v in e.items() if k!='words'} for e in self.entries],
            source_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
            ROM_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.glob('*.hex')},
            constant_zero_word=ZERO,constant_zero_bits=0,capacity=CAP,queries=[8192,8193,8194,8195],
            arithmetic_qualification=False,physical_qualification=False,modeled_cycles=None)
        (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
        (out/'model.json').write_text(json.dumps(model(),indent=2)+'\n')

def main():
    p=argparse.ArgumentParser();p.add_argument('--tools',required=True,type=Path);p.add_argument('--out',required=True,type=Path);a=p.parse_args()
    S,R,C,I=load(a.tools)
    if C.PW!=690:raise ValueError('actual pinned native word ABI changed')
    Compiler(S,R,C,I).build().write(a.out)
if __name__=='__main__':main()

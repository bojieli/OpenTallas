#!/usr/bin/env python3
"""Execute the entire retained TP96 graph from checkpoint embedding to LM head.

CPU functional execution is separate from complete ordinary GPU lowering and
DUT RTL. Typed attention recipes consume this program's actual produced values.
Other kernels retain explicit reference-software bindings, never timing credit.
Golden shards are read only AFTER execution, for optional comparisons.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time
from types import FunctionType,SimpleNamespace
import numpy as np
import w19_hbm_tp96_isa as H
import w19_attention_lowered_proof as A
import w19_rope_table_service as R
from deepseek_hbm_complete_isa import WarpBackend,clone_numeric_modules
from deepseek_hbm_complete_program import compile_program,ROOT
from deepseek_hbm_complete_memory import PersistentMemory,FiniteCollective


class InitialCoefficientFixture:
    """Offline setup rows, not runtime nativeCOS/SIN. Whole resident images pending."""
    def __init__(self,m,pos):
        self.m=m;self.rows={}
        for variant in ['plain','yarn']:
            positions={pos}
            if variant=='yarn':positions|={pos+1-r for r in m.ratio if r>0}
            for p in sorted(positions):
                row=R.coefficients(m.c,variant,[p])[0];self.rows[variant,p]=(row[:32].copy(),row[32:].copy())
        self.requests=0
    def get(self,freqs,pos):
        if np.array_equal(freqs,self.m.freqs_plain):variant='plain'
        elif np.array_equal(freqs,self.m.freqs_yarn):variant='yarn'
        else:raise ValueError('unbound coefficient frequency source')
        self.requests+=1
        if (variant,pos) not in self.rows:raise ValueError('coefficient row not resident in explicit initial fixture')
        return self.rows[variant,pos]


class StateArray:
    """Finite software row service over explicit initialKV/produced row backing.

Payload here is decoded F32 BF16-valued fixture storage, NOT packed HBM image.
Physical 288/68B producer/decoder bridge is a separate required lowering gate.
"""
    def __init__(self,base,memory,family,source):self.base=base;self.memory=memory;self.family=family;self.source=source;self.written=set()
    @property
    def shape(self):return self.base.shape
    def __getitem__(self,idx):
        ids=np.asarray(list(range(*idx.indices(self.base.shape[0]))) if isinstance(idx,slice) else idx)
        out=[]
        for i in ids.reshape(-1):
            i=int(i);key=('KV',self.family,self.source,i)
            if i in self.written:data=self.memory.read_object(key)
            else:
                row=self.base[i]
                if not np.all(np.isfinite(row)):raise ValueError('unwritten initialKV row')
                raw=row.tobytes();parts=[]
                for off in range(0,len(raw),512):
                    pk=(*key,'fixture',off);self.memory.preload(pk,raw[off:off+512]);parts.append(self.memory.transact(pk));del self.memory.values[pk];del self.memory.epochs[pk]
                data=b''.join(parts)
            out.append(np.frombuffer(data,dtype=self.base.dtype).copy())
        if ids.ndim==0:return out[0]
        return np.asarray(out,dtype=self.base.dtype).reshape(*ids.shape,*self.base.shape[1:])
    def __setitem__(self,idx,value):
        if not isinstance(idx,(int,np.integer)):raise ValueError('append exactly one owned row per producer')
        if not 0<=idx<len(self.base):raise ValueError('persistent capacity exceeded; no modulo')
        row=np.asarray(value,dtype=self.base.dtype)
        if row.shape!=self.base.shape[1:]:raise ValueError('row shape')
        self.memory.write_object(('KV',self.family,self.source,int(idx)),row.tobytes());self.memory.fence()
        self.base[idx]=row;self.written.add(int(idx))


class Executor(H.Executor):
    def __init__(self,m,st,pos,hist,variant='oreduce',log=print):
        super().__init__(m,st,pos,hist,variant,log)
        self.memory=PersistentMemory();self.fabric=FiniteCollective();self.coefficients=InitialCoefficientFixture(m,pos)
        self.operator_receipts=[];self.primitive_counts={};self.current=None
        for family in ['ckv','ik']:
            arrays=getattr(st,family)
            for source,base in list(arrays.items()):arrays[source]=StateArray(base,self.memory,family,source)
        # Original pinned functions/globals untouched. These two handlers load
        # explicit setup coefficient rows through the companion interface.
        self.warp_backend=WarpBackend()
        gp,vp,ve=clone_numeric_modules(self.warp_backend,self.coefficients.get)
        self.bound_handlers={}
        for name,original in vars(H.Executor).items():
            if not hasattr(original,'__code__'):continue
            fn=FunctionType(original.__code__,{**original.__globals__,'G':gp,'V':vp},name,original.__defaults__)
            self.bound_handlers[name]=fn
            if name not in vars(Executor):setattr(self,name,fn.__get__(self,type(self)))
        # HC methods execute the same source control/order with the typed
        # primitive backend, preserving actual produced inputs and rounding.
        for name in ['hc_mixes','hc_pre','hc_post']:
            original=getattr(H.V.Model,name)
            fn=FunctionType(original.__code__,ve,name,original.__defaults__)
            setattr(m,name,fn.__get__(m,type(m)))
    def cs(self,L):return self.coefficients.get(self.m.freqs_yarn if self.m.ratio[L]>0 else self.m.freqs_plain,self.pos)
    def f_compressor(self,rk,op):
        self.bound_handlers['f_compressor'](self,rk,op);self.memory.fence()
    def f_index_q(self,rk,op):self.bound_handlers['f_index_q'](self,rk,op)
    def f_q_norm_kv_row(self,rk,op):
        self.bound_handlers['f_q_norm_kv_row'](self,rk,op)
        key=('window',rk.r,op['layer'],self.pos)
        self.memory.write_object(key,rk.get('win_new').tobytes());self.memory.fence()
        row=np.frombuffer(self.memory.read_object(key),dtype=np.float32).copy()
        rk.put('win_new',row);rk.win[op['layer']][-1]=row
    def f_swiglu(self,rk,op):
        e=op['slot'];r0,r1=H.even(2304)[rk.r]
        route=rk.get('route_w')[e] if e<self.m.k_exp else None
        a=self.warp_backend.swiglu(rk.get(f'e{e}.g',r0,r1),rk.get(f'e{e}.u',r0,r1),self.m.limit,route)
        rk.put('ea',a,lo=e*2304+r0,n=(self.m.k_exp+1)*2304)
    def f_attend(self,rk,op):
        L=op['layer'];rows=rk.win[L]
        if op['yarn']:rows=np.concatenate([rows,rk.sel_rows[self.m.kv_of[L]]])
        q=rk.get('q_own').reshape(512);sink=self.m.lw(L,'attn.attn_sink')[rk.r]
        got,machines=A.connected(q,rows,sink,self.cs(L),self.m.attn_scale)
        for machine in machines.values():
            for t in machine.trace:self.primitive_counts[t['op']]=self.primitive_counts.get(t['op'],0)+1
        rk.put('o',got['final'],lo=rk.r*512,n=32768);rk.put('o_own',got['final'])
    def _collective(self,op):
        names=op.get('bufs',[op['buf']] if 'buf' in op else [])
        if op['kind']=='topk_merge':names=[op['what']+'_v',op['what']+'_i']
        metadata={};segments=[];j=0
        for name in names:
            for rk in self.ranks:
                if name not in rk.mem:continue
                mask=rk.ok[name].copy();v=rk.mem[name][mask];metadata[j]=(rk,name,mask,v.dtype);segments.append((j,v.tobytes()));j+=1
        method={'all_gather':'op_gather','all_reduce':'op_reduce','topk_merge':'op_merge','kv_gather':'op_kv_gather'}[op['kind']]
        def consumer(returned):
            for j,data in returned:
                rk,name,mask,dt=metadata[j];rk.mem[name][mask]=np.frombuffer(data,dtype=dt)
            return self.bound_handlers[method](self,op)
        return self.fabric.publish(op['kind'],segments,consumer)
    def execute_instruction(self,instruction):
        o=instruction['op'];self.current=instruction;t=time.monotonic();before=self.warp_backend.snapshot()
        if o['kind'] in ['all_gather','all_reduce','topk_merge','kv_gather']:self._collective(o)
        else:super().run([o])
        if o['kind']=='all_gather' and o['tag']=='expert_intermediate_gather':self.split_ea()
        self.memory.fence();self.fabric.memory.fence()
        receipt={'pc':instruction['pc'],'layer':instruction['layer'],'source_op_id':o['id'],
                 'function':instruction['function'],'numerical_backend':instruction['numerical_backend'],
                 'completed':True,'CPU_wall_s':round(time.monotonic()-t,6),'GPU_cycles':None,'DUT_executed':False}
        receipt['scalar_GPU_recipe_costs']={k:v-before.get(k,0) for k,v in self.warp_backend.snapshot().items()}
        self.operator_receipts.append(receipt);return receipt


def execute(program,*,out,stop_after=None,compare_reference=False):
    if out.exists():raise ValueError('refuse overwrite run/failure evidence')
    if subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip():raise ValueError('clean pinned source required')
    out.mkdir(parents=True);records=[];failure=None;ex=None;started=time.monotonic()
    result={'schema':'opentallas.deepseek.hbm.complete-execution.v1','source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
      'program_sha256':hashlib.sha256(json.dumps(program,sort_keys=True).encode()).hexdigest(),
      'source_pins':program['source_pins'],'entry_activation':'actual checkpoint embedding currenttoken, replicatedHC4',
      'perlayer_reference_injection':False,'ordinary_GPU_lowering_complete':False,'DUT_RTL_executed':False,'physical_qualified':False,
      'provider':'finite synchronous CPU backing commit/consume events, no DRAM cycle credit',
      'KV_representation':'decoded F32 software fixture/produced rows; packed production bridge unbound'}
    try:
        if program['source_pins']!=compile_program()['source_pins']:raise ValueError('source pin drift')
        instructions=program['instructions']
        if stop_after is not None:
            if not 1<=stop_after<=len(instructions):raise ValueError('bounded prefix count')
            instructions=instructions[:stop_after]
        layers={i['layer'] for i in instructions if isinstance(i['layer'],int)}
        ck=H.LC.Checkpoint();m,init_sha=H.LC.build_model(ck,engram=bool(layers&{1,14}))
        ref=json.loads(H.REF_RECORD.read_text());ctx=ref['context'];pos=ctx-1
        if pos!=program['position']:raise ValueError('initial state position/program mismatch')
        st=H.State(m,ctx,ref['seed'],layers)
        if layers==set(range(40)):
            want=json.loads(ref['state'].replace("'",'"')) if isinstance(ref['state'],str) else ref['state']
            if st.state_sha256!=want['state_sha256']:raise ValueError('initial fixture digest mismatch')
        ex=Executor(m,st,pos,list(ref['token_history']),log=lambda x:None)
        h=np.repeat(ck.rows('embed.weight',[ref['token_history'][-1]]),m.hc,axis=0).astype(np.float32)
        for rk in ex.ranks:rk.put('h',h);rk.put('pre',np.array([1,0,0,0],np.float32))
        result.update(initial_state_sha256=st.state_sha256,model_init_sha256=init_sha,entry_sha256=hashlib.sha256(h.tobytes()).hexdigest())
        for j,instruction in enumerate(instructions):
            receipt=ex.execute_instruction(instruction)
            # End-of-layer comparisons only observe produced data. Never load
            # a reference into rank memory or replace a failed result.
            boundary=j==len(instructions)-1 or instructions[j+1]['layer']!=instruction['layer']
            if boundary:
                L=instruction['layer'];full_layer=instruction['source_op_id']==max(i['source_op_id'] for i in program['instructions'] if i['layer']==L)
                r={'layer':L,'prefix_complete':full_layer,'h_sha256':hashlib.sha256(ex.ranks[0].get('h').tobytes()).hexdigest()}
                if compare_reference and full_layer and L!='head':
                    with np.load(H.REF_SHARDS/f'ctx{ctx}_L{L:02d}.npz',allow_pickle=False) as z:
                        r['h_bit_exact']=all(np.array_equal(rk.get('h').view(np.uint32),z['h_out'].reshape(-1).view(np.uint32)) for rk in ex.ranks)
                        r['pre_bit_exact']=all(np.array_equal(rk.get('pre').view(np.uint32),z['pre_out'].reshape(-1).view(np.uint32)) for rk in ex.ranks)
                    if not r['h_bit_exact'] or not r['pre_bit_exact']:raise ValueError('produced layer differs from reference; retained, never replaced')
                records.append(r)
                if full_layer and L!='head':
                    for name in list(m.w):
                        if name.startswith(f'layers.{L}.'):del m.w[name]
                    for rk in ex.ranks:rk.clear(keep=('h','pre','sel'))
        complete=len(instructions)==len(program['instructions'])
        result['full_token_software_executed']=complete
        if complete:
            lg=np.concatenate([rk.get('logits',*H.even(129280)[rk.r]) for rk in ex.ranks]);tok=int(ex.ranks[0].get('token')[0])
            result['head']={'token':tok,'logits_sha256':H.LC.digest(lg),'reference_token':ref['next_token'],
                            'reference_logits_sha256':ref['logits_sha256'],'bit_exact':tok==ref['next_token'] and H.LC.digest(lg)==ref['logits_sha256']}
            if not result['head']['bit_exact']:raise ValueError('end-to-end head mismatch')
    except Exception as e:failure={'type':type(e).__name__,'message':str(e)}
    result.update(verdict='FAIL' if failure else 'PASS',failure=failure,layers=records,CPU_wall_s=round(time.monotonic()-started,3),
                  full_token_software_executed=result.get('full_token_software_executed',False))
    if ex is not None:result.update(operator_receipts=ex.operator_receipts,primitive_counts=ex.primitive_counts,
      memory=ex.memory.summary(),scalar_GPU_recipes=ex.warp_backend.summary(),collective_events=ex.fabric.events,coefficient_initial_fixture_loads=ex.coefficients.requests)
    (out/'execution.json').write_text(json.dumps(result,indent=2)+'\n');return result

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--stop-after',type=int)
    ap.add_argument('--compare-reference',action='store_true');a=ap.parse_args()
    r=execute(compile_program(),out=a.out,stop_after=a.stop_after,compare_reference=a.compare_reference)
    print(json.dumps({'verdict':r['verdict'],'completed':len(r.get('operator_receipts',[])),'full_token_software_executed':r['full_token_software_executed'],'failure':r['failure']}))
    raise SystemExit(r['verdict']!='PASS')

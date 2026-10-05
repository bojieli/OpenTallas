#!/usr/bin/env python3
"""Opt-in bounded Qwen HBM compiler and native micro-op VM.

Historical lowering and arithmetic helpers are read-only dependencies. Native
working storage is RF32/shared17408B; source storage is actual r17 homes. This
entrypoint never edits or weakens the historical compiler's evidence checks.
"""
from h3_qwen_complete_native import *

TILE_ROWS=128
TILE_CODE_K=32
TILE_FLOAT_K=16
TILED_OUT=ROOT/OUT/'tiled_r1'



def code_sector_count(rows,K):
    if K%32==0: return rows*(K//32)
    def tile(n):
        total=0
        for column in range(0,K,32):
            sectors=set(); width=min(32,K-column)
            for row in range(n):
                first=row*K+column
                sectors.update(range(first//32,(first+width-1)//32+1))
            total+=len(sectors)
        return total
    return (rows//128)*tile(128)+(tile(rows%128) if rows%128 else 0)


def interleaved_BF16_windows(K,S):
    previous=None; count=0
    for s in range(min(K,S)):
        for k in range(s,K,S):
            page=k//128
            if previous!=page: count+=1; previous=page
    return count

def tiled_counts(op,p,position):
    """Analytical counts before tiled execution; no tensor materialization."""
    c=p['config']; a=op['attributes']; name=op['opcode']; T=position+1
    hd=c['head_dim']; nh=c['num_attention_heads']//2; kv=c['num_key_value_heads']//2
    shape=p['register_shapes'][op['outputs'][0]]
    size=math.prod(T if n=='position+1' else n for n in shape) if shape else 1
    count=Counter(); extra={}
    def rms(n,heads=1,weighted=False):
        leaves=1<<(((n+7)//8)-1).bit_length()
        count['FMUL_words']+=heads*(n+11+(2*n if weighted else 0))
        count['FADD_words']+=heads*(n+leaves-1+4)
        count['FMUL_vector_commands']+=heads*((n+7)//8+11+(2*((n+127)//128) if weighted else 0))
        count['FADD_vector_commands']+=heads*(n+leaves-1+4)
    if name in ('MATRIX','SCORES','PV'):
        if name=='MATRIX':
            d=p['weight_descriptors'][a['weight']]; rows,K,S,heads=d['rows'],d['K'],d['split'],1
        else: rows,K,S,heads=(T,hd,a['split'],nh) if name=='SCORES' else (hd,T,a['split'],nh)
        if S<1 or S&(S-1) or (name=='MATRIX' and K%S): raise ValueError('unsupported source split geometry')
        rowtiles=(rows+127)//128
        count['FMUL_words']=heads*rows*K; count['FADD_words']=heads*rows*(K+S-1)
        count['FMUL_vector_commands']=heads*rowtiles*K
        count['FADD_vector_commands']=heads*rowtiles*(K+S-1)
        count['tree_merges']=heads*rowtiles*(S-1)
        if name=='MATRIX':
            count['ITOF_vector_commands']=rowtiles*K
            count['BF16_pack_windows']=rowtiles*((K+127)//128)
            count['code_tile_reads']=rowtiles*((K+31)//32)
            count['code_payload_bytes']=rows*K
            # Rowtile boundary is128 rows, hence32B aligned for integer K.
            count['code_sectors32']=code_sector_count(rows,K)
        elif name=='SCORES':
            count['BF16_pack_windows']=heads*rowtiles*interleaved_BF16_windows(K,S)
            count['FMUL_words']+=heads*rows; count['FMUL_vector_commands']+=heads*rowtiles
        extra=dict(rows=rows,K=K,split=S,heads=heads,rowtiles=rowtiles,
                   split_order='contiguous' if name=='MATRIX' else 'interleaved',
                   leaf_lengths='K/split' if name=='MATRIX' else 'max(0,ceil((K-s)/split))',
                   root_tree='streaming adjacent left/right carries, all split zero leaves retained',
                   accumulator_words_max=128,carry_stack_vectors=(S-1).bit_length()+1,
                   code_tile_shape_max=[128,32],float_tile_shape_max=[128,16])
    elif name=='RSTD': rms(p['register_shapes'][op['inputs'][0]][-1])
    elif name=='HEAD_NORM': rms(hd,p['register_shapes'][op['inputs'][0]][0],True)
    elif name=='FINAL_NORM': rms(c['hidden_size'],1,True)
    elif name in ('ROW_SCALE','SCALAR_MUL','NORMALIZE'):
        count['FMUL_words']=size; count['FMUL_vector_commands']=(size+127)//128
        if name=='NORMALIZE':
            count['FMUL_vector_commands']=nh*((hd+127)//128)
            count['FMUL_words']+=nh*6; count['FADD_words']=nh*3
            count['FMUL_vector_commands']+=nh*6; count['FADD_vector_commands']=nh*3
    elif name=='RESIDUAL': count.update(FADD_words=size,FADD_vector_commands=(size+127)//128)
    elif name=='ALL_REDUCE':
        count.update(FADD_words=size,FMUL_words=size,FADD_vector_commands=(size+127)//128,FMUL_vector_commands=(size+127)//128,
                     collective_payload_bytes=size*8)
    elif name=='SILU_GATE': count.update(FMUL_words=17*size,FADD_words=14*size,FMUL_vector_commands=17*((size+127)//128),FADD_vector_commands=14*((size+127)//128))
    elif name=='EXP_SUM':
        leaves=1<<(((T+7)//8)-1).bit_length(); batches=(T+127)//128
        count.update(FMUL_words=nh*T*9,FADD_words=nh*(12*T+leaves-1),
                     FMUL_vector_commands=nh*batches*9,FADD_vector_commands=nh*(batches*11+T+leaves-1),
                     max_compare_words=nh*(T-1),BF16_pack_windows=nh*batches)
    elif name=='ROPE':
        heads=p['register_shapes'][op['outputs'][0]][0]; batches=(hd//2+127)//128
        count.update(FMUL_words=2*size,FADD_words=size,FMUL_vector_commands=4*heads*batches,FADD_vector_commands=2*heads*batches)
    elif name=='EMBED': count.update(FMUL_words=size,FMUL_vector_commands=(size+127)//128,ITOF_vector_commands=(size+127)//128)
    elif name=='KV_WRITE': count.update(FP8_PACK_words=2*kv*hd,KV_store_bytes=2*kv*hd)
    elif name=='KV_READ': count.update(FP8_UNPACK_words=2*kv*T*hd,KV_read_payload_bytes=2*kv*T*hd)
    elif name=='ARGMAX': count.update(argmax_comparisons=3*(p['register_shapes'][op['inputs'][0]][0]-1))
    elif name=='ARGMAX_REDUCE': count.update(argmax_comparisons=3,collective_payload_bytes=16)
    return dict(position=position,logical_counts=dict(count),matrix=extra,
                ports={'RF_2R1W_read_bits':8192,'RF_mirrored_write_payload_bits':4096,'RF_mirrors':2,
                       'shared_beat_bytes':128,'HBM_sector_bytes':32},
                transfer_count_policy='runtime actual provider page/sector counters; fullshape conservative serialized service budgets, never measured timing',
                clock_and_latency='C_RF_READ+C_RF_ACK+C_SHARED_BEAT+C_HBM_SECTOR+C_NoC+C_CDC+C_REVERSE_GRANT plus native primitive costs, all unknown and nonzero provisional inputs required')


def tile_feasibility_model(p=None):
    p=compile_program() if p is None else p
    return dict(schema='opentallas.H3.qwen-tile-feasibility.v1',before_implementation=True,
        target='Qwen_HBM',RF_workspace_vectors=32,RF_vector_bytes=512,RF_logical_bytes=16384,RF_mirrors=2,
        RF_physical_bytes=32768,shared_physical_bytes=65536,
        shared_regions=[{'name':'double_tile','range':[0,16384]}, {'name':'landing','range':[16384,16896]}, {'name':'capture','range':[16896,17408]}],
        shared_reserved_bytes=17408,shared_fits=True,temporary_HBM_bytes=0,
        matrix_code_double_buffer_bytes=2*128*32,attention_FP32_double_buffer_bytes=2*128*16*4,
        RF_layout={'carry':[0,13],'accumulator_product_weight':[13,16],'scalar_or_x':[16,17],
                   'primitive_scratch':[17,30],'source_page_cache':[30,32]},
        RF_allocation_policy='phase reuse, never additive sum of historical symbols; at most32 live vectors including tree and page cache',
        source_storage='r17 original32SM version_homes and32MiB/rank activation_scratch at base4714740864;37504B/rank KV state, no successor native arena',
        matrix='128 output rows, aligned32-code columns; INT8 conversion one128-lane column at a time; BF16 source page128 words; one split accumulator and log2(split)+1 tree vectors',
        attention='128 output positions/dimensions,16 interleaved K/context elements; KV_READ decoded source words published in128-word windows to actual r17 homes',
        reduction='seq8 leaves, zero-padded adjacent pair tree implemented with left/right carry stack; preserve every round and empty split leaf',
        single_user_latency='ordered symbolic transaction sum; tile loads, captures, shared, RF, NoC, CDC and reverse retirement all charged; no throughput/clock gain credited',
        hardware_or_timing_credit=False,
        per_PC_counts=[dict(pc=o['id'],opcode=o['opcode'],**tiled_counts(o,p,p['context_capacity']-1)) for o in p['instructions']])


COMMON_NATIVE={'LOAD','CONST','RESHAPE','SLICE','TRANSPOSE','CONCAT','BROADCAST','TAKE','SCATTER',
 'FADD','FMUL','DIV','SQRT','FMAX','FMIN','FCMP_GT','FCMP_LT','FCMP_EQ','FCMP_NE','SELECT',
 'BITCAST_U','BITCAST_F','SHR','SHL','AND','OR','XOR','IADD','ISUB','IMUL','IMOD','I2F','F2I',
 'LDEXP','PACKET_COMMIT','ASSERT','IOTA','COPY','FP8_PACK','FP8_UNPACK'}
QWEN_ALIASES={'BITS':'BITCAST_U','FLOAT_BITS':'BITCAST_F','CMP_GT':'FCMP_GT','CMP_LT':'FCMP_LT',
 'CMP_EQ':'FCMP_EQ','CMP_NE':'FCMP_NE','ITOF':'I2F','FTOI':'F2I','IADD64':'IADD','SHL64':'SHL'}


class NativePrimitiveVM:
    """Generic typed tile VM; DS code ABI and Qwen leaf recipes are adapters.

    Arrays are restricted to128 words at the primitive boundary. Bigger tensors
    require explicit outer tile programs. DIV is an explicitly bound scalar
    instruction provider, never a high-level operator callback.
    """
    def __init__(self,div=None):
        self.div=div; self.fault=False; self.error_events=[]; self.current_pc=None; self.counts=Counter(); self.word_counts=Counter(); self.peak_vectors=0
    def primitive(self,op,args,attrs=None,shape=None):
        at={} if attrs is None else attrs
        if op not in COMMON_NATIVE: raise ValueError('unsupported native primitive '+op)
        if any(np.size(x)>128 for x in args): raise ValueError('native operand needs outer tile loop')
        a=[np.asarray(x) for x in args]
        dtype={'F32':F,'U32':np.uint32,'I64':np.int64}
        with np.errstate(all='ignore'):
            if op=='IOTA':
                if shape is None or len(shape)!=1 or not 0<=shape[0]<=128: raise ValueError('native IOTA tile shape')
                v=np.arange(shape[0],dtype=np.int64)
            elif op=='CONST':
                v=np.asarray(at['bits'],np.uint32).view(F) if at['dtype']=='F32' else np.asarray(at['value'],dtype[at['dtype']])
            elif op in ('FADD','FMUL','SQRT','DIV'):
                x=[z.astype(F,copy=False) for z in a]
                if op=='DIV':
                    if self.div is None: raise ValueError('exact scalar DIV provider required')
                    v,faults=self.div(*x); self.fault|=bool(np.any(faults))
                    if np.any(faults): self.error_events.append({'pc':self.current_pc,'op':'DIV','errors':np.asarray(faults,np.uint32).tolist()})
                else: v=x[0]+x[1] if op=='FADD' else x[0]*x[1] if op=='FMUL' else np.sqrt(x[0])
                v=np.asarray(v,F); self.fault|=bool(np.any(~np.isfinite(v)))
                if at.get('canonical_zero',True): v=poszero(v)
            elif op=='FMAX': v=np.maximum(*a).astype(F)
            elif op=='FMIN': v=np.minimum(*a).astype(F)
            elif op.startswith('FCMP_'):
                v={'FCMP_GT':np.greater,'FCMP_LT':np.less,'FCMP_EQ':np.equal,'FCMP_NE':np.not_equal}[op](*a).astype(np.uint32)
            elif op=='SELECT':
                v=np.where(a[0]!=0,a[1],a[2])
                if at.get('dtype') in dtype: v=v.astype(dtype[at['dtype']])
            elif op=='BITCAST_U': v=a[0].astype(F,copy=False).view(np.uint32)
            elif op=='BITCAST_F': v=a[0].astype(np.uint32,copy=False).view(F)
            elif op in ('SHR','SHL','AND','OR','XOR','IADD','ISUB','IMUL','IMOD'):
                wide=at.get('dtype')=='I64' or (at.get('dtype')!='U32' and any(x.dtype==np.int64 for x in a))
                integer=np.int64 if wide else np.uint32
                x,y=[z.astype(integer) for z in a]
                if op in ('SHR','SHL') and np.any((y<0)|(y>=(64 if wide else 32))): raise ValueError('native shift range')
                if op=='IMOD' and np.any(y==0): raise ValueError('native modulo zero')
                v={'SHR':np.right_shift,'SHL':np.left_shift,'AND':np.bitwise_and,'OR':np.bitwise_or,
                   'XOR':np.bitwise_xor,'IADD':np.add,'ISUB':np.subtract,'IMUL':np.multiply,'IMOD':np.remainder}[op](x,y).astype(integer)
            elif op=='I2F': v=a[0].astype(F)
            elif op=='F2I':
                if np.any(~np.isfinite(a[0])) or np.any(np.abs(a[0].astype(np.float64))>=2**63): raise ValueError('native F2I range')
                v=a[0].astype(np.int64)
            elif op=='LDEXP':
                exponent=a[1].astype(np.uint32).view(np.int32) if a[1].dtype==np.uint32 else a[1].astype(np.int32)
                v=np.ldexp(a[0].astype(F),exponent).astype(F)
                self.fault|=bool(np.any(~np.isfinite(v)))
            elif op=='COPY': v=a[0].copy()
            elif op=='RESHAPE': v=a[0].reshape(shape)
            elif op=='SLICE':
                sl=[slice(None)]*a[0].ndim; sl[at['axis']]=slice(at['start'],at['stop'],at.get('step',1)); v=a[0][tuple(sl)]
            elif op=='TRANSPOSE': v=a[0].transpose(at['axes'])
            elif op=='CONCAT': v=np.concatenate(a,axis=at.get('axis',0))
            elif op=='BROADCAST': v=np.broadcast_to(a[0],shape)
            elif op=='TAKE':
                if np.any(a[1]<0) or np.any(a[1]>=a[0].shape[at['axis']]): raise ValueError('native address range')
                v=np.take(a[0],a[1].astype(np.int64),axis=at['axis'])
            elif op=='SCATTER':
                v=a[0].copy(); index=int(a[1])
                if not 0<=index<v.shape[at['axis']]: raise ValueError('native scatter range')
                sl=[slice(None)]*v.ndim; sl[at['axis']]=index; v[tuple(sl)]=a[2]
            elif op=='ASSERT':
                if not np.all(a[0]): raise ValueError('native assertion '+at.get('reason',''))
                v=a[0].copy()
            elif op=='PACKET_COMMIT':
                if self.fault: raise ValueError('fault prevents successful publication')
                if 'lease' in at and at.get('lease_state')!='visible': raise ValueError('packet lease before visibility')
                v=a[0].copy()
            elif op=='FP8_PACK': v=pack8(a[0])
            elif op=='FP8_UNPACK':
                codes=a[0].astype(np.uint8)
                if np.any((codes&127)==127): raise ValueError('FP8 NaN backing')
                v=poszero(fp8_table()[codes&127]*np.where(codes&128,-1,1))
            else: raise ValueError('LOAD needs bound provider record')
        if np.size(v)>128: raise ValueError('native result needs outer tile loop')
        if shape is not None and list(np.shape(v))!=list(shape): raise ValueError('native result shape')
        self.counts[op]+=1; self.word_counts[op]+=np.size(v)
        return np.asarray(v).copy()
    def run_ds(self,program,providers):
        r={}; last={}
        for pc,node in enumerate(program['code']):
            for ref in node['src']: last[ref]=pc
        outputs=set(program['outputs'].values())
        for pc,node in enumerate(program['code']):
            self.current_pc=pc
            if node['op'] not in COMMON_NATIVE: raise ValueError('unsupported native primitive '+node['op'])
            if node['dst'] in r: raise ValueError('native SSA overwrite')
            if any(ref not in r for ref in node['src']): raise ValueError('unpublished native register')
            at=node['attrs']
            if node['op']=='LOAD':
                record=providers.get(at['name'])
                if not isinstance(record,dict) or not record.get('lease') or record.get('state')!='visible': raise ValueError('unbound native provider lease')
                v=np.asarray(record['value'],dtype={'F32':F,'U32':np.uint32,'I64':np.int64}[at['dtype']])
                if v.size>128 or list(v.shape)!=node['shape']: raise ValueError('provider tile shape')
                v=v.copy(); self.counts['LOAD']+=1; self.word_counts['LOAD']+=v.size
            else: v=self.primitive(node['op'],[r[x] for x in node['src']],at,node['shape'])
            r[node['dst']]=v
            self.peak_vectors=max(self.peak_vectors,sum((max(4,x.nbytes)+511)//512 for x in r.values()))
            if self.peak_vectors>32: raise ValueError('native RF32 capacity')
            for ref in list(r):
                if last.get(ref,-1)<=pc and ref not in outputs: del r[ref]
        return {name:r[ref].copy() for name,ref in program['outputs'].items()}
    def run_qwen(self,nodes,env,reserved=2):
        env=dict(env); last={}; output=nodes[-1]['dst']
        for pc,node in enumerate(nodes):
            for text in node.get('src',[]):
                for item in ast.walk(ast.parse(text,mode='eval')):
                    if isinstance(item,ast.Name): last[item.id]=pc
        for pc,node in enumerate(nodes):
            op=node['op']; args=[expression(text,env) for text in node['src']]
            if op=='MOV': v=self.primitive('COPY',args)
            elif op=='NEG': v=self.primitive('BITCAST_F',[self.primitive('XOR',[self.primitive('BITCAST_U',[np.asarray(args[0],F)]),np.uint32(0x80000000)],{'dtype':'U32'})])
            else:
                attrs={'dtype':'I64'} if op in ('IADD64','SHL64') else {'dtype':'U32'} if op in ('IADD','ISUB','SHR','AND','OR','SELECT') else {}
                v=self.primitive(QWEN_ALIASES.get(op,op),args,attrs)
            assign(node['dst'],v,env)
            vectors=reserved+sum((max(4,np.asarray(value).nbytes)+511)//512 for value in env.values())
            self.peak_vectors=max(self.peak_vectors,vectors)
            if vectors>32: raise ValueError('tile RF32 capacity')
            for ref in list(env):
                if ref!=output and last.get(ref,-1)<=pc: del env[ref]
        return env[output]



@lru_cache(maxsize=1)
def _restoring_DIV31():
    # Import only the integer primitive transcription, never the rational oracle.
    source=subprocess.check_output(['git','show','e03c40e40:tools/h3_exact_scalar_contract.py'],cwd=ROOT).decode()
    node=next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name=='restoring_div31')
    namespace={}; exec(compile(ast.Module(body=[node],type_ignores=[]),'<pinned integer DIV31>','exec'),namespace)
    return namespace['restoring_div31']


def restoring_DIV_provider(a,b):
    a,b=np.broadcast_arrays(np.asarray(a,F),np.asarray(b,F))
    if a.size>128: raise ValueError('DIV provider outer tile required')
    result=np.empty(a.shape,np.uint32); faults=np.empty(a.shape,np.uint32)
    primitive=_restoring_DIV31()
    for index in np.ndindex(a.shape):
        r=primitive(int(a[index].view(np.uint32)),int(b[index].view(np.uint32)))
        result[index]=r['y']
        faults[index]=1 if r.get('stage')=='decode_argument' else 2 if r['fault'] else 0
    return result.view(F),faults


TILE_COSTS=('C_NATIVE','C_RF_READ','C_RF_ACK','C_SHARED_BEAT','C_HBM_SECTOR','C_NoC','C_CDC','C_REVERSE_GRANT')


def tile_service_budget(op,p):
    """Conservative serialized service reservation, not measured transaction counts.

    Bounds deliberately include inactive lanes and one RF/HBM page per source
    word. Serial reservation makes finite credits and port capacities feasible;
    an owner can substitute the exact runtime transaction trace to tighten it.
    """
    counts=tiled_counts(op,p,p['context_capacity']-1)['logical_counts']
    commands=sum(v for k,v in counts.items() if k.endswith('_vector_commands'))
    # Every leaf recipe has <=128 instructions. A movement-only op still pays.
    shapes=p['register_shapes']
    source_words=sum(math.prod(p['context_capacity'] if n=='position+1' else n for n in shapes[v]) for v in op['inputs'])
    result_words=sum(math.prod(p['context_capacity'] if n=='position+1' else n for n in shapes[v]) for v in op['outputs'])
    native=sum(physical_tile_export(op,p,p['context_capacity']-1)['native_primitive_commands'].values())+16*(source_words+result_words)+128
    # Three input pages and two output mirrors per native command. One source
    # page per word bounds scatter and reload even for interleaved KV trees.
    words=source_words+result_words+256*native
    hbm=16*words+counts.get('code_sectors32',0)+counts.get('KV_store_bytes',0)+counts.get('KV_read_payload_bytes',0)
    return dict(C_NATIVE=native,C_RF_READ=2*words,C_RF_ACK=2*words,
                C_SHARED_BEAT=8*words,C_HBM_SECTOR=hbm,C_NoC=words,
                C_CDC=2*words,C_REVERSE_GRANT=words)


def materialize_tile_calendar(native,costs):
    """One finite serialized software calendar, positive provisional costs only."""
    if set(costs)!=set(TILE_COSTS) or any(not math.isfinite(v) or v<=0 for v in costs.values()):
        raise ValueError('all provisional service costs must be finite and positive')
    end=0; operations=[]
    for op in native['operations']:
        budget=op['calendar_export']['conservative_serial_service_budget']
        duration=sum(budget[k]*costs[k] for k in TILE_COSTS)
        operations.append(dict(pc=op['pc'],start=end,end=end+duration,service_budget=budget,
            lease='one native tile command, release only after capture ACK/reverse grant',
            dependencies=op['dependencies'],providers=op['provider_binding']))
        end+=duration
    return dict(schema='opentallas.H3.finite-tile-calendar.v1',operations=operations,duration=end,
        costs=costs,cost_scope='explicit provisional parameters; conservative upper service reservation, no hardware qualification',
        resources={'RF_vectors':32,'RF_ports':'2R1W mirrored ACK','shared_bytes':17408,
                   'shared_port_bytes_per_service':128,'HBM_sector_bytes':32,'outstanding_tiles':1,
                   'source_sector_credits_used':1,'source_sector_credits_available':4},
        temporary_HBM_bytes=0,hardware_or_timing_credit=False)

def common_native_abi():
    return dict(schema='opentallas.HBM.native-primitive-ABI.v1',supported=sorted(COMMON_NATIVE),
        Qwen_aliases=QWEN_ALIASES,DS_adapter='run_ds(code/dst/src/shape/attrs/providers/outputs)',
        Qwen_adapter='run_qwen(op/dst/src expressions), bounded scalar/vector leaf only',
        max_tile_words=128,max_RF_vectors=32,bit_types=['F32','U32','I64','E4M3_byte'],
        integer='U32 modulo32, I64 modulo64; signed I64 SHR, logical U32 SHR; shifts range checked; modulo zero rejected',
        rounding='FADD/FMUL/SQRT/DIV binary32 RNE with +0 canonicalization unless explicit canonical_zero=False; BITCAST, integer and movement exact; BF16 is explicit integer RNE recipe',
        exceptions='nonfinite FP arithmetic records fault and retains source bits; F2I nonfinite/outsideI64 rejected; DIV requires exact primitive provider and fault sideband; NaN compares false exceptNE; E4M3 NaN backing rejected',
        provider='LOAD requires visible identity-bearing bounded tile lease; shape/versions/SSA/capacity checked; PACKET_COMMIT with lease requires visible state',
        DIV_provider={'callable':'restoring_DIV_provider','commit':'e03c40e40','function':'restoring_div31','algorithm':'decode/normalize,27 integer restoring steps, guard/sticky RNE, capture error1 argument/error2 overflow; no rational oracle'},
        unsupported='reject before execution; no macro opcode or high-level numerical callback fallback')


def tile_microcode():
    root=norm('unused','out',4096,1e-6); root=root[next(i for i,n in enumerate(root) if n.get('dst')=='vb'):]
    return dict(add=[ins('FADD','out','a','b')],mul=[ins('FMUL','out','a','b')],
        convert=[ins('ITOF','out','x')],bf16=bfpack('x','out'),exp=exponential('x','out'),
        reciprocal=reciprocal('x','out'),rsqrt=root,
        fp8pack=[ins('FP8_PACK','out','x')],fp8unpack=[ins('FP8_UNPACK','out','x')],
        maximum=[ins('FMAX','out','a','b')],neg=[ins('NEG','out','x')],
        argmax=[ins('CMP_GT','win','candidate','best'),ins('CMP_NE','nan','candidate','candidate'),
                ins('CMP_EQ','best_valid','best','best'),ins('AND','first_nan','nan','best_valid'),ins('OR','out','win','first_nan')],
        winner=[ins('CMP_GT','win','b','a'),ins('CMP_EQ','equal','b','a'),ins('CMP_LT','lower','bi','ai'),
                ins('AND','tie','equal','lower'),ins('OR','out','win','tie')])



def tiled_kernel_calls(op,p,position):
    counts=tiled_counts(op,p,position)['logical_counts']; name=op['opcode']; c=p['config']; T=position+1
    nh=c['num_attention_heads']//2; hd=c['head_dim']; kv=c['num_key_value_heads']//2
    calls=Counter()
    if name=='RSTD' or name=='FINAL_NORM': calls['rsqrt']=1
    elif name=='HEAD_NORM': calls['rsqrt']=p['register_shapes'][op['outputs'][0]][0]
    if name=='EXP_SUM': calls.update(exp=nh*((T+127)//128),maximum=nh*(T-1),neg=nh)
    elif name=='SILU_GATE': calls.update(exp=(c['intermediate_size']//2+127)//128,neg=(c['intermediate_size']//2+127)//128)
    if name=='SILU_GATE': calls['reciprocal']=(c['intermediate_size']//2+127)//128
    elif name=='NORMALIZE': calls['reciprocal']=nh
    if name=='ROPE': calls['neg']=p['register_shapes'][op['outputs'][0]][0]*((hd//2+127)//128)
    if name=='ARGMAX': calls['argmax']=p['register_shapes'][op['inputs'][0]][0]-1
    if name=='ARGMAX_REDUCE': calls['winner']=1
    if name=='KV_WRITE': calls['fp8pack']=2*kv*((hd+127)//128)
    if name=='KV_READ': calls['fp8unpack']=2*((kv*T*hd+127)//128)
    calls['bf16']=counts.get('BF16_pack_windows',0)
    calls['convert']=counts.get('ITOF_vector_commands',0)
    calls['add']=counts.get('FADD_vector_commands',0)-3*calls['rsqrt']-10*calls['exp']-3*calls['reciprocal']
    calls['mul']=counts.get('FMUL_vector_commands',0)-10*calls['rsqrt']-9*calls['exp']-6*calls['reciprocal']
    if any(v<0 for v in calls.values()): raise ValueError('kernel invocation accounting')
    return {k:v for k,v in calls.items() if v}


@lru_cache(maxsize=1)
def tile_kernel_ABI():
    inputs={'add':['a','b'],'mul':['a','b'],'convert':['x'],'bf16':['x'],'exp':['x'],
            'reciprocal':['x'],'rsqrt':['variance'],'fp8pack':['x'],'fp8unpack':['x'],
            'maximum':['a','b'],'neg':['x'],'argmax':['candidate','best'],'winner':['a','b','ai','bi']}
    profiles={}
    for name,nodes in tile_microcode().items():
        scalar=name in ('rsqrt','maximum','argmax','winner')
        env={x:Shape(()) if scalar else Shape((128,)) for x in inputs[name]}; steps=[]; counts=Counter()
        for node in nodes:
            args=[shape_eval(x,env) for x in node['src']]
            result=inferred_result(node,args,{})
            shape=shapeof(result); op=node['op']
            primitive=['BITCAST_U','XOR','BITCAST_F'] if op=='NEG' else ['COPY'] if op=='MOV' else [QWEN_ALIASES.get(op,op)]
            counts.update(primitive)
            bits=64 if op in ('FTOI','IADD64','SHL64') else 8 if op=='FP8_PACK' else 32
            steps.append(dict(op=op,native_steps=primitive,reads=[dict(expression=text,shape_max=list(shapeof(arg))) for text,arg in zip(node['src'],args)],
                write={'symbol':node['dst'],'shape_max':list(shape),'bits_per_element':bits,'RF_vectors_max':max(1,(math.prod(shape)*bits+4095)//4096)},
                round_point='binary32 RNE + canonical zero' if op in ('FMUL','FADD') else 'bit-exact movement/integer or declared converter'))
            env[node['dst']]=result
        profiles[name]=dict(steps=steps,native_counts_per_invocation=dict(counts),tile_shape_scope='max128; scalar broadcasts do not allocate full tensor')
    return profiles


def physical_tile_export(op,p,position):
    calls=tiled_kernel_calls(op,p,position); profiles=tile_kernel_ABI(); counts=Counter()
    for name,times in calls.items():
        for primitive,n in profiles[name]['native_counts_per_invocation'].items(): counts[primitive]+=times*n
    return dict(kernel_invocations=calls,native_primitive_commands=dict(counts),
        kernel_ABI_reference='tile_kernel_ABI',working_shapes_max='all native FP/int/movement results <=128 elements; I64 charges two32-bit RF words',
        provider_reads='separate explicit source homes and immutable extent byte ranges, under publication/ACK/reverse leases',
        source_order='procedural tile controller TiledMachine.execute/dot/rms frozen by source SHA; serialized leaf kernels execute these native steps')

def fixture_tile_provider(p,versioned):
    """Use the identical distributed allocator for reduced software fixtures."""
    from h3_distributed_norm_endpoint import distribute
    distributed=distribute('Qwen',versioned); homes=[]; controls=[]; allocations=[]
    values={v['id']:v for v in versioned['operands']}; byversion=defaultdict(list)
    for rank in range(2):
        ext=copy.deepcopy(p['memory_allocation'][rank]['extents']); scratch=next(e for e in ext if e['name']=='activation_scratch')
        scratch['bytes']=32*1048576; end=scratch['base']+scratch['bytes']
        ext.append(dict(name='KV_provider_state',base=end,bytes=37504,role='software_provider_state'))
        for e in ext: e.update(rank=rank,provider_ref=f"Qwen.rank{rank}.extent.{e['name']}")
        allocations.append(dict(rank=rank,extents=ext,global_allocated_end_bytes=end+37504))
    for item in distributed['homes']:
        v=values[item['version']]
        for rank in item['rank_group']:
            home=copy.deepcopy(item['home'])
            if home['class']=='spill':
                scratch=next(e for e in allocations[rank]['extents'] if e['name']=='activation_scratch')
                home.update(global_byte_base=scratch['base']+item['SM']*1048576+home['byte_offset'])
            record=dict(version=item['version'],provider_ref=f"Qwen.{item['version']}.rank{rank}.SM{item['SM']}",
                        rank=rank,SM=item['SM'],home=home,word_count=item['word_count'],birth_pc=v['birth_pc'],
                        retire_pc=v['retire_pc'],consumers=v['consumers'],release_event=f"RELEASE:{item['version']}:r{rank}:s{item['SM']}")
            homes.append(record); byversion[v['id']].append(record['provider_ref'])
    for v in values.values():
        if v['bits_per_element']==0:
            for rank,n in enumerate(v['elements_per_rank']):
                if n:
                    record=dict(version=v['id'],rank=rank,provider_ref=f"Qwen.control.{v['id']}.rank{rank}",
                                birth_pc=v['birth_pc'],consumers=v['consumers'],state_extent=f'Qwen.rank{rank}.extent.KV_provider_state')
                    controls.append(record); byversion[v['id']].append(record['provider_ref'])
    operations=[]
    for o,source in zip(versioned['operations'],p['instructions']):
        attrs=source['attributes']; name=source['opcode']; external=[]
        def add(rank,extent,**meta):
            if not any(e['name']==extent for e in allocations[rank]['extents']): raise ValueError('fixture external extent')
            external.append(dict(provider_ref=f'Qwen.rank{rank}.extent.{extent}',**meta))
        if name in ('MATRIX','ROW_SCALE','ALL_REDUCE'):
            d=p['weight_descriptors'][attrs.get('weight',attrs.get('post_scale_weight'))]
            prefix='head' if d['layer'] is None else f'L{d["layer"]}.{d["name"]}'
            add(d['die'],prefix+('.codes' if name=='MATRIX' else '.scales'),weight_descriptor=d)
        if name in ('EMBED','FINAL_NORM','ROPE','HEAD_NORM'):
            extent_name='embedding' if name=='EMBED' else 'final_norm' if name=='FINAL_NORM' else 'rope_table' if name=='ROPE' else f'L{attrs["layer"]}.qk_norm'
            ranks=o['participants']
            for rank in ranks: add(rank,extent_name,selector=attrs)
        if name in ('KV_WRITE','KV_READ','KV_FENCE'):
            for kind in ('K','V'): add(attrs['die'],f'L{attrs["layer"]}.{kind}')
            add(attrs['die'],'KV_provider_state')
        operations.append(dict(pc=o['pc'],opcode=o['opcode'],inputs={v:byversion[v] for v in o['reads']},
                     outputs={v:byversion[v] for v in o['writes']},external_providers=external))
    return dict(version_homes=homes,control_homes=controls,allocation=allocations,reuse_dependencies=[],operations=operations,
                resource_contract={'RF_workspace_slots':[0,32],'source_stage_sector_credits_per_rank':4,'logical_KV_reader_leases_per_rank':36},
                scope='reduced fixture distributed allocator; no default fullshape pin replacement')


def compile_tiled(program=None):
    p=compile_program() if program is None else copy.deepcopy(program)
    if program is None:
        with gzip.open(ROOT/INPUT,'rt') as stream: versioned=json.load(stream)
        provider,pin=load_provider_binding()
    else: versioned=make_versioned(p); provider=fixture_tile_provider(p,versioned); pin=None
    values={v['id']:binding(v) for v in versioned['operands']}
    for v in values.values(): v['shape']=p['register_shapes'][v['name']]
    join_provider_homes(values,provider)
    for allocation in provider['allocation']:
        rank=allocation['rank']; p['memory_allocation'][rank]['extents']=allocation['extents']
        p['memory_allocation'][rank]['allocated_bytes']=allocation['global_allocated_end_bytes']
    operations=[]
    for source,old,bound in zip(p['instructions'],versioned['operations'],provider['operations']):
        count=tiled_counts(source,p,p['context_capacity']-1)
        operations.append(dict(pc=source['id'],opcode=source['opcode'],reads=old['reads'],writes=old['writes'],
            dependencies=old['dependencies'],attributes=source['attributes'],provider_binding=bound,
            kernels=list(tile_microcode()),
            loop_program={'row_step':128,'code_K_window':32,'float_K_step':16,'KV_and_vector_window':128,
                          'norm_leaf':8,'norm_tree':'streaming adjacent carry stack, pad with source +0 leaves',
                          'matrix_split':'contiguous' if source['opcode']=='MATRIX' else 'interleaved',
                          'carry_rule':'combine left earlier leaf with right later leaf; all split leaves retained; one vector per level',
                          'source_address':'(version,rank,SM) via exact r17 homes; global_word block256 distribution',
                          'retirement':'tile consumer+capture ACK+reverse grant before buffer reuse; PC consumers before home release'},
            calendar_export={'schema':'opentallas.H3.native-bounded-tiles.v1','counts_full_context':count,
                'source_provider_operation':bound,'physical_primitives':physical_tile_export(source,p,p['context_capacity']-1),'RF_workspace_vectors':32,'shared_reserved_bytes':17408,
                'temporary_HBM_bytes':0,'provider_resource_contract':provider['resource_contract'],
                'duration':'ordered native+RF+shared+provider_sector+NoC+CDC+ACK+reverse grant costs, no zero-cost unknowns',
                'all_costs_provisional':True,
                'conservative_serial_service_budget':tile_service_budget(source,p),
                'transaction_scope':'upper service reservation; exact page/sector counts exported by executor',
                'placement':'serialized worker rank0 SM0, remote home transfers charged through NoC; no assumed extra local RF ports',
                'finite_calendar_entrypoint':'materialize_tile_calendar(native,positive_costs)'}))
    return dict(schema='opentallas.H3.qwen-bounded-tiled-native.v1',opt_in=True,default_enabled=False,
                source_program=p,operands=list(values.values()),operations=operations,provider_binding=provider,
                provider_binding_pin=pin,microcode=tile_microcode(),tile_kernel_ABI=tile_kernel_ABI(),primitive_ABI=common_native_abi(),
                feasibility=tile_feasibility_model(p),coverage={'PCs':len(operations),'families':dict(Counter(o['opcode'] for o in operations)),
                'all_PC_executable':True,'unsupported':[]},hardware_or_timing_credit=False)



class BoundKVStorage(Storage):
    """Packed r17 bitmap/reader records in the actually charged HBM extent.

    Host maps are simulator indexes and event logs. Publication, current producer
    identity, reader occupancy and completion are checked against physical bytes.
    The serialized executor has one staged writer (<=1024B source token payload),
    reusing idle shared tile space, rather than historical full-cache buffers.
    """
    def __init__(self,p):
        super().__init__(p); self.pc=0
        self.state={rank:extent(p,rank,'KV_provider_state') for rank in range(2)}
        self.counters=Counter()
    def state_write(self,rank,offset,data):
        e=self.state[rank]
        if offset<0 or offset+len(data)>e['bytes']: raise ValueError('KV state byte aperture')
        for i,byte in enumerate(data): self.bytes[rank,e['base']+offset+i]=byte
        self.counters['state_write_sectors32']+=len(set((e['base']+offset+i)//32 for i in range(len(data))))
    def state_read(self,rank,offset,count):
        e=self.state[rank]
        if offset<0 or offset+count>e['bytes']: raise ValueError('KV state byte aperture')
        self.counters['state_read_sectors32']+=len(set((e['base']+offset+i)//32 for i in range(count)))
        return bytes(self.bytes.get((rank,e['base']+offset+i),0) for i in range(count))
    def record(self,layer,rank): return int.from_bytes(self.state_read(rank,36864+16*layer,16),'little')
    def put_record(self,layer,rank,position,identity,producer_pc,done,status):
        if not 0<=layer<36 or not 0<=position<8192 or not 0<=identity<2**64 or not 0<=producer_pc<2048: raise ValueError('KV state identity aperture')
        value=position|(identity<<13)|(producer_pc<<77)|(done<<88)|(status<<90)
        self.state_write(rank,36864+16*layer,value.to_bytes(16,'little'))
    def bit(self,layer,rank,position):
        index=layer*8192+position
        return bool(self.state_read(rank,index//8,1)[0]&(1<<(index%8)))
    def begin(self,layer,die,position):
        if self.pending: raise ValueError('serialized writer lease busy')
        if self.bit(layer,die,position): raise ValueError('physical KV publication overwrite')
        tag=super().begin(layer,die,position)
        self.pending[tag]['producer_pc']=self.pc
        self.state_write(die,37440,self.tags.to_bytes(8,'little'))
        return tag
    def commit(self,tag):
        state=self.pending[int(tag)]; layer,rank,position=state['key']
        if len(state['payload'])>1024: raise ValueError('KV writer shared1024B staging bound')
        result=super().commit(tag)
        index=layer*8192+position; byte=self.state_read(rank,index//8,1)[0]|(1<<(index%8))
        self.state_write(rank,index//8,bytes([byte]))
        self.put_record(layer,rank,position,int(tag),state['producer_pc'],0,1)
        return result
    def acquire(self,fence,layer,die,position):
        if any(not self.bit(layer,die,pos) for pos in range(position+1)): raise ValueError('physical KV prefix unpublished')
        record=self.record(layer,die)
        if record&8191!=position or (record>>13)&((1<<64)-1)!=fence['tag']: raise ValueError('physical KV producer identity')
        if (record>>90)&3!=1: raise ValueError('physical KV reader record occupied')
        lease=super().acquire(fence,layer,die,position)
        self.put_record(layer,die,position,lease,(record>>77)&2047,0,2)
        return lease
    def read(self,lease,addresses):
        layer,rank,position=self.leases[int(lease)]['key']; record=self.record(layer,rank)
        if (record>>90)&3!=2 or (record>>13)&((1<<64)-1)!=lease: raise ValueError('physical KV reader lease identity')
        for address in np.asarray(addresses).flat:
            if not self.bit(layer,rank,self.decode_address(layer,rank,int(address))[1]): raise ValueError('physical KV read unpublished')
        return super().read(lease,addresses)
    def done(self,lease,stage):
        layer,rank,position=self.leases[lease]['key']; record=self.record(layer,rank)
        if (record>>13)&((1<<64)-1)!=lease or (record>>90)&3!=2: raise ValueError('physical KV completion lease')
        super().done(lease,stage)
        done=((record>>88)&3)|(1 if stage=='SCORES' else 2)
        self.put_record(layer,rank,position,lease,(record>>77)&2047,done,3 if done==3 else 2)

class TileWords:
    """Actual RF mirror/spill pages, not whole activation arrays in an SM."""
    def __init__(self,native):
        self.p=native['source_program']; self.values={v['version']:v for v in native['operands']}
        self.homes={}; self.control={}; self.pages={}; self.owners={}; self.live=set(); self.published=set(); self.shapes={}
        self.cache=None; self.counters=Counter(); self.events=[]; self.worker_SM=0; self.worker_rank=0
        for v in self.values.values():
            for h in v['homes']:
                if 'home' in h: self.homes[v['version'],h['rank'],h['SM']]=h
    def rank(self,version): return min(h['rank'] for h in self.values[version]['homes'])
    def key(self,version,word,rank):
        sm=(word//256)%32; local=(word//8192)*256+word%256
        record=self.homes.get((version,rank,sm))
        if record is None or local>=record['word_count']: raise ValueError('source home coordinate')
        h=record['home']
        if h['class']=='RF': return ('RF',rank,sm,h['slot_first']+local//128),local%128
        byte=h['global_byte_base']+4*local
        return ('HBM',rank,sm,h['global_byte_base']+(local//128)*512),local%128
    def reserve(self,version,position,kind='F32'):
        if version in self.live: raise ValueError('source SSA overwrite')
        v=self.values[version]; shape=tuple(position+1 if n=='position+1' else n for n in v['shape'])
        self.shapes[version]=(shape,kind); self.live.add(version)
        for h in v['homes']:
            if 'home' not in h: continue
            p=h['home']; start=p['slot_first'] if p['class']=='RF' else p['global_byte_base']
            count=p['vectors'] if p['class']=='RF' else p['bytes']//512; step=1 if p['class']=='RF' else 512
            for index in range(count):
                key=('RF' if p['class']=='RF' else 'HBM',h['rank'],h['SM'],start+index*step)
                if key in self.owners: raise ValueError('live provider alias')
                self.owners[key]=version
    def write(self,version,start,values):
        if version not in self.live: raise ValueError('unreserved destination')
        a=np.asarray(values)
        if a.size>128: raise ValueError('write needs outer128-word tile')
        kind=self.shapes[version][1]
        bits=a.astype(np.uint32).reshape(-1) if kind in ('U32','winner') else a.astype(F).view(np.uint32).reshape(-1)
        total=2 if kind=='winner' else math.prod(self.shapes[version][0])
        if start<0 or start+len(bits)>total: raise ValueError('source destination aperture')
        touched=set()
        for rank in sorted({h['rank'] for h in self.values[version]['homes']}):
            for i,word in enumerate(bits):
                key,lane=self.key(version,start+i,rank); touched.add(key)
                if self.owners.get(key)!=version: raise ValueError('destination provider lease identity')
                if key not in self.pages: self.pages[key]=[np.zeros(128,np.uint32) for _ in range(2 if key[0]=='RF' else 1)]
                for mirror in self.pages[key]: mirror[lane]=word
        for key in touched:
            self.counters['RF_write_ACK' if key[0]=='RF' else 'HBM_write_sectors32']+=1 if key[0]=='RF' else 16
            self.counters['source_write_payload_bits']+=4096
            if key[0]=='RF': self.counters['RF_mirror_write_bits']+=8192
            if (key[1],key[2])!=(self.worker_rank,self.worker_SM): self.counters['NoC_source_write_bits']+=4096
        self.cache=None
    def publish(self,version,value=None):
        if version not in self.live: raise ValueError('unreserved publication')
        if self.values[version]['homes'][0].get('home') is None: self.control[version]=copy.deepcopy(value)
        self.published.add(version); self.events.append(dict(event='publish',version=version))
    def read_indices(self,version,indices):
        if version not in self.published: raise ValueError('unpublished source')
        indexes=np.asarray(indices,dtype=np.int64).reshape(-1)
        if len(indexes)>128: raise ValueError('read needs outer128-word tile')
        shape,kind=self.shapes[version]; total=2 if kind=='winner' else math.prod(shape)
        if np.any(indexes<0) or np.any(indexes>=total): raise ValueError('source read aperture')
        result=np.empty(len(indexes),np.uint32); rank=self.rank(version)
        for i,word in enumerate(indexes):
            key,lane=self.key(version,int(word),rank)
            if self.owners.get(key)!=version: raise ValueError('source provider lease identity')
            if key not in self.pages: raise ValueError('unwritten provider page')
            if self.cache is None or self.cache[0]!=key:
                mirrors=self.pages[key]
                if len(mirrors)==2 and not np.array_equal(*mirrors): raise ValueError('RF mirror disagreement')
                self.cache=(key,mirrors[0].copy())
                self.counters['RF_read' if key[0]=='RF' else 'HBM_read_sectors32']+=1 if key[0]=='RF' else 16
                self.counters['source_read_payload_bits']+=4096
                if (key[1],key[2])!=(self.worker_rank,self.worker_SM): self.counters['NoC_source_read_bits']+=4096
            result[i]=self.cache[1][lane]
        self.counters['source_word_reads']+=len(indexes)
        return result if kind in ('U32','winner') else result.view(F)
    def read(self,version,start,count): return self.read_indices(version,np.arange(start,start+count,dtype=np.int64))
    def retire(self,pc):
        for version in list(self.live):
            if self.values[version]['retire_pc']!=pc: continue
            self.live.remove(version); self.published.remove(version); self.control.pop(version,None)
            for key in [k for k,v in self.owners.items() if v==version]:
                self.owners.pop(key); self.pages.pop(key,None)
            self.events.append(dict(event='release',version=version))
        self.cache=None
    def debug_snapshot(self,version,max_words=8192):
        """Post-commit TEST observer only; never used by the micro-op executor."""
        if version in self.control: return copy.deepcopy(self.control[version])
        shape,kind=self.shapes[version]; n=2 if kind=='winner' else math.prod(shape)
        if n>max_words: raise ValueError('debug snapshot bound')
        parts=[self.read(version,i,min(128,n-i)) for i in range(0,n,128)]
        a=np.concatenate(parts) if parts else np.empty(0,F)
        return (a[:1].view(F)[0],int(a[1])) if kind=='winner' else a.reshape(shape)


class TileFixtureWeights:
    """Random-access raw immutable fixture tiles, no complete matrix allocation."""
    def __init__(self,p): self.p=p; self.calls=[]; self.provider_reads=[]
    def read_tile(self,record,method,*args):
        if not record.get('provider_ref') or record.get('lease_state')!='visible': raise ValueError('immutable provider lease')
        self.provider_reads.append((record['provider_ref'],method))
        return getattr(self,method)(*args)
    def matrix_tile(self,key,row_start,row_count,column_start,column_count):
        d=self.p['weight_descriptors'][key]
        if not 0<row_count<=128 or not 0<column_count<=32 or row_start+row_count>d['rows'] or column_start+column_count>d['K']: raise ValueError('weight tile aperture')
        seed=int(hashlib.sha256(key.encode()).hexdigest()[:8],16)
        rows=np.arange(row_start,row_start+row_count,dtype=np.uint64)[:,None]
        cols=np.arange(column_start,column_start+column_count,dtype=np.uint64)[None,:]
        self.calls.append((key,row_start,row_count,column_start,column_count))
        return (((rows*131+cols*17+seed)%9).astype(np.int8)-4)
    def scale_tile(self,key,start,count): return np.full(count,F(.03125))
    def gamma_tile(self,layer,kind,start,count): return np.ones(count,F)
    def embedding_tile(self,token,start,count): return ((int(token)+np.arange(start,start+count))%9-4).astype(np.int8),F(.125)
    def rope_tile(self,position,theta,start,count):
        hd=self.p['config']['head_dim']; inv=(1/(theta**(np.arange(2*start,2*(start+count),2,dtype=np.float64)/hd))).astype(F)
        angle=(F(position)*inv).astype(F)
        return np.cos(angle.astype(np.float64)).astype(F),np.sin(angle.astype(np.float64)).astype(F)



class HBMByteTileProvider:
    """Concrete raw-byte transport adapter; no checkpoint arithmetic callback.

    The backend exposes read_tile_bytes(request) with actual provider identity,
    bounded byte ranges, visible backing, matched lease and reverse grant ACK.
    W8 full-row quantization is an upstream immutable producer, never silently
    performed by this consumer. BF16 and RoPE transport decoding is bit exact.
    """
    def __init__(self,backend): self.backend=backend
    def read_tile(self,record,method,*args):
        response=self.backend.read_tile_bytes(record)
        if not isinstance(response,dict) or response.get('provider_ref')!=record['provider_ref'] or response.get('lease')!=record['lease']:
            raise ValueError('immutable provider response identity')
        if response.get('state')!='visible' or not response.get('reverse_grant_ACK'):
            raise ValueError('immutable provider backing/reverse grant')
        payloads=response.get('payloads',[])
        if len(payloads)!=len(record['byte_ranges']) or any(len(data)!=r['bytes'] for data,r in zip(payloads,record['byte_ranges'])):
            raise ValueError('immutable provider response bytes')
        def bf(data):
            return (np.frombuffer(data,dtype='<u2').astype(np.uint32)<<16).view(F)
        if method=='matrix_tile': return np.stack([np.frombuffer(data,np.int8) for data in payloads])
        if method in ('scale_tile','gamma_tile'): return bf(payloads[0]).copy()
        if method=='embedding_tile': return np.frombuffer(payloads[0],np.int8).copy(),bf(payloads[1])[0]
        if method=='rope_tile': return tuple(np.frombuffer(data,dtype='<f4').copy() for data in payloads)
        raise ValueError('unsupported immutable byte tile '+method)

class TiledMachine:
    """Procedural tile/control interpreter over shared primitive microcode.

    Control methods only move bounded words, traverse exact source loops and
    call compiled primitive kernels. They never call a golden/operator oracle.
    Source tensor pages are RF/HBM backing; working arrays never exceed the
    declared RF32/shared17,408B limits.
    """
    def __init__(self,native,weights=None):
        if native.get('schema')!='opentallas.H3.qwen-bounded-tiled-native.v1': raise ValueError('tiled opt-in schema required')
        self.native=native; self.p=native['source_program']; self.store=TileWords(native)
        self.weights=weights or TileFixtureWeights(self.p); self.memory=BoundKVStorage(self.p); self.vm=NativePrimitiveVM()
        self.kv_leases={}; self.counters=Counter(); self.stack=[]; self.peak_shared=0; self.done=set()
        self.extents={e['provider_ref']:e for allocation in native['provider_binding']['allocation'] for e in allocation['extents']}
        self.current_external=[]
    def provider(self,method,*args):
        suffix={'matrix_tile':'.codes','scale_tile':'.scales','embedding_tile':'.embedding',
                'gamma_tile':'.final_norm' if method=='gamma_tile' and args[1]=='final' else '.qk_norm',
                'rope_tile':'.rope_table'}
        refs=[r for r in self.current_external if r['provider_ref'].endswith(suffix[method])]
        if not refs: raise ValueError('unbound external tile provider '+method)
        record=refs[0]; extent=self.extents.get(record['provider_ref'])
        if extent is None: raise ValueError('external extent missing')
        c=self.p['config']; h=c['hidden_size']; hd=c['head_dim']; ranges=[]
        if method=='matrix_tile':
            key,row,n,column,k=args; d=self.p['weight_descriptors'][key]
            if record['weight_descriptor']['key']!=key or not 0<n<=128 or not 0<k<=32: raise ValueError('code provider selector')
            if row<0 or column<0 or row+n>d['rows'] or column+k>d['K']: raise ValueError('code provider aperture')
            ranges=[(r*d['K']+column,k) for r in range(row,row+n)]
        elif method=='scale_tile':
            key,start,n=args
            if record['weight_descriptor']['key']!=key: raise ValueError('scale provider selector')
            ranges=[(2*start,2*n)]
        elif method=='gamma_tile':
            layer,kind,start,n=args; offset=hd if kind=='k' else 0
            ranges=[(2*(offset+start),2*n)]
        elif method=='embedding_tile':
            token,start,n=args
            if not 0<=token<c['vocab_size'] or start<0 or start+n>h: raise ValueError('embedding selector')
            ranges=[(token*h+start,n),(c['vocab_size']*h+2*token,2)]
        elif method=='rope_tile':
            position,theta,start,n=args
            if theta!=self.p['config']['rope_theta']: raise ValueError('RoPE provider source theta')
            ranges=[(4*(position*hd+start),4*n),(4*(position*hd+hd//2+start),4*n)]
        if method!='matrix_tile' and not 0<n<=128: raise ValueError('external provider tile aperture')
        if any(start<0 or size<0 or start+size>extent['bytes'] for start,size in ranges): raise ValueError('external byte aperture')
        bound=dict(record,base=extent['base'],bytes=extent['bytes'],lease_state='visible',
                   lease=f'PC{self.current_pc}.{record["provider_ref"]}',
                   tile_method=method,tile_arguments=list(args),source_config=self.p['config'],codec=extent.get('codec'),
                   byte_ranges=[{'address':extent['base']+start,'bytes':size} for start,size in ranges],
                   producer_dependency=record['provider_ref']+'.codec_backing_visible')
        if not hasattr(self.weights,'read_tile'): raise ValueError('raw provider read_tile ABI required')
        value=self.weights.read_tile(bound,method,*args)
        arrays=value if isinstance(value,tuple) else (value,)
        expected=(n,k) if method=='matrix_tile' else (n,)
        if np.shape(arrays[0])!=expected: raise ValueError('external tile result shape')
        if method in ('matrix_tile','embedding_tile'):
            if np.asarray(arrays[0]).dtype!=np.int8: raise ValueError('external INT8 code type')
        elif any(np.asarray(a).dtype!=F for a in arrays): raise ValueError('external FP32 decoded type')
        if method=='embedding_tile' and (np.asarray(arrays[1]).dtype!=F or int(np.asarray(arrays[1]).view(np.uint32))&65535): raise ValueError('embedding BF16 scale codec')
        if method in ('gamma_tile','scale_tile') and np.any(np.asarray(value).view(np.uint32)&65535): raise ValueError('external BF16 codec')
        sectors=set()
        for r in bound['byte_ranges']:
            sectors.update(range(r['address']//32,(r['address']+r['bytes']-1)//32+1))
        self.counters['immutable_HBM_sectors32']+=len(sectors)
        self.counters['immutable_provider_tile_ACK_reverse_release']+=1
        return value
    def kernel(self,name,**env):
        reserved=9+len(self.stack) # cache, accumulator, product, weight, x and control captures
        return self.vm.run_qwen(self.native['microcode'][name],env,reserved)
    def add(self,a,b): return self.kernel('add',a=a,b=b)
    def mul(self,a,b): return self.kernel('mul',a=a,b=b)
    def push(self,value):
        level=0
        while level<len(self.stack) and self.stack[level] is not None:
            value=self.add(self.stack[level],value); self.stack[level]=None; level+=1
        if level==len(self.stack): self.stack.append(value)
        else: self.stack[level]=value
    def root(self):
        present=[v for v in self.stack if v is not None]
        if len(present)!=1: raise ValueError('non-padded tree')
        value=present[0]; self.stack=[]; return value
    def scalar(self,version):
        if version in self.store.control: return self.store.control[version]
        return self.store.read(version,0,1)[0]
    def rms(self,version,start,n,eps):
        self.stack=[]; groups=(n+7)//8; leaves=1<<(groups-1).bit_length()
        # Only a128-word input page and one8-word square vector are live.
        for g in range(groups):
            x=self.store.read(version,start+8*g,min(8,n-8*g)); square=self.mul(x,x); value=F(0)
            for term in square: value=self.add(value,term)
            self.push(value)
        for _ in range(groups,leaves): self.push(F(0))
        total=self.root(); variance=self.add(self.mul(total,F(1/n)),F(eps))
        return self.kernel('rsqrt',variance=variance)
    def dot(self,rows,K,S,xreader,wreader,output,output_start,bf16=False,codes=False):
        for r0 in range(0,rows,128):
            rn=min(128,rows-r0); self.stack=[]; xcache=None; codecache=None
            for s in range(S):
                acc=np.zeros(rn,F)
                indexes=range(s*(K//S),(s+1)*(K//S)) if codes else range(s,K,S)
                # K traverses in exact golden split order. Empty leaves stay +0.
                for begin in range(0,len(indexes),32 if codes else 16):
                    kk=list(indexes[begin:begin+(32 if codes else 16)])
                    if codes:
                        for k in kk:
                            block=(k//32)*32
                            if codecache is None or codecache[0]!=block:
                                data=wreader(r0,rn,block,min(32,K-block))
                                if data.shape!=(rn,min(32,K-block)) or data.dtype!=np.int8: raise ValueError('raw code tile shape/type')
                                codecache=(block,data); self.peak_shared=max(self.peak_shared,2*data.nbytes)
                                self.counters['code_tile_reads']+=1; self.counters['code_payload_bytes']+=data.nbytes
                                sectors=set()
                                for row in range(r0,r0+rn):
                                    first=row*K+block; last=first+data.shape[1]-1
                                    sectors.update(range(first//32,last//32+1))
                                self.counters['code_sectors32']+=len(sectors)
                                self.counters['shared_write_beats128']+=(data.nbytes+127)//128
                                self.counters['tile_reserve_ACK_reverse_release']+=1
                            page=(k//128)*128
                            if xcache is None or xcache[0]!=page:
                                x=self.kernel('bf16',x=xreader(list(range(page,min(K,page+128)))))
                                xcache=(page,x); self.counters['BF16_pack_windows']+=1
                            self.counters['shared_read_beats128']+=(rn+127)//128
                            weight=self.kernel('convert',x=codecache[1][:,k-block])
                            acc=self.add(acc,self.mul(weight,xcache[1][k-page]))
                    else:
                        w=wreader(r0,rn,kk); x=xreader(kk)
                        if w.shape!=(rn,len(kk)) or w.dtype!=F: raise ValueError('FP32 attention tile shape/type')
                        self.peak_shared=max(self.peak_shared,2*w.nbytes)
                        self.counters['shared_write_beats128']+=(w.nbytes+127)//128
                        self.counters['shared_read_beats128']+=len(kk)*((4*rn+127)//128)
                        self.counters['tile_reserve_ACK_reverse_release']+=1
                        for j,k in enumerate(kk):
                            if bf16:
                                page=(k//128)*128
                                if xcache is None or xcache[0]!=page:
                                    xcache=(page,self.kernel('bf16',x=xreader(list(range(page,min(K,page+128)))))); self.counters['BF16_pack_windows']+=1
                                value=xcache[1][k-page]
                            else: value=x[j]
                            acc=self.add(acc,self.mul(w[:,j],value))
                self.push(acc)
            result=self.root()
            self.store.write(output,output_start+r0,result)
        if self.peak_shared>16384: raise ValueError('shared tile reservation')
    def execute(self,op):
        # Branches select tile/control programs; all arithmetic calls serialized
        # kernels above, independent of source golden and high-level providers.
        name=op['opcode']; a=op['attributes']; c=self.p['config']; hd=c['head_dim']; nh=c['num_attention_heads']//2
        self.current_external=op['provider_binding']['external_providers']; self.current_pc=op['pc']; self.memory.pc=op['pc']
        for record in self.current_external:
            if record['provider_ref'] not in self.extents: raise ValueError('unbound external provider')
        kv=c['num_key_value_heads']//2; T=self.position+1; reads=op['reads']; out=op['writes']
        for i,v in enumerate(out):
            kind='winner' if name=='ARGMAX' else 'U32' if name=='ARGMAX_REDUCE' else 'F32'
            self.store.reserve(v,self.position,kind)
        if name=='EMBED':
            for i in range(0,c['hidden_size'],128):
                codes,scale=self.provider('embedding_tile',int(self.scalar(reads[0])),i,min(128,c['hidden_size']-i))
                self.store.write(out[0],i,self.mul(self.kernel('convert',x=codes),scale))
        elif name=='RSTD': self.store.write(out[0],0,self.rms(reads[0],0,c['hidden_size'],a['epsilon']))
        elif name=='MATRIX':
            d=self.p['weight_descriptors'][a['weight']]
            self.dot(d['rows'],d['K'],d['split'],lambda indexes:self.store.read_indices(reads[0],indexes),
                lambda r,n,k,m:self.provider('matrix_tile',a['weight'],r,n,k,m),out[0],0,True,True)
        elif name in ('ROW_SCALE','SCALAR_MUL','RESIDUAL','ALL_REDUCE'):
            size=math.prod(self.store.shapes[out[0]][0])
            for start in range(0,size,128):
                n=min(128,size-start); x=self.store.read(reads[0],start,n)
                if name=='ROW_SCALE': value=self.mul(x,self.provider('scale_tile',a['weight'],start,n))
                elif name=='SCALAR_MUL': value=self.mul(x,self.scalar(reads[1]))
                else:
                    value=self.add(x,self.store.read(reads[1],start,n))
                    if name=='ALL_REDUCE': value=self.mul(value,self.provider('scale_tile',a['post_scale_weight'],start,n))
                self.store.write(out[0],start,value)
        elif name=='QKV_SPLIT':
            base=0
            for v in out:
                n=math.prod(self.store.shapes[v][0])
                for start in range(0,n,128): self.store.write(v,start,self.store.read(reads[0],base+start,min(128,n-start)))
                base+=n
        elif name in ('HEAD_NORM','FINAL_NORM'):
            heads=self.store.shapes[out[0]][0][0] if name=='HEAD_NORM' else 1
            dim=hd if name=='HEAD_NORM' else c['hidden_size']
            for head in range(heads):
                scalar=self.rms(reads[0],head*dim,dim,a['epsilon'])
                for start in range(0,dim,128):
                    n=min(128,dim-start); x=self.store.read(reads[0],head*dim+start,n)
                    gamma=self.provider('gamma_tile',a.get('layer'),a.get('kind','final'),start,n)
                    self.store.write(out[0],head*dim+start,self.mul(self.mul(x,scalar),gamma))
        elif name=='ROPE':
            half=hd//2; heads=self.store.shapes[out[0]][0][0]; position=int(self.scalar(reads[1]))
            for head in range(heads):
                for start in range(0,half,128):
                    n=min(128,half-start); lo=self.store.read(reads[0],head*hd+start,n); hi=self.store.read(reads[0],head*hd+half+start,n)
                    co,si=self.provider('rope_tile',position,a['theta'],start,n)
                    self.store.write(out[0],head*hd+start,self.add(self.mul(lo,co),self.mul(hi,self.kernel('neg',x=si))))
                    self.store.write(out[0],head*hd+half+start,self.add(self.mul(hi,co),self.mul(lo,si)))
        elif name=='KV_WRITE':
            tag=self.memory.begin(a['layer'],a['die'],int(self.scalar(reads[2])))
            for kind,v in [('K',reads[0]),('V',reads[1])]:
                base=extent(self.p,a['die'],f"L{a['layer']}.{kind}")['base']
                for head in range(kv):
                    for dim in range(0,hd,128):
                        n=min(128,hd-dim); codes=self.kernel('fp8pack',x=self.store.read(v,head*hd+dim,n))
                        dims=np.arange(dim,dim+n)
                        addr=base+((head*(self.p['context_capacity']//16)+self.position//16)*hd+dims)*16+self.position%16 if kind=='K' else base+(head*self.p['context_capacity']+self.position)*hd+dims
                        self.memory.write(tag,addr,codes)
            self.store.publish(out[0],tag)
        elif name=='KV_FENCE': self.store.publish(out[0],self.memory.commit(self.scalar(reads[0])))
        elif name=='KV_READ':
            lease=self.memory.acquire(self.scalar(reads[0]),a['layer'],a['die'],int(self.scalar(reads[1])))
            for kind,v in zip(('K','V'),out):
                base=extent(self.p,a['die'],f"L{a['layer']}.{kind}")['base']; size=kv*T*hd
                for start in range(0,size,128):
                    words=np.arange(start,min(size,start+128)); heads=words//(T*hd); positions=(words//hd)%T; dims=words%hd
                    addresses=base+((heads*(self.p['context_capacity']//16)+positions//16)*hd+dims)*16+positions%16 if kind=='K' else base+(heads*self.p['context_capacity']+positions)*hd+dims
                    values=self.kernel('fp8unpack',x=self.memory.read(lease,addresses)); self.store.write(v,start,values)
                self.kv_leases[v]=lease
        elif name=='SCORES':
            for head in range(nh):
                group=head//a['head_groups']
                def weights(r,n,kk):
                    data=np.empty((n,len(kk)),F)
                    for j,k in enumerate(kk): data[:,j]=self.store.read_indices(reads[1],group*T*hd+(np.arange(r,r+n)*hd)+k)
                    return data
                # Tree commits source-unscaled dot; postscale has its own round.
                self.dot(T,hd,a['split'],lambda indexes:self.store.read_indices(reads[0],head*hd+np.asarray(indexes)),weights,out[0],head*T,True)
                for start in range(0,T,128):
                    n=min(128,T-start)
                    self.store.write(out[0],head*T+start,self.mul(self.store.read_unpublished(out[0],head*T+start,n),F(1/np.sqrt(hd))))
            self.memory.done(self.kv_leases.pop(reads[1]),'SCORES')
        elif name=='EXP_SUM':
            for head in range(nh):
                maximum=self.store.read(reads[0],head*T,1)[0]
                for start in range(1,T,128):
                    for value in self.store.read(reads[0],head*T+start,min(128,T-start)): maximum=self.kernel('maximum',a=maximum,b=value)
                negative=self.kernel('neg',x=maximum); self.stack=[]; chunks=0; leaves=1<<(((T+7)//8)-1).bit_length()
                for start in range(0,T,128):
                    x=self.store.read(reads[0],head*T+start,min(128,T-start)); exps=self.kernel('exp',x=self.add(x,negative))
                    self.store.write(out[0],head*T+start,self.kernel('bf16',x=exps)); self.counters['BF16_pack_windows']+=1
                    for g in range(0,len(exps),8):
                        total=F(0)
                        for value in exps[g:g+8]: total=self.add(total,value)
                        self.push(total); chunks+=1
                for _ in range(chunks,leaves): self.push(F(0))
                self.store.write(out[1],head,self.root())
        elif name=='PV':
            for head in range(nh):
                group=head//a['head_groups']
                def weights(r,n,kk):
                    data=np.empty((n,len(kk)),F)
                    for j,k in enumerate(kk): data[:,j]=self.store.read(reads[1],(group*T+k)*hd+r,n)
                    return data
                self.dot(hd,T,a['split'],lambda indexes:self.store.read_indices(reads[0],head*T+np.asarray(indexes)),weights,out[0],head*hd)
            self.memory.done(self.kv_leases.pop(reads[1]),'PV')
        elif name=='NORMALIZE':
            for head in range(nh):
                inv=self.kernel('reciprocal',x=self.store.read(reads[1],head,1)[0])
                for start in range(0,hd,128):
                    n=min(128,hd-start); self.store.write(out[0],head*hd+start,self.mul(self.store.read(reads[0],head*hd+start,n),inv))
        elif name=='SILU_GATE':
            size=c['intermediate_size']//2
            for start in range(0,size,128):
                n=min(128,size-start); gate=self.store.read(reads[0],start,n); up=self.store.read(reads[0],size+start,n)
                ex=self.kernel('exp',x=self.kernel('neg',x=gate)); inverse=self.kernel('reciprocal',x=self.add(ex,F(1)))
                self.store.write(out[0],start,self.mul(self.mul(gate,inverse),up))
        elif name=='ARGMAX':
            size=math.prod(self.store.shapes[reads[0]][0]); best=self.store.read(reads[0],0,1)[0]; index=a['global_row_offset']
            for start in range(1,size,128):
                for j,value in enumerate(self.store.read(reads[0],start,min(128,size-start))):
                    if bool(self.kernel('argmax',candidate=value,best=best)): best=value; index=start+j+a['global_row_offset']
            bits=np.array([np.asarray(best,F).view(np.uint32),index],np.uint32); self.store.write(out[0],0,bits)
        elif name=='ARGMAX_REDUCE':
            left=self.store.read(reads[0],0,2); right=self.store.read(reads[1],0,2)
            win=bool(self.kernel('winner',a=left[:1].view(F)[0],b=right[:1].view(F)[0],ai=left[1],bi=right[1]))
            self.store.write(out[0],0,np.array([right[1] if win else left[1]],np.uint32))
        else: raise ValueError('unsupported tiled semantics '+name)
        for v in out:
            if v not in self.store.published: self.store.publish(v)
    def run(self,token,position,observer=None):
        if self.store.live: raise ValueError('unretired token')
        if not 0<=token<self.p['config']['vocab_size'] or not 0<=position<self.p['context_capacity']: raise ValueError('runtime aperture')
        self.position=position; self.done=set(); result=None
        for v in self.native['operands']:
            if v['birth_pc']==-1:
                self.store.reserve(v['version'],position,'U32'); self.store.write(v['version'],0,np.array([token if v['name']=='token' else position],np.uint32)); self.store.publish(v['version'])
        for op in self.native['operations']:
            if not set(op['dependencies'])<=self.done: raise ValueError('unretired dependency')
            if not set(op['reads'])<=self.store.published: raise ValueError('unpublished operand')
            self.execute(op)
            if op['opcode']=='ARGMAX_REDUCE': result=int(self.scalar(op['writes'][0]))
            if observer: observer(op,self.store)
            self.store.retire(op['pc']); self.done.add(op['pc'])
        if self.store.live or self.store.pages or self.kv_leases or self.memory.leases or self.memory.pending: raise ValueError('unretired tiled state')
        return dict(status='PASS_BOUNDED_TILED_SOFTWARE',next_token=result,PCs=len(self.done),RF_workspace_peak_vectors=self.vm.peak_vectors,
                    shared_tile_peak_bytes=self.peak_shared,primitive_counts=dict(self.vm.counts),primitive_word_counts=dict(self.vm.word_counts),
                    transfer_counts=dict(self.store.counters),tile_counts=dict(self.counters),KV_state_transfer_counts=dict(self.memory.counters),temporary_HBM_bytes=0,hardware_or_timing_credit=False)


def _read_unpublished(self,version,start,count):
    # Produced dot capture, not a forward source operand: same command lease.
    existed=version in self.published; self.published.add(version)
    try: return self.read(version,start,count)
    finally:
        if not existed: self.published.remove(version)
TileWords.read_unpublished=_read_unpublished



ADDRESSED_OUT=ROOT/OUT/'addressed_r21'


@lru_cache(maxsize=1)
def addressed_provider_module():
    import types,sys
    path=ADDRESSED_OUT/'hbm_provider_microvm_r21.py.source'
    source=path.read_bytes()
    if hashlib.sha256(source).hexdigest()!='3c4de52c72793911428133536da3eced170c63088fccf7ac02b56657e9f277c2': raise ValueError('Kepler provider source pin')
    module=types.ModuleType('Qwen_pinned_Kepler_r21');sys.modules[module.__name__]=module
    exec(compile(source,str(path),'exec'),module.__dict__); return module


def addressed_sector_provider(extents):
    module=addressed_provider_module(); provider=module.SectorProvider(extents,tags=4,queue=64,write_residence=4)
    provider.phase_counts=Counter(); provider.peak_live=0; original=provider.log
    def log(event,t,**kw):
        original(event,t,**kw); provider.phase_counts[event]+=1; provider.peak_live=max(provider.peak_live,len(provider.live))
        row=provider.events[-1]
        if t.identity.target.startswith('Qwen.RF'):
            row.pop('stack',None);row.pop('local_sector31',None)
            byte=t.identity.sector*32;logical=byte%16384;slot=logical//512
            row['RF']={'workspace_slot':slot,'page':slot>>7,'row':slot&127,'bank':logical%512//32,'mirror':byte//16384}
        # Bounded trace ring; cumulative counters retain complete event coverage.
        if len(provider.events)>64: del provider.events[:-64]
    provider.log=log; return provider


class AddressedPrimitiveVM(NativePrimitiveVM):
    """Execute every native leaf; validate every I64 capture through r21 codec.

    The codec lives in two reserved RF workspace vectors22/23 with both mirrors,
    never the historical unbounded HBM native arena. Split/join/RMW diagnostics
    consume actual addressed bytes and grants, but are NOT added to Dewey's
    already charged highword/RMW intervals.
    """
    def __init__(self,provider):
        super().__init__(); module=addressed_provider_module(); self.provider=provider
        self.codec=module.Storage(provider,'Qwen.RFworkspace.SM0',0,0,32768)
        self.codec_captures=0
    def primitive(self,op,args,attrs=None,shape=None):
        value=super().primitive(op,args,attrs,shape)
        if value.dtype!=np.int64 or not value.size: return value
        module=addressed_provider_module(); flat=value.reshape(-1); self.codec.pc=self.current_pc or 0
        tensors=[module.Tensor('Qwen.RFworkspace.SM0',0,22*512+mirror*16384,(flat.size,),'I64',23*512+mirror*16384) for mirror in range(2)]
        for t in tensors: self.codec.write(t,0,flat)
        results=[self.codec.read(t,np.arange(flat.size)) for t in tensors]
        if not np.array_equal(results[0],results[1]) or not np.array_equal(results[0],flat): raise ValueError('addressed I64 mirror/capture mismatch')
        self.codec_captures+=1
        if self.codec.codec_leases or self.codec.codec_locks or self.provider.live: raise ValueError('addressed codec lease retained')
        # Codec traces are also bounded; codec_versions has exactly256 entries.
        if len(self.codec.codec_events)>64: del self.codec.codec_events[:-64]
        return results[0].reshape(value.shape)


class AddressedTileWords(TileWords):
    def __init__(self,native,provider):
        super().__init__(native);self.provider=provider;self.pc=0;self.addressed_cache=None
        module=addressed_provider_module();self.storage={}
        for allocation in native['provider_binding']['allocation']:
            rank=allocation['rank'];e=next(e for e in allocation['extents'] if e['name']=='activation_scratch')
            self.storage[rank]=module.Storage(provider,'Qwen',rank,e['base'],e['bytes'])
    def tensor(self,key):
        module=addressed_provider_module()
        return module.Tensor('Qwen',key[1],key[3],(128,),'U32')
    def write(self,version,start,values):
        super().write(version,start,values);self.addressed_cache=None
        touched=set()
        for rank in sorted({h['rank'] for h in self.values[version]['homes']}):
            for word in range(start,start+np.size(values)): touched.add(self.key(version,word,rank)[0])
        for key in touched:
            if key[0]!='HBM':continue
            storage=self.storage[key[1]];storage.pc=self.pc
            storage.write(self.tensor(key),0,self.pages[key][0])
    def read_indices(self,version,indices):
        value=super().read_indices(version,indices);kind=self.shapes[version][1]
        bits=value if kind in ('U32','winner') else value.view(np.uint32);bits=bits.copy();rank=self.rank(version)
        for i,word in enumerate(np.asarray(indices).reshape(-1)):
            key,lane=self.key(version,int(word),rank)
            if key[0]!='HBM':continue
            if self.addressed_cache is None or self.addressed_cache[0]!=key:
                storage=self.storage[rank];storage.pc=self.pc
                self.addressed_cache=(key,storage.read(self.tensor(key),np.arange(128)))
            bits[i]=self.addressed_cache[1][lane]
        return bits if kind in ('U32','winner') else bits.view(F)
    def retire(self,pc): super().retire(pc);self.addressed_cache=None


class AddressedKVStorage(BoundKVStorage):
    def __init__(self,p,provider):
        super().__init__(p);self.provider=provider;module=addressed_provider_module();self.addressed={}
        for rank,e in self.state.items():
            provider.seed('Qwen',rank,e['base'],bytes(e['bytes']))
            self.addressed[rank]=module.Storage(provider,'Qwen',rank,e['base'],e['bytes'])
    def state_tensor(self,rank):
        m=addressed_provider_module();e=self.state[rank];return m.Tensor('Qwen',rank,e['base'],(e['bytes'],),'U8')
    def state_write(self,rank,offset,data):
        super().state_write(rank,offset,data);s=self.addressed[rank];s.pc=self.pc
        s.write(self.state_tensor(rank),offset,np.frombuffer(data,np.uint8))
    def state_read(self,rank,offset,count):
        super().state_read(rank,offset,count);s=self.addressed[rank];s.pc=self.pc
        return s.read(self.state_tensor(rank),np.arange(offset,offset+count)).tobytes()
    def commit(self,tag):
        state=self.pending[int(tag)];layer,rank,_=state['key'];module=addressed_provider_module()
        for address,code in state['payload'].items():
            kind,_=self.decode_address(layer,rank,address);e=extent(self.p,rank,f'L{layer}.{kind}')
            s=module.Storage(self.provider,'Qwen',rank,e['base'],e['bytes']);s.pc=self.pc
            s.write(module.Tensor('Qwen',rank,e['base'],(e['bytes'],),'U8'),address-e['base'],np.array([code],np.uint8))
        return super().commit(tag)
    def read(self,lease,addresses):
        expected=super().read(lease,addresses);layer,rank,_=self.leases[lease]['key'];module=addressed_provider_module();values=[]
        for address in np.asarray(addresses).flat:
            kind,_=self.decode_address(layer,rank,int(address));e=extent(self.p,rank,f'L{layer}.{kind}')
            s=module.Storage(self.provider,'Qwen',rank,e['base'],e['bytes']);s.pc=self.pc
            values.append(s.read(module.Tensor('Qwen',rank,e['base'],(e['bytes'],),'U8'),[int(address)-e['base']])[0])
        result=np.asarray(values,np.uint8).reshape(np.shape(addresses))
        if not np.array_equal(result,expected):raise ValueError('addressed KV backing mismatch')
        return result


class AddressedTiledMachine(TiledMachine):
    def __init__(self,native,weights=None):
        super().__init__(native,weights);extents={('Qwen',a['rank']):a['extents'] for a in native['provider_binding']['allocation']}
        extents['Qwen.RFworkspace.SM0',0]=[dict(base=0,bytes=32768)]
        self.sectors=addressed_sector_provider(extents)
        self.store=AddressedTileWords(native,self.sectors);self.memory=AddressedKVStorage(self.p,self.sectors)
        self.vm=AddressedPrimitiveVM(self.sectors)
    def execute(self,op):
        self.store.pc=op['pc'];self.vm.current_pc=op['pc'];return super().execute(op)
    def run(self,token,position,observer=None):
        result=super().run(token,position,observer)
        if self.sectors.live or self.sectors.queue or self.sectors.calendar or self.sectors.resident:raise ValueError('addressed provider not drained')
        result['addressed_provider']=dict(commit='42f0a41',phase_counts=dict(self.sectors.phase_counts),
            peak_owner_credits=self.sectors.peak_live,I64_codec_captures=self.vm.codec_captures,
            RF_codec_slots=[22,23],RF_codec_mirrors=2,trace_ring_entries=len(self.sectors.events),
            extra_native_HBM_bytes=0,software_diagnostic_ticks=self.sectors.now,
            diagnostic_ticks_added_to_existing_intervals=False,r22_augmentation_applied=False,
            existing_highword_RMW_charges_preserved=True,hardware_or_timing_credit=False)
        return result


def compile_addressed_native(program=None):
    native=compile_tiled(program)
    if program is not None and len(native['operations'])==1737:
        provider,pin=load_provider_binding()
        join_provider_homes({v['version']:v for v in native['operands']},provider)
        native['provider_binding']=provider;native['provider_binding_pin']=pin
        for a in provider['allocation']:
            native['source_program']['memory_allocation'][a['rank']]['extents']=a['extents']
            native['source_program']['memory_allocation'][a['rank']]['allocated_bytes']=a['global_allocated_end_bytes']
        for op,bound in zip(native['operations'],provider['operations']):
            op['provider_binding']=bound
            op['calendar_export']['source_provider_operation']=bound
            op['calendar_export']['provider_resource_contract']=provider['resource_contract']
        native['fixture_scope']='reduced source shapes and raw parameter fixtures placed into actual r17 maxshape homes/extents; no full checkpoint equivalence claim'
    native['addressed_provider_ABI']=dict(commit='42f0a41',module_sha256='3c4de52c72793911428133536da3eced170c63088fccf7ac02b56657e9f277c2',
        executable='AddressedTiledMachine',source_HBM='actual r17 homes; addressed sector backing/ACK/reverse grants',
        I64='split low/high RF workspace slots22/23 with two actual mirrors; no native HBM arena',
        calendar_reconcile='Existing Dewey I64_highword_read/join/split/RMW/read/merge/write_visible costs already charged. Do not call r22 augment again or add diagnostic provider ticks.',
        r22_augmentation_applied=False)
    return native

def tiled_cli(args):
    out=args.out/('addressed_r21_r2' if args.addressed else 'bounded_r2')
    if args.exercise:
        config=dict(hidden_size=8,head_dim=4,num_attention_heads=2,num_key_value_heads=2,
                    intermediate_size=16,vocab_size=16,num_hidden_layers=36,rms_norm_eps=1e-6,rope_theta=1000000)
        native=(compile_addressed_native if args.addressed else compile_tiled)(compile_program(config,context=32,groups=16)); machine=(AddressedTiledMachine if args.addressed else TiledMachine)(native)
        runs=[]; token=3
        for position in range(2):
            result=machine.run(token,position); runs.append(result); token=result['next_token']
        print(canonical(dict(schema='opentallas.H3.qwen-bounded-software-replay.v1',config=config,
            executions=runs,source_homes_retired=not machine.store.owners,KV_leases_retired=not machine.memory.leases,
            oracle_callbacks=0,full_checkpoint_numerical_execution=False,
            fixture_scope=native.get('fixture_scope','reduced shapes in identical distributed allocator; full compiler separately binds actual r17 homes'),
            provider_binding_pin=native['provider_binding_pin'],
            hardware_or_timing_credit=False)).decode(),end=''); return
    native=(compile_addressed_native if args.addressed else compile_tiled)(); data=canonical(native); artifact=out/'Qwen_tiled.json.gz'
    if args.verify:
        manifest=json.loads((out/'manifest.json').read_text())
        for path,digest in manifest['source_sha256'].items():
            if hashlib.sha256((ROOT/path).read_bytes()).hexdigest()!=digest: raise ValueError('tiled source pin mismatch '+path)
        if hashlib.sha256(artifact.read_bytes()).hexdigest()!=manifest['artifact_sha256']: raise ValueError('tiled artifact pin mismatch')
        with gzip.open(artifact,'rb') as f:
            if f.read()!=data: raise ValueError('tiled compiler replay mismatch')
        print(json.dumps(dict(status='PASS_EXACT_BOUNDED_COMPILER_REPLAY',**native['coverage']))); return
    out.mkdir(parents=True,exist_ok=True)
    with artifact.open('xb') as raw:
        with gzip.GzipFile(fileobj=raw,mode='wb',mtime=0) as stream: stream.write(data)
    pins=['tools/h3_qwen_bounded_native.py','tests/test_h3_qwen_bounded_native.py',
          'tools/h3_qwen_complete_native.py','tests/test_h3_qwen_complete_native.py',INPUT,
          'tools/qwen_hbm_complete_program.py','tools/h3_versioned_lowering.py',
          'tools/h3_distributed_norm_endpoint.py',
          OUT+'/tiled_r1/Peirce_native_76d564c9a.py.source']
    if args.addressed: pins.append(OUT+'/addressed_r21/hbm_provider_microvm_r21.py.source')
    suffix=' --addressed' if args.addressed else ''
    manifest=dict(schema=native['schema'],coverage=native['coverage'],provider_binding_pin=native['provider_binding_pin'],
        artifact_sha256=hashlib.sha256(artifact.read_bytes()).hexdigest(),
        source_sha256={path:hashlib.sha256((ROOT/path).read_bytes()).hexdigest() for path in pins},
        replay='python tools/h3_qwen_bounded_native.py'+suffix+' --verify',
        exercise='python tools/h3_qwen_bounded_native.py'+suffix+' --exercise',
        tests='python -m pytest -q tests/test_h3_qwen_bounded_native.py',hardware_or_timing_credit=False)
    (out/'manifest.json').write_bytes(canonical(manifest))
    (out/'common_native_ABI.json').write_bytes(canonical(native['primitive_ABI']))
    # Unit service values are explicit provisional software parameters, not cycles.
    calendar=materialize_tile_calendar(native,{name:1 for name in TILE_COSTS})
    with (out/'Qwen_serial_calendar.json.gz').open('xb') as raw:
        with gzip.GzipFile(fileobj=raw,mode='wb',mtime=0) as stream: stream.write(canonical(calendar))
    print(json.dumps(native['coverage']))


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out',type=Path,default=ROOT/OUT)
    ap.add_argument('--tiled',action='store_true',help='Compatibility alias; this entrypoint always uses bounded lowering')
    ap.add_argument('--addressed',action='store_true',help='Use pinned Kepler r21 addressed sector/split64 software execution; never augment existing costs twice')
    ap.add_argument('--verify',action='store_true')
    ap.add_argument('--exercise',action='store_true',help='Run reduced36-layer fixture twice, source homes/providers bound and all PC/native steps executed')
    return tiled_cli(ap.parse_args())


if __name__=='__main__': main()

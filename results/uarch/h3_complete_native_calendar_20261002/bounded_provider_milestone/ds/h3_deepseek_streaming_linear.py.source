#!/usr/bin/env python3
"""Forward streaming regular DS Q8-weight matvec, source chunk8/tree unchanged.

K blocks are32 and row tiles128. The activation is quantized once, stored as
finite software-provider blocks, then reused. Each weight block is decoded once
per output row, not scalar demand-recomputed. No golden numerical call executes.
"""
from collections import Counter
import math
import numpy as np
import h3_deepseek_complete_native as N

K_BLOCK=32;ROW_TILE=128


def quant_program():
    b=N.Builder();x=b.load('x',(32,));_,q,ex=b.codec(x,'FP8')
    b.output('units',b.reshape(b.op('F2I',b.op('FMUL',q,b.const(512.))),(32,)))
    b.output('exponent',b.reshape(ex,()))
    return b.finish()


def block_program(rows,fmt):
    b=N.Builder();q=b.load('units',(32,),'I64');ex=b.load('exponent',(),'U32')
    raw=b.load('weight_codes',(rows,16 if fmt=='fp4' else 32),'U32');scale=b.load('weight_scale_codes',(rows,1),'U32')
    b.emit('ASSERT',b.op('FCMP_LT',scale,b.const(255,'U32')),shape=(rows,1),reason='finite weight exponent codes')
    if fmt=='fp4':
        lo=b.op('AND',raw,b.const(15,'U32'));hi=b.op('SHR',raw,b.const(4,'U32'));ids=b.reshape(b.stack([lo,hi],2),(rows,32))
        table=b.const([0,256,512,768,1024,1536,2048,3072,0,-256,-512,-768,-1024,-1536,-2048,-3072],'I64')
    elif fmt=='fp8':
        ids=raw;b.emit('ASSERT',b.op('FCMP_LT',b.op('AND',ids,b.const(127,'U32')),b.const(127,'U32')),shape=(rows,32),reason='finite weight E4M3 codes')
        values=[int(v*512) for v in N.positive_codes(True)]+[0];table=b.const(values+[-v for v in values],'I64')
    else:raise ValueError('source weight format')
    w=b.reshape(b.take(table,ids),(rows,1,32));q=b.reshape(q,(1,1,32));acc=N.integer_sum(b,b.op('IMUL',w,q))
    power=b.op('ISUB',b.op('IADD',b.op('ISUB',scale,b.const(127,'I64')),ex),b.const(18,'I64'))
    block=b.reshape(b.op('LDEXP',b.op('I2F',acc),power),(rows,));b.output('block',block)
    return b.finish()


def add_program(rows):
    b=N.Builder();b.output('out',b.op('FADD',b.load('a',(rows,)),b.load('b',(rows,))));return b.finish()


def pack_program(rows):
    b=N.Builder();b.output('out',b.bf16(b.load('x',(rows,))));return b.finish()


def footprint(program):
    last={};width={};sizes={};live={};peak=0
    for pc,i in enumerate(program['code']):
        for v in i['src']:last[v]=pc
    for v in program['outputs'].values():last[v]=len(program['code'])
    for pc,i in enumerate(program['code']):
        for v in list(live):
            if last.get(v,-1)<pc:del live[v]
        op=i['op']
        if op in ('LOAD','CONST'):w=8 if i['attrs']['dtype']=='I64' else 4
        elif op=='F2I':w=8
        elif op in ('I2F','FADD','FMUL','DIV','SQRT','LDEXP','BITCAST_U','BITCAST_F') or op.startswith('FCMP'):w=4
        else:w=max((width[v] for v in i['src']),default=8 if op=='IOTA' else 4)
        width[i['dst']]=w;sizes[i['dst']]=max(1,math.prod(i['shape']))*w;live[i['dst']]=sizes[i['dst']];peak=max(peak,sum(live.values()))
    # Native VM value/r copies and returned arrays; conservative transient reserve.
    return {'typed_live_bytes':peak,'transient_and_output_reserve_bytes':2*max(sizes.values())+2*sum(sizes[v] for v in program['outputs'].values()),
            'scalar_evaluations_by_opcode':dict(Counter({op:sum(max(1,math.prod(i['shape'])) for i in program['code'] if i['op']==op) for op in {i['op'] for i in program['code']}}))}


def model(rows,k,fmt='fp8'):
    if type(rows) is not int or rows<1 or type(k) is not int or k<32 or k%32:raise ValueError('source fullK multiple32')
    blocks=k//32;chunks=(blocks+7)//8;padded=1<<(chunks-1).bit_length();levels=padded.bit_length()
    q=footprint(quant_program());m=footprint(block_program(min(rows,ROW_TILE),fmt))
    regular_bytes=max(q['typed_live_bytes']+q['transient_and_output_reserve_bytes'],m['typed_live_bytes']+m['transient_and_output_reserve_bytes'])+ROW_TILE*4*(levels+4)
    if regular_bytes>1048576:raise ValueError('reserved1MiB perSM live-range workspace cap')
    counts=Counter({op:n*blocks for op,n in q['scalar_evaluations_by_opcode'].items()})
    full,tail=divmod(rows,ROW_TILE)
    for tile_rows,repeats in [(ROW_TILE,full),(tail,int(tail>0))]:
        if not repeats:continue
        for op,n in footprint(block_program(tile_rows,fmt))['scalar_evaluations_by_opcode'].items():counts[op]+=n*blocks*repeats
        for op,n in footprint(add_program(tile_rows))['scalar_evaluations_by_opcode'].items():counts[op]+=n*(chunks*8+padded-1)*repeats
        for op,n in footprint(pack_program(tile_rows))['scalar_evaluations_by_opcode'].items():counts[op]+=n*repeats
    return {'rows':rows,'fullK':k,'weight_format':fmt,'Kblock':32,'row_tile':128,'blocks':blocks,'chunks8':chunks,'tree_padded_chunks':padded,
            'typed_live_workspace_upper_bytes_per_SM':regular_bytes,'reserved_workspace_bytes_per_SM':1048576,
            'quantized_input_provider_bytes_per_rank':blocks*260,'input_quantization_calls':blocks,'weight_decode_rows_blocks':rows*blocks,
            'floating_block_reduction_FADD':rows*(chunks*8+padded-1),'integer_products':rows*k,'integer_block_IADD':rows*blocks*31,
            'opcode_scalar_evaluations':dict(counts),'cross_row_requantization':0,'scalar_dependency_recomputations':0,
            'logical_provider_commands_upper':blocks*2+((rows+127)//128)*blocks+rows*blocks*2+((rows+127)//128),
            'provider_MAX_fragment':512,'selected_read_credit':1,'selected_write_credit':1,'transfer_costs_required':True,
            'latency_cycles':None,'hardware_admitted':False,'source_order':'quantize32 independently; exact integer32 dot; I2F once; LDEXP; chunk8 sequential from+0; padded left/right pairwise tree; BF16 once at final output'}


class StreamingLinear:
    def __init__(self,owner):
        if len(owner)!=5:raise ValueError('PC/version/rank/SM/generation required')
        self.owner=tuple(owner);self.memory=N.PersistentMemory(credits=1);self.counts=Counter();self.kernel_calls=Counter();self.read_bytes=0;self.write_bytes=0;self.fault=False
    def read(self,key,array):
        raw=np.asarray(array).tobytes()
        # Each source fragment is accepted independently, not a fullweight preload.
        chunks=[]
        for off in range(0,len(raw),512):
            sub=(*key,off)
            if sub not in self.memory.values:self.memory.preload(sub,raw[off:off+512])
            chunks.append(self.memory.transact(sub));self.read_bytes+=len(chunks[-1])
        return np.frombuffer(b''.join(chunks),dtype=array.dtype).copy().reshape(array.shape)
    def execute(self,p,inputs,kind):
        vm=N.Machine(p,inputs,N.primitive_div);out=vm.run();self.fault|=vm.fault;self.kernel_calls[kind]+=1
        for i in p['code']:self.counts[i['op']]+=max(1,math.prod(i['shape']))
        return out
    def run(self,x,codes,scales,fmt='fp8'):
        x=np.asarray(x,np.float32);codes=np.asarray(codes,np.uint32);scales=np.asarray(scales,np.uint32)
        rows= codes.shape[0];k=x.size;plan=model(rows,k,fmt);blocks=k//32
        if x.shape!=(k,) or codes.shape!=(rows,k//2 if fmt=='fp4' else k) or scales.shape!=(rows,blocks):raise ValueError('source linear geometry')
        self.memory.fence();qprog=quant_program()
        for b in range(blocks):
            xb=self.read(('x',*self.owner,b),x[32*b:32*b+32]);q=self.execute(qprog,{'x':xb},'quantize32')
            raw=q['units'].tobytes()+np.asarray(q['exponent'],np.uint32).tobytes()
            self.memory.transact(('Q8block',*self.owner,b),write=True,payload=raw);self.write_bytes+=len(raw)
        observed=[]
        for first in range(0,rows,ROW_TILE):
            nr=min(ROW_TILE,rows-first);bp=block_program(nr,fmt);ap=add_program(nr);pp=pack_program(nr);pending=np.zeros(nr,np.float32);carry={};chunk=0
            def add(a,b):return self.execute(ap,{'a':a,'b':b},'FADD128')['out']
            def push(value):
                level=0
                while level in carry:value=add(carry.pop(level),value);level+=1
                carry[level]=value
            for b in range(blocks):
                raw=self.memory.transact(('Q8block',*self.owner,b));self.read_bytes+=len(raw);units=np.frombuffer(raw,np.int64,count=32).copy();exp=np.frombuffer(raw,np.uint32,count=1,offset=256).copy().reshape(())
                width=16 if fmt=='fp4' else 32;wc=[];ws=[]
                for row in range(first,first+nr):
                    wc.append(self.read(('weight',*self.owner,row,b),codes[row,b*width:(b+1)*width]));ws.append(self.read(('scale',*self.owner,row,b),scales[row,b:b+1]))
                value=self.execute(bp,{'units':units,'exponent':exp,'weight_codes':np.stack(wc),'weight_scale_codes':np.stack(ws)},'dot32')['block']
                pending=add(pending,value)
                if b%8==7:push(pending);pending=np.zeros(nr,np.float32);chunk+=1
            if blocks%8:
                for _ in range(8-blocks%8):pending=add(pending,np.zeros(nr,np.float32))
                push(pending);chunk+=1
            while chunk<plan['tree_padded_chunks']:push(np.zeros(nr,np.float32));chunk+=1
            if len(carry)!=1:raise AssertionError('closed golden tree')
            out=self.execute(pp,{'x':next(iter(carry.values()))},'BF16_final')['out'];observed.extend(out)
            # Produced bytes may be staged; no complete-version publication until
            # every row validates. Accepted writes are drained even after fault.
            raw=out.tobytes()
            for off in range(0,len(raw),512):self.memory.transact(('output_staging',*self.owner,first,off),write=True,payload=raw[off:off+512]);self.write_bytes+=len(raw[off:off+512])
        self.memory.fence()
        status='FAULT_NO_VERSION_PUBLICATION' if self.fault else 'PASS_FORWARD_STREAMING_NATIVE_LINEAR'
        return (None if self.fault else np.asarray(observed,np.float32)),{'status':status,'plan':plan,'executed_primitive_scalars':dict(self.counts),'kernel_calls':dict(self.kernel_calls),'recomputed_dependency_scalars':0,'read_bytes':self.read_bytes,'write_bytes':self.write_bytes,'provider':self.memory.summary(),'logical_complete_version_published':not self.fault,'physical_visibility_qualified':False}


def unpack_units(b,name,count,width):
    raw=b.load(name+'_codes',(count,width//2),'U32');lo=b.op('AND',raw,b.const(15,'U32'));hi=b.op('SHR',raw,b.const(4,'U32'))
    ids=b.reshape(b.stack([lo,hi],2),(count,width));table=b.const([0,1,2,3,4,6,8,12,0,-1,-2,-3,-4,-6,-8,-12],'I64')
    return b.reshape(b.take(table,ids),(count,width//32,32))


def decoded_assert(b,units,exp,source,shape):
    decoded=b.reshape(b.bf16(b.op('LDEXP',b.op('FMUL',b.op('I2F',units),b.const(.5)),b.reshape(exp,b.shapes[exp]+(1,)))),shape)
    b.emit('ASSERT',b.op('FCMP_EQ',source,decoded),shape=shape,reason='index integer units/exponent match produced BF16 operand')


def query_program(heads,width):
    b=N.Builder();q=b.load('iqf',(heads,width));exp=b.load('query_exp',(heads,width//32),'I64');units=unpack_units(b,'query',heads,width)
    decoded_assert(b,units,exp,q,(heads,width));b.output('units',units);b.output('exponent',exp);return b.finish()


def index_program(heads,width,rows,first,rank):
    b=N.Builder();blocks=width//32;qu=b.load('query_units',(heads,blocks,32),'I64');qe=b.load('query_exp',(heads,blocks),'I64');key=b.load('keys',(rows,width));ke=b.load('key_exp',(rows,blocks),'I64');ku=unpack_units(b,'key',rows,width)
    decoded_assert(b,ku,ke,key,(rows,width))
    prod=b.op('IMUL',b.reshape(qu,(heads,1,blocks,32)),b.reshape(ku,(1,rows,blocks,32)))
    power=b.op('ISUB',b.op('IADD',b.reshape(qe,(heads,1,blocks)),b.reshape(ke,(1,rows,blocks))),b.const(2,'I64'))
    dot=b.bf16(b.reduce(b.op('LDEXP',b.op('I2F',N.integer_sum(b,prod)),power)))
    terms=b.bf16(b.op('FMUL',b.op('FMAX',dot,b.const(0.)),b.reshape(b.load('iw',(heads,)),(heads,1))))
    b.output('is_v',b.bf16(b.reduce(b.transpose(terms,(1,0)))))
    row=b.op('IADD',b.iota(rows),b.const(first,'I64'));ids=b.op('IADD',b.op('IMUL',b.op('IADD',b.op('IMUL',b.op('SHR',row,b.const(3,'I64')),b.const(96,'I64')),b.const(rank,'I64')),b.const(8,'I64')),b.op('AND',row,b.const(7,'I64')))
    b.output('is_i',ids);return b.finish()


def index_model(rows,heads,width):
    p=index_program(heads,width,1,0,0);f=footprint(p);q=footprint(query_program(heads,width))
    # Retained query units/exponents/weights live through every key row.
    retained=heads*width*8+heads*(width//32)*8+heads*4
    live=max(f['typed_live_bytes']+f['transient_and_output_reserve_bytes']+retained,q['typed_live_bytes']+q['transient_and_output_reserve_bytes'])
    if live>1048576:raise ValueError('index row tile exceeds1MiB actual live-range reserve')
    counts=Counter(q['scalar_evaluations_by_opcode'])
    for op,n in f['scalar_evaluations_by_opcode'].items():counts[op]+=n*rows
    return {'rows':rows,'heads':heads,'fullK':width,'independent_key_row_tile':1,'typed_live_workspace_upper_bytes_per_SM':live,
            'opcode_scalar_evaluations':dict(counts),'integer_products':rows*heads*width,'retained_query_bytes':retained,
            'query_decode_repeats_explicit':1,'scalar_dependency_recomputations':0,'input_query_is_already_quantized':True,
            'rounding':'original index_scores packed-code exact integer32; singleI2F; blockchunk8; BF16score; max0; BF16weighted; headchunk8; BF16final',
            'row_identity':'((global_local_row>>3)*96+rank)*8+(global_local_row&7)',
            'latency_cycles':None,'hardware_admitted':False,'no_ideal_query_cache_or_overlap':True}


class StreamingIndex(StreamingLinear):
    def run_index(self,inputs,rank):
        heads,width=np.asarray(inputs['iqf']).shape;rows=np.asarray(inputs['keys']).shape[0];plan=index_model(rows,heads,width);scores=[];ids=[]
        self.memory.fence();qp=query_program(heads,width);query={name:self.read(('query_source',*self.owner,name),np.asarray(inputs[name])) for name in qp['providers']}
        q=self.execute(qp,query,'query_decode_once');iw=self.read(('query_weight',*self.owner),np.asarray(inputs['iw']))
        # Explicit software-producer write/read events, then retained lane/shared
        # query resident objects; no zero-cost repeated HBM query reload.
        for name,value in q.items():
            key=('retained_query',*self.owner,name);self.memory.write_object(key,value.tobytes());self.write_bytes+=value.nbytes
            raw=self.memory.read_object(key);self.read_bytes+=len(raw);q[name]=np.frombuffer(raw,dtype=value.dtype).copy().reshape(value.shape)
        for first in range(rows):
            p=index_program(heads,width,1,first,rank);tile={'query_units':q['units'],'query_exp':q['exponent'],'iw':iw}
            for name in ('keys','key_codes','key_exp'):tile[name]=self.read(('index_source',*self.owner,name,first),np.asarray(inputs[name])[first:first+1])
            out=self.execute(p,tile,'index_row');scores.extend(out['is_v']);ids.extend(out['is_i'])
            payload=out['is_v'].tobytes()+out['is_i'].tobytes();self.memory.transact(('index_output_staging',*self.owner,first),write=True,payload=payload);self.write_bytes+=len(payload)
        self.memory.fence()
        return ({} if self.fault else {'is_v':np.asarray(scores,np.float32),'is_i':np.asarray(ids,np.int64)}),{'status':'FAULT_NO_VERSION_PUBLICATION' if self.fault else 'PASS_FORWARD_STREAMING_NATIVE_INDEX','plan':plan,'executed_primitive_scalars':dict(self.counts),'kernel_calls':dict(self.kernel_calls),'recomputed_dependency_scalars':0,'provider':self.memory.summary(),'read_bytes':self.read_bytes,'write_bytes':self.write_bytes,'physical_visibility_qualified':False}


def float_block_program(rows):
    b=N.Builder();x=b.load('x',(8,));w=b.load('weight',(rows,8));prod=b.op('FMUL',w,b.reshape(x,(1,8)))
    b.output('block',b.reduce(prod));return b.finish()


def float_model(rows,k,round_output=False):
    chunks=(k+7)//8;padded=1<<(chunks-1).bit_length();f=footprint(float_block_program(min(rows,128)))
    counts=Counter({op:n*chunks for op,n in footprint(pack_program(8))['scalar_evaluations_by_opcode'].items()})
    full,tail=divmod(rows,128)
    for tile,repeats in [(128,full),(tail,int(tail>0))]:
        if not repeats:continue
        for op,n in footprint(float_block_program(tile))['scalar_evaluations_by_opcode'].items():counts[op]+=n*chunks*repeats
        for op,n in footprint(add_program(tile))['scalar_evaluations_by_opcode'].items():counts[op]+=n*(padded-1)*repeats
        if round_output:
            for op,n in footprint(pack_program(tile))['scalar_evaluations_by_opcode'].items():counts[op]+=n*repeats
    return {'rows':rows,'fullK':k,'Kchunk':8,'row_tile':128,'padded_tree_chunks':padded,'opcode_scalar_evaluations':dict(counts),
            'typed_live_workspace_upper_bytes_per_SM':f['typed_live_bytes']+f['transient_and_output_reserve_bytes']+128*4*(padded.bit_length()+4),
            'round_output_BF16':round_output,'FADD_reduction_scalars':rows*(chunks*8+padded-1),'FMUL_scalars_including_finite_zero_pad':rows*chunks*8,
            'cross_row_input_BF16_reconversion':0,'scalar_dependency_recomputations':0,'latency_cycles':None,'hardware_admitted':False,
            'source_order':'BF16input once; separateF32products; chunk8from+0; original padded left/right tree; preserve unrounded MV/WO and BF16 only linear_bf16'}


class StreamingFloat(StreamingLinear):
    def run_float(self,x,weight,round_output=False):
        x=np.asarray(x,np.float32);weight=np.asarray(weight,np.float32);rows,k=weight.shape
        if x.shape!=(k,):raise ValueError('fullK floating shape')
        plan=float_model(rows,k,round_output);chunks=(k+7)//8;self.memory.fence()
        for c in range(chunks):
            xb=np.zeros(8,np.float32);valid=min(8,k-8*c);xb[:valid]=self.read(('float_x',*self.owner,c),x[8*c:8*c+valid])
            xb=self.execute(pack_program(8),{'x':xb},'BF16_input8')['out'];self.memory.transact(('BF16chunk',*self.owner,c),write=True,payload=xb.tobytes());self.write_bytes+=32
        observed=[]
        for first in range(0,rows,128):
            nr=min(128,rows-first);bp=float_block_program(nr);ap=add_program(nr);carry={}
            def add(a,b):return self.execute(ap,{'a':a,'b':b},'FADD128')['out']
            def push(value):
                level=0
                while level in carry:value=add(carry.pop(level),value);level+=1
                carry[level]=value
            for c in range(chunks):
                raw=self.memory.transact(('BF16chunk',*self.owner,c));self.read_bytes+=len(raw);xb=np.frombuffer(raw,np.float32).copy();w=np.zeros((nr,8),np.float32);valid=min(8,k-8*c)
                for row in range(nr):w[row,:valid]=self.read(('float_weight',*self.owner,first+row,c),weight[first+row,8*c:8*c+valid])
                push(self.execute(bp,{'x':xb,'weight':w},'float_dot8')['block'])
            for _ in range(chunks,plan['padded_tree_chunks']):push(np.zeros(nr,np.float32))
            out=next(iter(carry.values()))
            if round_output:out=self.execute(pack_program(nr),{'x':out},'BF16_final')['out']
            observed.extend(out);raw=out.tobytes();self.memory.transact(('float_output_staging',*self.owner,first),write=True,payload=raw);self.write_bytes+=len(raw)
        self.memory.fence()
        return (None if self.fault else np.asarray(observed,np.float32)),{'status':'FAULT_NO_VERSION_PUBLICATION' if self.fault else 'PASS_FORWARD_STREAMING_NATIVE_FLOAT','plan':plan,'executed_primitive_scalars':dict(self.counts),'recomputed_dependency_scalars':0,'provider':self.memory.summary(),'read_bytes':self.read_bytes,'write_bytes':self.write_bytes,'physical_visibility_qualified':False}


def gather_model(ranks,n):
    counts=Counter();peak=0
    for width,repeats in [(128,n//128),(n%128,int(n%128>0))]:
        if not repeats:continue
        p=N.recipe('all_gather',{'n':width,'ranks':ranks},{});f=footprint(p);peak=max(peak,f['typed_live_bytes']+f['transient_and_output_reserve_bytes'])
        for op,count in f['scalar_evaluations_by_opcode'].items():counts[op]+=count*repeats
    return {'ranks':ranks,'elements':n,'column_tile':128,'typed_live_workspace_upper_bytes_per_SM':peak,'opcode_scalar_evaluations':dict(counts),'scalar_dependency_recomputations':0,
            'provider_read_fragments_exact':2*ranks*((n+127)//128),'source_order':'per column native rank-order integer ownership sum and SELECT; no FP reduction or reordered payload; preserve rawF32 bits',
            'latency_cycles':None,'hardware_admitted':False}


class StreamingGather(StreamingLinear):
    def run_gather(self,parts,mask):
        parts=np.asarray(parts,np.float32);mask=np.asarray(mask,np.uint32)
        if parts.shape!=mask.shape or parts.ndim!=2:raise ValueError('gather provider geometry')
        ranks,n=parts.shape;plan=gather_model(ranks,n);observed=[];self.memory.fence()
        if np.any(mask>1):raise ValueError('one-bit ownership mask required')
        for first in range(0,n,128):
            width=min(128,n-first);p=N.recipe('all_gather',{'n':width,'ranks':ranks},{});data=[];owners=[]
            for rank in range(ranks):
                data.append(self.read(('gather_parts',*self.owner,rank,first),parts[rank,first:first+width]));owners.append(self.read(('gather_mask',*self.owner,rank,first),mask[rank,first:first+width]))
            out=self.execute(p,{'parts':np.stack(data),'ownership_mask':np.stack(owners)},'gather_columns128')['out'];observed.extend(out);raw=out.tobytes()
            self.memory.transact(('gather_output_staging',*self.owner,first),write=True,payload=raw);self.write_bytes+=len(raw)
        self.memory.fence()
        return np.asarray(observed,np.float32),{'status':'PASS_FORWARD_STREAMING_NATIVE_GATHER','plan':plan,'executed_primitive_scalars':dict(self.counts),'recomputed_dependency_scalars':0,'provider':self.memory.summary(),'read_bytes':self.read_bytes,'write_bytes':self.write_bytes,'physical_visibility_qualified':False}

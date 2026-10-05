"""Pinned Haswell DGEMM exceptional block candidate; no generic BLAS claim.

Original production batches use query32 by owned keys5464/5456/10928/10920,
CH16384. Runtime dispatch and assembly must accompany admission. Finite
common-scale products remain the separate exact integer block-dot recipe.
This module implements exceptional selection with ordinary U32 instructions;
it does not emulate finite FP64 arithmetic, nor change the golden contract.
"""
import numpy as np
import hashlib
import os
from pathlib import Path
from threadpoolctl import threadpool_info
import deepseek_hbm_complete_index as X
import deepseek_hbm_complete_index_exceptional as E
ins=X.K.ins
branch=X.K.branch

def pinned_runtime():
    infos=[i for i in threadpool_info() if i.get('internal_api')=='openblas']
    expected='0bd815d04b6b54990e3cccc7528fbb696456d09569f533d0390c13f0cdc4dd4a'
    if os.environ.get('NPY_DISABLE_CPU_FEATURES') or np.__version__!='2.2.6' or len(infos)!=1:raise ValueError('unproved NumPy/BLAS runtime')
    i=infos[0]
    if i.get('architecture')!='Haswell' or i.get('num_threads')!=1 or hashlib.sha256(Path(i['filepath']).read_bytes()).hexdigest()!=expected:
        raise ValueError('unproved BLAS binary/kernel/thread dispatch')
    core=Path(np._core._multiarray_umath.__file__)
    return {'numpy':np.__version__,'blas':i,'library_sha256':expected,
        'numpy_core_binary':str(core),'numpy_core_sha256':hashlib.sha256(core.read_bytes()).hexdigest(),
        'numpy_CPU_features':np._core._multiarray_umath.__cpu_features__}


def classify(symbol,prefix):
    return [ins('AND',prefix+'abs',symbol,0x7fffffff),ins('AND',prefix+'exp',symbol,0x7f800000),
        ins('IEQ',prefix+'special',prefix+'exp',0x7f800000),ins('AND',prefix+'mant',symbol,0x7fffff),
        ins('INE',prefix+'nonzero',prefix+'mant',0),ins('AND',prefix+'nan',prefix+'special',prefix+'nonzero'),
        ins('IEQ',prefix+'inf',prefix+'abs',0x7f800000),ins('IEQ',prefix+'zero',prefix+'abs',0)]

def exceptional_block_program():
    p=[ins('MOV','state',0)]
    for term in range(32):
        p += [ins('LOAD','q',f'q{term}'),ins('LOAD','k',f'k{term}')]+classify('q','q_')+classify('k','k_')
        p += [ins('OR','operand_nan','q_nan','k_nan'),ins('OR','operand_inf','q_inf','k_inf'),
              ins('XOR','product_sign','q','k'),ins('AND','product_sign','product_sign',0x80000000),
              ins('OR','product_inf','product_sign',0x7f800000),
              ins('AND','invalid_q','q_inf','k_zero'),ins('AND','invalid_k','k_inf','q_zero'),
              ins('OR','invalid','invalid_q','invalid_k')]+classify('state','s_')
        invalid=[ins('MOV','state',0xffc00000)]
        inf=[branch('BEQ','s_inf',1,[ins('XOR','opposite','state','product_inf'),
              branch('BEQ','opposite',0,[],invalid)], [ins('MOV','state','product_inf')])]
        ordinary=[branch('BEQ','s_nan',1,[],[branch('BEQ','invalid',1,invalid,
                    [branch('BEQ','operand_inf',1,inf,[])])])]
        # Haswell FMA231 uses packed query as first multiplicand: a current
        # query NaN precedes current key NaN, both precede accumulator NaN.
        nan=[branch('BEQ','q_nan',1,[ins('OR','state','q',0x00400000)],
                                  [ins('OR','state','k',0x00400000)])]
        p += [branch('BEQ','operand_nan',1,nan,ordinary)]
    p += [ins('STORE','exceptional_bits','state')]
    return p

def block(q,keys,trace=False):
    q=np.asarray(q,np.float32);keys=np.asarray(keys,np.float32)
    if q.shape!=(32,32) or keys.shape!=(32,):raise ValueError('one key block,32 heads')
    memory={f'q{j}':q[:,j][None,:].view(np.uint32) for j in range(32)}
    memory.update({f'k{j}':np.full((1,32),keys[j],np.float32).view(np.uint32) for j in range(32)})
    runner=E.TracedSIMT((1,32),memory,kernel='haswell_exceptional_block') if trace else X.SIMT((1,32),memory)
    runner.run(exceptional_block_program())
    return runner.stores['exceptional_bits'].reshape(32),runner

def sanitize(values):
    a=np.asarray(values,np.float32);flat=a.reshape(-1);pad=(-len(flat))%32
    memory={'input':np.pad(flat,(0,pad)).reshape(-1,32).view(np.uint32)}
    p=[ins('LOAD','x','input'),ins('AND','exp','x',0x7f800000),ins('IEQ','special','exp',0x7f800000),
       branch('BEQ','special',1,[ins('MOV','x',0)],[]),ins('STORE','finite','x')]
    m=X.SIMT(memory['input'].shape,memory).run(p)
    return m.stores['finite'].reshape(-1)[:len(flat)].view(np.float32).reshape(a.shape),m

def ieee_program(op,nan_priority=None):
    # Explicit NaN priority and invalid-operation value, not a native GPU
    # payload policy assumption. G.add/mul canonicalize either signed zero.
    p=[ins('LOAD','a','a'),ins('LOAD','b','b')]+classify('a','a_')+classify('b','b_')
    p += [ins(op,'r','a','b')]+classify('r','r_')
    first,second=('b','a') if nan_priority=='right' or (nan_priority is None and op=='FMUL') else ('a','b')
    p += [branch('BEQ',first+'_nan',1,[ins('OR','r',first,0x00400000)],
        [branch('BEQ',second+'_nan',1,[ins('OR','r',second,0x00400000)],
         [branch('BEQ','r_nan',1,[ins('MOV','r',0xffc00000)],[])])]),ins('STORE','r','r')]
    return p

def binary(op,a,b):
    a,b=np.broadcast_arrays(np.asarray(a,np.float32),np.asarray(b,np.float32))
    shape=a.shape;memory={'a':a.reshape(-1,32).view(np.uint32),'b':b.reshape(-1,32).view(np.uint32)}
    m=X.SIMT(memory['a'].shape,memory).run(ieee_program(op))
    return m.stores['r'].view(np.float32).reshape(shape),m

def source_sized_scores(q,keys,weights,original_batch_size):
    """Bounded ordinary-op software candidate; original DGEMM shape explicit.

No64-key BLAS reexecution: shape selects pinned original macro policy while
finite key tiles are compiler loops. Only production shapes tested so far.
Every sanitize/selection/finish kernel contributes its ordinary-op receipt.
"""
    pinned_runtime()
    if original_batch_size not in [5456,5464,10920,10928,16384]:raise ValueError('unproved original BLAS dispatch shape')
    q=np.asarray(q,np.float32);keys=np.asarray(keys,np.float32);weights=np.asarray(weights,np.float32)
    if q.shape!=(32,128) or keys.ndim!=2 or keys.shape[1]!=128 or len(keys)>64 or weights.shape!=(32,):raise ValueError('bounded64-key,32-head candidate')
    programs=[];blocks=[]
    for j in range(4):
        fq,m=sanitize(q[:,j*32:(j+1)*32]);programs.append(m)
        fk,m=sanitize(keys[:,j*32:(j+1)*32]);programs.append(m)
        qu,qe,m=X.decode(fq);programs.append(m);ku,ke,m=X.decode(fk);programs.append(m)
        finite,m=X.block(qu,ku,qe,ke);programs.append(m)
        memory={f'q{t}':q[:,j*32+t][None,:].view(np.uint32) for t in range(32)}
        memory.update({f'k{t}':keys[:,j*32+t,None].view(np.uint32) for t in range(32)})
        p=exceptional_block_program()+[ins('LOAD','finite_result','finite_result'),
             branch('BEQ','state',0,[ins('MOV','state','finite_result')],[]),ins('STORE','chosen','state')]
        m=X.SIMT((len(keys),32),{**memory,'finite_result':finite.view(np.uint32)}).run(p);programs.append(m)
        blocks.append(m.stores['chosen'].view(np.float32))
    acc=np.zeros((len(keys),32),np.float32)
    for j in range(8):
        acc,m=binary('FADD',acc,blocks[j] if j<4 else np.float32(0));programs.append(m)
    # Actual source BF16 integer rounding and np.maximum operand/tie policy.
    p=[ins('LOAD','score','score')]+E.C.bf16_bits('bf','score','score_')
    p += X.L.compare('positive','bf','@ZERO',True,'max_')+[ins('STORE','positive','positive')]
    m=X.SIMT((len(keys),32),{'score':acc.view(np.uint32)}).run(p);programs.append(m)
    terms,m=binary('FMUL',m.stores['positive'].view(np.float32),weights[None,:]);programs.append(m)
    p=[ins('LOAD','terms','terms')]+E.C.bf16_bits('out','terms','terms_')+[ins('STORE','terms','out')]
    m=X.SIMT((len(keys),32),{'terms':terms.view(np.uint32)}).run(p);programs.append(m)
    # Preserve chunk8+tree and wrap each FADD with source NaN policy.
    reduction=[]
    for instruction in X.reduce_program():
        if instruction['op']=='FADD':
            body=[ins('MOV','a',instruction['src'][0]),ins('MOV','b',instruction['src'][1])]+ieee_program('FADD','right' if instruction.get('predicate_stride')==8 else 'left')[2:-1]+[ins('MOV',instruction['dst'],'r')]
            stride=instruction.get('predicate_stride')
            if stride:body=[{**item,'predicate_stride':stride} for item in body]
            reduction.extend(body)
        else:reduction.append(instruction)
    m=X.SIMT((len(keys),32),{'terms':m.stores['terms']}).run(reduction);programs.append(m)
    return m.stores['final'][:,0].view(np.float32),programs

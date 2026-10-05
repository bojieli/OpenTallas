"""Actual source index-score consumer fallback, explicitly not GPU lowering.

Normal finite operands keep the ordinary INT32/FP32 score shader. Exceptions
execute the unchanged H.f_index_scores control with private chunk8 V globals,
using current query/weights and actual returned rows. No reference injection.
The source FP64 block-dot macro is retained and has no GPU hardware credit.
"""
from types import FunctionType,SimpleNamespace
import inspect
import numpy as np
import w19_hbm_tp96_isa as H
import deepseek_hbm_complete_index_codec as C
import deepseek_hbm_complete_index as X


def reference_modules():
    env={**vars(H.V),'ARITH':'chunk8'}
    for name,fn in vars(H.V).items():
        if inspect.isfunction(fn) and fn.__globals__ is H.V.__dict__:
            env[name]=FunctionType(fn.__code__,env,name,fn.__defaults__,fn.__closure__)
    return SimpleNamespace(**env)


def reference_scores(query,keys,weights,ids=None):
    """Bind the exact existing handler to produced operand arrays, not goldens."""
    query=np.asarray(query,np.float32);keys=np.asarray(keys,np.float32);weights=np.asarray(weights,np.float32)
    if query.shape!=(32,128) or keys.ndim!=2 or keys.shape[1]!=128 or weights.shape!=(32,):raise ValueError('full source consumer shapes')
    ids=np.arange(len(keys),dtype=np.int64) if ids is None else np.asarray(ids,np.int64)
    if ids.shape!=(len(keys),) or len(set(ids.tolist()))!=len(ids):raise ValueError('unique actual owned globalIDs')
    class ReturnedRows:
        def __init__(self):self.local={int(g):i for i,g in enumerate(ids)}
        def __getitem__(self,indices):return keys[[self.local[int(g)] for g in indices]]
    class Rank:
        def __init__(self):self.values={'iqf':query,'iw':weights}
        def get(self,name):return self.values[name]
        def put(self,name,value,**kwargs):self.values[name]=value
    # The same actual source loop/blockdot/maximum/BF16/head-tree runs, including
    # its own full CH=16384 CPU macro shape and F64 ABI stores. A finite64-key
    # physical shader cannot claim this software workset or macro is implemented.
    n=int(ids.max())+1 if len(ids) else 0
    owner=SimpleNamespace(m=SimpleNamespace(ih=32,ihd=128),st=SimpleNamespace(n={0:n},ik={0:ReturnedRows()}),owned=lambda rk,n:ids)
    rank=Rank();original=H.Executor.f_index_scores
    fn=FunctionType(original.__code__,{**original.__globals__,'V':reference_modules()},original.__name__,original.__defaults__)
    with np.errstate(over='ignore',under='ignore',invalid='ignore'):fn(owner,rank,{'n':n,'src':0})
    return rank.values['is_v']


def route_scores(query,keys,weights,backend=None,ids=None):
    q=np.asarray(query,np.float32);k=np.asarray(keys,np.float32);w=np.asarray(weights,np.float32)
    if q.shape!=(32,128) or k.ndim!=2 or k.shape[1]!=128 or w.shape!=(32,):raise ValueError('current source operands')
    # Typed IEEE exponent tests, including scale253-producedInf even though the
    # transport tag was packed. Do not infer finite decoded values from fmt1.
    checks=[];exceptional=False
    for row in list(q)+list(k):
        flag,programs=C.classify(row);exceptional |= flag;checks.extend(m.summary() for m in programs)
    # Weight IEEE exceptions also need the source path; classify a padded row
    # using the same ordinary integer test, not a free native isfinite service.
    flag,programs=C.classify(np.pad(w,(0,96)));exceptional |= flag;checks.extend(m.summary() for m in programs)
    if exceptional:
        result=reference_scores(q,k,w,ids)
        return result,{'path':'actual H.Executor.f_index_scores source fallback',
          'producer_operands':'current query/weights plus actual returned produced index rows',
          'reference_injection':False,'ordinary_GPU_score_lowered':False,
          'CPU_reference_FP64_macro_used':True,'GPU_cycles':None,'classification_programs':checks,
          'software_cached_key_bytes':k.nbytes,'physical_workset_and_exceptional_score_calendar':None}
    results=[];summaries=[]
    for start in range(0,len(k),64):
        result,programs=X.scores(q,k[start:start+64],w,backend)
        results.append(result);summaries.extend(m.summary() for m in programs)
    result=np.concatenate(results) if results else np.empty(0,np.float32)
    return result.astype(np.float64),{'path':'ordinary INT32/FP32 index score shader',
      'reference_injection':False,'ordinary_programs':summaries,'finite_outer_tile_rows':64,
      'classification_programs':checks,'GPU_cycles':None,'physical_admission':'FAIL_CLOSED'}

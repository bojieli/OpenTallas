"""Explicit eight independent source groups; preserve each eight-input tree.
No numerical reduction runs in the provider; it only gathers owned operands.
"""
import copy,hashlib,json,math
from collections import Counter
import numpy as np
from h3_ds_checkpoint_provider_r33 import Provider as Previous

def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':')).encode()

def lower_template(t):
    if t['family']!='all_reduce' or t['providers']['parts']['shape']!=[8,1024] or t['outputs']!={'out':'v34'}:
        raise ValueError('pinned single-group template contract')
    new=copy.deepcopy(t)
    for n in new['code']:
        if n['shape']==[8,1024]:n['shape']=[8,8,1024]
        elif n['shape']==[1,1024]:n['shape']=[1,8,1024]
        elif n['shape']==[1024]:n['shape']=[8,1024]
        elif n['shape']!=[]:raise ValueError('unexpected source group instruction shape')
    new['code'].append(dict(dst='r34_group_output',op='RESHAPE',src=['v34'],shape=[8192],attrs={},rf_scalar_slot=6))
    new['outputs']['out']='r34_group_output';new['providers']['parts']['shape']=[8,8,1024]
    new['providers']['parts']['role']='contributor j then group g then word: source rank=8*g+j'
    new['shape_parameters']['groups']=8;new['shape_parameters']['n']=8192
    r=new['resources'];r['materialized_tensor_workspace_bytes']*=8;r['peak_interpreter_live_words']*=8
    # Retain conservative original materialization charge, including new view.
    r['instruction_batches128_by_opcode']=dict(Counter())
    batches=Counter()
    for n in new['code']:batches[n['op']]+=math.ceil(max(1,math.prod(n['shape']))/128)
    r['instruction_batches128_by_opcode']=dict(batches)
    r['streaming_tiling_fit_proved']=False;r['hardware_latency']=None
    new['group_binding_scope']='eight independent original trees and final flatten; finite dispatch reprice required'
    return new

def lower_native(native):
    out=copy.deepcopy(native);witness=[]
    for o in out['instructions']:
        if o['family']!='all_reduce':continue
        source=o['source_op']
        if (source['groups'],source['per_group'],source['elems'])!=(8,8,8192):raise ValueError('source group geometry differs')
        for old in list(o['provider_bindings']):
            t=lower_template(native['templates'][old]);key=hashlib.sha256(canonical(t)).hexdigest();out['templates'][key]=t
            b=o['provider_bindings'].pop(old);b['parts']['view']='source rank=8*group+contributor; LOAD[contributor,group,word]'
            o['provider_bindings'][key]=b
            for rb in o['rank_bindings']:
                if rb['template']==old:rb['template']=key
            witness.append(dict(PC=o['pc'],old_template=old,new_template=key,source_order='((0+1)+(2+3))+((4+5)+(6+7)) separately per group; source BF16 RNE unchanged',output_words=8192,input_words=65536,materialized_workspace_bytes=t['resources']['materialized_tensor_workspace_bytes']))
    return out,witness

def gather_parts(restore, version, producer, spec):
    """All64 owned source fragments, without summing or fabricating a rank."""
    if spec['shape']!=[8,8,1024] or spec['dtype']!='F32':raise ValueError('explicit group LOAD shape')
    rows=producer['source_op']['rows']
    if len(rows)!=96:raise ValueError('source96 rank row directory')
    a=np.empty((8,8,1024),np.float32)
    for rank in range(64):
        group,j=divmod(rank,8)
        if rows[rank]!=[group*1024,(group+1)*1024]:raise ValueError('source group row identity')
        payload=restore(version,rank)
        if payload.shape!=(1024,) or payload.dtype!=np.float32:raise ValueError('owned group fragment shape/type')
        a[j,group]=payload
    if any(lo!=hi for lo,hi in rows[64:]):raise ValueError('unexpected additional source contribution')
    a.flags.writeable=False
    return a

class Provider(Previous):
    def _read_one(self,op,owned,key,bindings,generation,collective=None):
        if op['family']!='all_reduce':return super()._read_one(op,owned,key,bindings,generation,collective)
        if generation!=self.generation or set(bindings)!={'parts'}:raise ValueError('group owner generation/provider contract')
        b=bindings['parts'];version=b['version']
        source=[o for o in self.native['instructions'] if any(w['version']==version for w in o['writes'])]
        if len(source)!=1:raise ValueError('unique owned group producer')
        a=gather_parts(self.restore,version,source[0],self.native['templates'][key]['providers']['parts'])
        value=dict(field='parts',rank=owned['rank'],generation=generation,kind='versioned_operand',data=a,version=version,view_contract=b['native_address_view'],leased_versions=[version],source_ranks=list(range(64)),provenance_certified=True)
        result={'parts':value};self.views[op['pc'],owned['rank'],generation,id(result)]=result;return result

def create_provider(manifest,native,dispatch,homes):return Provider(manifest,native,dispatch,homes)

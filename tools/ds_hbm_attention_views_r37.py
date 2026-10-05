"""Exact data-only W19 f_attend views over actual addressed producer locations.
Source q reshape and window-then-selection concatenation only; no attention math.
"""
import math
import numpy as np
from h3_ds_checkpoint_provider_r30 import DTYPES,CAP

class AttentionViewsMixin:
    def _read_one(self,op,owned,key,bindings,generation,collective=None):
        target={n:b for n,b in bindings.items() if op['family']=='attend' and n in ('q_own','rows','sink')}
        if not target:return super()._read_one(op,owned,key,bindings,generation,collective)
        if generation!=self.generation or not 0<=owned['rank']<64:raise ValueError('actual attention head owner/generation')
        specs=self.native['templates'][key]['providers'];rank=owned['rank'];plan={}
        if 'q_own' in target:
            b=target['q_own']
            if b['kind']!='versioned_operand' or b['native_address_view']!='full source value reshaped to declared LOAD shape' or specs['q_own']['shape']!=[1,512] or specs['q_own']['dtype']!='F32':raise ValueError('source q reshape contract')
            plan['q_own']=[(b['version'],[512])]
        if 'rows' in target:
            b=target['rows'];versions=b['additional_versions'];yarn=op['source_op']['yarn'];want=[640,512] if yarn else [128,512]
            if b['native_address_view']!='oldest WINDOW128 then selected512 when yarn' or specs['rows']['shape']!=want or specs['rows']['dtype']!='F32' or len(versions)!=(3 if yarn else 2) or versions[1]!=b['version']:raise ValueError('exact source window/selected order')
            plan['rows']=[(versions[1],[128,512])]+([(versions[2],[512,512])] if yarn else [])
        # Validate every actual location before any backing requests.
        for name,parts in plan.items():
            for version,shape in parts:
                loc=self.locations.get((version,rank))
                if loc is None or list(loc['shape'])!=shape or np.dtype(loc['dtype'])!=np.dtype('float32'):raise ValueError('actual attention producer location/shape')
        if sum(math.prod(specs[n]['shape'])*4 for n in plan)>CAP:raise ValueError('bounded attention host workspace')
        result=super()._read_one(op,owned,key,{n:b for n,b in bindings.items() if n not in target},generation,collective)
        for name,parts in plan.items():result[name]=dict(field=name,rank=rank,generation=generation,kind=target[name]['kind'],data=None,leased_versions=[v for v,s in parts],provenance_certified=False)
        for name,parts in plan.items():
            out=np.empty(math.prod(specs[name]['shape']),np.float32);cursor=0;receipts=[]
            for version,shape in parts:
                count=math.prod(shape)
                for first in range(0,count,128):
                    words,_,receipt=self.C0_source_views._read_words(version,rank,np.arange(first,min(first+128,count),dtype=np.int64));out[cursor:cursor+len(words)]=words.view(np.float32);cursor+=len(words);receipts.append(receipt)
            out=out.reshape(specs[name]['shape']);out.flags.writeable=False
            result[name].update(data=out,provenance_certified=True,version=target[name]['version'],view_contract=target[name]['native_address_view'],source_journal_spans=receipts,source_binding=target[name],hardware_qualified=False)
        if 'sink' in target:
            b=target['sink'];spec=specs['sink'];tensor=f"layers.{op['source_op']['layer']}.attn.attn_sink"
            if b['kind']!='immutable_parameter_provider' or b['logical_tensor']!=tensor or spec['shape']!=[1] or spec['dtype']!='F32':raise ValueError('source head sink slice contract')
            a,dt=self.checkpoint.tensor(tensor)
            if dt not in ('BF16','F32') or a.shape!=(64,) or a.dtype!=np.float32:raise ValueError('actual released per-head sink tensor')
            a=a[rank:rank+1].view();a.flags.writeable=False
            result['sink']=dict(field='sink',rank=rank,generation=generation,kind=b['kind'],data=a,logical_tensor=tensor,source_slice=[rank,rank+1],provenance_certified=True,source_binding=b,revision=self.revision)
        return result

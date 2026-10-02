"""Source declared initialization and ordered actual producer merges.
No arithmetic kernels. Data-only rank concatenation, checked against native LOAD.
"""
import math
import numpy as np
from h3_ds_checkpoint_provider_r30 import CAP,DTYPES
from ds_hbm_finite_state_homes_r30 import output_spec

class SourceMergeMixin:
    def _read_one(self,op,owned,key,bindings,generation,collective=None):
        zeros={n:b for n,b in bindings.items() if b['kind']=='zero_initial_partial_destination'}
        merge={n:b for n,b in bindings.items() if op['family']=='topk_merge' and n in ('ids','scores')}
        targeted={**zeros,**merge};specs=self.native['templates'][key]['providers'];plans={}
        if targeted and generation!=self.generation:raise ValueError('exact source initializer/merge generation')
        for name,b in zeros.items():
            spec=specs[name]
            if spec['dtype']!='F32' or math.prod(spec['shape'])!=b['full_elements'] or b['new_version'] not in {w['version'] for w in op['writes']}:raise ValueError('source declared zero extent and destination')
        for name,b in merge.items():plans[name]=merge_plan(self.native,op,name,b,specs[name])
        if sum(math.prod(specs[n]['shape'])*np.dtype(DTYPES[specs[n]['dtype']]).itemsize for n in targeted)>CAP:raise ValueError('finite source merge workspace')
        result=super()._read_one(op,owned,key,{n:b for n,b in bindings.items() if n not in targeted},generation,collective)
        # Retain all source owners before the first real backing read.
        for name,plan in plans.items():
            result[name]=dict(field=name,rank=owned['rank'],generation=generation,kind=bindings[name]['kind'],data=None,version=plan['version'],leased_versions=[plan['version']],source_ranks=[r['rank'] for r in plan['ranks']],provenance_certified=False)
        for name,b in zeros.items():
            a=np.zeros(specs[name]['shape'],np.float32);a.flags.writeable=False
            result[name]=dict(field=name,rank=owned['rank'],generation=generation,kind=b['kind'],data=a,source_binding=b,provenance_certified=True,initialization_bytes=a.nbytes,initialization_cost='source-defined software initialization; hardware service cost not measured')
        for name,plan in plans.items():
            spec=specs[name];output=np.empty(math.prod(spec['shape']),DTYPES[spec['dtype']]);cursor=0;journals=[]
            for row in plan['ranks']:
                loc=self.locations.get((plan['version'],row['rank']))
                if loc is None or list(loc['shape'])!=row['shape'] or np.dtype(loc['dtype'])!=np.dtype(DTYPES[spec['dtype']]):raise ValueError('actual addressed candidate producer shape/version missing')
                raw=np.empty(row['bytes']//4,np.uint32)
                # Bounded128-word addressed requests; no whole-array restore.
                for first in range(0,len(raw),128):
                    words,_,receipt=self.C0_source_views._read_words(plan['version'],row['rank'],np.arange(first,min(first+128,len(raw)),dtype=np.int64));raw[first:first+len(words)]=words;journals.append(receipt)
                data=raw.view(DTYPES[spec['dtype']]);output[cursor:cursor+len(data)]=data;cursor+=len(data)
            if cursor!=len(output):raise ValueError('ordered source candidate extent incomplete')
            output=output.reshape(spec['shape']);output.flags.writeable=False
            result[name].update(data=output,provenance_certified=True,source_journal_spans=journals,source_binding=bindings[name],view_contract=bindings[name].get('native_address_view'),source_concat_order='increasing actual rank then original local output order',hardware_qualified=False)
        return result

def merge_plan(native,consumer,name,b,spec):
    if consumer['family']!='topk_merge' or name not in ('ids','scores'):raise ValueError('source candidate merge only')
    if b['kind']=='explicit_auxiliary_provider':
        versions=b['identity_from_versions']
        if name!='scores' or len(versions)!=2 or versions[1]!=consumer['provider_bindings'][next(iter(consumer['provider_bindings']))]['ids']['version']:raise ValueError('exact candidate value/index auxiliary identities')
        version=versions[0]
    elif b['kind']=='versioned_operand':version=b['version']
    else:raise ValueError('source merge provider kind')
    producers=[(o,w) for o in native['instructions'] if o['pc']<consumer['pc'] for w in o['writes'] if w['version']==version]
    if len(producers)!=1:raise ValueError('unique ordered source candidate producer')
    producer,w=producers[0];rows=[]
    for rb in producer['rank_bindings']:
        if rb.get('empty_owned_extent'):continue
        out=output_spec(native['templates'][rb['template']],w['native_result_binding']['result'])
        if out['dtype']!=spec['dtype'] or len(out['shape'])!=1:raise ValueError('ordered source candidate producer dtype/shape')
        rows.append(dict(rank=rb['rank'],**out))
    if [r['rank'] for r in rows]!=sorted({r['rank'] for r in rows}) or sum(math.prod(r['shape']) for r in rows)!=math.prod(spec['shape']):raise ValueError('source candidate concatenation cannot pad or reshape')
    return dict(version=version,producer_PC=producer['pc'],ranks=rows,bytes=sum(r['bytes'] for r in rows),output_shape=spec['shape'],dtype=spec['dtype'])

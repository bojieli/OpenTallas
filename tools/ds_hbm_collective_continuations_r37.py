"""Independent source-buffer continuations and accepted Engram ownership.
Retains peer implementation. Never creates an arithmetic/ACK callback.
"""
import copy,math
import numpy as np
from h3_ds_checkpoint_provider_r30 import CAP

def continuation_contract(native,PC,collective,source_sha,peer_contract,engram_owners=None):
    op=native['instructions'][PC];version=collective['read_version']
    if op['family']!='all_gather':raise ValueError('actual source collective required')
    matches=[i for i,b in enumerate(op['rank_bindings'][0]['buffer_programs']) if b['read_version']==version and b['write_version']==collective['write_version'] and b['template']==collective['template']]
    if len(matches)!=1:raise ValueError('exact independent source buffer continuation')
    index=matches[0];name=op['native_outer_loops']['all_gather_buffers'][index];read=next(r for r in op['reads'] if r['version']==version)
    producers=[(p,w) for p in native['instructions'][:PC] for w in p['writes'] if w['version']==version]
    if len(producers)!=1:raise ValueError('unique source continuation producer')
    producer,w=producers[0];extent=w['producer_extent']
    if isinstance(extent,dict) and extent.get('dynamic_owner')=='token_history_hash%96':
        if producer['family']!='engram_fetch' or name!='eg_rows' or extent['full_extent']!=6144 or engram_owners is None:raise ValueError('actual accepted Engram ownership required')
        if engram_owners['generation']<=0 or engram_owners['version']!=version or engram_owners['ranks']!=set(range(96)):raise ValueError('all native Engram writer owners must complete')
        ids=engram_owners['ids']
        if ids.dtype!=np.int64 or ids.shape!=(24,):raise ValueError('exact accepted Engram row IDs')
        owners=[[[i*256,(i+1)*256] for i in range(24) if int(ids[i])%96==rank] for rank in range(96)]
        return dict(version=version,shape=[96,6144],buffer=name,producer_PC=producer['pc'],rank_intervals=owners,owner_elements=[256*len(r) for r in owners],source_method='source hash IDs%96 from locked row IDs and all96 actual WR completion receipts',hardware_qualified=False)
    # Validate the exact continuation directly, allowing source-declared
    # empty ranks. Empty extents contribute neither payload nor fake requests.
    if isinstance(extent,dict):
        total=extent['full_extent'];layer=producer['source_op']['layer']
        siblings=[(p,w) for p in native['instructions'][:producer['pc']+1] for w in p['writes'] if p.get('family')==producer['family'] and p['source_op'].get('layer')==layer and isinstance(w.get('producer_extent'),dict) and 'slot' in w['producer_extent'] and w['native_result_binding']['result']==name]
        slots={w['producer_extent']['slot']:(p,w) for p,w in siblings}
        if sorted(slots)!=list(range(extent['slot']+1)):raise ValueError('source compound slots missing or unordered')
        owners=[[w['producer_extent']['rank_local_slice'][rank] for slot,(p,w) in sorted(slots.items())] for rank in range(96)]
    else:
        if len(extent)!=96:raise ValueError('all96 source producer extents required')
        total=max(hi for lo,hi in extent);owners=[[interval] for interval in extent]
    coverage=[];active=[]
    for rank,intervals in enumerate(owners):
        nonempty=[]
        for lo,hi in intervals:
            if type(lo)!=int or type(hi)!=int or not 0<=lo<=hi<=total:raise ValueError('source extent outside continuation')
            if hi!=lo:coverage.append((lo,hi,rank));nonempty.append([lo,hi])
        active.append(nonempty)
        if not any(b['elements']==total and b['read_version']==version and b['write_version']==collective['write_version'] for b in op['rank_bindings'][rank]['buffer_programs']):raise ValueError('all96 exact consumer source continuation')
    cursor=0
    for lo,hi,rank in sorted(coverage):
        if lo!=cursor:raise ValueError('source continuation overlap or uncovered words')
        cursor=hi
    if cursor!=total:raise ValueError('source continuation extent incomplete')
    return dict(version=version,shape=[96,total],buffer=name,producer_PC=producer['pc'],rank_intervals=active,owner_elements=[sum(hi-lo for lo,hi in r) for r in active],source_method='unchanged source producer extents; independent exact buffer and empty-rank continuation',hardware_qualified=False)

def source_views_class(peer_class,peer_contract):
    class Views(peer_class):
        def gather_views(self,op,owned,key,bindings,generation,collective):
            self._check();p=self.provider
            if generation!=p.generation:raise ValueError('source continuation generation')
            contract=continuation_contract(p.native,op['pc'],collective,self.source_sha,peer_contract,getattr(p,'engram_owners',{}).get(collective['read_version']))
            specs=p.native['templates'][key]['providers'];shape=contract['shape']
            if set(bindings)!={'parts','ownership_mask'} or specs['parts']['shape']!=shape or specs['parts']['dtype']!='F32' or specs['ownership_mask']['shape']!=shape or specs['ownership_mask']['dtype']!='U32':raise ValueError('source continuation typed LOAD')
            if math.prod(shape)*8+max(contract['owner_elements'])*4>CAP:raise ValueError('finite source continuation workspace')
            # Distinct buffers of one PC/rank coexist until their own source
            # consumes finish. Version is part of each retained lease.
            if any(k[:3]==(op['pc'],owned['rank'],generation) and any(v.get('version')==contract['version'] for v in vs.values()) for k,vs in p.views.items()):raise ValueError('same source buffer lease already live')
            result={name:dict(field=name,rank=owned['rank'],generation=generation,kind=b['kind'],version=contract['version'],leased_versions=[contract['version']],source_ranks=list(range(96)),provenance_certified=False,data=None) for name,b in bindings.items()}
            p.views[op['pc'],owned['rank'],generation,id(result)]=result
            parts=np.zeros(shape,np.float32);mask=np.zeros(shape,np.uint32);journals=[]
            for rank,intervals in enumerate(contract['rank_intervals']):
                if not intervals:continue # no owned source words; no fake read
                values,receipt=self._owned_payload(contract,rank);journals.append(receipt);first=0
                for lo,hi in intervals:parts[rank,lo:hi]=values[first:first+hi-lo];mask[rank,lo:hi]=1;first+=hi-lo
            if not np.all(mask.sum(axis=0)==1):raise ValueError('exact nonoverlapping source ownership incomplete')
            for name,array in [('parts',parts),('ownership_mask',mask)]:
                array.flags.writeable=False;b=bindings[name]
                result[name].update(data=array,provenance_certified=True,source_binding=b,view_contract=b.get('native_address_view'),source_journal_spans=journals,source_extent_contract=contract,hardware_qualified=False)
            return result
    return Views

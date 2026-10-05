"""Source-owned producer extents for DS collective typed-view bridges.

This imports native writes, not guessed source_op.rows. It supplies sparse
source views for Kepler's provider, never numerical callbacks, generated
payloads, transport timing or hardware qualification.
"""
import hashlib,json
import numpy as np

def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':')).encode()

def collective_contract(native,PC,*,native_sha256):
    op=native['instructions'][PC]
    if op['family']!='all_gather':raise ValueError('actual all_gather source instruction required')
    buffers=op['native_outer_loops']['all_gather_buffers']
    if len(buffers)!=1:raise ValueError('explicit single-buffer source continuation required')
    name=buffers[0];version=op['reads'][0]['version']
    producers=[(p,w) for p in native['instructions'][:PC] for w in p['writes'] if w['version']==version]
    if len(producers)!=1:raise ValueError('unique actual source producer required')
    producer,write=producers[0];extent=write['producer_extent'];compound=isinstance(extent,dict)
    if compound:
        total=extent['full_extent'];layer=producer['source_op']['layer']
        siblings=[(p,w) for p in native['instructions'][:producer['pc']+1] for w in p['writes']
            if p['family']==producer['family'] and p['source_op'].get('layer')==layer and isinstance(w['producer_extent'],dict)
            and w['native_result_binding']['result']==name]
        slots={w['producer_extent']['slot']:(p,w) for p,w in siblings}
        if sorted(slots)!=list(range(extent['slot']+1)):raise ValueError('compound source slots missing or unordered')
        owners=[[w['producer_extent']['rank_local_slice'][rank] for slot,(p,w) in sorted(slots.items())] for rank in range(96)]
        source_slots=[dict(slot=slot,producer_PC=p['pc'],version=w['version']) for slot,(p,w) in sorted(slots.items())]
    else:
        if len(extent)!=96:raise ValueError('complete96-rank source producer partition required')
        total=max(hi for lo,hi in extent);owners=[[interval] for interval in extent];source_slots=[]
    coverage=[];bindings={b['rank']:b for b in op['rank_bindings']}
    for rank,intervals in enumerate(owners):
        for lo,hi in intervals:
            if type(lo)!=int or type(hi)!=int or not 0<=lo<hi<=total:raise ValueError('actual producer extent outside collective buffer')
            coverage.append((lo,hi,rank))
        programs=bindings[rank]['buffer_programs']
        if not any(b['elements']==total and b['read_version']==version for b in programs):raise ValueError('source consumer buffer/producer extent mismatch')
    cursor=0
    for lo,hi,rank in sorted(coverage):
        if lo!=cursor:raise ValueError('source sparse owners overlap or leave holes')
        cursor=hi
    if cursor!=total:raise ValueError('source owned extent incomplete')
    return dict(schema='H4_C0_SOURCE_PRODUCER_EXTENTS_V1',native_sha256=native_sha256,consumer_PC=PC,
        producer_PC=producer['pc'],version=version,buffer=name,shape=[96,total],dtype='F32',ownership_dtype='U32',
        rank_intervals=owners,compound_slots=source_slots,latest_compound_version_required=compound,
        owner_elements=[sum(hi-lo for lo,hi in row) for row in owners],
        source_method='native writes producer_extent plus actual consumer buffer_programs',
        generated_payloads=False,hardware_qualified=False)

def bind_local_payload(contract,rank,*,version,generation,lease,payload,home,source_receipt):
    """Check a published rank-owned local result without synthesizing holes.

    Payload is in the source interval order. A full global sparse buffer must
    be sliced by its producer before this gate; shape alone never owns bytes.
    This validates typed bytes/lease identity, not an ACK or numerical result.
    """
    if type(rank)!=int or not 0<=rank<96 or version!=contract['version'] or type(generation)!=int or generation<=0 or not lease:raise ValueError('exact source version/rank/generation/lease required')
    expected=dict(version=version,rank=rank,generation=generation,lease=lease)
    if any(home.get(k)!=v or source_receipt.get(k)!=v for k,v in expected.items()):raise ValueError('published source home/receipt identity mismatch')
    array=np.asarray(payload)
    if array.dtype!=np.dtype('float32') or array.shape!=(contract['owner_elements'][rank],):raise ValueError('actual local producer F32 extent required')
    digest=hashlib.sha256(array.tobytes()).hexdigest()
    if source_receipt.get('payload_sha256')!=digest:raise ValueError('actual published source byte digest mismatch')
    return dict(**expected,source_native_sha256=contract['native_sha256'],source_consumer_PC=contract['consumer_PC'],
        source_intervals=contract['rank_intervals'][rank],payload_sha256=digest,payload_bytes=array.nbytes,
        typed_source_view_bound=True,ACK_reverse_qualified=False,hardware_qualified=False)

def require_complete_rank_views(contract,views):
    if len(views)!=96 or {v['rank'] for v in views}!=set(range(96)):raise ValueError('all96 actual source rank views required')
    for view in views:
        if view['version']!=contract['version'] or view['source_intervals']!=contract['rank_intervals'][view['rank']] or view['source_native_sha256']!=contract['native_sha256'] or view['source_consumer_PC']!=contract['consumer_PC'] or view['payload_bytes']!=4*contract['owner_elements'][view['rank']]:
            raise ValueError('mixed source ownership view')
    if len({(v['generation'],v['source_consumer_PC']) for v in views})!=1:raise ValueError('mixed collective source generations/PCs')
    return dict(typed_rank_views_bound=True,actual_transport_ACK_reverse_qualified=False,hardware_qualified=False)

def bind_current_typed_view(native,PC,rank,template,field,view,*,generation,revision,native_sha256,source_receipt):
    """Delegate source dtype/shape/provenance to the existing full driver.

    Preserves scalar route weights, ordered expert operands and query-code
    bytes. No sorting, broadcasting, rounding or numerical conversion here.
    """
    from h3_deepseek_full_token_driver import validate_view
    if type(PC)!=int or not 0<=PC<len(native['instructions']) or type(rank)!=int or not 0<=rank<96 or type(generation)!=int or generation<=0:raise ValueError('finite actual source owner required')
    op=native['instructions'][PC]
    if not any(b['rank']==rank and (b['template']==template or any(p['template']==template for p in b['buffer_programs'])) for b in op['rank_bindings']):raise ValueError('typed view template not owned by actual source rank/PC')
    required=op['provider_bindings'][template][field];spec=native['templates'][template]['providers'][field]
    data=validate_view(field,view,required,spec,rank,generation,revision)
    identity=dict(native_sha256=native_sha256,PC=PC,rank=rank,generation=generation,template=template,field=field)
    if source_receipt.get('identity')!=identity or source_receipt.get('source_binding')!=required or source_receipt.get('payload_sha256')!=hashlib.sha256(data.tobytes()).hexdigest():raise ValueError('actual typed source byte receipt mismatch')
    return dict(identity=identity,shape=spec['shape'],dtype=spec['dtype'],payload_sha256=source_receipt['payload_sha256'],
        source_binding_sha256=hashlib.sha256(canonical(required)).hexdigest(),
        typed_source_view_bound=True,order_and_bytes_preserved=True,ACK_reverse_qualified=False,hardware_qualified=False)

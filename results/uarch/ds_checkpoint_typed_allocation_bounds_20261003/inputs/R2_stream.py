"""Default-off typed-state streaming primitive for a prospective V3 successor.

This writes exactly the pinned V3 Writer.tree canonical format and payload order.
It does not capture, publish, construct, restore, relax guards or admit a job.
A production caller must retain every quiescence/source/atomic gate. Containers
are traversed in source order, never re-associated or supplied oracle data.
"""
import hashlib,json
from pathlib import Path
V3_SHA256='e323ce55e837e32418a74ae271897357952780681a5161205d8a12498060321e'


def require_source(base):
    if hashlib.sha256(Path(base.__file__).read_bytes()).hexdigest()!=V3_SHA256:
        raise ValueError('exact V3 leaf writer source required')


def stream_typed_state(base,value,writer,sink,*,enabled=False):
    if enabled is not True:raise ValueError('typed state streaming is default off')
    require_source(base)
    if type(writer)is not base.Writer:raise ValueError('exact V3 payload Writer required')
    active=set()
    metrics={'containers':0,'leaves':0,'max_depth':0,'max_leaf_metadata_bytes':0,
             'max_leaf_tree_heap_bytes':0,'max_live_container_frames':0,'metadata_bytes':0,
             'full_encoded_container_tree_created':False}
    def emit(raw):
        n=sink.write(raw)
        if n is not None and n!=len(raw):raise ValueError('short typed metadata write')
        metrics['metadata_bytes']+=len(raw)
    def walk(v,depth):
        metrics['max_depth']=max(metrics['max_depth'],depth)
        # Preserve exact V3 type dispatch: dtype/ndarray/SectorBacking are leaves,
        # and numpy scalar is converted before traversing its ordinary value.
        if isinstance(v,base.np.generic):return walk(v.item(),depth)
        if isinstance(v,(dict,tuple,list,set)):
            if id(v) in active:raise ValueError('cyclic actual state unsupported')
            active.add(id(v));metrics['containers']+=1
            metrics['max_live_container_frames']=max(metrics['max_live_container_frames'],len(active))
            try:
                kind='dict' if isinstance(v,dict) else type(v).__name__
                emit(b'{'+base.canonical(kind)+b':[')
                if isinstance(v,dict):
                    for i,(k,x) in enumerate(v.items()):
                        if i:emit(b',')
                        emit(b'[');walk(k,depth+1);emit(b',');walk(x,depth+1);emit(b']')
                else:
                    for i,x in enumerate(v):
                        if i:emit(b',')
                        walk(x,depth+1)
                emit(b']}')
            finally:active.remove(id(v))
            return
        # The pinned writer validates all source leaf types, address extents,
        # byte masks, ndarray dtype/order/writeability and payload boundaries.
        leaf=base.Writer.tree(writer,v)
        raw=base.canonical(leaf)
        metrics['leaves']+=1
        metrics['max_leaf_metadata_bytes']=max(metrics['max_leaf_metadata_bytes'],len(raw))
        metrics['max_leaf_tree_heap_bytes']=max(metrics['max_leaf_tree_heap_bytes'],base.deep_metadata_bytes(leaf))
        emit(raw)
    walk(value,0)
    return metrics


class _TypedSnapshot:
    def __init__(self,value,metadata_sha256=None):
        self.value=value
        self.metadata_sha256=metadata_sha256


def _ordinary_json(base,value,sink,typed_writer):
    """Canonical closure JSON: metadata keys are strings; typed state is special."""
    if type(value)is _TypedSnapshot:
        class CheckedSink:
            def __init__(self):self.h=hashlib.sha256()
            def write(self,data):
                self.h.update(data)
                return sink.write(data)
        checked=CheckedSink()
        metrics=stream_typed_state(base,value.value,typed_writer,checked,enabled=True)
        if value.metadata_sha256 is not None and checked.h.hexdigest()!=value.metadata_sha256:
            raise ValueError('actual typed metadata changed during streamed pass')
        return metrics
    if isinstance(value,dict):
        if any(type(k)is not str for k in value):raise ValueError('closure metadata requires string keys')
        sink.write(b'{')
        for i,key in enumerate(sorted(value)):
            if i:sink.write(b',')
            sink.write(base.canonical(key));sink.write(b':');_ordinary_json(base,value[key],sink,typed_writer)
        sink.write(b'}');return
    if isinstance(value,(list,tuple)):
        sink.write(b'[')
        for i,item in enumerate(value):
            if i:sink.write(b',')
            _ordinary_json(base,item,sink,typed_writer)
        sink.write(b']');return
    sink.write(base.canonical(value))


def save_streamed(base,provider,engine,path,*,enabled=False):
    """Actual source-gated save primitive; no atomic publication or admission.

    Same V3 snapshot/identity/source/quiescence validation, payload format and
    seal. Two bounded passes avoid an encoded snapshot tree and full closure
    JSON buffers. The second pass hashes discarded payload writes and refuses
    drift before COMPLETE. Existing failure directories remain untouched.
    Callers must use an independently priced successor capture/atomic wrapper;
    this function is not selected by R68 and does not replace its guards.
    """
    import os
    if enabled is not True:raise ValueError('streamed save is default off')
    require_source(base)
    p=base.quiescent(provider,engine);inventory=base.inventory(provider,engine)
    base.validate_backing(p)
    root=Path(path)
    minimum=inventory['produced_and_initial_cached_array_bytes']+inventory['raw_sector_payload_bytes']
    stat=os.statvfs(root.parent)
    if stat.f_bavail*stat.f_frsize<minimum:raise ValueError('disk headroom before payload')
    if root.exists():raise ValueError('fresh checkpoint only')
    root.mkdir(parents=True);writer=base.Writer(root)
    class PayloadHash:
        def __init__(self):self.h=hashlib.sha256();self.bytes=0
        def write(self,data):self.h.update(data);self.bytes+=len(data);return len(data)
    try:
        snapshot=base.snapshot_state(p,engine)
        metadata_hash=PayloadHash()
        first=stream_typed_state(base,snapshot,writer,metadata_hash,enabled=True)
        writer.close();payload_sha=base.sha(root/'payload.bin')
        closure={'schema':base.SCHEMA,'identity':base.identity(p,engine),'inventory':inventory,
                 'state':_TypedSnapshot(snapshot,metadata_hash.h.hexdigest()),'run_scope':base.run_scope(p),
                 'scope_role_proof':base.scope_role_proof(p,engine),
                 'historical_journal_inventory':base.journal_inventory(p,engine,hashes=True),
                 'opened_checkpoint_shards':base.checkpoint_shards(p),
                 'payload_sha256':payload_sha,'payload_bytes':writer.bytes}
        class SizeCounter:
            def __init__(self):self.bytes=0
            def write(self,data):self.bytes+=len(data);return len(data)
        size_counter=SizeCounter();metadata_only=dict(closure,state=None)
        _ordinary_json(base,metadata_only,size_counter,None)
        state_bytes=size_counter.bytes-len(base.canonical(None))+first['metadata_bytes']
        stat=os.statvfs(root)
        if stat.f_bavail*stat.f_frsize<state_bytes+4096:
            raise ValueError('disk headroom before streamed closure')
        replay=base.Writer.__new__(base.Writer);replay.f=PayloadHash();replay.bytes=0
        replay.arrays=0;replay.array_temporary_bytes=0
        with (root/'state.json').open('xb') as f:
            _ordinary_json(base,closure,f,replay);f.flush();os.fsync(f.fileno())
        if (root/'state.json').stat().st_size!=state_bytes:
            raise ValueError('metadata size changed during streamed pass')
        if replay.bytes!=writer.bytes or replay.f.h.hexdigest()!=payload_sha:
            raise ValueError('actual payload changed during streamed metadata pass')
        # Recheck real ownership, debt and raw backing before certification.
        base.quiescent(provider,engine);base.validate_backing(p)
        if base.identity(p,engine)!=closure['identity']:raise ValueError('source identity drift')
        seal={'state_sha256':base.sha(root/'state.json'),'payload_sha256':payload_sha,'schema':base.SCHEMA}
        with (root/'COMPLETE.json').open('xb') as f:
            f.write(base.canonical(seal));f.flush();os.fsync(f.fileno())
        fd=os.open(root,os.O_RDONLY)
        try:os.fsync(fd)
        finally:os.close(fd)
        return {'producer_seal':seal,'stream_metrics':first,
                'full_encoded_tree_or_closure_bytes_materialized':False,
                'atomic_publication_performed':False}
    except BaseException:
        if not writer.f.closed:writer.close()
        raise


def profile_streamed_state(base,provider,engine,*,enabled=False):
    """Read-only actual state traversal. Counts are not a host admission guard."""
    if enabled is not True:raise ValueError('streamed state profile is default off')
    require_source(base);p=base.quiescent(provider,engine);base.validate_backing(p)
    class Count:
        def __init__(self):self.bytes=0
        def write(self,data):self.bytes+=len(data);return len(data)
    writer=base.Writer.__new__(base.Writer);writer.f=Count();writer.bytes=0;writer.arrays=0;writer.array_temporary_bytes=0
    metadata=Count();metrics=stream_typed_state(base,base.snapshot_state(p,engine),writer,metadata,enabled=True)
    return dict(metrics,payload_bytes=writer.bytes,serialized_arrays=writer.arrays,
                maximum_array_contiguity_temporary_bytes=writer.array_temporary_bytes,
                workspace_page_upper_bytes=None,allocator_peak_proved=False,
                producer_state_modified=False,physical_admission=False)

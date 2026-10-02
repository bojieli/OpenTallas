"""Opt-in quiescent actual-provider checkpoint. No pickle or arithmetic callback.

The caller supplies an exact fresh cold (provider, engine) constructor. Historical
journals are evidence, never replayed as data. This cannot recover exited R45 RAM.
"""
import hashlib
import inspect
import json
import os
from pathlib import Path
import numpy as np

SCHEMA = 'DS_ACTUAL_PRODUCER_QUIESCENT_RESUME_V1'
STATE = ('published', 'locations', 'backing', 'seq', 'query_visible', 'routes',
         'route_consumers', 'engram_owners', 'field_locations',
         'fullgraph_source_sha', 'fullgraph_source_failed')
PORT_STATE = ('extents', 'tags', 'qd', 'write_cap', 'read_ticks', 'write_ticks',
              'reverse_ticks', 'costs', 'cost_scope', 'accept_sequence', 'backing',
              'generations', 'now', 'order', 'allocation_identity')
PROVIDER_FIELDS=set(STATE)|{'journal_budget','retired_journals','manifest','native','homes',
    'generation','revision','checkpoint','views','memories','trace','immutable_views','rf','state',
    'bindings','source_images','auxiliary_images','pending_routes','codec_receipts','query_homes',
    'history','history_view_leases','C0_source_views'}
ENGINE_FIELDS={'provider','native','dispatch','generation','revision','homes','retired','last_use',
    'allocations','journal','native_calls','expected_outputs','groups','unconsumed_plan',
    'unconsumed_retired','pc10_endpoint_scope','_verified_checkpoint_resume'}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(1048576), b''): h.update(b)
    return h.hexdigest()


def unwrap(provider):
    # Comparators contain expected outputs. They are never traversed or saved.
    return provider.provider if type(provider).__name__ == 'Observed' else provider


def quiescent(provider, engine):
    p = unwrap(provider)
    unknown=set(vars(p))-PROVIDER_FIELDS
    if unknown:raise ValueError('unknown provider object state: '+','.join(sorted(unknown)))
    unknown=set(vars(engine))-ENGINE_FIELDS
    if unknown:raise ValueError('unknown engine object state: '+','.join(sorted(unknown)))
    if engine.provider is not provider: raise ValueError('exact engine/provider object')
    if p.generation != engine.generation: raise ValueError('generation mismatch')
    if hasattr(p,'fullgraph_source_sha') or hasattr(p,'fullgraph_source_failed'):
        if getattr(p,'fullgraph_source_failed',None) is not False:
            raise ValueError('failed or incomplete fullgraph source')
        if getattr(p,'fullgraph_source_sha',None)!=hashlib.sha256(canonical(p.native)).hexdigest():
            raise ValueError('fullgraph source identity mismatch')
    for name in ('views', 'memories', 'pending_routes', 'history_view_leases'):
        if getattr(p, name, None): raise ValueError('live owner: ' + name)
    for name in ('rf', 'state'):
        for port in getattr(p, name, {}).values():
            for field in ('live', 'queue', 'calendar', 'resident', 'faults'):
                if getattr(port, field): raise ValueError('live reverse/provider debt: ' + field)
            if port.events.closed: raise ValueError('closed live backing port')
    history = getattr(p, 'history', None)
    if history is not None and (history.leases or history.pending):
        raise ValueError('live/partial paired history')
    for obj in (getattr(p, 'C0_source_views', None), getattr(engine, 'groups', None)):
        if obj is not None and obj.failed: raise ValueError('failed bridge/group')
    groups=getattr(engine,'groups',None)
    if groups is not None and getattr(getattr(groups,'shared',None),'memories',{}):
        raise ValueError('shared source owners require separate schema before checkpoint')
    retired = engine.retired
    if not retired or any(type(pc) is not int for pc in retired) or retired != set(range(max(retired)+1)):
        raise ValueError('complete retired prefix required')
    return p


def identity(p, engine):
    manifest = dict(p.manifest)
    manifest.pop('journal_root', None)  # sole permitted coldconstructor relocation
    source = {}
    for obj in (p, engine):
        for cls in type(obj).__mro__:
            try: path = inspect.getsourcefile(cls)
            except TypeError: path = None
            if path and Path(path).is_file():
                parts=Path(path).parts
                marker='tools' if 'tools' in parts else 'results' if 'results' in parts else None
                key=str(Path(*parts[parts.index(marker):])) if marker else str(Path(path).resolve())
                source[key] = sha(path)
    # Source-image identities are exact immutable input records, not expected output.
    images = {name:p.manifest.get(name,[]) for name in ('initial_versions','history_images','view_bindings')}
    return dict(manifest_sha256=hashlib.sha256(canonical(manifest)).hexdigest(),
        native_sha256=hashlib.sha256(canonical(p.native)).hexdigest(),
        homes_sha256=hashlib.sha256(canonical(p.homes)).hexdigest(),
        last_use_sha256=hashlib.sha256(canonical(engine.last_use)).hexdigest(),
        dispatch_sha256=hashlib.sha256(canonical(engine.dispatch)).hexdigest(),
        allocations_sha256=hashlib.sha256(canonical(getattr(engine,'allocations',{}))).hexdigest(),
        helper_sha256=sha(__file__),
        retention_policy_sha256=hashlib.sha256(canonical({'unconsumed_plan':getattr(engine,'unconsumed_plan',{}),
            'pc10_endpoint_scope':getattr(engine,'pc10_endpoint_scope',{})})).hexdigest(),
        revision=p.revision, generation=p.generation, source_sha256=source,
        immutable_inputs_sha256=hashlib.sha256(canonical(images)).hexdigest())


def verify_inputs(p):
    seen = {}
    images = list(getattr(p, 'source_images', {}).values()) + list(getattr(p, 'auxiliary_images', {}).values())
    if hasattr(p, 'history'): images += list(p.history.images.values())
    for image in images:
        record = image.record; path = str(Path(record['path']).resolve())
        wanted = record.get('sha256', record.get('file_sha256'))
        if not wanted: raise ValueError('immutable input hash required')
        if path not in seen: seen[path] = sha(path)
        if seen[path] != wanted: raise ValueError('immutable input drift')
    index = p.checkpoint.path / 'model.safetensors.index.json'
    if sha(index) != p.manifest['checkpoint_index_sha256']: raise ValueError('checkpoint index drift')
    return {'unique_source_files': len(seen), 'source_file_bytes': sum(Path(f).stat().st_size for f in seen)}


def checkpoint_shards(p):
    return {name:{'path':str(p.checkpoint.path/name),
                  'stamp':[stamp.st_dev,stamp.st_ino,stamp.st_size,stamp.st_mtime_ns,stamp.st_ctime_ns],
                  'header_sha256':digest}
            for name,(_,header,base,stamp,digest) in p.checkpoint.files.items()}


def verify_shards(rows):
    import struct
    for row in rows.values():
        path=Path(row['path']);stamp=path.stat()
        if [stamp.st_dev,stamp.st_ino,stamp.st_size,stamp.st_mtime_ns,stamp.st_ctime_ns]!=row['stamp']:
            raise ValueError('checkpoint shard identity changed')
        with path.open('rb') as f:
            length=struct.unpack('<Q',f.read(8))[0]
            header=f.read(length)
        if len(header)!=length or hashlib.sha256(header).hexdigest()!=row['header_sha256']:
            raise ValueError('checkpoint shard header drift')


def lock_shards(p,rows):
    import fcntl,struct
    verify_shards(rows)
    for name,row in rows.items():
        if str(p.checkpoint.path/name)!=row['path']:raise ValueError('checkpoint shard path')
        if name in p.checkpoint.files:continue
        fd=os.open(row['path'],os.O_RDONLY)
        try:
            fcntl.flock(fd,fcntl.LOCK_SH|fcntl.LOCK_NB)
            stamp=os.fstat(fd)
            if [stamp.st_dev,stamp.st_ino,stamp.st_size,stamp.st_mtime_ns,stamp.st_ctime_ns]!=row['stamp']:
                raise ValueError('checkpoint changed before retained lock')
            n=struct.unpack('<Q',os.pread(fd,8,0))[0];raw=os.pread(fd,n,8)
            if hashlib.sha256(raw).hexdigest()!=row['header_sha256']:raise ValueError('locked header drift')
            p.checkpoint.files[name]=(fd,json.loads(raw),8+n,stamp,row['header_sha256'])
        except BaseException:os.close(fd);raise


class Writer:
    def __init__(self, root):
        self.f = (root/'payload.bin').open('xb'); self.bytes = 0; self.arrays = 0
    def tree(self, v):
        if isinstance(v, np.dtype):
            if v.hasobject: raise ValueError('object dtype')
            return {'dtype':v.str}
        if isinstance(v, np.ndarray):
            if v.dtype.hasobject: raise ValueError('object payload forbidden')
            a = np.ascontiguousarray(v); offset = self.bytes
            raw = memoryview(a).cast('B')
            for first in range(0, len(raw), 1048576): self.f.write(raw[first:first+1048576])
            self.bytes += len(raw); self.arrays += 1
            return {'array': [offset, len(raw), a.dtype.str, list(a.shape), bool(v.flags.writeable)]}
        if isinstance(v, (bytes, bytearray)):
            offset = self.bytes; self.f.write(v); self.bytes += len(v)
            return {'bytes': [offset, len(v), isinstance(v, bytearray)]}
        if isinstance(v, np.generic): return self.tree(v.item())
        if isinstance(v, dict): return {'dict': [[self.tree(k), self.tree(x)] for k, x in v.items()]}
        if isinstance(v, (tuple, list, set)): return {type(v).__name__: [self.tree(x) for x in v]}
        if v is None or type(v) in (str, int, float, bool): return v
        raise ValueError('unpriced/untyped state: ' + type(v).__name__)
    def close(self):
        self.f.flush(); os.fsync(self.f.fileno()); self.f.close()


def read_tree(v, payload):
    if not isinstance(v, dict): return v
    if len(v) != 1: raise ValueError('typed state encoding')
    kind, items = next(iter(v.items()))
    if kind=='dtype':
        dtype=np.dtype(items)
        if dtype.hasobject:raise ValueError('object dtype')
        return dtype
    if kind in ('array', 'bytes'):
        offset, n = items[:2]
        if type(offset) is not int or type(n) is not int or min(offset, n)<0 or offset+n>len(payload):
            raise ValueError('payload bounds')
        raw = payload[offset:offset+n]
        if kind == 'bytes': return bytearray(raw) if items[2] else bytes(raw)
        dtype = np.dtype(items[2])
        if dtype.hasobject: raise ValueError('object payload')
        a = np.frombuffer(raw, dtype=dtype).reshape(items[3]).copy()
        a.flags.writeable = items[4]; return a
    if kind == 'dict': return {read_tree(k,payload):read_tree(x,payload) for k,x in items}
    constructors = {'tuple': tuple, 'list': list, 'set': set}
    if kind not in constructors: raise ValueError('unknown state kind')
    return constructors[kind](read_tree(x,payload) for x in items)


def inventory(p, engine):
    p = quiescent(p, engine)
    ports = list(p.rf.values()) + list(p.state.values())
    arrays = [a for k,a in p.published.items() if k not in getattr(p,'source_images',{})]
    return dict(retired_PCs=sorted(engine.retired), produced_locations=len(p.locations),
        produced_and_initial_cached_array_bytes=sum(a.nbytes for a in arrays),
        raw_sectors=sum(len(x.backing) for x in ports),
        raw_sector_payload_bytes=32*sum(len(x.backing) for x in ports),
        future_source_windows=len(getattr(p,'source_images',{})),
        external_source_inputs=verify_inputs(p),
        metadata_bytes='priced exactly by serialized closure before publication',
        same_home_restore=True, hardware_qualified=False)


def validate_backing(p):
    """Check source homes against retained raw bytes without manufacturing ACKs.
    This is a read-only checkpoint check, not runtime provider consumption.
    """
    from h3_ds_checkpoint_provider_r30 import RF_SM, DTYPES
    def owned_bytes(port, base, size):
        for address in range(base,base+size,32):
            sector,within=divmod(address,32)
            backing=port.backing.get(('DeepSeek',rank,sector))
            n=min(32-within,base+size-address)
            if backing is None or len(backing)!=32 or any(v is None for v in backing[within:within+n]):
                raise ValueError('owned backing missing or partially valid')
    def check(port, base, raw):
        for offset in range(0,len(raw),32):
            address=base+offset;sector,within=divmod(address,32)
            backing=port.backing.get(('DeepSeek',rank,sector))
            # Actual sector keys are (target,rank,sector).
            if backing is None:raise ValueError('owned backing missing')
            wanted=raw[offset:offset+32]
            actual=backing[within:within+len(wanted)]
            if any(v is None for v in actual) or bytes(actual)!=wanted:
                raise ValueError('owned backing/produced bytes mismatch')
    for (version,rank),loc in p.locations.items():
        if loc.get('kind')=='state_fragment':
            # publish_state deliberately retains only addressed backing, not a
            # published ndarray. Validate that actual source binding verbatim;
            # never reconstruct this publication from a comparison witness.
            b=loc['binding'];shape=tuple(loc['shape']);dtype=np.dtype(loc['dtype'])
            size=int(np.prod(shape))*dtype.itemsize
            if (b['PC'],b['version'],b['rank'])!=(loc['pc'],version,rank):
                raise ValueError('state source identity mismatch')
            matches=[h for h in p.homes if h.get('version')==version and rank in h.get('rank_group',[]) and h.get('binding')==b]
            if len(matches)!=1 or matches[0]['home']['class']!='HBM_NATIVE_STATE':
                raise ValueError('state source home mismatch')
            if shape!=tuple(b['shape']) or dtype!=DTYPES[b['dtype']] or size>b['reservation_bytes'] or size%4:
                raise ValueError('state shape/type/extent mismatch')
            if b['base']%32 or not 33554432<=b['base'] or b['base']+b['reservation_bytes']>67108864 or rank not in p.state:
                raise ValueError('state finite aperture mismatch')
            owned_bytes(p.state[rank],b['base'],size)
            if (version,rank) in p.published:
                a=p.published[version,rank]
                if a.shape!=shape or a.dtype!=dtype:raise ValueError('owned shape/type mismatch')
                check(p.state[rank],b['base'],np.ascontiguousarray(a).tobytes())
            continue
        if (version,rank) not in p.published:raise ValueError('owned publication missing')
        a=p.published[version,rank]
        if tuple(loc['shape'])!=a.shape or np.dtype(loc['dtype'])!=a.dtype:
            raise ValueError('owned shape/type mismatch')
        words=np.ascontiguousarray(a).view(np.uint32).reshape(-1)
        if loc.get('kind')=='state_fragment':
            check(p.state[rank],loc['binding']['base'],words.tobytes())
        else:
            indices=np.arange(len(words));covered=set()
            for i in loc['indices']:
                h=p.homes[i]
                if h['version']!=version or rank not in h['rank_group']:raise ValueError('source home mismatch')
                block=(indices%5120)//256 if h['partition']=='HC_plane_dimension' else indices//256
                chosen=indices[block%32==h['SM']]
                if len(chosen)!=h['word_count'] or covered.intersection(chosen.tolist()):raise ValueError('home extent mismatch')
                covered.update(chosen.tolist());raw=words[chosen].tobytes()
                for copy in range(2):check(p.rf[rank],(h['SM']*2+copy)*RF_SM+h['home']['slot_first']*512,raw)
            if covered!=set(range(len(words))):raise ValueError('partial owned home')


def snapshot_state(p,engine):
    source_images=getattr(p,'source_images',{})
    state={name:getattr(p,name) for name in STATE if hasattr(p,name)}
    state['published']={k:v for k,v in p.published.items() if k not in source_images}
    ports={name:{rank:{f:getattr(port,f) for f in PORT_STATE} for rank,port in getattr(p,name).items()}
           for name in ('rf','state')}
    extra={}
    if hasattr(p,'history'):extra['history']={'visible':p.history.visible,'sequence':p.history.sequence}
    if hasattr(engine,'groups'):extra['group_completed']=engine.groups.completed
    if hasattr(engine,'unconsumed_retired'):extra['unconsumed_retired']=engine.unconsumed_retired
    return dict(provider=state,ports=ports,immutable_published_keys=[k for k in p.published if k in source_images],
                source_image_keys=list(source_images),retired=engine.retired,extra=extra)


def measure_state(p,engine):
    class Sink:
        def write(self,data):return len(data)
    counter=Writer.__new__(Writer);counter.f=Sink();counter.bytes=0;counter.arrays=0
    tree=counter.tree(snapshot_state(p,engine))
    return counter.bytes,len(canonical(tree)),counter.arrays


def save(provider, engine, path, *, enabled=False):
    if enabled is not True: raise ValueError('default-off checkpoint')
    p = quiescent(provider,engine); model = inventory(provider,engine); root=Path(path)
    validate_backing(p)
    stat=os.statvfs(root.parent)
    minimum=model['produced_and_initial_cached_array_bytes']+model['raw_sector_payload_bytes']
    if stat.f_bavail*stat.f_frsize < minimum: raise ValueError('disk headroom before payload')
    if root.exists(): raise ValueError('fresh checkpoint only')
    root.mkdir(parents=True); writer=Writer(root)
    try:
        snapshot=snapshot_state(p,engine)
        closure={'schema':SCHEMA,'identity':identity(p,engine),'inventory':model,'state':writer.tree(snapshot),
                 'opened_checkpoint_shards':checkpoint_shards(p)}
        writer.close(); closure['payload_sha256']=sha(root/'payload.bin')
        closure['payload_bytes']=(root/'payload.bin').stat().st_size
        data=canonical(closure)
        stat=os.statvfs(root)
        if stat.f_bavail*stat.f_frsize < len(data)+4096: raise ValueError('disk headroom before closure')
        with (root/'state.json').open('xb') as f: f.write(data); f.flush(); os.fsync(f.fileno())
        seal={'state_sha256':sha(root/'state.json'),'payload_sha256':closure['payload_sha256'],'schema':SCHEMA}
        with (root/'COMPLETE.json').open('xb') as f: f.write(canonical(seal)); f.flush(); os.fsync(f.fileno())
        fd=os.open(root,os.O_RDONLY); os.fsync(fd); os.close(fd)
        return seal
    except BaseException:
        if not writer.f.closed: writer.close()
        # Partial directories preserved; absence of COMPLETE forbids restore.
        raise


def restore(path, factory, *, expected_seal, enabled=False):
    if enabled is not True: raise ValueError('default-off restore')
    root=Path(path); seal=json.loads((root/'COMPLETE.json').read_bytes())
    if seal != expected_seal or seal['schema'] != SCHEMA: raise ValueError('trusted source checkpoint seal')
    for name,key in [('state.json','state_sha256'),('payload.bin','payload_sha256')]:
        if (root/name).is_symlink() or sha(root/name)!=seal[key]: raise ValueError('tampered checkpoint')
    closure=json.loads((root/'state.json').read_bytes())
    if closure['schema']!=SCHEMA or closure['payload_sha256']!=seal['payload_sha256']: raise ValueError('closure identity')
    verify_shards(closure['opened_checkpoint_shards'])
    # No side-effecting provider construction until the entire saved closure validates.
    size=(root/'payload.bin').stat().st_size
    payload=np.memmap(root/'payload.bin',dtype=np.uint8,mode='r') if size else b''
    saved=read_tree(closure['state'],payload)
    provider,engine=factory(); p=unwrap(provider)
    if p.views or p.memories or p.locations or engine.retired or p.rf or p.state:
        raise ValueError('restore requires exact cold empty producer')
    if identity(p,engine)!=closure['identity']: raise ValueError('cold source/manifest/home/retention mismatch')
    verify_inputs(p)
    lock_shards(p,closure['opened_checkpoint_shards'])
    from hbm_bound_event_journal_r30 import BoundSectorProvider, CompactSectors
    for name, ports in saved['ports'].items():
        for rank, s in ports.items():
            port=BoundSectorProvider(s['extents'],journal_budget=p.journal_budget,
                allocation_identity=s['allocation_identity'],tags=s['tags'],queue=s['qd'],
                write_residence=s['write_cap'],read_ticks=s['read_ticks'],write_ticks=s['write_ticks'],reverse_ticks=s['reverse_ticks'])
            for field,value in s.items(): setattr(port,field,value)
            port.backing=CompactSectors(port.backing)
            getattr(p,name)[rank]=port
    kept=set(saved['source_image_keys'])
    if not kept<=set(p.source_images):raise ValueError('cold future source views missing')
    released={k[0] for k in p.source_images if k not in kept}
    if any(k[0] in released for k in kept):raise ValueError('partial source rank release not modelled')
    for version in released:p.release_version(version,p.generation)
    if set(p.source_images)!=kept:raise ValueError('source retention policy release mismatch')
    cold=p.published
    for key in saved['immutable_published_keys']:
        if key not in p.source_images: raise ValueError('cold immutable view missing')
    for key,value in saved['provider']['published'].items():
        if key in cold and (cold[key].dtype!=value.dtype or cold[key].shape!=value.shape or cold[key].tobytes()!=value.tobytes()):
            raise ValueError('cold initial stimulus mismatch')
    for name,value in saved['provider'].items(): setattr(p,name,value)
    for key in saved['immutable_published_keys']: p.published[key]=p.source_images[key].check()
    engine.retired.clear();engine.retired.update(saved['retired'])
    extra=saved['extra']
    if 'history' in extra:
        p.history.visible=extra['history']['visible'];p.history.sequence=extra['history']['sequence']
    if 'group_completed' in extra:
        engine.groups.completed.clear();engine.groups.completed.update(extra['group_completed'])
    if 'unconsumed_retired' in extra: engine.unconsumed_retired=extra['unconsumed_retired']
    quiescent(provider,engine)
    validate_backing(p)
    return provider,engine


def execute_remaining(engine, *, stop_after):
    """Use the original source execute_operation, skipping only certified retired PCs.
    Original R45 run() cannot resume: it deliberately refuses already-retired PCs.
    """
    if not engine.retired or engine.retired!=set(range(max(engine.retired)+1)):
        raise ValueError('verified contiguous prefix required')
    if not getattr(engine,'_verified_checkpoint_resume',False):
        raise ValueError('resume loop requires successful verified restore')
    for op in engine.native['instructions']:
        if op['pc']>stop_after: break
        if op['pc'] not in engine.retired: engine.execute_operation(op)
    return sorted(engine.retired)


def project_checkpoint(engine, provider, witness, *, boundary_pc, destination):
    p=quiescent(provider,engine)
    if engine.retired!=set(range(boundary_pc+1)): raise ValueError('exact capture boundary')
    if witness is None or witness.failed or not witness.seen: raise ValueError('actual observation provenance required')
    if any(key[0]>boundary_pc or key[3]!=p.generation for key in witness.seen): raise ValueError('witness boundary/generation')
    required={key for key in witness.expected if key[0]<=boundary_pc}
    if witness.seen!=required:raise ValueError('complete actual observed prefix identities required')
    model=inventory(provider,engine)
    payload,metadata,arrays=measure_state(p,engine)
    # Walk the same serialization schema, including routes and append row data.
    # Future images/reference outputs never enter that payload tree.
    model['payload_bytes']=payload;model['serialized_arrays']=arrays
    model['typed_state_metadata_bytes']=metadata
    witness_metadata={'seen':[list(k) for k in sorted(witness.seen)],
        'initialization_provenance':witness.initialization_provenance,'observation_journal':witness.events.summary()}
    model['metadata_bytes_upper']=metadata+2*len(canonical(identity(p,engine)))+len(canonical(checkpoint_shards(p)))+len(canonical(witness_metadata))+2*len(canonical(model))+16384
    model['filesystem_reservation_bytes']=model['payload_bytes']+model['metadata_bytes_upper']
    dest=Path(destination);parent=dest.parent
    if dest.exists(): raise ValueError('fresh destination')
    stat=os.statvfs(parent);model['available_disk_bytes']=stat.f_bavail*stat.f_frsize
    if model['available_disk_bytes']<model['filesystem_reservation_bytes']:raise ValueError('checkpoint aggregate disk headroom')
    model['old_journal_bytes']=p.journal_budget.path.stat().st_size
    model['continuation_journal_bytes']='runner positive reviewed projection required separately; no zero default'
    return model


def join_storage_projection(projection, *, continuation_new_bytes, other_new_bytes, available_bytes):
    """Compose newly allocated disk only; existing journals already reduce free.
    The runner supplies reviewed incremental journal/index/dictionary demand.
    This is an admission calculation, not a filesystem capacity reservation.
    """
    for v in (continuation_new_bytes,other_new_bytes,available_bytes):
        if type(v) is not int or v<0:raise ValueError('exact nonnegative disk byte projection required')
    if continuation_new_bytes==0:raise ValueError('positive continuation projection required')
    checkpoint=projection['filesystem_reservation_bytes']
    if type(checkpoint) is not int or checkpoint<=0:raise ValueError('positive checkpoint projection required')
    required=checkpoint+continuation_new_bytes+other_new_bytes
    return dict(status='PASS_STORAGE_PROJECTION' if available_bytes>=required else 'REFUSE_STORAGE_HEADROOM',
        checkpoint_new_bytes=checkpoint,continuation_new_bytes=continuation_new_bytes,
        other_new_bytes=other_new_bytes,required_new_bytes=required,available_bytes=available_bytes,
        headroom_bytes=available_bytes-required,old_journal_bytes_already_in_used_space=projection['old_journal_bytes'],
        physical_qualified=False,capacity_reservation_acquired=False)


def capture_quiescent(engine, provider, witness, *, boundary_pc, destination, source_contract):
    projection=project_checkpoint(engine,provider,witness,boundary_pc=boundary_pc,destination=destination)
    if not source_contract or source_contract.get('identity')!=identity(unwrap(provider),engine):
        raise ValueError('explicit exact capture source contract')
    # Source-contract extensions are caller-owned metadata of arbitrary size.
    # Charge them before any payload write, rather than hiding them in margin.
    extra=len(canonical(source_contract))
    projection['metadata_bytes_upper']+=extra
    projection['filesystem_reservation_bytes']+=extra
    stat=os.statvfs(Path(destination).parent)
    if stat.f_bavail*stat.f_frsize<projection['filesystem_reservation_bytes']:
        raise ValueError('checkpoint aggregate metadata disk headroom')
    seal=save(provider,engine,destination,enabled=True)
    root=Path(destination)
    # Witness seen identities are metadata of actual observations only; expected
    # values/digests are never saved or fed to numeric execution.
    actual={'seen':[list(k) for k in sorted(witness.seen)],
            'initialization_provenance':witness.initialization_provenance,
            'observation_journal':witness.events.summary(),
            'source_contract':source_contract,'boundary_pc':boundary_pc,
            'projection':projection,'producer_seal':seal}
    with (root/'actual_observations.json').open('xb') as f:
        f.write(canonical(actual));f.flush();os.fsync(f.fileno())
    receipt={'producer_seal':seal,'actual_observations_sha256':sha(root/'actual_observations.json')}
    with (root/'RUNNER_COMPLETE.json').open('xb') as f:
        f.write(canonical(receipt));f.flush();os.fsync(f.fileno())
    fd=os.open(root,os.O_RDONLY);os.fsync(fd);os.close(fd)
    return receipt


def verify_checkpoint(checkpoint_dir, *, source_contract, next_pc, constructor_contract):
    root=Path(checkpoint_dir);receipt=json.loads((root/'RUNNER_COMPLETE.json').read_bytes())
    if receipt!=constructor_contract.get('checkpoint_receipt'):raise ValueError('trusted external checkpoint receipt')
    if sha(root/'actual_observations.json')!=receipt['actual_observations_sha256']:raise ValueError('actual observation drift')
    actual=json.loads((root/'actual_observations.json').read_bytes())
    if actual['source_contract']!=source_contract or constructor_contract.get('identity')!=source_contract.get('identity'):
        raise ValueError('source/constructor contract')
    if next_pc!=actual['boundary_pc']+1:raise ValueError('exact contiguous next PC')
    for name,key in [('state.json','state_sha256'),('payload.bin','payload_sha256')]:
        if (root/name).is_symlink() or sha(root/name)!=receipt['producer_seal'][key]:raise ValueError('actual payload drift')
    return {'checkpoint_dir':str(root),'receipt':receipt,'actual':actual,'source_contract':source_contract,'next_pc':next_pc}


def restore_quiescent(verified_manifest, engine, provider, witness):
    v=verified_manifest
    # Reverify on use; callers cannot turn a stale verified object into authority.
    fresh=verify_checkpoint(v['checkpoint_dir'],source_contract=v['source_contract'],next_pc=v['next_pc'],
        constructor_contract={'identity':identity(unwrap(provider),engine),'checkpoint_receipt':v['receipt']})
    if fresh!=v:raise ValueError('stale verified manifest')
    actual=v['actual']
    p=unwrap(provider)
    # Validate *all* cold constructor ownership before applying any saved bytes.
    if p.views or p.memories or p.locations or engine.retired or p.rf or p.state:
        raise ValueError('restore requires cold producer')
    if witness.failed or witness.seen or witness.initialization_provenance!=actual['initialization_provenance']:
        raise ValueError('exact fresh witness provenance')
    seen={tuple(k) for k in actual['seen']}
    if not seen<=set(witness.expected):raise ValueError('actual witness source identities')
    restore(v['checkpoint_dir'],lambda:(provider,engine),expected_seal=v['receipt']['producer_seal'],enabled=True)
    if engine.retired!=set(range(v['next_pc'])):raise ValueError('restored retired prefix')
    witness.seen=seen
    engine._verified_checkpoint_resume=True
    return {'retired':sorted(engine.retired),'next_pc':v['next_pc'],
            'prior_actual_observation_journal':actual['observation_journal'],
            'same_home_restored':True,'hardware_qualified':False}

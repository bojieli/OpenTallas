"""Opt-in quiescent actual-provider checkpoint. No pickle or arithmetic callback.

The caller supplies an exact fresh cold (provider, engine) constructor. Historical
journals are evidence, never replayed as data. This cannot recover exited R45 RAM.
"""
import hashlib
import inspect
import json
import os
import struct
import sys
from pathlib import Path
import numpy as np

SCHEMA = 'DS_ACTUAL_PRODUCER_QUIESCENT_RESUME_V3'
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
RUN_SCOPE_FIELDS=('prefix_stop','journal_root','journal_capacity_bytes')
ROLE_PINS={'h3_ds_checkpoint_provider_r30.py':'4b7a74d246f8a594062ddc27a1c23038484342838cd1ae9fef173eab605722b9',
    'hbm_bound_event_journal_r30.py':'1efaea518056231512ebd1a59743d66ddedd775728183e70913a9755d53ba9f0'}
CALENDAR_PIN='dc04ddb7da27b7a1230691a01bba6af6bdd45bacf59b8afc58b0ad853c6c0a21'
JOIN_PIN='00bd0b2fa93de9afd11ca65722563fec2df939729a937413f4e66451418d36c2'


def compact_runtime():
    import h3_complete_native_calendar_successor_r1 as c
    import ds_hbm_additive_endpoint_join_r54 as join
    if sha(c.__file__)!=CALENDAR_PIN or sha(join.__file__)!=JOIN_PIN:
        raise ValueError('exact compact runtime enrollment source required')
    if join.verify_calendar() is not c:raise ValueError('compact calendar origin mismatch')
    return c,join


def event_backend(port):
    from h3_ds_query_provider_r36 import SizedEvents
    return port.events.source if type(port.events)is SizedEvents else port.events


def lifecycle_state(port):
    events=event_backend(port)
    if not hasattr(events,'validator'):return None
    c,join=compact_runtime()
    if type(events)is not c.CompactDiskEvents or type(events.validator)is not c.CompactLifecycle:
        raise ValueError('exact compact lifecycle classes required')
    join.verify_installed_provider(type(port))
    v=events.validator
    if v.live or v.fault is not None or events.fault is not None or events.closed:
        raise ValueError('live/faulted compact lifecycle debt')
    if set(vars(v))!={'live','generations','fault','last_tick','tag_capacity','write_capacity'}:
        raise ValueError('unknown compact lifecycle state')
    if any(type(tag)is not int or not 0<=tag<port.tags or gen!=port.generations[tag]
           for tag,gen in v.generations.items()) or any(gen and v.generations.get(tag)!=gen for tag,gen in enumerate(port.generations)):
        raise ValueError('compact lifecycle tag generation mismatch')
    if v.tag_capacity not in (None,port.tags) or v.write_capacity not in (None,port.write_cap) or v.last_tick>port.now:
        raise ValueError('compact lifecycle capacity/time mismatch')
    return {name:getattr(v,name) for name in ('generations','last_tick','tag_capacity','write_capacity')}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(1048576), b''): h.update(b)
    return h.hexdigest()


def run_scope(p):
    cap=p.manifest['journal_capacity_bytes'];root=str(Path(p.manifest['journal_root']).resolve())
    if type(cap)is not int or cap<131072 or p.journal_budget.cap!=cap or str(p.journal_budget.root.resolve())!=root:
        raise ValueError('actual journal evidence scope mismatch')
    return dict(prefix_stop=p.manifest.get('prefix_stop'),journal_root=root,journal_capacity_bytes=cap)


def scope_role_proof(p,engine):
    """Narrow evidence-budget role, never a blanket resource exemption."""
    from h3_ds_checkpoint_provider_r30 import Provider as Base
    from hbm_bound_event_journal_r30 import JournalBudget
    compact=None
    if Path(inspect.getsourcefile(type(p.journal_budget))).name=='h3_complete_native_calendar_successor_r1.py':
        c,join=compact_runtime()
        if type(p.journal_budget)is not c.CompactJournalBudget:raise ValueError('unreviewed compact budget role')
        from hbm_bound_event_journal_r30 import BoundSectorProvider
        join.verify_installed_provider(BoundSectorProvider)
        compact={Path(c.__file__).name:CALENDAR_PIN,Path(join.__file__).name:JOIN_PIN}
        # The installer changes aliases, never this immutable source file.
        sources=(inspect.getsourcefile(Base),str(Path(__file__).with_name('hbm_bound_event_journal_r30.py')))
    else:
        if type(p.journal_budget)is not JournalBudget:raise ValueError('unreviewed journal budget role')
        sources=(inspect.getsourcefile(Base),inspect.getsourcefile(JournalBudget))
    pins={}
    for source in sources:
        path=Path(source);digest=sha(path)
        if digest!=ROLE_PINS.get(path.name):raise ValueError('journal evidence role source mismatch')
        pins[path.name]=digest
    for obj in (p,engine):
        for cls in type(obj).__mro__:
            if cls is object:continue
            body=inspect.getsource(cls)
            if 'prefix_stop' in body or (cls is not Base and any(k in body for k in ('journal_capacity_bytes','journal_root'))):
                raise ValueError('unreviewed run-scope use in data class')
    return dict(schema='SOURCE_JOURNAL_EVIDENCE_ROLE_V1',source_sha256=pins,
        compact_runtime_source_sha256=compact,
        native_ports_unchanged=True,capacity_role='SQLite metadata admission guard; not tags/queues/backing extent',
        stop_role='external execution bound; no use in provider/engine data classes')


def data_identity(value):
    # Used ONLY by an explicit validated transition; normal enrollment stays
    # strict. Every other identity field, including full future-use, is exact.
    return {k:v for k,v in value.items() if k!='manifest_sha256'}


def unwrap(provider):
    # Comparators contain expected outputs. They are never traversed or saved.
    return provider.provider if type(provider).__name__ == 'Observed' else provider


def shared_factory(p,engine):
    shared=getattr(getattr(engine,'groups',None),'shared',None)
    if shared is None:return None
    from h4_hbm_w19_pc10_endpoints import ProductionSharedFactory
    if type(shared) is not ProductionSharedFactory or set(vars(shared))!={'budget','memories','sources'}:
        raise ValueError('exact PC10 shared factory schema required')
    if shared.budget is not p.journal_budget:raise ValueError('shared journal ownership mismatch')
    return shared


def validate_shared(p,engine):
    shared=shared_factory(p,engine)
    if shared is None:return
    from h4_hbm_w19_pc10_endpoints import RF_BYTES, SHARED_BYTES, inputs
    if shared.sources!=inputs():raise ValueError('shared immutable source contract mismatch')
    if len(shared.memories)>96*32:raise ValueError('shared capacity')
    for key,memory in shared.memories.items():
        if set(vars(memory))!={'extent','p','serial','owner'}:raise ValueError('unknown shared memory state')
        owner=memory.owner;rank,sm=key
        if (type(rank)is not int or not 0<=rank<96 or type(sm)is not int or not 0<=sm<32
            or owner.get('rank')!=rank or owner.get('SM')!=sm or owner.get('PC')!=10
            or type(owner.get('generation'))is not int or owner['generation']!=p.generation
            or set(owner)-{'PC','rank','SM','generation','tile','template'}):
            raise ValueError('shared source owner identity mismatch')
        if 10 not in engine.retired:raise ValueError('unretired shared source owner')
        if 'tile' in owner and (type(owner['tile'])is not int or owner['tile']<0):raise ValueError('shared tile identity')
        if 'template' in owner and not isinstance(owner['template'],str):raise ValueError('shared template identity')
        extent=dict(base=RF_BYTES+sm*SHARED_BYTES,bytes=SHARED_BYTES,rank=rank,SM=sm)
        port=memory.p
        if set(vars(port))!=set(PORT_STATE)|{'live','queue','events','calendar','resident','faults'}:
            raise ValueError('unknown shared provider state')
        if memory.extent!=extent or port.extents!={('DeepSeek',rank):[dict(base=extent['base'],bytes=SHARED_BYTES)]}:
            raise ValueError('shared exact finite extent mismatch')
        if port.allocation_identity!=dict(owner,die=rank,address_class='shared'):
            raise ValueError('shared allocation identity mismatch')
        if any(getattr(port,f) for f in ('live','queue','calendar','resident','faults')) or port.events.closed:
            raise ValueError('live shared reverse/provider debt')
        lifecycle_state(port)
        if type(memory.serial)is not int or not 0<=memory.serial<=2**40 or memory.serial!=port.accept_sequence:
            raise ValueError('shared serial/accepted sequence mismatch')
        if port.tags!=1 or len(port.generations)!=1:raise ValueError('shared source tag geometry')
        for (target,r,sector),data in port.backing.items():
            if target!='DeepSeek' or r!=rank or not extent['base']<=sector*32<extent['base']+SHARED_BYTES or len(data)!=32:
                raise ValueError('shared backing address mismatch')
            if any(v is not None and (type(v)is not int or not 0<=v<256) for v in data):raise ValueError('shared byte validity')


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
            lifecycle_state(port)
    history = getattr(p, 'history', None)
    if history is not None and (history.leases or history.pending):
        raise ValueError('live/partial paired history')
    for obj in (getattr(p, 'C0_source_views', None), getattr(engine, 'groups', None)):
        if obj is not None and obj.failed: raise ValueError('failed bridge/group')
    validate_shared(p,engine)
    retired = engine.retired
    if not retired or any(type(pc) is not int for pc in retired) or retired != set(range(max(retired)+1)):
        raise ValueError('complete retired prefix required')
    return p


def identity(p, engine):
    manifest = dict(p.manifest)
    manifest.pop('journal_root', None)  # sole permitted coldconstructor relocation
    data_manifest=dict(p.manifest)
    for name in RUN_SCOPE_FIELDS:data_manifest.pop(name,None)
    source = {}
    shared=shared_factory(p,engine)
    for obj in (p, engine) if shared is None else (p,engine,shared):
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
        journal_backend_sha256=hashlib.sha256(canonical(scope_role_proof(p,engine))).hexdigest(),
        manifest_data_sha256=hashlib.sha256(canonical(data_manifest)).hexdigest(),
        native_sha256=hashlib.sha256(canonical(p.native)).hexdigest(),
        homes_sha256=hashlib.sha256(canonical(p.homes)).hexdigest(),
        last_use_sha256=hashlib.sha256(canonical(engine.last_use)).hexdigest(),
        dispatch_sha256=hashlib.sha256(canonical(engine.dispatch)).hexdigest(),
        allocations_sha256=hashlib.sha256(canonical(getattr(engine,'allocations',{}))).hexdigest(),
        helper_sha256=sha(__file__),
        retention_policy_sha256=hashlib.sha256(canonical({'unconsumed_plan':getattr(engine,'unconsumed_plan',{}),
            'pc10_endpoint_scope':getattr(engine,'pc10_endpoint_scope',{})})).hexdigest(),
        revision=p.revision, generation=p.generation, source_sha256=source,
        immutable_inputs_sha256=hashlib.sha256(canonical(images)).hexdigest(),
        shared_sources_sha256={} if shared is None else {k:hashlib.sha256(v).hexdigest() for k,v in sorted(shared.sources.items())})


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


class SectorBacking:
    def __init__(self,port):self.values=port.backing;self.extents=port.extents


SECTOR_RECORD=struct.Struct('<HQI32s')


class Writer:
    def __init__(self, root):
        self.f = (root/'payload.bin').open('xb'); self.bytes = 0; self.arrays = 0; self.array_temporary_bytes = 0
    def tree(self, v):
        if type(v)is SectorBacking:
            table=[];lookup={};offset=self.bytes
            for (target,rank,sector),values in v.values.items():
                if type(target)is not str or type(rank)is not int or type(sector)is not int or sector<0 or len(values)!=32:
                    raise ValueError('typed actual sector identity/size required')
                if not any(e['base']<=sector*32 and sector*32+32<=e['base']+e['bytes'] for e in v.extents.get((target,rank),[])):
                    raise ValueError('sector outside actual source port extent')
                key=(target,rank)
                if key not in lookup:lookup[key]=len(table);table.append(key)
                if len(table)>65536:raise ValueError('sector identity table width')
                mask=0;raw=bytearray(32)
                for i,value in enumerate(values):
                    if value is not None:
                        if type(value)is not int or not 0<=value<256:raise ValueError('sector byte validity')
                        mask|=1<<i;raw[i]=value
                self.f.write(SECTOR_RECORD.pack(lookup[key],sector,mask,raw));self.bytes+=SECTOR_RECORD.size
            return {'sector_backing':{'table':table,'offset':offset,'count':len(v.values),'record_bytes':SECTOR_RECORD.size}}
        if isinstance(v, np.dtype):
            if v.hasobject: raise ValueError('object dtype')
            return {'dtype':v.str}
        if isinstance(v, np.ndarray):
            if v.dtype.hasobject: raise ValueError('object payload forbidden')
            if not v.flags.c_contiguous:self.array_temporary_bytes=max(self.array_temporary_bytes,v.nbytes)
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
    if kind=='sector_backing':
        from hbm_bound_event_journal_r30 import CompactSectors
        offset=items['offset'];count=items['count'];table=items['table']
        if type(offset)is not int or type(count)is not int or min(offset,count)<0 or items['record_bytes']!=SECTOR_RECORD.size or offset+count*SECTOR_RECORD.size>len(payload):
            raise ValueError('sector payload bounds')
        if len(table)>65536 or len({tuple(key) for key in table})!=len(table):raise ValueError('sector table identity')
        if any(len(key)!=2 or type(key[0])is not str or type(key[1])is not int for key in table):raise ValueError('sector typed table')
        out=CompactSectors()
        for i in range(count):
            index,sector,mask,raw=SECTOR_RECORD.unpack_from(payload,offset+i*SECTOR_RECORD.size)
            if index>=len(table):raise ValueError('sector table index')
            key=(*table[index],sector)
            if key in out:raise ValueError('duplicate serialized sector')
            out[key]=[raw[j] if mask>>j&1 else None for j in range(32)]
        return out
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
    shared=shared_factory(p,engine)
    ports = list(p.rf.values()) + list(p.state.values()) + ([] if shared is None else [m.p for m in shared.memories.values()])
    arrays = [a for k,a in p.published.items() if k not in getattr(p,'source_images',{})]
    return dict(retired_PCs=sorted(engine.retired), produced_locations=len(p.locations),
        produced_and_initial_cached_array_bytes=sum(a.nbytes for a in arrays),
        raw_sectors=sum(len(x.backing) for x in ports),
        raw_sector_payload_bytes=32*sum(len(x.backing) for x in ports),
        future_source_windows=len(getattr(p,'source_images',{})),
        retained_shared_homes=0 if shared is None else len(shared.memories),
        external_source_inputs=verify_inputs(p),
        metadata_bytes='priced exactly by serialized closure before publication',
        same_home_restore=True, hardware_qualified=False)


def journal_inventory(p,engine,witness=None, *, hashes=False):
    """Freeze/flush source evidence streams; never replay them as operands."""
    shared=shared_factory(p,engine)
    streams=[port.events for port in list(p.rf.values())+list(p.state.values())]
    if shared is not None:streams.extend(m.p.events for m in shared.memories.values())
    for holder in (getattr(engine,'journal',None),getattr(engine,'native_calls',None),getattr(witness,'events',None)):
        if holder is not None:
            if hasattr(holder,'flush'):streams.append(holder)
            elif hasattr(holder,'summary'):holder.summary()
    for stream in streams:stream.flush()
    p.journal_budget.db.commit();root=p.journal_budget.root.resolve();rows=[]
    for path in sorted(root.iterdir()):
        if path.is_symlink() or not path.is_file():raise ValueError('journal inventory regular files only')
        allowed=path.name in ('events.sqlite','dictionary.sqlite','checkpoint_restore_scope.json')
        if not allowed:
            import re
            if not re.fullmatch(r'[0-9]{8}\.(events|index)',path.name):raise ValueError('unknown journal inventory file')
            mate=path.with_suffix('.index' if path.suffix=='.events' else '.events')
            if not mate.is_file() or mate.is_symlink():raise ValueError('partial compact event/index pair')
        st=path.stat();stamp=[st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns,st.st_ctime_ns]
        digest=None
        if hashes:
            with path.open('rb') as f:os.fsync(f.fileno())
            digest=sha(path);after=path.stat()
            if stamp!=[after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns]:raise ValueError('journal changed during hash closure')
        rows.append(dict(path=str(path),bytes=st.st_size,stamp=stamp,sha256=digest))
    if hashes:
        fd=os.open(root,os.O_RDONLY);os.fsync(fd);os.close(fd)
    return dict(root=str(root),files=rows,total_bytes=sum(r['bytes'] for r in rows),
        hashes_complete=hashes,physical_qualified=False)


def verify_journal_inventory(record):
    if record.get('hashes_complete')is not True:raise ValueError('journal hash closure required')
    root=Path(record['root'])
    expected={row['path'] for row in record['files']}
    if {str(path) for path in root.iterdir()}!=expected:
        raise ValueError('historical journal inventory drift')
    for row in record['files']:
        path=Path(row['path'])
        if path.is_symlink() or not path.is_file():raise ValueError('historical journal missing')
        st=path.stat()
        if row['stamp']!=[st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns,st.st_ctime_ns] or sha(path)!=row['sha256']:
            raise ValueError('historical journal drift')


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
    validate_query_fields(p)


def validate_query_fields(p):
    """Read addressed field backing directly; no new requests or credits."""
    visible=getattr(p,'query_visible',{})
    if not visible:return
    from ds_hbm_history_codec_r36 import decode
    manifest={ (b['version'],b['rank'],b['field']):b for b in p.manifest['query_field_homes']['rows'] }
    if p.query_homes!=manifest:raise ValueError('query field manifest home mismatch')
    for (version,rank),identity in visible.items():
        if identity['version']!=version or identity['rank']!=rank or identity['generation']!=p.generation:
            raise ValueError('query visible source identity mismatch')
        if (version,rank) not in p.locations or (version,rank) not in p.published or p.locations[version,rank]['pc']!=identity['PC']:
            raise ValueError('query visible parent publication missing')
        if identity['home_indices']!=p.locations[version,rank].get('indices'):
            raise ValueError('query visible parent home identity mismatch')
        op=p.native['instructions'][identity['PC']]
        if op['pc']!=identity['PC'] or op['family']!='index_q':raise ValueError('query visible source opcode mismatch')
        arrays={};intervals=[]
        for field in ('query_codes','query_exp'):
            b=manifest[version,rank,field];dtype=np.dtype({'U32':'<u4','I64':'<i8'}[b['dtype']])
            size=int(np.prod(b['shape']))*dtype.itemsize
            if (b['PC'],b['generation'])!=(identity['PC'],p.generation) or size!=b['bytes'] or size>b['reservation_bytes'] or b['base']%32 or not 33554432<=b['base'] or b['base']+b['reservation_bytes']>67108864:
                raise ValueError('query exact field extent/identity mismatch')
            lo,hi=b['base'],b['base']+b['reservation_bytes']
            if any(lo<end and start<hi for start,end in intervals):raise ValueError('query field alias')
            intervals.append((lo,hi));raw=bytearray()
            for address in range(lo,lo+size,32):
                data=p.state[rank].backing.get(('DeepSeek',rank,address//32));n=min(32,lo+size-address)
                if data is None or len(data)!=32 or any(v is None for v in data[:n]):raise ValueError('query field backing missing')
                raw.extend(data[:n])
            arrays[field]=np.frombuffer(raw,dtype=dtype).reshape(b['shape'])
        exp=arrays['query_exp']
        if exp.dtype==np.uint32:exp=exp.view(np.int32).astype(np.int64)
        actual=decode(arrays['query_codes'],exp,'FP4E8');parent=p.published[version,rank]
        if parent.dtype!=np.float32 or parent.shape!=(32,128) or not np.array_equal(actual.view(np.uint32),parent.view(np.uint32)):
            raise ValueError('query codec/actual parent bit identity mismatch')


def snapshot_state(p,engine):
    source_images=getattr(p,'source_images',{})
    state={name:getattr(p,name) for name in STATE if hasattr(p,name)}
    state['published']={k:v for k,v in p.published.items() if k not in source_images}
    ports={name:{rank:port_state(port) for rank,port in getattr(p,name).items()}
           for name in ('rf','state')}
    extra={}
    if hasattr(p,'history'):extra['history']={'visible':p.history.visible,'sequence':p.history.sequence}
    if hasattr(engine,'groups'):extra['group_completed']=engine.groups.completed
    if hasattr(engine,'unconsumed_retired'):extra['unconsumed_retired']=engine.unconsumed_retired
    shared=shared_factory(p,engine)
    if shared is not None:
        extra['shared']={key:dict(extent=m.extent,owner=m.owner,serial=m.serial,
            port=port_state(m.p)) for key,m in shared.memories.items()}
    return dict(provider=state,ports=ports,immutable_published_keys=[k for k in p.published if k in source_images],
                source_image_keys=list(source_images),retired=engine.retired,extra=extra)


def port_state(port):
    state={f:getattr(port,f) for f in PORT_STATE}
    state['backing']=SectorBacking(port);state['compact_lifecycle']=lifecycle_state(port)
    return state


def apply_port_state(port,state):
    for field,value in state.items():
        if field!='compact_lifecycle':setattr(port,field,value)
    from hbm_bound_event_journal_r30 import CompactSectors
    port.backing=CompactSectors(port.backing)
    saved=state['compact_lifecycle'];events=event_backend(port)
    if saved is not None:
        c,_=compact_runtime()
        if type(events)is not c.CompactDiskEvents:raise ValueError('restored compact stream missing')
        for name,value in saved.items():setattr(events.validator,name,value)
        lifecycle_state(port)
    elif hasattr(events,'validator'):raise ValueError('journal format changed across restore')


def deep_metadata_bytes(tree):
    seen=set()
    def size(value):
        if id(value) in seen:return 0
        seen.add(id(value));n=sys.getsizeof(value)
        if isinstance(value,dict):n+=sum(size(k)+size(v) for k,v in value.items())
        elif isinstance(value,(list,tuple,set)):n+=sum(size(v) for v in value)
        return n
    return size(tree)


def measure_state(p,engine):
    class Sink:
        def write(self,data):return len(data)
    counter=Writer.__new__(Writer);counter.f=Sink();counter.bytes=0;counter.arrays=0;counter.array_temporary_bytes=0
    tree=counter.tree(snapshot_state(p,engine))
    encoded=len(canonical(tree))
    return counter.bytes,encoded,counter.arrays,deep_metadata_bytes(tree),counter.array_temporary_bytes


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
                 'run_scope':run_scope(p),'scope_role_proof':scope_role_proof(p,engine),
                 'historical_journal_inventory':journal_inventory(p,engine,hashes=True),
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


def restore(path, factory, *, expected_seal, enabled=False, run_scope_transition=None):
    if enabled is not True: raise ValueError('default-off restore')
    root=Path(path); seal=json.loads((root/'COMPLETE.json').read_bytes())
    if seal != expected_seal or seal['schema'] != SCHEMA: raise ValueError('trusted source checkpoint seal')
    for name,key in [('state.json','state_sha256'),('payload.bin','payload_sha256')]:
        if (root/name).is_symlink() or sha(root/name)!=seal[key]: raise ValueError('tampered checkpoint')
    closure=json.loads((root/'state.json').read_bytes())
    if closure['schema']!=SCHEMA or closure['payload_sha256']!=seal['payload_sha256']: raise ValueError('closure identity')
    verify_shards(closure['opened_checkpoint_shards'])
    verify_journal_inventory(closure['historical_journal_inventory'])
    # No side-effecting provider construction until the entire saved closure validates.
    size=(root/'payload.bin').stat().st_size
    payload=np.memmap(root/'payload.bin',dtype=np.uint8,mode='r') if size else b''
    saved=read_tree(closure['state'],payload)
    provider,engine=factory(); p=unwrap(provider)
    if p.views or p.memories or p.locations or engine.retired or p.rf or p.state:
        raise ValueError('restore requires exact cold empty producer')
    shared=shared_factory(p,engine)
    if shared is not None and shared.memories:raise ValueError('restore requires cold empty shared factory')
    current=identity(p,engine)
    if run_scope_transition is None:
        if current!=closure['identity']:raise ValueError('cold source/manifest/home/retention mismatch')
    else:
        validate_scope_transition(run_scope_transition,old_identity=closure['identity'],new_identity=current,
            old_scope=closure['run_scope'],next_pc=max(saved['retired'])+1,
            new_scope=run_scope(p),role_proof=scope_role_proof(p,engine))
        if run_scope(p)['prefix_stop']>=len(p.native['instructions']):raise ValueError('scope outside complete native program')
    verify_inputs(p)
    lock_shards(p,closure['opened_checkpoint_shards'])
    from hbm_bound_event_journal_r30 import BoundSectorProvider, CompactSectors
    for name, ports in saved['ports'].items():
        for rank, s in ports.items():
            port=BoundSectorProvider(s['extents'],journal_budget=p.journal_budget,
                allocation_identity=s['allocation_identity'],tags=s['tags'],queue=s['qd'],
                write_residence=s['write_cap'],read_ticks=s['read_ticks'],write_ticks=s['write_ticks'],reverse_ticks=s['reverse_ticks'])
            apply_port_state(port,s)
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
    if 'shared' in extra:
        if shared is None:raise ValueError('cold shared factory missing')
        for key,s in extra['shared'].items():
            memory=shared(s['owner'])
            if key!=(s['owner']['rank'],s['owner']['SM']) or memory.extent!=s['extent']:
                raise ValueError('restored shared finite home mismatch')
            memory.serial=s['serial']
            apply_port_state(memory.p,s['port'])
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
    bound=unwrap(engine.provider).manifest.get('prefix_stop')
    if bound is not None and (type(stop_after)is not int or stop_after>bound):raise ValueError('execution exceeds enrolled run scope')
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
    payload,metadata,arrays,tree_bytes,array_temporary=measure_state(p,engine)
    # Walk the same serialization schema, including routes and append row data.
    # Future images/reference outputs never enter that payload tree.
    model['payload_bytes']=payload;model['serialized_arrays']=arrays
    model['typed_state_metadata_bytes']=metadata
    model['metadata_python_tree_bytes']=tree_bytes
    model['metadata_serialization_peak_envelope_bytes']=tree_bytes+2*metadata
    model['maximum_array_contiguity_temporary_bytes']=array_temporary
    model['serialization_workspace_envelope_bytes']=tree_bytes+2*metadata+array_temporary+1048576
    model['raw_sector_record_bytes']=SECTOR_RECORD.size
    witness_metadata={'seen':[list(k) for k in sorted(witness.seen)],
        'initialization_provenance':witness.initialization_provenance,'observation_journal':witness.events.summary()}
    model['metadata_bytes_upper']=metadata+2*len(canonical(identity(p,engine)))+len(canonical(checkpoint_shards(p)))+len(canonical(witness_metadata))+2*len(canonical(model))+16384
    model['filesystem_reservation_bytes']=model['payload_bytes']+model['metadata_bytes_upper']
    dest=Path(destination);parent=dest.parent
    if dest.exists(): raise ValueError('fresh destination')
    stat=os.statvfs(parent);model['available_disk_bytes']=stat.f_bavail*stat.f_frsize
    if model['available_disk_bytes']<model['filesystem_reservation_bytes']:raise ValueError('checkpoint aggregate disk headroom')
    history=journal_inventory(p,engine,witness)
    model['old_journal_inventory']=history
    model['old_journal_bytes']=history['total_bytes']
    # Count this closure separately from model/projection copies; hashes add
    # at most66B per entry beyond the explicitly unhashed projection rows.
    journal_meta=len(canonical(history))+66*len(history['files'])
    model['metadata_bytes_upper']+=3*journal_meta
    model['filesystem_reservation_bytes']+=3*journal_meta
    model['metadata_serialization_peak_envelope_bytes']+=3*journal_meta
    model['serialization_workspace_envelope_bytes']+=3*journal_meta
    if model['available_disk_bytes']<model['filesystem_reservation_bytes']:raise ValueError('complete checkpoint metadata disk headroom')
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
            'projection':projection,'producer_seal':seal,
            'run_scope':run_scope(unwrap(provider)),
            'scope_role_proof':scope_role_proof(unwrap(provider),engine)}
    with (root/'actual_observations.json').open('xb') as f:
        f.write(canonical(actual));f.flush();os.fsync(f.fileno())
    receipt={'producer_seal':seal,'actual_observations_sha256':sha(root/'actual_observations.json')}
    with (root/'RUNNER_COMPLETE.json').open('xb') as f:
        f.write(canonical(receipt));f.flush();os.fsync(f.fileno())
    fd=os.open(root,os.O_RDONLY);os.fsync(fd);os.close(fd)
    return receipt


def verify_checkpoint(checkpoint_dir, *, source_contract, next_pc, constructor_contract):
    if type(next_pc)is not int:raise ValueError('typed next PC required')
    root=Path(checkpoint_dir);receipt=json.loads((root/'RUNNER_COMPLETE.json').read_bytes())
    if receipt!=constructor_contract.get('checkpoint_receipt'):raise ValueError('trusted external checkpoint receipt')
    if sha(root/'actual_observations.json')!=receipt['actual_observations_sha256']:raise ValueError('actual observation drift')
    actual=json.loads((root/'actual_observations.json').read_bytes())
    if actual['source_contract']!=source_contract:
        raise ValueError('source/constructor contract')
    transition=constructor_contract.get('run_scope_transition')
    if transition is None:
        if constructor_contract.get('identity')!=source_contract.get('identity'):raise ValueError('source/constructor contract')
    else:
        if transition['checkpoint_receipt']!=receipt:raise ValueError('transition producer receipt')
        validate_scope_transition(transition,old_identity=source_contract['identity'],
            new_identity=constructor_contract['identity'],old_scope=actual['run_scope'],next_pc=next_pc,
            new_scope=constructor_contract['run_scope'],role_proof=actual['scope_role_proof'])
    if next_pc!=actual['boundary_pc']+1:raise ValueError('exact contiguous next PC')
    for name,key in [('state.json','state_sha256'),('payload.bin','payload_sha256')]:
        if (root/name).is_symlink() or sha(root/name)!=receipt['producer_seal'][key]:raise ValueError('actual payload drift')
    verify_journal_inventory(json.loads((root/'state.json').read_bytes())['historical_journal_inventory'])
    result={'checkpoint_dir':str(root),'receipt':receipt,'actual':actual,'source_contract':source_contract,'next_pc':next_pc}
    if transition is not None:result['run_scope_transition']=transition
    return result


def validate_scope_transition(t, *, old_identity,new_identity,old_scope,new_scope,next_pc,role_proof):
    keys={'schema','old_identity','new_identity','old_run_scope','new_run_scope','next_pc','checkpoint_receipt','role_proof','seal_sha256'}
    if set(t)!=keys or t['schema']!='DS_EXPLICIT_RUN_SCOPE_TRANSITION_V1':raise ValueError('exact run-scope transition schema')
    unsigned={k:v for k,v in t.items() if k!='seal_sha256'}
    if hashlib.sha256(canonical(unsigned)).hexdigest()!=t['seal_sha256']:raise ValueError('run-scope transition seal')
    if (t['old_identity'],t['new_identity'],t['old_run_scope'],t['new_run_scope'],t['next_pc'],t['role_proof'])!=(old_identity,new_identity,old_scope,new_scope,next_pc,role_proof):
        raise ValueError('run-scope exact old/new binding')
    if data_identity(old_identity)!=data_identity(new_identity):raise ValueError('run-scope data identity changed')
    old,new=old_scope['prefix_stop'],new_scope['prefix_stop']
    if type(old)is not int or type(new)is not int or not next_pc<=new or new<old or old<next_pc-1:
        raise ValueError('run-scope extension boundary')
    if old_scope['journal_root']==new_scope['journal_root']:raise ValueError('fresh continuation journal required')
    if type(new_scope['journal_capacity_bytes'])is not int or new_scope['journal_capacity_bytes']<131072:
        raise ValueError('positive evidence capacity')


def plan_run_scope_transition(checkpoint_dir, *, source_contract,checkpoint_receipt,provider,engine,next_pc):
    """Seal authorized continuation policy, without weakening source identity."""
    verified=verify_checkpoint(checkpoint_dir,source_contract=source_contract,next_pc=next_pc,
        constructor_contract={'identity':source_contract['identity'],'checkpoint_receipt':checkpoint_receipt})
    p=unwrap(provider);role=scope_role_proof(p,engine)
    if p.views or p.memories or p.locations or engine.retired or p.rf or p.state:
        raise ValueError('continuation scope requires exact cold constructor')
    if role!=verified['actual']['scope_role_proof']:raise ValueError('continuation role proof changed')
    scope=run_scope(p)
    if type(scope['prefix_stop'])is not int or scope['prefix_stop']>=len(p.native['instructions']):
        raise ValueError('scope outside complete native program')
    t=dict(schema='DS_EXPLICIT_RUN_SCOPE_TRANSITION_V1',old_identity=source_contract['identity'],new_identity=identity(p,engine),
        old_run_scope=verified['actual']['run_scope'],new_run_scope=scope,next_pc=next_pc,
        checkpoint_receipt=checkpoint_receipt,role_proof=role)
    t['seal_sha256']=hashlib.sha256(canonical(t)).hexdigest()
    validate_scope_transition(t,old_identity=t['old_identity'],new_identity=t['new_identity'],
        old_scope=t['old_run_scope'],new_scope=scope,next_pc=next_pc,role_proof=role)
    return t


def restore_quiescent(verified_manifest, engine, provider, witness):
    v=verified_manifest
    # Reverify on use; callers cannot turn a stale verified object into authority.
    contract={'identity':identity(unwrap(provider),engine),'checkpoint_receipt':v['receipt']}
    if 'run_scope_transition' in v:
        contract.update(run_scope_transition=v['run_scope_transition'],run_scope=run_scope(unwrap(provider)))
    fresh=verify_checkpoint(v['checkpoint_dir'],source_contract=v['source_contract'],next_pc=v['next_pc'],constructor_contract=contract)
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
    restore(v['checkpoint_dir'],lambda:(provider,engine),expected_seal=v['receipt']['producer_seal'],enabled=True,
        run_scope_transition=v.get('run_scope_transition'))
    if engine.retired!=set(range(v['next_pc'])):raise ValueError('restored retired prefix')
    witness.seen=seen
    engine._verified_checkpoint_resume=True
    # Even the unchanged legacy root-only relocation gets an exact sealed
    # output receipt. Stop/capacity changes still require the explicit plan.
    scope_receipt=dict(schema='DS_RESTORED_RUN_SCOPE_RECEIPT_V1',
        producer_checkpoint_receipt=v['receipt'],old_run_scope=actual['run_scope'],
        new_run_scope=run_scope(p),old_identity=v['source_contract']['identity'],
        new_identity=identity(p,engine),retired=sorted(engine.retired),
        explicit_transition=v.get('run_scope_transition'),role_proof=scope_role_proof(p,engine))
    scope_receipt['seal_sha256']=hashlib.sha256(canonical(scope_receipt)).hexdigest()
    with (p.journal_budget.root/'checkpoint_restore_scope.json').open('xb') as f:
        f.write(canonical(scope_receipt));f.flush();os.fsync(f.fileno())
    fd=os.open(p.journal_budget.root,os.O_RDONLY);os.fsync(fd);os.close(fd)
    return {'retired':sorted(engine.retired),'next_pc':v['next_pc'],
            'prior_actual_observation_journal':actual['observation_journal'],
            'same_home_restored':True,'hardware_qualified':False,'run_scope_receipt':scope_receipt}

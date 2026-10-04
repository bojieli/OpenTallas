"""Read-only typed-state counts and CPython object-space lifetime envelopes.

No producer construction or numerical execution. Bounds cover object storage;
allocator arenas, file cache, kernel, host pages and peer leases are explicit
separate obligations. No metadata-size multiplier or repeated native graph.
"""
import collections,hashlib,json,struct,sys
from pathlib import Path
import numpy as np
V3_SHA='e323ce55e837e32418a74ae271897357952780681a5161205d8a12498060321e'


def require(v,msg):
    if not v:raise ValueError(msg)


def layout():
    require(sys.implementation.name=='cpython' and sys.version_info[:3]==(3,10,12),'priced CPython3.10.12 required')
    require(struct.calcsize('P')==8,'64-bit pointers required')
    return dict(interpreter=sys.version,pointer=8,list_header=sys.getsizeof([]),dict_header=sys.getsizeof({}),
        dict_single_entry=sys.getsizeof({0:0}),tuple_header=sys.getsizeof(()),set_header=sys.getsizeof(set()),
        set_single_entry=sys.getsizeof({0}),bytearray_header=sys.getsizeof(bytearray()),
        bytes_header=sys.getsizeof(b''),unicode4_header=sys.getsizeof('\U0010ffff')-4,
        bool=sys.getsizeof(True),none=sys.getsizeof(None),float=sys.getsizeof(0.0))


def list_bytes(n,L):
    require(type(n)is int and n>=0,'list length')
    # CPython list_resize growth: ((n+n/8+6)&~3). Include the generic
    # iterable constructor's8-slot length hint; this overprices small lists.
    cap=0 if not n else max(8,((n+(n>>3)+6)&~3))
    return L['list_header']+cap*L['pointer']


def dict_bytes(n,L):
    require(type(n)is int and n>=0,'dict length')
    # Overprice each entry with a complete singleton table, retaining header.
    # CPython compact dict min8/power-of-two table+<=2/3 fill stays below this.
    return L['dict_header']+n*L['dict_single_entry']


def array_header(ndim):
    require(type(ndim)is int and 0<=ndim<=32,'ndarray dimensions')
    return sys.getsizeof(np.empty((0,)*ndim,dtype=np.uint8)) if ndim else sys.getsizeof(np.empty((),dtype=np.uint8))-1


class JsonCounts:
    def __init__(self,L):self.L=L;self.kinds=collections.Counter();self.nodes=0;self.heap=0;self.list_items=0;self.dict_entries=0;self.str_chars=0;self.max_string_chars=0;self.max_integer_chars=0;self.keys=set();self.max_list_len=0;self.max_dict_len=0
    def node(self,kind,n=0,scalar=None):
        self.kinds[kind]+=1;self.nodes+=1
        if kind=='dict':self.heap+=dict_bytes(n,self.L);self.dict_entries+=n;self.max_dict_len=max(self.max_dict_len,n)
        elif kind=='list':self.heap+=list_bytes(n,self.L);self.list_items+=n;self.max_list_len=max(self.max_list_len,n)
        elif kind=='str':self.heap+=self.L['unicode4_header']+4*n;self.str_chars+=n;self.max_string_chars=max(self.max_string_chars,n)
        elif kind=='int':self.heap+=sys.getsizeof(scalar);self.max_integer_chars=max(self.max_integer_chars,len(str(scalar)))
        elif kind in ('bool','none','float'):self.heap+=self.L[kind]
        else:raise ValueError('JSON kind')
    def walk(self,v):
        if type(v)is dict:
            self.node('dict',len(v))
            for k,x in v.items():require(type(k)is str,'JSON metadata key');self.keys.add(k);self.node('str',len(k));self.walk(x)
        elif type(v)in (list,tuple):
            self.node('list',len(v))
            for x in v:self.walk(x)
        elif type(v)is str:self.node('str',len(v))
        elif type(v)is bool:self.node('bool')
        elif v is None:self.node('none')
        elif type(v)is int:self.node('int',scalar=v)
        elif type(v)is float:self.node('float')
        else:raise ValueError('unpriced JSON node')
    def result(self):return dict(kinds=dict(self.kinds),nodes=self.nodes,list_items=self.list_items,dict_entries=self.dict_entries,
        decoded_unicode_characters=self.str_chars,max_decoded_string_chars=self.max_string_chars,max_integer_chars=self.max_integer_chars,
        JSON_dictionary_key_names=sorted(self.keys),max_list_len=self.max_list_len,max_dict_len=self.max_dict_len,
        decoder_key_memo_table_upper_bytes=dict_bytes(len(self.keys),self.L),unshared_python_object_heap_upper_bytes=self.heap)


def profile_typed_value(base,value,*,enabled=False):
    """Walk an actual snapshot or primitive test value without encoded tree.
    Original V3 leaves validate ndarray flags/sector bytes/extents; only tiny
    leaf descriptors exist. Values are never sourced from expected outputs.
    """
    if enabled is not True:raise ValueError('allocation profile default off')
    require(hashlib.sha256(Path(base.__file__).read_bytes()).hexdigest()==V3_SHA,'exact V3 source')
    L=layout();J=JsonCounts(L);source=collections.Counter();active=set()
    stats=dict(payload_bytes=0,arrays=0,array_copy_bytes=0,max_array_bytes=0,max_contiguity_copy_bytes=0,
      array_headers=0,sector_backing_records=0,sector_full_records=0,sector_partial_records=0,
      sector_tables=0,sector_decode_heap_upper=0,all_restore_table_copy_upper=0,
      largest_restore_table_copy_upper=0,typed_container_decode_heap_upper=0,
      bytes_decode_copy_bytes=0,bytes_decode_headers=0,dtype_decode_heap_upper=0,
      max_depth=0,metadata_bytes=0,max_leaf_metadata_bytes=0,max_leaf_json_heap_upper=0)
    arrays=[];array_ids=set()
    class Count:
        def write(self,data):return len(data)
    W=base.Writer.__new__(base.Writer);W.f=Count();W.bytes=0;W.arrays=0;W.array_temporary_bytes=0
    def wrap(kind,n):
        J.node('dict',1);J.keys.add(kind);J.node('str',len(kind));J.node('list',n)
    def walk(v,depth):
        stats['max_depth']=max(stats['max_depth'],depth)
        if isinstance(v,np.generic):source['numpy_scalar']+=1;return walk(v.item(),depth)
        if type(v)in (dict,tuple,list,set):
            require(id(v) not in active,'cyclic state');active.add(id(v));source[type(v).__name__]+=1
            try:
                kind=type(v).__name__;n=len(v);wrap(kind,n)
                # Metadata punctuation and type marker are exact canonical bytes.
                stats['metadata_bytes']+=len(base.canonical(kind))+5+max(0,n-1)
                if type(v)is dict:
                    stats['typed_container_decode_heap_upper']+=dict_bytes(n,L)
                    for k,x in v.items():
                        J.node('list',2);stats['metadata_bytes']+=3
                        walk(k,depth+1);walk(x,depth+1)
                else:
                    if type(v)is tuple:stats['typed_container_decode_heap_upper']+=L['tuple_header']+8*n
                    elif type(v)is list:stats['typed_container_decode_heap_upper']+=list_bytes(n,L)
                    else:stats['typed_container_decode_heap_upper']+=L['set_header']+n*L['set_single_entry']
                    for x in v:walk(x,depth+1)
            finally:active.remove(id(v))
            return
        if type(v)is base.SectorBacking:
            source['SectorBacking']+=1;n=len(v.values);stats['sector_backing_records']+=n;stats['sector_tables']+=1
            # all saved old tables remain alive as every new copied table is added
            copy_table=dict_bytes(n,L)+sys.getsizeof(type(v.values)())-L['dict_header']
            stats['all_restore_table_copy_upper']+=copy_table
            stats['largest_restore_table_copy_upper']=max(stats['largest_restore_table_copy_upper'],copy_table)
            stats['sector_decode_heap_upper']+=copy_table
            for (target,rank,sector),values in v.values.items():
                partial=any(x is None for x in values)
                stats['sector_partial_records' if partial else 'sector_full_records']+=1
                # target/rank alias the retained decoded identity table. Sector
                # integer and tuple key are new, contents are byte atoms/None.
                value_heap=list_bytes(32,L) if partial else L['bytearray_header']+33
                stats['sector_decode_heap_upper']+=L['tuple_header']+3*8+sys.getsizeof(sector)+value_heap
        elif isinstance(v,np.ndarray):
            source['ndarray']+=1;stats['arrays']+=1;stats['array_copy_bytes']+=v.nbytes
            stats['array_headers']+=array_header(v.ndim);stats['max_array_bytes']=max(stats['max_array_bytes'],v.nbytes)
            if not v.flags.c_contiguous:stats['max_contiguity_copy_bytes']=max(stats['max_contiguity_copy_bytes'],v.nbytes)
            arrays.append(dict(object_id=id(v),pointer=int(v.__array_interface__['data'][0]),base_id=None if v.base is None else id(v.base),
                bytes=v.nbytes,dtype=v.dtype.str,shape=list(v.shape),strides=list(v.strides),c_contiguous=bool(v.flags.c_contiguous),writeable=bool(v.flags.writeable)))
            array_ids.add(id(v))
        elif isinstance(v,np.dtype):source['dtype']+=1;stats['dtype_decode_heap_upper']+=sys.getsizeof(v)
        elif type(v)in (bytes,bytearray):
            source[type(v).__name__]+=1;stats['bytes_decode_copy_bytes']+=len(v)
            stats['bytes_decode_headers']+=L['bytes_header'] if type(v)is bytes else L['bytearray_header']+1
        else:source[type(v).__name__]+=1
        leaf=W.tree(v);j=JsonCounts(L);j.walk(leaf);J.walk(leaf)
        encoded=base.canonical(leaf);stats['metadata_bytes']+=len(encoded)
        stats['max_leaf_metadata_bytes']=max(stats['max_leaf_metadata_bytes'],len(encoded))
        stats['max_leaf_json_heap_upper']=max(stats['max_leaf_json_heap_upper'],j.heap)
    walk(value,0);stats['payload_bytes']=W.bytes
    return dict(schema='DS_TYPED_OBJECT_ALLOCATION_PROFILE_V1',layout=L,source_type_occurrences=dict(source),
      typed_JSON=J.result(),counts=stats,arrays=arrays,array_object_aliases=len(arrays)-len(array_ids),
      source_array_alias_discount_for_restore_bytes=0,all_arrays_restored_as_copies=True,
      full_encoded_snapshot_tree_created=False,profile_is_physical_page_certificate=False,
      profiler_reporting_object_heap_separate=True,allocator_retention_upper_bytes=None,
      filecache_kernel_peer_upper_bytes=None)


def profile_actual_state(base,provider,engine,*,enabled=False):
    if enabled is not True:raise ValueError('allocation profile default off')
    require(hashlib.sha256(Path(base.__file__).read_bytes()).hexdigest()==V3_SHA,'exact V3 source')
    p=base.quiescent(provider,engine);base.validate_backing(p)
    result=profile_typed_value(base,base.snapshot_state(p,engine),enabled=True)
    result.update(actual_quiescent_provider_traversed=True,retired_PCs=sorted(engine.retired),
                  expected_outputs_used_as_stimulus=False,source_V3_SHA256=V3_SHA)
    return result


def phase_object_bounds(profile,*,closure_heap_upper,state_file_bytes,observation_heap_upper,observation_file_bytes,
                        identity_and_journal_workspace_upper,constructor_heap_upper):
    """Logical object-space phases; independent terms must be source counted.
    Closure includes typed JSON tree; unshared bounds never use interned-key or
    mmap/filecache alias discounts. No arbitrary metadata multiplication.
    """
    values=(closure_heap_upper,state_file_bytes,observation_heap_upper,observation_file_bytes,identity_and_journal_workspace_upper,constructor_heap_upper)
    require(all(type(v)is int and v>=0 for v in values),'complete counted source terms')
    s=profile['counts'];restore=(s['typed_container_decode_heap_upper']+s['sector_decode_heap_upper']+
        s['all_restore_table_copy_upper']+s['array_copy_bytes']+s['array_headers']+
        s['bytes_decode_copy_bytes']+s['bytes_decode_headers']+s['dtype_decode_heap_upper']+
        profile['typed_JSON']['unshared_python_object_heap_upper_bytes'])
    # bytes read -> json.loads creates UTF8 decoded text -> builds JSON object
    # tree. Price allthree even though input bytes can die before tree completes.
    parser=state_file_bytes+sys.getsizeof(b'')+4*state_file_bytes+profile['layout']['unicode4_header']+closure_heap_upper
    return dict(schema='DS_CHECKPOINT_PHASE_OBJECT_BOUNDS_V1',
      projection=dict(typed_metadata_tree_upper=profile['typed_JSON']['unshared_python_object_heap_upper_bytes'],
        identity_journal_workspace_upper=identity_and_journal_workspace_upper),
      atomic_verify=dict(closure_parse_upper=parser,retained_observation_tree_upper=observation_heap_upper,
        observation_read_text_upper=5*observation_file_bytes),
      cold_restore=dict(constructor_heap_upper=constructor_heap_upper,closure_and_parser_upper=parser,
        decoded_state_and_all_port_copies_upper=restore,observation_tree_upper=observation_heap_upper,
        identity_journal_workspace_upper=identity_and_journal_workspace_upper,
        logical_sum_upper=constructor_heap_upper+parser+restore+observation_heap_upper+identity_and_journal_workspace_upper),
      complete_source_phase_bounds=False,
      missing_source_terms=['decoder_C_scratch_and_stack','snapshot_wrapper_and_frame_storage','witness_compare_temporary_arrays','identity_journal_role_graph_peak','allocator_retention_and_host_page_union'],
      corrected_table_copy_upper=s['all_restore_table_copy_upper'],old_largest_table_only=s['largest_restore_table_copy_upper'],
      mmap_resident_payload_and_filecache_upper=None,allocator_pages_upper=None,physical_admission=False)


def profile_json_metadata(base,value,*,enabled=False):
    """Count an actual ordinary closure/identity/journal object without dumping it."""
    if enabled is not True:raise ValueError('metadata profile default off')
    require(hashlib.sha256(Path(base.__file__).read_bytes()).hexdigest()==V3_SHA,'exact V3 source')
    L=layout();J=JsonCounts(L);J.walk(value)
    count=0;max_scalar=0;max_sorted_entries=0
    def walk(v):
        nonlocal count,max_scalar,max_sorted_entries
        if type(v)is dict:
            max_sorted_entries=max(max_sorted_entries,len(v));count+=2+max(0,len(v)-1)
            # Byte count does not depend on order; avoid a sorted-items copy.
            for k,x in v.items():count+=len(base.canonical(k))+1;walk(x)
        elif type(v)in (list,tuple):
            count+=2+max(0,len(v)-1)
            for x in v:walk(x)
        else:
            n=len(base.canonical(v));count+=n;max_scalar=max(max_scalar,n)
    walk(value)
    # C/Python JSON sort path holds list(items)+tuplepairs+sort temporary;
    # the one largest active dict is priced separately from the returned tree.
    sorted_workspace=list_bytes(max_sorted_entries,L)+max_sorted_entries*(L['tuple_header']+16+16)
    return dict(J.result(),encoded_bytes=count,max_scalar_encoded_bytes=max_scalar,
                max_sorted_dictionary_entries=max_sorted_entries,sorted_dictionary_workspace_upper_bytes=sorted_workspace,
                full_json_text_or_bytes_created=False,allocator_pages_upper=None)



def frozen_r69_restore_correction(root):
    """Reprice every copied table using unchanged source sector/entry bounds.

    No producer, payload, checkpoint or constructor is opened. This corrects
    one overlapping allocation term, never certifies the full phase envelope.
    """
    root=Path(root);layout()
    pc=json.loads((root/'inputs/PC01_model.json').read_bytes())['RAM']
    old=json.loads((root/'inputs/R56_preflight_model.json').read_bytes())['RAM']['interpreter']
    ledger=json.loads((root/'inputs/R69_ledger.json').read_bytes())
    require(ledger['full_native_PCs']==2213 and ledger['full_homes']==290730,'complete production identity')
    require(ledger['retained_base_components']['restore_port_dictionary_copy']==pc['source_PC01_saved_dictionary_copy_bytes'],'same old allowance')
    n=pc['source_PC01_sector_union'];ports=pc['source_PC01_port_count'];unit=old['singleton_dict_bytes']
    require(all(type(v)is int and v>0 for v in (n,ports,unit)),'positive source bounds')
    table_entries=n*unit
    # Include empty CompactSectors object+attribute dict for every table;
    # original singleton allowance already conservatively prices whole tables.
    header=sys.getsizeof({})+sys.getsizeof(types_simple_object())
    headers=ports*header
    old_copy=pc['source_PC01_saved_dictionary_copy_bytes']
    return dict(schema='R69_ALL_RESTORED_PORT_TABLE_OVERLAP_CORRECTION',
      R69_commit='23bc3975b2483774dfbecf68a06bc2108006122c',full_native_PCs=2213,full_homes=290730,
      restored_sector_upper=n,restored_port_upper=ports,existing_singleton_table_allowance=unit,
      all_table_entries_upper_bytes=table_entries,all_empty_table_headers_upper_bytes=headers,
      all_table_copies_upper_bytes=table_entries+headers,old_largest_only_allowance_bytes=old_copy,
      missing_copy_increment_upper_bytes=table_entries+headers-old_copy,
      R69_retained_base_before_correction_bytes=ledger['retained_candidate_base_bytes'],
      retained_base_with_corrected_table_term_bytes=ledger['retained_candidate_base_bytes']+table_entries+headers-old_copy,
      copied_key_and_sector_values_alias_saved_objects=True,duplicate_sector_contents_charged_here=False,
      simultaneous_lifetime='saved retains all decoded backing dictionaries until restore returns; copied tables accumulate in installed RF/state/shared ports',
      constructor_floor_unchanged_bytes=ledger['original_R68_constructor_RAM_bytes'],
      full_runtime_upper_bytes=None,complete_source_phase_bounds=False,physical_admission=False,
      existing_guard_changed=False,actual_constructor_runs=0,actual_payload_reads=0)


def types_simple_object():
    # Bound the subtype header without executing source constructors. Python
    # dictionary subclass with a normal instance dict matches CompactSectors.
    class HeaderOnly(dict):pass
    return HeaderOnly()


def audit_record(root):
    root=Path(root);correction=frozen_r69_restore_correction(root)
    return dict(schema='R69_TYPED_ALLOCATION_AUDIT',restore_correction=correction,
      source_sha256={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((root/'inputs').glob('*')) if p.is_file()},
      APIs={'profile_actual_state':'default-off; exact V3 quiescence/backing -> snapshot -> typed node/array/sector counts; no provider constructor',
        'profile_json_metadata':'actual identity/role/journal/witness/closure objects -> source node and exact canonical byte counts; no full JSON buffer',
        'phase_object_bounds':'partial logical storage ledger only; rejects unknown supplied terms; cannot produce admission'},
      phases={
        'constructor':{'source_floor_bytes':40910816974,'changed':False,'missing':'allocator/pages, kernel/peer growth and cumulative physical write-set'},
        'project':{'retained':'V3 measure_state constructs encoded tree and canonical buffer, followed by deep_metadata seen set; original projection retained',
          'required_counts':['typed node histogram','maximum canonical scalar','full closure/identity/role/journal/witness node counts','max active sorted-dict workspace','deep_metadata seen-set cardinality','snapshot wrapper counts']},
        'capture':{'retained':'R2 two passes/hash consistency, original leaf writer, no whole encoded tree; original V3 project still runs first',
          'required_counts':['max stream frame depth','snapshot wrappers','max leaf tree/canonical bytes','noncontiguous array temporary','identity/role/journal/witness graphs','atomic observations JSON']},
        'atomic_verify':{'retained':'full state/observations JSON read and parse; fsynced sibling rename no payload copy',
          'required_counts':['state and observations encoded bytes','decoded JSON nodes/key memo','CPython scanner scratch','retained source contract/receipt/observations']},
        'cold_restore':{'retained':'full constructor, closure parse, decoded arrays/sectors, all old tables plus all accumulating copies, exact same-home identities',
          'table_overlap_upper_bytes':correction['all_table_copies_upper_bytes'],
          'required_counts':['actual closure node histogram','all decoded state primitive/container nodes','arrays copied per occurrence','source image equality two tobytes temporaries','restored port/provider auxiliary objects','shared factory objects/counters','verify_actual_restore compare temporaries']},
        'physical':{'required_counts':['allocator retained-page upper','mmap/file-cache touch union','source process-to-process cumulative COW union','kernel and peer lease growth'],
          'pagecache_release_credit_bytes':0,'guest_plus_host_available_sum':False}},
      complete_source_phase_bounds=False,full_runtime_upper_bytes=None,
      actual_state_snapshot_available=False,actual_constructor_runs=0,actual_payload_reads=0,
      source_upper_is_not_measured_usage=True,original_guards_changed=False,
      protected_R2_source_unchanged=True,physical_admission=False)


if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser();ap.add_argument('--verify',action='store_true');ap.add_argument('--generate',type=Path)
    a=ap.parse_args();root=Path(__file__).resolve().parents[1]/'results/uarch/ds_checkpoint_typed_allocation_bounds_20261003'
    result=audit_record(root)
    if a.verify:require(result==json.loads((root/'model.json').read_bytes()),'exact audit replay')
    if a.generate:a.generate.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print(json.dumps(result['restore_correction'],sort_keys=True))

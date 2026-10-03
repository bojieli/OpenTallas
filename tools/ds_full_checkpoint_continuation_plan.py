"""Read-only all-PC source/resource continuation census. Never constructs a provider.

Finite quantities are component projections, not whole-runtime admission. Missing
operator/provider journal schemas remain null, never a zero-cost assumption.
"""
import argparse
import collections
import gzip
import hashlib
import json
import math
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
NATIVE='results/uarch/ds_hbm_storage_home_binding_r41_20261002/inputs/actual_native_c65.json.gz'
HOMES='results/uarch/ds_hbm_connected_source_r37_20261002/inputs/actual_DeepSeek_homes.json.gz'
MANIFEST='results/uarch/ds_hbm_connected_source_r37_20261002/inputs/prefix_input_manifest.json.gz'
DISPATCH='results/uarch/ds_hbm_bound_engine_r43_20261002/inputs/actual_dispatch_bcf.json.gz'
PINS={'results/uarch/ds_hbm_storage_home_binding_r41_20261002/inputs/actual_native_c65.json.gz': 'c65a584c1b1cfafcd00391af216870136a44ec142b0d11106df570db7b8eb264', 'results/uarch/ds_hbm_connected_source_r37_20261002/inputs/actual_DeepSeek_homes.json.gz': 'e4751c4164368e98295f78d4270bf65992a8a7ee273a04ceffa528072f855424', 'results/uarch/ds_hbm_connected_source_r37_20261002/inputs/prefix_input_manifest.json.gz': '2c7d0d38d9e5c1a2b049ba14eecfe8bae91eaaf2e96629f418b4ade9693c1c01', 'results/uarch/ds_hbm_bound_engine_r43_20261002/inputs/actual_dispatch_bcf.json.gz': 'bcf7d800aa64aeff92b8a1954cab328911c400025179d6a9ab9f211a934c253c', 'tools/ds_producer_checkpoint_resume_v3.py': 'e323ce55e837e32418a74ae271897357952780681a5161205d8a12498060321e', 'tools/ds_hbm_source_prefix_r45.py': '362ca1a8ca327f585451f5bd4fdb2b7d0b9dff135a75cabd9bc52a9d75d4d620', 'tools/h3_ds_source_prefix_provider_r39.py': 'dd50f6afb9a52fe58efe285564cd53da2e0622c31f191d5fded3511ea9d36d6d', 'tools/h3_ds_checkpoint_provider_r30.py': '4b7a74d246f8a594062ddc27a1c23038484342838cd1ae9fef173eab605722b9', 'tools/h3_ds_checkpoint_provider_r34.py': '9d47acf6f44481cf15458e8162118ec53395a03b3aa1d5242c1d1423e7d8b014', 'tools/ds_hbm_pc10_engine_r44.py': '96949401e4ef66977211d03d4d64821ca7cff4bd818a8701d8806344484bc31d', 'tools/ds_hbm_storage_home_binding_r41.py': 'feaba8f44842282ad9c2cd314f0640a196f56dbd6ec546527d23942d5dcbe3f1', 'tools/ds_hbm_pc10_projection_r46.py': '6abf0fe6946ba8cdd1580ee6f8c27b4c71d4f08bb4741f49b67549c94879ded5', 'tools/ds_hbm_additive_endpoint_join_r54.py': '00bd0b2fa93de9afd11ca65722563fec2df939729a937413f4e66451418d36c2', 'tools/ds_hbm_registered_loader_r57.py': 'a8f338aac3bcd33b0c81deef05135613dc7454d2a98aeb09c92c5d8691a23ba9', 'tools/ds_hbm_checkpointed_prefix_r55.py': 'd8afd90b1d9e9ff374c85caf1e55e71a5e5bca6afd1639d077fdeb9f1c51ab39', 'tools/h3_complete_native_calendar_successor_r1.py': 'dc04ddb7da27b7a1230691a01bba6af6bdd45bacf59b8afc58b0ad853c6c0a21', 'results/uarch/ds_hbm_dual_resources_r56_20261003/model.json': 'c41b8feadef2f83c863d5f558c8bba30d3007b21dd7f0bcbdee8771c83ce0c6f', 'results/uarch/ds_hbm_source_prefix_r39_20261002/journal_schema_envelope_r2.json': '5281b5c4f237feca913adc8b13dd50337206b42698846120f953adfcc9309455', 'results/uarch/ds_hbm_connected_source_r37_20261002/inputs/h3_deepseek_streaming_linear.py': 'e938187d1701bffe8ace7c565fe8fc6567eed476f85ddd16e174de63a62e7bc9', 'results/uarch/ds_hbm_connected_source_r37_20261002/peer_source_pins.json': 'ac08d45b958cbf0401c1abe706d19da8cca4c1ebf15243bc1a3b4181c4188641'}

MRO_PINS={'tools/h3_ds_checkpoint_provider_r31.py': '12debf3d035611c0751459a5b15925a988998b2857f0fed50b75ab7072146ecc', 'tools/h3_ds_checkpoint_provider_r33.py': '722a0f5407b77fe6270e71092f7398702075fbe67923ef279a8bb88c5074d00f', 'tools/ds_hbm_group_provider_r34.py': '3650aeaec460723a29ca1d5fdff8295c2bc14ba4c8418135b33a9538400b4fb1', 'tools/h3_ds_history_provider_r36.py': '04b8f20c9aec5591be7fd86f2c4e11e31e42967a08918ab42bd98b0dcd4545df', 'tools/h3_ds_query_provider_r36.py': '717f127d48779d3552a1fc00aab25e2468d768d9a4cbcf6c690326959fdb78f9', 'tools/ds_hbm_source_merge_r37.py': '7d683ae8c7362a6f7f981afbb1614045b066da9c35449b8e7849238d8bdfdcab', 'tools/h3_ds_connected_provider_r37.py': '085b86a67e53fa1ae2b9c43c3d346cea514944601d2ea89477928f9d2990ffe3', 'tools/ds_hbm_collective_continuations_r37.py': '834807707285f70118a09c9878db86e501cd8420c9e744ba3b3dd4ce0ad1a84b'}

def load(path):return json.loads(gzip.decompress(path.read_bytes()) if path.suffix=='.gz' else path.read_bytes())
def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':')).encode()
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def ceil(n,d):return (n+d-1)//d


def merged(spans):
    out=[]
    for a,b in sorted(spans):
        if a<0 or b<=a:raise ValueError('positive extent')
        if out and a<=out[-1][1]:out[-1][1]=max(out[-1][1],b)
        else:out.append([a,b])
    return out


def shape_size(spec):
    widths={'F32':4,'U32':4,'I64':8}
    if spec['dtype'] not in widths or any(type(n)is not int or n<0 for n in spec['shape']):
        raise ValueError('finite native provider shape/type required')
    return math.prod(spec['shape'])*widths[spec['dtype']]


def provider_handler(op,name,binding):
    kind=binding['kind']
    if kind=='immutable_weight_provider':
        if isinstance(binding['logical_tensor'],list):
            tensor=binding['logical_tensor']
            if op['family']!='linear_q' or len(tensor)!=2 or type(tensor[0]) is not int or not 0<=tensor[0]<=6 or tensor[1] not in ('w1','w3','w2'):
                return 'r33 rejects non-expert composite weight descriptor'
            return 'r33 accepted-route/shared-slot weight_view -> r30 code/scale reads'
        if name=='weight' and binding['logical_tensor'].endswith('attn.wo_a.weight'):return 'r33 wo_a aligned head/K ownership and released codec'
        if name=='weight' and binding.get('format')=='bf16':return 'r31 exact BF16 selected-row weight_view'
        return 'r30 raw weight_code/scale selected-row reads'
    if kind=='explicit_auxiliary_provider':
        if op['family']=='all_gather' and name=='ownership_mask':return 'r37 continuation actual source ownership mask synthesis'
        if op['family']=='kv_gather' and name in ('selected_ckv_codes','selected_ckv_scales','selected_row_ids'):return 'r36 actual selected history read/paired codec + actual sel IDs'
        if op['family']=='topk_merge' and name=='scores':return 'r37 ordered addressed candidate producer merge'
        return 'explicit immutable auxiliary manifest record'
    return {'versioned_operand':'source-defined current version/location/query/history/collective view',
            'immutable_parameter_provider':'r30 selected checkpoint parameter tensor',
            'zero_initial_partial_destination':'r31/r37 source-declared zero destination'}.get(kind,'UNSUPPORTED_PROVIDER_KIND')


def missing_binding(op,tid,name,binding,manifest):
    kind=binding['kind']
    if provider_handler(op,name,binding)=='r33 rejects non-expert composite weight descriptor':return 'COMPOSITE_WEIGHT_SOURCE_HANDLER_UNBOUND'
    if kind=='explicit_auxiliary_provider' and provider_handler(op,name,binding)=='explicit immutable auxiliary manifest record':
        record=manifest.get('view_bindings',{}).get(f"{op['pc']}/{tid}/{name}")
        if record is None:return 'EXPLICIT_AUXILIARY_SOURCE_UNBOUND'
        if record.get('source_binding')!=binding or record.get('generation')!=manifest['generation'] or record.get('checkpoint_revision')!=manifest['checkpoint_revision']:
            return 'EXPLICIT_AUXILIARY_IDENTITY_MISMATCH'
        path=Path(record['path']);path=path if path.is_absolute() else ROOT/path
        if not path.is_file():return 'EXPLICIT_AUXILIARY_FILE_UNAVAILABLE'
    if provider_handler(op,name,binding)=='UNSUPPORTED_PROVIDER_KIND':return 'UNSUPPORTED_PROVIDER_KIND'
    return None


def source_rows(native,homes,manifest,footprint):
    if len(native['instructions'])!=2213 or [o['pc'] for o in native['instructions']]!=list(range(2213)):
        raise ValueError('complete contiguous actual native program required')
    fps={key:footprint(program) for key,program in native['templates'].items()}
    rows=[];gaps=[]
    for op in native['instructions']:
        row={'PC':op['pc'],'family':op['family'],'layer':op['source_op'].get('layer'),
             'dependencies':op['dependencies'],'native_calls':0,'primitive_scalar_counts':collections.Counter(),
             'CPU_native_live_and_transient_bytes':0,'immutable_LOAD_bytes':0,'sector_requests_component_upper':0,
             'output_publication_keys':0,'provider_kinds':collections.Counter(),'numeric_status':'NOT_EXECUTED_BY_THIS_PLAN',
             'checkpoint_extra_journal_component_bytes':None,'whole_runtime_projection_complete':False}
        for tid,bindings in op['provider_bindings'].items():
            for name,b in bindings.items():
                reason=missing_binding(op,tid,name,b,manifest)
                if reason:gaps.append({'PC':op['pc'],'family':op['family'],'template':tid,'operand':name,
                                       'kind':b['kind'],'reason':reason,'logical_tensor':b.get('logical_tensor')})
        for owned in op['rank_bindings']:
            if owned.get('empty_owned_extent'):continue
            buffers=owned.get('buffer_programs') or [{'template':owned['template']}]
            for buffer in buffers:
                tid=buffer['template'];p=native['templates'][tid];fp=fps[tid]
                row['native_calls']+=1
                row['CPU_native_live_and_transient_bytes']=max(row['CPU_native_live_and_transient_bytes'],
                    fp['typed_live_bytes']+fp['transient_and_output_reserve_bytes'])
                row['primitive_scalar_counts'].update(fp['scalar_evaluations_by_opcode'])
                for name,spec in p['providers'].items():
                    b=op['provider_bindings'][tid][name];kind=b['kind'];row['provider_kinds'][kind]+=1
                    size=shape_size(spec)
                    if kind in ('versioned_operand','explicit_auxiliary_provider'):
                        # Same source R45 conservative restore/fragment-tail envelope.
                        # It excludes physical timing and family-specific history/code append traffic.
                        row['sector_requests_component_upper']+=ceil(size,32)+32*(96 if name=='parts' else 1)
                    if kind in ('immutable_weight_provider','immutable_parameter_provider'):row['immutable_LOAD_bytes']+=size
            row['output_publication_keys']+=len(op['writes'])
        for write in op['writes']:
            for i in write['home_indices']:
                h=homes[i];n=h['word_count']
                row['sector_requests_component_upper']+=len(h['rank_group'])*(3*ceil(n,8)+2*int(n%8!=0))
        row['provider_kinds']=dict(row['provider_kinds']);row['primitive_scalar_counts']=dict(row['primitive_scalar_counts'])
        rows.append(row)
    return rows,gaps


def home_inventory(homes,manifest,boundary):
    intervals=collections.defaultdict(list);selected=0
    for h in homes:
        birth=h.get('birth_pc',h.get('binding',{}).get('PC'))
        if birth is None:raise ValueError('source home birth absent')
        if birth>boundary:continue
        selected+=1
        for rank in h['rank_group']:
            if h['home']['class']=='RF':
                for copy in (0,1):
                    a=(2*h['SM']+copy)*262144+h['home']['slot_first']*512
                    b=a+h['home']['vectors']*512
                    if b>16777216:raise ValueError('RF aperture')
                    intervals['rf',rank].append([a//32,ceil(b,32)])
            elif h['home']['class']=='HBM_NATIVE_STATE':
                b=h['binding'];a=b['base'];end=a+b['reservation_bytes']
                if not 33554432<=a<end<=67108864:raise ValueError('AW27 state aperture')
                intervals['state',rank].append([a//32,ceil(end,32)])
            else:raise ValueError('unsupported home class')
    for image in manifest['initial_versions']:
        if 'home' in image:
            h=image['home'];intervals['state',image['rank']].append([h['base']//32,ceil(h['base']+h['reservation_bytes'],32)])
    ports={f'{kind}:{rank}':merged(v) for (kind,rank),v in intervals.items()}
    counts={key:sum(b-a for a,b in spans) for key,spans in ports.items()}
    # R58's already-produced PC10 shared scratch remains part of every later
    # captured state. Price all currently charged 3072 apertures conservatively.
    shared_sectors=96*32*65536//32 if boundary>=10 else 0
    total=sum(counts.values())+shared_sectors
    return {'boundary_PC':boundary,'source_home_count':selected,'RF_state_port_count':len(ports),
            'shared_port_upper':3072 if boundary>=10 else 0,'resident_sector_upper':total,
            'largest_port_sector_upper':max([2048 if shared_sectors else 0]+list(counts.values())),
            'serialized_sector_payload_upper_bytes':46*total,'raw_byte_extent_upper':32*total,
            'persisted_raw_contents_not_reclaimed_on_version_release':True,'AW':27,
            'actual_checkpoint_bytes':None,'whole_checkpoint_projection_complete':False}


def segments(native,rows):
    # Every source PC is retained in the plan. Milestones are evidence boundaries,
    # not changes to the program or reductions in the completion goal.
    stops={19,20,2212}
    for o in native['instructions']:
        layer=o['source_op'].get('layer')
        next_layer=native['instructions'][o['pc']+1]['source_op'].get('layer') if o['pc']<2212 else None
        if layer is not None and layer!=next_layer and o['pc']>=20:stops.add(o['pc'])
    first=11;answer=[]
    for stop in sorted(stops):
        if stop<first:continue
        part=rows[first:stop+1]
        answer.append({'first_PC':first,'last_PC':stop,'families':dict(collections.Counter(r['family'] for r in part)),
          'native_calls':sum(r['native_calls'] for r in part),'sector_requests_component_upper':sum(r['sector_requests_component_upper'] for r in part),
          'primitive_scalar_counts':dict(sum((collections.Counter(r['primitive_scalar_counts']) for r in part),collections.Counter())),
          'immutable_LOAD_bytes':sum(r['immutable_LOAD_bytes'] for r in part),
          'CPU_native_live_and_transient_bytes':max(r['CPU_native_live_and_transient_bytes'] for r in part),
          'native_numerical_pass':None,'whole_journal_bytes':None,'cold_metadata_and_RAM_complete':False})
        first=stop+1
    if first!=2213:raise ValueError('all-PC milestones incomplete')
    return answer


def generate():
    for name,want in PINS.items():
        if sha(ROOT/name)!=want:raise ValueError('enrolled source drift: '+name)
    from ds_hbm_pc10_projection_r46 import source_inputs
    from h3_ds_connected_provider_r37 import peer
    import ds_producer_checkpoint_resume_v3 as C
    native,homes,manifest=source_inputs()
    if C.sha(C.__file__)!='e323ce55e837e32418a74ae271897357952780681a5161205d8a12498060321e':
        raise ValueError('unchanged strict V3 required')
    rows,gaps=source_rows(native,homes,manifest,peer('h3_deepseek_streaming_linear').footprint)
    stages=segments(native,rows)
    # Exact current serialization schema for source graph; cold metadata lives
    # outside actual produced payload, but consumes host RAM at every constructor.
    graph={'native':native,'homes':homes,'manifest':manifest}
    graph_bytes=len(C.canonical(graph));graph_heap=C.deep_metadata_bytes(graph)
    ram_unit=load(ROOT/'results/uarch/ds_hbm_dual_resources_r56_20261003/model.json')['RAM']['interpreter']
    per_sector=ram_unit['sector_entry_bytes']
    envelope=load(ROOT/'results/uarch/ds_hbm_source_prefix_r39_20261002/journal_schema_envelope_r2.json')['selected_envelope_bytes']
    for stage in stages:
        inv=home_inventory(homes,manifest,stage['last_PC']);stage['checkpoint_sector_inventory']=inv
        requests=stage['sector_requests_component_upper']
        stage['conservative_sector_journal_component_bytes']=requests*8*8*(envelope+64)
        # Finite file headers, existing source dictionary bootstrap and restored
        # streams. New operator receipt/dictionary schemas not priced as zero.
        streams=inv['RF_state_port_count']+inv['shared_port_upper']+4
        stage['fresh_journal_bootstrap_component_bytes']=131072+streams*8192
        stage['compact_complete_historical_file_upper']=2*streams+2
        raw=inv['resident_sector_upper']*per_sector
        stage['old_and_restored_sector_heap_component_bytes']=2*raw
        stage['largest_restore_dictionary_copy_component_bytes']=inv['largest_port_sector_upper']*ram_unit['singleton_dict_bytes']
        stage['two_cold_source_graph_heap_component_bytes']=2*graph_heap
        stage['canonical_source_graph_workspace_component_bytes']=4*graph_bytes
        stage['remaining_prices']=['family-specific history/query/route/Engram/provider append and read schemas',
            'source-read/group-call/publication/witness dictionary and framed event records',
            'actual retained array payload/closure metadata and source_contract extensions',
            'old/new live graph instances and alias counts; immutable mappings; state codec and checkpoint tensor temporaries',
            'actual shared endpoint support for later collectives; unique roots across all sealed checkpoints']
    return {'schema':'DS_ALL_PC_CHECKPOINT_CONTINUATION_PLAN_V1','status':'SOURCE_COUNTED_COMPONENTS_WITH_EXPLICIT_MISSING_NATIVE_BINDINGS',
      'source_sha256':PINS,'PCs':2213,'families':dict(collections.Counter(r['family'] for r in rows)),
      'templates':len(native['templates']),'rows':rows,'milestones':stages,'missing_provider_bindings':gaps,
      'cold_metadata':{'source_graph_canonical_bytes':graph_bytes,'source_graph_python_heap_bytes':graph_heap,
          'source_graph_fixed_for_all_scopes':True,'CPython_sector_cost_basis':ram_unit},
      'binding_gap_counts':dict(collections.Counter(g['reason'] for g in gaps)),
      'current_runner_blockers':[
        {'first_PC':11,'source':'tools/h3_ds_source_prefix_provider_r39.py:validate_prefix','reason':'Only stop9/10 admitted; need additive exact full-scope constructor enrollment'},
        {'first_PC':11,'source':'tools/ds_hbm_source_prefix_r45.py:driver_class.run_buffer','reason':'Non-group PC>9 refused; unchanged generic native/streaming executor needs additive source-bound selection'},
        {'first_PC':20,'source':'tools/h3_ds_checkpoint_provider_r33.py:weight_view','reason':'Path implemented; require actual PC19 route IDs, all-rank PC20 descriptor retirement and selected checkpoint tensor codec before weight reads'},
        {'first_PC':None,'source':'tools/ds_producer_checkpoint_resume_v3.py:validate_shared','reason':'PC10 original shared-owner schema only; any later-PC shared-owner successor requires separately source-pinned schema, no V3 weakening'},
        {'first_PC':11,'source':'tools/ds_hbm_pc10_engine_r44.py:Witness','reason':'Current independent output coverage ends PC10; full remaining producer outputs need independent actual-source comparison enrollment'}],
      'strict_checkpoint_interface':['project_checkpoint','capture_quiescent','plan_run_scope_transition','verify_checkpoint','restore_quiescent'],
      'continuation_rule':'Fresh journal and exact cold data identity; only verified contiguous retired prefix skipped. All old inventories retained immutable.',
      'first_next_milestone':'PC11..19 inclusive; PC20 selected-expert admission is separate next boundary, not omitted from full token',
      'physical_timing_or_rate_qualified':False,'native_arithmetic_order_changed':False,'actual_prefix_launch':False,
      'full_token_numerical_pass':None,'whole_resource_admission':False}


def reconcile_from_retained(path):
    """Refine provider binding/cadence census without recomputing numerical work."""
    for name,want in dict(PINS,**MRO_PINS).items():
        if globals()['sha'](ROOT/name)!=want:raise ValueError('enrolled source drift: '+name)
    if globals()['sha'](path)!='7635b10a1f6b17e5922806145e5609a563bc96e41c5f933110632a363813a2ca':raise ValueError('exact retained complete source-count model required')
    retained=load(path)
    if retained['source_sha256']!=PINS:raise ValueError('retained source enrollment mismatch')
    from ds_hbm_pc10_projection_r46 import source_inputs
    native,homes,manifest=source_inputs()
    if [(r['PC'],r['family'],r['dependencies']) for r in retained['rows']]!=[(o['pc'],o['family'],o['dependencies']) for o in native['instructions']]:
        raise ValueError('retained complete per-PC identity mismatch')
    gaps=[]
    for op in native['instructions']:
        for tid,bindings in op['provider_bindings'].items():
            for name,b in bindings.items():
                reason=missing_binding(op,tid,name,b,manifest)
                if reason:gaps.append(dict(PC=op['pc'],family=op['family'],template=tid,operand=name,kind=b['kind'],reason=reason,logical_tensor=b.get('logical_tensor')))
    retained['missing_provider_bindings']=gaps
    retained['binding_gap_counts']=dict(collections.Counter(g['reason'] for g in gaps))
    retained['current_runner_blockers']=[b for b in retained['current_runner_blockers'] if not (b['first_PC']==20 and b['source']=='tools/h3_ds_checkpoint_provider_r30.py:weight_view')]
    retained['current_runner_blockers'].append(dict(first_PC=20,source='tools/h3_ds_checkpoint_provider_r33.py:weight_view',reason='Implemented conditional route-to-weight path; actual route IDs/descriptors/source codecs require ordered execution, not reference substitution'))
    # Source collective code reads each actually owned source fragment, not
    # every zero-filled position of declared parts/mask arrays. The ownership
    # mask is locally generated and never a sector read stimulus.
    version_requests={}
    for op in native['instructions']:
        for w in op['writes']:
            version_requests[w['version']]=sum(len(homes[i]['rank_group'])*ceil(homes[i]['word_count'],8) for i in w['home_indices'])
    for op,row in zip(native['instructions'],retained['rows']):
        row['source_owned_sector_request_component_upper']=row['sector_requests_component_upper']
        row['collective_generated_mask_sector_requests']=None
        if op['family'] not in ('all_gather','all_reduce'):continue
        declared=0;owned=0
        for rb in op['rank_bindings']:
            if rb.get('empty_owned_extent'):continue
            buffers=rb.get('buffer_programs') or [{'template':rb['template']}]
            for b in buffers:
                tid=b['template'];program=native['templates'][tid]
                for name,spec in program['providers'].items():
                    binding=op['provider_bindings'][tid][name]
                    if binding['kind'] in ('versioned_operand','explicit_auxiliary_provider'):
                        declared+=ceil(shape_size(spec),32)+32*(96 if name=='parts' else 1)
                    if name=='parts':
                        version=b.get('read_version',binding['version'])
                        if version not in version_requests:raise ValueError('collective actual producer home absent')
                        owned+=version_requests[version]
                    elif name!='ownership_mask':raise ValueError('unreviewed collective operand')
        row['source_owned_sector_request_component_upper']+=owned-declared
        if row['source_owned_sector_request_component_upper']<0:raise ValueError('negative source-owned count')
        row['collective_generated_mask_sector_requests']=0
        row['source_owned_collective_READ_requests']=owned
    from ds_hbm_connected_prepare_r37 import load as decode
    envelope=decode(ROOT/'results/uarch/ds_hbm_source_prefix_r39_20261002/journal_schema_envelope_r2.json')['selected_envelope_bytes']
    for stage in retained['milestones']:
        part=retained['rows'][stage['first_PC']:stage['last_PC']+1]
        stage['source_owned_sector_request_component_upper']=sum(r['source_owned_sector_request_component_upper'] for r in part)
        stage['source_owned_conservative_sector_journal_component_bytes']=stage['source_owned_sector_request_component_upper']*8*8*(envelope+64)
    from h3_ds_connected_provider_r37 import composed_class
    import inspect
    cls=composed_class()  # Class/source introspection only, no provider constructor.
    retained['composed_provider_source_sha256']=MRO_PINS
    retained['composed_provider_MRO']=[{'class':c.__name__,'source':str(Path(inspect.getsourcefile(c)).relative_to(ROOT))} for c in cls.__mro__ if c is not object]
    retained['effective_weight_view_source']=str(Path(inspect.getsourcefile(cls.weight_view)).relative_to(ROOT))
    handlers=collections.Counter();dynamic=[];resolved_aux=[]
    for op in native['instructions']:
        for tid,bindings in op['provider_bindings'].items():
            for name,b in bindings.items():
                handler=provider_handler(op,name,b);handlers[handler]+=1
                if b['kind']=='immutable_weight_provider' and isinstance(b['logical_tensor'],list):
                    dynamic.append(dict(PC=op['pc'],family=op['family'],template=tid,operand=name,slot_matrix=b['logical_tensor'],implementation='r33',descriptor_supported=handler!='r33 rejects non-expert composite weight descriptor',route_required=(b['logical_tensor'][0]<6 if type(b['logical_tensor'][0]) is int else None),actual_route_or_shared_source_binding_pass=None))
                if b['kind']=='explicit_auxiliary_provider' and f"{op['pc']}/{tid}/{name}" not in manifest['view_bindings'] and handler!='explicit immutable auxiliary manifest record':
                    resolved_aux.append(dict(PC=op['pc'],template=tid,operand=name,handler=handler))
    retained['source_handler_counts']=dict(handlers);retained['dynamic_weight_source_dependencies']=dynamic
    retained['auxiliary_manifest_absence_resolved_by_actual_source_hooks']=resolved_aux
    per_sector=retained['cold_metadata']['CPython_sector_cost_basis']['sector_entry_bytes']
    for stage in retained['milestones']:
        inv=stage['checkpoint_sector_inventory']
        field_rows=[b for b in manifest['query_field_homes']['rows'] if b['PC']<=stage['last_PC']]
        extra=sum(ceil(b['reservation_bytes'],32) for b in field_rows)
        inv['query_field_home_count']=len(field_rows);inv['query_field_sector_component_upper']=extra
        inv['all_declared_home_and_query_sector_component_upper']=inv['resident_sector_upper']+extra
        inv['all_declared_home_and_query_serialized_sector_component_bytes']=46*(inv['resident_sector_upper']+extra)
        inv['all_finite_RF_state_shared_aperture_sector_upper']=96*((16<<20)+(32<<20)+32*65536)//32
        inv['all_finite_RF_state_shared_aperture_serialized_sector_upper_bytes']=46*inv['all_finite_RF_state_shared_aperture_sector_upper']
        stage['old_and_restored_declared_home_query_heap_component_bytes']=2*(inv['resident_sector_upper']+extra)*per_sector
    retained['next_implementation_gate']={
        'first_contiguous_segment':[11,19],
        'whole_completion_PC_end':2212,
        'constructor':'Add external full-source scope validator/cold-constructor orchestration retaining original provider+engine class enrollment, homes/dispatch/source graph/generation and retention; old stop9/10 launcher untouched',
        'controller':'Source-pinned default-off full-native primitive step/controller for all non-group PCs; source numeric/read/publish/release/retire order and all rank/field identities unchanged. No high-level family oracle, no override of live R58 methods.',
        'strict_V3_identity':'Restore with exact old source class identity. A different engine class/MRO source SHA is NOT an allowed run_scope transition; independently bind any external controller through source_contract and journal provenance before its use.',
        'evidence':'Actual restored PC10 first; then actual PC11..19 independent ordered numerical/output receipts; every later milestone remains required. Actual PC20 route source is prerequisite to selected expert reads.',
        'pricing':'Per-operator bridge/publication/witness records, state history/query codec read/append records and cold metadata/array copies remain required before complete resource admission; no unknown cost converted to zero.'}
    retained['audit_correction']='r2/r3 inspected r30 base only and falsely classified inherited r31/r33 and r36/r37 paths as missing. All earlier artifacts preserved; r6 actual MRO supersedes those classifications; six composite compressor descriptors remain rejected by actual r33 call identity/schema. Implementation existence does not establish trained numerical PASS.'
    retained['refinement']={'retained_model_sha256':sha(path),'operator_counts_RAM_home_extents_reused_unchanged':True,
        'collective_scope':'One addressed read per owned fragment sector per receiver; local mask synthesis0 reads; both mirror writes + addressed readback retained; codecs/append streams still unpriced',
        'actual_numeric_or_provider_execution':False}
    return retained



def next_scope_request(model, retired_PCs, old_journal_root, new_journal_root):
    """Plan a continuation only; V3 independently verifies actual retired state.

    This never grants admission, substitutes payload, or executes an operator.
    A runner may call it automatically after each qualified checkpoint boundary.
    """
    if not retired_PCs or any(type(pc) is not int for pc in retired_PCs) or retired_PCs!=list(range(retired_PCs[-1]+1)):
        raise ValueError('contiguous retired prefix required')
    first=retired_PCs[-1]+1
    if first<11 or first>model['PCs']:raise ValueError('PC10 checkpoint required; no prefix repetition')
    if Path(old_journal_root).resolve()==Path(new_journal_root).resolve():raise ValueError('fresh journal root required')
    if first==model['PCs']:return {'complete':True,'execution_authorized_by_this_helper':False}
    stage=next(s for s in model['milestones'] if s['first_PC']<=first<=s['last_PC'])
    return dict(first_PC=first,prefix_stop=stage['last_PC'],old_journal_root=str(old_journal_root),
        new_journal_root=str(new_journal_root),repeat_retired_prefix=False,
        source_data_identity_changed=False,execution_authorized_by_this_helper=False,
        pending=['V3 actual checkpoint/complete historical inventory verification',
          'exact cold constructor/source-contract extension and scope role proof',
          'independent numerical reference enrollment for requested PCs',
          'actual selected source handlers and primitive controller enrollment',
          'complete checkpoint+journal+RAM projection against fresh headroom'],
        checkpoint_APIs=model['strict_checkpoint_interface'])

def main():
    a=argparse.ArgumentParser();a.add_argument('--out',type=Path,required=True);a.add_argument('--reconcile-from',type=Path);args=a.parse_args()
    if args.out.exists():raise ValueError('fresh model output; preserve earlier records')
    result=reconcile_from_retained(args.reconcile_from) if args.reconcile_from else generate();args.out.mkdir(parents=True)
    (args.out/'model.json').write_bytes(json.dumps(result,sort_keys=True,indent=2).encode()+b'\n')
    print(json.dumps({'PCs':result['PCs'],'families':len(result['families']),'next':result['milestones'][0],
       'gap_counts':result['binding_gap_counts'],'cold_metadata':result['cold_metadata']},sort_keys=True))

if __name__=='__main__':main()

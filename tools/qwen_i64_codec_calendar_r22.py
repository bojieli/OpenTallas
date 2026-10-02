"""Add actual split64 homes/traffic to pinned5881 schedules and reprove finite DAG.
No native payload, execution callback, physical clock, RTL or rate admission.
"""
import argparse,ast,copy,gzip,hashlib,json,math
from collections import Counter,defaultdict
from pathlib import Path
D=Path(__file__).resolve().parents[1]/'results/uarch/qwen_i64_codec_calendar_r22_20261002'

def inputs():
    receipt=json.loads((D/'input_receipt.json').read_bytes())
    for name,sha in receipt['files'].items():
        if hashlib.sha256((D/name).read_bytes()).hexdigest()!=sha:raise ValueError('input digest '+name)
    return json.loads(gzip.decompress((D/'calendar_codec_metadata.json.gz').read_bytes())),json.loads((D/'source_manifest.json').read_bytes())

def source_checks():
    source=(D/'calendar_source.py.snapshot').read_text();tree=ast.parse(source)
    names={'positive','ceil','Calendar','verify_calendar','verify_native_program'}
    nodes=[n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name in names]
    namespace={'Counter':Counter,'defaultdict':defaultdict,'math':math}
    exec(compile(ast.Module(body=nodes,type_ignores=[]),'<pinned5881 pure checks>','exec'),namespace)
    return namespace

def augment(program,homes,costs):
    """Preserve source operation order, loop repetitions and exact lowword homes."""
    for h in homes.values():
        if h['semantic_bits']!=64 or h['highword_bytes']!=h['bytes'] or h['highword_base']%32:raise ValueError('split64 codec capacity/alignment')
        if h['base']<h['highword_base']+h['highword_reserved_bytes'] and h['highword_base']<h['end_exclusive']:raise ValueError('low/high alias')
    ordered=sorted((h['highword_base'],h['highword_base']+h['highword_reserved_bytes']) for h in homes.values())
    if any(a[1]>b[0] for a,b in zip(ordered,ordered[1:])):raise ValueError('highword symbol alias')
    p=copy.deepcopy(program);old_duration=p['duration'];traffic=Counter()
    read_cost=costs['HBM_read_sector']+2*(costs['owner_lookup']+costs['owner_held_accept'])+sum(costs[k] for k in ['forward_CDC','consume','reverse_CDC','validated_reverse_grant','retire'])
    write_cost=costs['HBM_write_sector']+2*(costs['owner_lookup']+costs['owner_held_accept'])+sum(costs[k] for k in ['visibility_fence','forward_CDC','consume','reverse_CDC','validated_reverse_grant','retire'])
    if min(read_cost,write_cost,costs['I64_codec_split_join'])<=0:raise ValueError('positive codec cost required')
    def walk(nodes,multiplier):
        offset=0
        for n in nodes:
            n['offset']=offset
            if n['kind']=='loop':
                child=walk(n['body'],multiplier*n['count']);n['duration']=child*n['count']+n.get('control_cycles',n.get('explicit_empty_loop_control_cycles',0))
                if 'iteration_stride' in n:n['iteration_stride']=child
            else:
                src=n['source_instruction'];reads=[]
                for text in src.get('src',[]):
                    parsed=ast.parse(text,mode='eval');names={a.id for a in ast.walk(parsed) if isinstance(a,ast.Name)}&set(homes)
                    # Current three wide symbols are direct arrays. Fail on a new view rather than infer traffic.
                    if names and not isinstance(parsed.body,ast.Name):raise NotImplementedError('wide indexed-expression codec cadence')
                    reads.extend(sorted(names))
                destination=src.get('dst','').split('[')[0];writes=[destination] if destination in homes else []
                batches=n['batches128'];extra_read=len(reads)*batches*16;extra_write=len(writes)*batches*16
                if reads or writes:
                    n['split64_provider_bindings']={s:homes[s] for s in set(reads+writes)}
                    n['split64_intervals']={'read':'Acquire immutable PC/symbol/definition/iteration generation; capture lower+upper under finite staging, decode only after both, release logical reader after consumer','write':'Retain pair lease; both lower and upper backing-visible ACK+validated reverse grants before publication and PC retirement','staging_bytes':1536,'physical_tag_release':'Sector capture/ACK consumer followed by validated reverse grant; logical pair lease remains across streams','no_timer_publication':True}
                    additions={}
                    if extra_read:additions.update(I64_highword_read=extra_read*read_cost,I64_highword_RF_read=len(reads)*batches*costs['RF_read'],I64_join=len(reads)*batches*costs['I64_codec_split_join'])
                    if extra_write:additions.update(I64_highword_write=extra_write*write_cost,I64_highword_RF_ACK=len(writes)*batches*costs['RF_write_ACK'],I64_split=len(writes)*batches*costs['I64_codec_split_join'])
                    # 64bit two-input operations use two64lane batches, fitting three512B staging vectors.
                    if src['op'] in ('SHL64','IADD64'):additions['I64_finite_staging_execute']=batches*costs['native:'+src['op']]
                    n['stage_cycles'].update(additions);n['duration']=sum(n['stage_cycles'].values())
                    traffic['highword_read_sectors']+=multiplier*extra_read;traffic['highword_write_sectors']+=multiplier*extra_write
                    traffic['codec_join_tiles']+=multiplier*len(reads)*batches;traffic['codec_split_tiles']+=multiplier*len(writes)*batches
            offset+=n['duration']
        return offset
    p['duration']=walk(p['primitive_tree'],1)+p.get('empty_owned_extent_control_cycles',0)
    p['split64_highword_homes']=homes;p['split64_duration_delta']=p['duration']-old_duration
    p['codec_contract']='Actual source64bit semantics retained as low32+high32 addressed streams; source4B lowword locations unchanged; no highword sharing or free ports'
    return p,dict(traffic)

def join():
    data,manifest=inputs();source=source_checks();costs=dict(manifest['endpoint_cycles']['values']);costs['I64_codec_split_join']=32
    native_hash=manifest['source_sha256']['results/uarch/h3_complete_native_calendar_20261002/final_qwen_8fab95560/Qwen_native.json.gz']
    assert native_hash==data['native_source_SHA256']
    homes=defaultdict(dict)
    for h in data['wide_homes']:homes[h['pc'],h['rank']][h['symbol']]=h
    programs={};durations=dict(data['program_durations']);rows=[];total=Counter()
    for key,program in data['native_programs'].items():
        pc,rank=data['program_pc_rank'][key];old_counts=source['verify_native_program'](program)
        amended,traffic=augment(program,homes[pc,rank],costs)
        assert source['verify_native_program'](amended)==old_counts
        programs[key]=amended;durations[key]=amended['duration'];total.update(traffic)
        rows.append({'program_ref':key,'pc':pc,'rank':rank,'source_duration':program['duration'],'codec_duration':amended['duration'],'delta':amended['split64_duration_delta'],'traffic':traffic,'symbols':sorted(homes[pc,rank])})
    source['verify_calendar'](data['events'],data['resources'])
    calendar=source['Calendar'](data['resources'])
    for e in data['events']:
        duration=e['end']-e['start'];attrs={k:e[k] for k in ['native_program_ref','pc','rank'] if k in e}
        if 'native_program_ref' in e:
            key=e['native_program_ref'];assert duration==data['program_durations'][key];duration=durations[key]
        calendar.add(e['id'],e['deps'],duration,{k:len(v) for k,v in e['resources'].items()},**attrs)
    proof=source['verify_calendar'](calendar.events,data['resources']);cycles=max(e['end'] for e in calendar.events)
    summary={'status':'PASS_SOFTWARE_SPLIT64_TRAFFIC_AND_FINITE_INTERVAL_JOIN_ONLY','parent_calendar_commit':'5881a3b92','final_native_SHA256':native_hash,'source_match':True,
        'affected_PCs':len({r['pc'] for r in rows}),'affected_rank_programs':len(rows),'split64_symbols':len(data['wide_homes']),
        'baseline_software_ticks':data['baseline_cycles'],'codec_join_software_ticks':cycles,'added_software_ticks':cycles-data['baseline_cycles'],
        'cycle_unit':'abstract_software_tick','calibration':'PROVISIONAL_UNCALIBRATED','added_endpoint_parameters':{'I64_codec_split_join':32},'traffic':dict(total),'affected_programs':rows,
        'existing_endpoints':{'highword_read_sector':106,'highword_write_sector':126,'two_context_lookups':24,'mirrored_highword_write_ACK':costs['RF_write_ACK']},
        'capacity':{'upper32_sidecar_bytes_per_rank':1572864,'new_RF_ports':0,'new_PHY_ports':0,'finite_data_staging_bytes':1536,'IADD64_SHL64_logical_lanes_per_batch':64,'replacement_or_area_credit':0},
        'proof':proof,'source_primitive_counts_unchanged':True,'source_scratch_homes_unchanged':True,
        'physical_tag_and_pair_ownership':'Actual software backing/capture, consume/reverse grant endpoints exercised by r21; physical provider still unqualified. No overwrite before joined generation retires.',
        'no_admission':{'hardware':False,'PHY':False,'SSFF':False,'rate':False,'trained_checkpoint_fulltoken':False},'jobs':[]}
    return summary,programs,calendar.events

def emit(out):
    summary,programs,events=join();out.mkdir(parents=True,exist_ok=True)
    raw=gzip.compress(json.dumps({'programs':programs,'events':events},sort_keys=True,separators=(',',':')).encode(),mtime=0)
    (out/'codec_calendar.json.gz').write_bytes(raw);summary['calendar_SHA256']=hashlib.sha256(raw).hexdigest();(out/'join.json').write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);emit(p.parse_args().output)

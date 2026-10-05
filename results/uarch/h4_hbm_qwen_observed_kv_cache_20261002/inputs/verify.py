"""Offline U8 ownership/state/read comparator for fresh observed output only.

A structurally valid file is not evidence of observing the historical live run.
Source/GO provenance and independent reference provenance remain separate gates.
"""
import hashlib
import json
from pathlib import Path
import struct


def require(value, reason):
    if not value:
        raise ValueError(reason)


def expected_addresses(native, layer, rank):
    p = native['source_program']; c = p['config']; context = p['context_capacity']
    extents = {e['name']:e for e in p['memory_allocation'][rank]['extents']}
    addresses = []
    for kind in ('K', 'V'):
        base = extents[f'L{layer}.{kind}']['base']
        for head in range(c['num_key_value_heads']//2):
            for dim in range(c['head_dim']):
                offset = (head*(context//16)*c['head_dim']+dim)*16 if kind == 'K' else head*context*c['head_dim']+dim
                addresses.append(base+offset)
    return set(addresses)


def event_plan(native):
    """Expected schema only. Never generates an observed journal."""
    names={v['version']:v['name'] for v in native['operands']}
    rows=[]
    for op in native['operations']:
        code=op['opcode']
        if code in ('KV_WRITE','KV_FENCE','KV_READ'):
            key=[op['attributes']['layer'],op['attributes']['die'],0]
            kinds=[{'KV_WRITE':'write_accept','KV_FENCE':'commit_publish','KV_READ':'acquire'}[code]]
        elif code in ('SCORES','PV'):
            name=names[op['reads'][1]].split('.')
            key=[int(name[0][1:]),int(name[1][1:]),0]
            kinds=['consumer_done']+(['release'] if code=='PV' else [])
        else:continue
        for kind in kinds:
            rows.append(dict(pc=op['pc'],event=kind,key=key,reads=op['reads'],writes=op['writes'],
                stage=code if kind=='consumer_done' else None))
    require(len(rows)==432,'source432eventplan')
    return rows


def verify_event_bindings(native, events):
    plan=event_plan(native)
    require(len(events)==len(plan),'missing432eventcoverage')
    for row,expected in zip(events,plan):
        require(all(row.get(k)==expected[k] for k in ('pc','event','key','reads','writes')), 'exact source PC/layer/rank/version binding')
        require(row.get('stage')==expected['stage'],'exact consumer stage')
    return plan


def verify_transition_state(native, events):
    tags={};leases={}
    for e in events:
        key=tuple(e['key']);layer,rank,position=key
        state=e['state'];extent=next(x for x in native['source_program']['memory_allocation'][rank]['extents'] if x['name']=='KV_provider_state')
        require(state['observation_moment']=='after_storage_method_return','actual transition snapshot timing')
        require(state['record_address']==extent['base']+36864+16*layer,'packedrecord address')
        require(state['bitmap_address']==extent['base']+(layer*8192+position)//8,'publicationbitmap address')
        kind=e['event'];value=int.from_bytes(bytes.fromhex(state['record_hex']),'little')
        require(len(bytes.fromhex(state['record_hex']))==16,'state record width')
        published=bool(state['bitmap_byte']&(1<<(position%8)))
        if kind=='write_accept':
            tags[key]=(e['tag'],e['pc'])
            require(not published and value==0 and state['pending_writers']==1 and state['active_readers']==0,'accepted notvisible')
        else:
            tag,pc=tags[key];identity=tag;done=0;status=1;readers=0
            if kind=='acquire':leases[key]=e['lease']
            if kind in ('acquire','consumer_done','release'):
                identity=leases[key];readers=1;status=2
            if kind=='consumer_done' and e['stage']=='SCORES':done=1
            if kind=='release' or (kind=='consumer_done' and e['stage']=='PV'):done=3;status=3;readers=0
            expected=position|(identity<<13)|(pc<<77)|(done<<88)|(status<<90)
            require(published and value==expected and state['pending_writers']==0 and state['active_readers']==readers,'actual publish/read/consumer retirement transition')
    return True


def payload_layout(native, key):
    layer,rank,position=key
    require(position==0,'position0qualifiedlayout')
    p=native['source_program'];c=p['config'];hd=c['head_dim'];context=p['context_capacity']
    ex={e['name']:e for e in p['memory_allocation'][rank]['extents']}
    operations={o['opcode']:o for o in native['operations'] if o['opcode'] in ('KV_WRITE','KV_READ') and o['attributes']['layer']==layer and o['attributes']['die']==rank}
    result={}
    for index,kind in enumerate(('K','V')):
        extent=ex[f'L{layer}.{kind}']
        for head in range(c['num_key_value_heads']//2):
            for dim in range(hd):
                offset=(head*(context//16)*hd+dim)*16 if kind=='K' else head*context*hd+dim
                result[extent['base']+offset]=dict(kind=kind,head=head,dim=dim,position=0,byte_offset=offset,
                    provider_ref=extent['provider_ref'],producer_version=operations['KV_WRITE']['reads'][index],
                    decoded_read_version=operations['KV_READ']['writes'][index])
    return result


def decoded_hashes(native, payloads):
    """Independent scalar E4M3FN unpack; canonical positive zero required."""
    hashes={}
    for key,values in payloads.items():
        layout=payload_layout(native,key)
        for kind in ('K','V'):
            selected=sorted((meta['head'],meta['dim'],values[address],meta) for address,meta in layout.items() if meta['kind']==kind)
            data=bytearray()
            for _,_,code,_ in selected:
                require(code!=128,'noncanonical negative FP8 zero')
                magnitude=code&127;exponent=magnitude>>3;mantissa=magnitude&7
                value=mantissa/512 if exponent==0 else (1+mantissa/8)*2**(exponent-7)
                if code&128:value=-value
                data.extend(struct.pack('<f',value))
            version=selected[0][3]['decoded_read_version']
            hashes[version]=hashlib.sha256(data).hexdigest()
    return hashes


def assess(native, directory, journal_validator, expected_u8=None, read_trace=None):
    directory=Path(directory)
    needed=['kv_journal.jsonl','payload_inventory.jsonl','committed_U8.bin','read_U8.bin','final_U8.bin',
        'final_state_rank0.bin','final_state_rank1.bin','observation_terminal.json']
    missing=[name for name in needed if not (directory/name).is_file()]
    if missing:return dict(status='UNKNOWN_MISSING_OBSERVATIONS',missing=missing,actual_RTL=False,physical_credit=False)
    return verify(native,directory,journal_validator,expected_u8,read_trace)


def verify(native, directory, journal_validator, expected_u8=None, read_trace=None):
    directory = Path(directory)
    events = [json.loads(line) for line in (directory/'kv_journal.jsonl').read_text().splitlines()]
    journal_validator(native, events)
    verify_event_bindings(native,events)
    verify_transition_state(native,events)
    groups = {(layer,rank,0) for layer in range(36) for rank in range(2)}
    expected = {key:expected_addresses(native,*key[:2]) for key in groups}
    inventory = [json.loads(line) for line in (directory/'payload_inventory.jsonl').read_text().splitlines()]
    files = ('committed_U8.bin','read_U8.bin','final_U8.bin')
    payloads = {name:{} for name in files}; cursors = {name:0 for name in files}
    commit_pcs = {tuple(e['key']):e['pc'] for e in events if e['event']=='commit_publish'}
    read_pcs = {tuple(e['key']):e['pc'] for e in events if e['event']=='acquire'}
    for record in inventory:
        name = record['file']; key = tuple(record['key'])
        require(name in files and key in groups, 'source file/key ownership')
        require(record['offset']==cursors[name] and record['bytes']==record['records']*9, 'exclusive contiguous inventory')
        require(record['record_format']=='<uint64_address,uint8_code>', 'U8 address codec')
        if name!='final_U8.bin':
            require(record['pc']==(commit_pcs if name=='committed_U8.bin' else read_pcs)[key], 'actual payload PC binding')
        with (directory/name).open('rb') as stream:
            stream.seek(record['offset']); data=stream.read(record['bytes'])
        require(len(data)==record['bytes'] and hashlib.sha256(data).hexdigest()==record['sha256'], 'raw payload identity')
        values=payloads[name].setdefault(key,{})
        for address,code in struct.iter_unpack('<QB',data):
            require(address in expected[key] and address not in values, 'source address/duplicate ownership')
            require(code&127!=127, 'FP8 NaN code')
            values[address]=code
        cursors[name]+=len(data)
    for name in files:
        require((directory/name).stat().st_size==cursors[name], 'unbound raw trailing bytes')
        require(set(payloads[name])==groups, 'complete72 payload groups')
        require(all(set(payloads[name][key])==expected[key] for key in groups), 'gapfree actual payload addresses')
    require(payloads[files[0]]==payloads[files[1]]==payloads[files[2]], 'commit/read/final U8 persistence')
    read_hashes=decoded_hashes(native,payloads['read_U8.bin'])
    if read_trace is not None:
        rows=[row for row in read_trace if row['opcode']=='KV_READ']
        wanted={op['pc']:op for op in native['operations'] if op['opcode']=='KV_READ'}
        require(len(rows)==72 and {row['pc'] for row in rows}==set(wanted),'complete unique72 actual KV read PCs')
        for row in rows:
            require([o['version'] for o in row['outputs']]==wanted[row['pc']]['writes'],'read PC output versions')
            require(all(o['shape']==[4,1,128] for o in row['outputs']),'position0decoded read shape')
        recorded={o['version']:o['sha256'] for row in rows for o in row['outputs']}
        require(recorded==read_hashes,'decoded FP8 actual read-hash binding')
    if expected_u8 is not None:
        require(expected_u8==payloads[files[0]], 'independent U8 numerical comparison')
    writes={tuple(e['key']):e for e in events if e['event']=='write_accept'}
    acquires={tuple(e['key']):e for e in events if e['event']=='acquire'}
    for rank in range(2):
        ext=next(e for e in native['source_program']['memory_allocation'][rank]['extents'] if e['name']=='KV_provider_state')
        state=bytearray(ext['bytes'])
        for layer in range(36):
            key=(layer,rank,0);state[layer*8192//8]|=1
            value=(acquires[key]['lease']<<13)|(writes[key]['pc']<<77)|(3<<88)|(3<<90)
            state[36864+16*layer:36864+16*layer+16]=value.to_bytes(16,'little')
        last_writer_counter=1+max(e['tag'] for e in writes.values() if e['key'][1]==rank)
        state[37440:37448]=last_writer_counter.to_bytes(8,'little')
        require((directory/f'final_state_rank{rank}.bin').read_bytes()==state, 'physical publication/producer/consumer retired state')
    terminal=json.loads((directory/'observation_terminal.json').read_text())
    require(terminal['groups']==72 and terminal['pending']==terminal['leases']==0, 'observed terminal drain')
    # Calendar must bind real emitted transitions and addressed bytes, not PC-derived events.
    sectors=sum(len({address//32 for address in addresses}) for addresses in expected.values())
    return dict(status='PASS_OBSERVED_U8_STRUCTURE_AND_STATE',groups=72,events=432,
        actual_committed_payload_bytes=73728,actual_read_payload_bytes=73728,
        committed_read_final_equal=True,packed_state_exact=True,decoded_read_hashes=read_hashes,
        actual_decoded_read_hash_binding=('PASS' if read_trace is not None else 'UNKNOWN_READ_TRACE_NOT_SUPPLIED'),
        independent_U8_numerical_comparison=('PASS' if expected_u8 is not None else 'UNKNOWN_REFERENCE_NOT_SUPPLIED'),
        observation_source_GO_provenance='REQUIRES_INDEPENDENT_RUNNER_BINDING',
        calendar=dict(causal_events=432,position=0,write_address_sectors32=sectors,
            read_address_sectors32=sectors,cycles=None,hardware_service_times='UNQUALIFIED_REQUIRED_INPUTS',
            HBM_command_or_refill_counts='UNKNOWN_NO_CACHE_OR_PHY_RECEIPT'),
        actual_RTL=False,physical_credit=False,rate_credit=False)

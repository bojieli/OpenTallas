"""Immutable paired-ROM S81 PQ action calendar; engine status never sets time."""
import json as _json
from pathlib import Path as _Path
# Measured controller latencies (single source: the PQ static calendar ABI).
ABI=_json.loads((_Path(__file__).resolve().parents[1]/'s81'/'pq_static_calendar_abi.json').read_text())
_EDGES=ABI['sampled_edge_to_registered_pin_edges']
MIN_COUNT_DRAIN=_EDGES['root_pin_to_last_consumed_count_edges']   # INCAP: 9 (was 8)
MIN_BOOT_AFTER_RESET=_EDGES['reset_release_to_first_boot_pw_edges'] # reset relay: 3
FIELDS={
 'accept_tag':(0,2),'vm_req':(2,1),'vm_addr':(3,19),'vm_resp':(22,1),
 'resp_k':(23,14),'resp_par':(37,1),'resp_fam':(38,1),'stream_req':(39,1),
 'stream_addr':(40,11),'stream_tag':(51,2),'stream_pos':(53,3),'stream_fam':(56,1),
 'stream_lastpos':(57,1),'stream_lastop':(58,1),'cfg':(59,1),'cfg_tag':(60,2),
 'launch':(62,1),'launch_tag':(63,2),'retire_mask':(65,4),'phase_end':(69,1)}


def action_word(fields, action_bits=72):
    if action_bits not in (72,75):raise ValueError("supported action width72 or75 required")
    layout={k:(lo+(3 if lo>=51 else 0),14 if k=="stream_addr" else w) for k,(lo,w) in FIELDS.items()} if action_bits==75 else FIELDS
    if not isinstance(fields,dict) or set(fields)-FIELDS.keys():
        raise ValueError('unknown native action field')
    word=0
    for key,value in fields.items():
        low,width=layout[key]
        if type(value)is not int or not 0<=value<1<<width:raise ValueError('action field bounds: '+key)
        word|=value<<low
    return word


def compile_events(events,commands,action_bits=72,pq_engine=0):
    """Commands are real emitted issuer rows, not an independently timed GO list.

    Issuer rowissue R -> cmdpin R+1 -> endpointGOpin R+2. Calendar timestamp
    R+1 -> actionpin R+2; the native controller captures both at R+3.
    """
    if not isinstance(events,list) or not 1<=len(events)<=4096:
        raise ValueError('actual calendar must fit paired4096x72 ROMs')
    if not commands:raise ValueError('real issuer PQ command rows required')
    rows=[];prev=-1;ends=[];by_time={}
    for e in events:
        t=e['timestamp']
        if type(t)is not int or not prev<t<1<<24:raise ValueError('strict increasing timestamp24 required')
        word=action_word(e['action'],action_bits=action_bits);rows.append((t<<action_bits)|word);by_time[t]=e['action'];prev=t
        if e['action'].get('phase_end',0):ends.append(t)
    if ends!=[prev]:raise ValueError('exactly one final phase_end required')
    occupied=set()
    for c in commands:
        if c['engine']!=pq_engine:raise ValueError('actual PQ engine%d issuer rows required'%pq_engine)
        t=c['issue']+1
        if t in occupied:raise ValueError('colliding actual PQ GO')
        occupied.add(t)
        if t not in by_time or by_time[t].get('accept_tag',0)!=c['native_tag']:
            raise ValueError('calendar ACCEPT tag must align actual endpoint registeredGO')
        # done = issue + 1 + measured command-pin -> observed-END latency (the
        # descriptor's observed_end_edges); never issue + latency.
        lat=c.get('pin_to_pin')
        if type(lat)is not int or lat<3:raise ValueError('PQ measured command-pin -> done-pin latency required')
        if c['done']!=c['issue']+1+lat:raise ValueError('PQ done row must equal issue + 1 + pin-to-pin latency')
    return rows


def viamap(words):
    """Actual ot_rom_4096x72_m8: logical address a -> arr[a//8][b*8+a%8]."""
    if len(words)>4096:raise ValueError('ROM capacity')
    physical=[0]*512
    for address,word in enumerate(words):
        if type(word)is not int or not 0<=word<1<<72:raise ValueError('ROM word72')
        for bit in range(72):physical[address//8]|=((word>>bit)&1)<<(bit*8+address%8)
    return ''.join(f'{row:0144x}\n' for row in physical)


def validate_tag_lifetimes(lifetimes,profile):
    """Offline pin-cycle proof obligations for actual 12-leaf live replication.

    The measured leaf contract and the actual controller must provide the
    profile. Missing controller return-consume timing prevents native dispatch.
    """
    if profile.get('source_bound')is not True:raise ValueError('actual count-chain source profile required')
    fill=profile['live_pin_to_farthest_leaf_edges']
    drain=profile['root_pin_to_last_consumed_count_edges']
    if type(fill)is not int or fill<12 or type(drain)is not int or drain<MIN_COUNT_DRAIN:
        raise ValueError('12-leaf fill and actual root/count drain (>= %d INCAP edges) required'%MIN_COUNT_DRAIN)
    last={}
    for row in sorted(lifetimes,key=lambda r:r['live_set']):
        tag=row['tag'];start=row['live_set'];first=row['first_root'];end=row['last_root'];clear=row['live_clear']
        if type(tag)is not int or tag not in range(4):raise ValueError('native tag2 required')
        if not start+fill<=first<=end<=clear-drain:raise ValueError('count live fill/drain violated')
        if tag in last and start<last[tag]+fill:raise ValueError('native tag reused before live-clear reaches all leaves')
        last[tag]=clear
    return True


def validate_boot_start(reset_release_edge,first_pw_edge):
    """Reader/endpoint registered reset relay releases 3 edges after the port;
    the compiler's boot/PW writer must not start earlier (initialization only)."""
    if type(reset_release_edge)is not int or type(first_pw_edge)is not int:raise ValueError('integer edges required')
    if first_pw_edge<reset_release_edge+MIN_BOOT_AFTER_RESET:
        raise ValueError('boot PW before reset-relay release (+%d edges)'%MIN_BOOT_AFTER_RESET)
    return True

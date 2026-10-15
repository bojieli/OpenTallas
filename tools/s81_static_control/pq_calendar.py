"""Immutable paired-ROM S81 PQ action calendar; engine status never sets time."""
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


def compile_events(events,commands,action_bits=72):
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
        if c['engine']!=0:raise ValueError('actual PQ engine0 issuer rows required')
        t=c['issue']+1
        if t in occupied:raise ValueError('colliding actual PQ GO')
        occupied.add(t)
        if t not in by_time or by_time[t].get('accept_tag',0)!=c['native_tag']:
            raise ValueError('calendar ACCEPT tag must align actual endpoint registeredGO')
        if c['done']<=c['issue']+2:raise ValueError('PQ observed completion deadline missing')
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
    if type(fill)is not int or fill<12 or type(drain)is not int or drain<5:
        raise ValueError('12-leaf fill and actual root/count drain required')
    last={}
    for row in sorted(lifetimes,key=lambda r:r['live_set']):
        tag=row['tag'];start=row['live_set'];first=row['first_root'];end=row['last_root'];clear=row['live_clear']
        if type(tag)is not int or tag not in range(4):raise ValueError('native tag2 required')
        if not start+fill<=first<=end<=clear-drain:raise ValueError('count live fill/drain violated')
        if tag in last and start<last[tag]+fill:raise ValueError('native tag reused before live-clear reaches all leaves')
        last[tag]=clear
    return True

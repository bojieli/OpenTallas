"""Bind actual per-resource MU initialization bytes to native KIT/slot bookings.

No return latency, source variant, reset epoch or first KS date is defaulted.
Resources are grouped by the caller's existing physical stage/copy/rank map.
"""
import hashlib,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'seqhost_timing_1026'))
from native_boot import compile_boot
from native_phase import seqhost_phase_contract


def decode_initialization(words):
    gaps=[];rl=None;events={};current=None;delays=set();attrs={}
    for word in words:
        if type(word)is not int or not 0<=word<1<<515 or not word&1 or word>>513:
            raise ValueError('MU initialization must contain actual active native CSR words')
        data=word>>1;op=data&255;p=(data>>32)&((1<<26)-1)
        if not p&(1<<25):raise ValueError('MU configuration valid bit missing')
        if op==0x15:
            if events:raise ValueError('MU gaps/RL must precede event rows')
            if p&(1<<24):
                if rl is not None:raise ValueError('duplicate MU return-latency configuration')
                rl=p&((1<<24)-1)
            else:gaps.append(p&((1<<24)-1))
        elif op==0x16:
            mode=(p>>21)&3
            if mode==0:
                current=p&255
                if current not in range(8)or current in events:raise ValueError('MU event header repeated/outside eight rows')
                events[current]=dict(kind=(p>>8)&1,endpoint=(p>>9)&3,attributes=[]);attrs[current]={}
            elif mode==1:
                if current is None or current in delays:raise ValueError('MU event delay missing header or repeated')
                events[current]['delay']=p&((1<<21)-1);delays.add(current)
            elif mode==2:
                if current is None:raise ValueError('MU slot attribute without event header')
                slot=p&1023
                if slot in attrs[current]:raise ValueError('duplicate MU slot attribute')
                attrs[current][slot]=dict(ab=(p>>10)&1,land=(p>>11)&1)
            else:raise ValueError('unsupported MU configuration word')
        else:raise ValueError('MU initialization file must contain only CSR0x15/0x16')
    slots=47 if len(gaps)==1 else len(gaps)
    if rl is None or set(events)!=set(range(8))or delays!=set(range(8)):
        raise ValueError('actual MU initialization needs gaps/RL and all eight complete events')
    for k in events:
        if set(attrs[k])!=set(range(slots)):raise ValueError('actual MU slot attributes incomplete')
        events[k]['attributes']=[attrs[k][s]for s in range(slots)]
    return dict(schema='opentallas.s81.seqhost_native_boot.v1',slot_gaps=gaps,return_latency=rl,events=[events[k]for k in range(8)])


def bind_contract(contract,root):
    if not contract or contract.get('schema')!='opentallas.s81.native_mu_return_calendar.v1':
        raise ValueError('explicit selected per-resource MU return calendar missing')
    root=Path(root);read=lambda p:json.loads((root/p).read_text())
    timing=read(contract['local_timing_receipt']);phase=read(contract['seqhost_phase_receipt'])
    if phase.get('verdict')!='PASS' or phase.get('masters',{}).get('dsdv_hostb_seqhost_mux')!=timing['masters']['dsdv_hostb_seqhost_mux']:
        raise ValueError('selected MU phase/timing master differs')
    if any(timing['source_sha256'].get(n)!=v for n,v in phase['source_sha256'].items()):raise ValueError('selected MU phase source differs')
    clock=seqhost_phase_contract(phase)
    if any(k in timing for k in('input_clock','seqhost_input_clock'))and seqhost_phase_contract(timing)!=clock:
        raise ValueError('selected MU phase key contracts conflict')
    timing=dict(timing,seqhost_input_clock=clock)
    words=[int(x,16)for x in(root/contract['initialization_host_file']).read_text().split()]
    config=decode_initialization(words);edges=timing['masters']['dsdv_hostb_seqhost_mux']['edges']
    edge=edges['f_ks_pin_event_plus_kit_issue_to_t_kd']
    if type(edge)is not int or edge<1:raise ValueError('measured selected KIT return age missing/malformed')
    offset=edge-1
    kit=config['return_latency']-offset
    if kit<0:raise ValueError('configured MU return precedes any possible native KIT')
    config['kit_issue']=kit;inventory=read(contract['bound_inventory'])
    encoded,emission=compile_boot(config,timing,allow_unbooked_launch=True,
        source_root=root/contract['source_root'],manifest=contract['asbuilt_manifest'],inventory=inventory)
    if encoded!=words:raise ValueError('actual MU bytes differ from complete selected native encoding')
    first=contract.get('first_KS_seq_capture');last=contract.get('initialization_last_seq_capture')
    if type(first)is not int or type(last)is not int or not 0<=last<first<1<<48 or first-last<16:
        raise ValueError('actual MU config/first KS sampled-edge bookings missing or insufficient')
    if not contract.get('clock_reset_identity'):raise ValueError('MU clock/reset identity missing')
    gaps=config['slot_gaps'];expanded=gaps*47 if len(gaps)==1 else gaps
    offsets=[sum(expanded[:i])for i in range(len(expanded))]
    identity=hashlib.sha256(json.dumps(dict(contract=contract,words=[f'{w:0129x}'for w in words],source=timing['source_sha256']),sort_keys=True).encode()).hexdigest()
    return dict(identity=identity,source_die_sha256=inventory['source_top_sha256'],source_asbuilt_sha256=inventory['source_asbuilt_sha256'],
        selected_params=dict(HOSTB_ENABLE=0,STATIC_KS6=0,STATIC_KS_SPAN=0,STATIC_KS_GRAPH_TAG=0,FMUT=0),source_pinned=True,
        clock_reset_identity=contract['clock_reset_identity'],initialization_last_seq_capture=last,first_KS_seq_capture=first,
        period=sum(expanded),slot_offsets=offsets,slot_gaps=expanded,return_latency=config['return_latency'],required_KIT_issue=kit,
        KS_sampling_to_KIT_return_fixed_edges=offset,initialization_HOST_words=len(words),
        scope='selected local source/actual CSR bytes/fixed return and slot compatibility only; no global admission or memory retirement assertion')


def check_job(job,receiver,mu,seq_ks):
    """Return concrete incompatibilities; never retag or retime source jobs."""
    problems=[]
    kits=[r for r in job['rows']if r['engine']==14]
    if len(kits)!=1:problems.append(dict(cause='native_MU_requires_exactly_one_KIT',actual_KIT_count=len(kits)))
    elif kits[0]['issue']!=mu['required_KIT_issue']:
        problems.append(dict(cause='native_KIT_disagrees_with_armed_MU_return',native_KIT=kits[0]['issue'],required_KIT=mu['required_KIT_issue'],configured_RL=mu['return_latency']))
    if job['native_die_sha256']!=mu['source_die_sha256']:
        problems.append(dict(cause='native_MU_programme_source_mismatch',native_die=job['native_die_sha256'],selected_die=mu['source_die_sha256']))
    actual=receiver.get('selected_parameters',{})
    if any(actual.get(k)!=v for k,v in mu['selected_params'].items()):
        problems.append(dict(cause='native_MU_receiver_source_variant_mismatch',receiver_parameters=actual,measured_parameters=mu['selected_params']))
    if receiver.get('clock_reset_identity')!=mu['clock_reset_identity']:
        problems.append(dict(cause='native_MU_clock_reset_identity_mismatch'))
    delta=seq_ks-mu['first_KS_seq_capture']
    if delta<0 or delta%mu['period']not in mu['slot_offsets']:
        problems.append(dict(cause='native_KS_off_selected_MU_slot',seq_KS=seq_ks,first_KS=mu['first_KS_seq_capture'],slot_offsets=mu['slot_offsets'],period=mu['period']))
    if mu['initialization_last_seq_capture']>=seq_ks:problems.append(dict(cause='native_MU_configuration_overlaps_start'))
    return problems

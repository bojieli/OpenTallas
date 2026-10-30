"""Encode selected local native entry page retirement and HOST seal protocol.

This emits real KIT/END/BEGIN/SEAL bytes; actual global HOST/KS dates and matching
incoming descriptors remain unbooked. Header phase is local issuer configuration.
"""
import copy,sys
from pathlib import Path
import dv_layer_compile as D
from layer_prog.entry_load_calendar import check_page
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'seqhost_timing_1026'))
from native_boot import compile_boot


def encode(page, timing, *, stage, start_phase):
    check_page(page)
    # This selected seqhost hardwires the native issuer stage default0. A new
    # stage contract must be source-qualified before another header is emitted.
    if stage!=0 or start_phase!=0:raise ValueError('selected local proof covers native stage0/headerphase0 only')
    if timing.get('schema')!='opentallas.s81.bound_control_local.v1' or timing.get('verdict')!='PASS':raise ValueError('selected local timing PASS required')
    master=timing['masters']['dsdv_hostb_seqhost_mux'];edges=master['edges']
    if master.get('params')!={'HOSTB_ENABLE':0,'STATIC_KS6':0}:raise ValueError('different native seqhost source variant')
    delta=edges['f_ks_pin_event_plus_kit_issue_to_t_kd']-edges['f_ks_pin_event_to_age0_command']
    if delta<0:raise ValueError('selected KIT local return precedes issuer event')
    kit=max(page['source_relative_retire_not_before'],max(r['done']for r in page['rows'])+1)
    end=kit+delta+1
    if end>=1<<24:raise ValueError('native KIT/END exceeds actual24bit age counter')
    result=copy.deepcopy(page)
    for engine,issue in[(D.ENG['KIT'],kit),(D.ENG['END'],end)]:
        result['rows'].append(dict(eng=engine,issue=issue,done=0,arg=0,row76=f'{D.pack_row(0,issue,engine,0):019x}'))
    result.update(stage=stage,start_phase=start_phase,local_KIT_issue=kit,local_END_issue=end,
        local_KIT_return_edge_from_age0=kit+delta,actual_global_launch_booked=False)
    validate_rows(result)
    # No MU traffic is required by these pages (only VN/VS target5/HLOAD/GAIN).
    # Explicitly initialize every event/slot with replay disabled, not defaults.
    gap=((end+edges['f_ks_pin_event_to_age0_command']+1+3)//4)*4
    config=dict(schema='opentallas.s81.seqhost_native_boot.v1',slot_gaps=[gap,gap],
        return_latency=kit+edges['f_ks_pin_event_plus_kit_issue_to_t_kd']-1,kit_issue=kit,
        events=[dict(kind=1,endpoint=0,delay=4+i,attributes=[dict(ab=0,land=0),dict(ab=0,land=0)])for i in range(8)])
    mux,emission=compile_boot(config,timing,allow_unbooked_launch=True)
    rows=result['rows'];words=list(mux)+[D.csr_len(len(rows)),D.csr_pw(0,D.pw_header(len(rows),stage,start_phase))]
    for n,r in enumerate(rows):words.extend(D.csr_pw(a,d)for a,d in D.pw_row_words(n,int(r['row76'],16)))
    words.append(D.csr_pw(0,D.pw_header(len(rows),stage,start_phase,seal=True)))
    words.extend(D.csr_template(t['i'],int(t['payload186'],16))for t in result['templates'])
    result.update(local_mux_config=config,local_mux_emission=emission,host_word_count=len(words),
        local_HOST_reservation_edges=5*len(words),BEGIN_emitted=True,SEAL_emitted=True,KIT_END_emitted=True,
        local_seal_protocol_encoded=True,native_job_sealed=False,host_boot_complete=False,full_token=False,
        protocol_holds=['actual global HOST/reset/KS pin bookings and matching incoming descriptor absent',
                        'actual native local SEAL execution is separate from encoded boot bytes',
                        'page reload must wait for this page END and no outstanding tracker starts',
                        'subsequent collective/norm arithmetic and physicalSTART not qualified'])
    decode_check(result,words)
    return result,words


def validate_rows(page):
    rows=page['rows'];kits=[r for r in rows if r['eng']==14];ends=[r for r in rows if r['eng']==15]
    if len(rows)!=104 or len(rows)>128 or len(kits)!=1 or len(ends)!=1 or rows[-1]is not ends[0]:raise ValueError('actual104rows need one KIT and last END')
    if kits[0]['issue']<page['source_relative_retire_not_before']or kits[0]['issue']>=ends[0]['issue']:
        raise ValueError('KIT/END precede qualified page stores or are reversed')
    if ends[0]['issue']<=page['local_KIT_return_edge_from_age0']:raise ValueError('END precedes selected KIT return')
    if ends[0]['issue']<=max(r['done']for r in rows):raise ValueError('END precedes normal completions')
    for a,b in zip(rows,rows[1:]):
        if a['issue']>b['issue']or a['issue']==b['issue']:raise ValueError('entry protocol uses distinct ordered issuer edges')
    for r in kits+ends:
        if r['done']or r['arg']or r['row76']!=f"{D.pack_row(0,r['issue'],r['eng'],0):019x}":raise ValueError('KIT/END native encoded row differs')


def decode_check(page,words):
    cells={};templates={};headers=[];lengths=[];mu15=mu16=0
    for word in words:
        if type(word)is not int or not 0<=word<1<<515:raise ValueError('HOST native word outside515bits')
        x=word>>1;op=x&255
        if op==0x10:
            value=(x>>32)&((1<<28)-1);a=(x>>96)&127;part=value>>26
            if part<3:cells[a,part]=value&((1<<26)-1)
            else:headers.append(value)
        elif op==0x11:lengths.append((x>>32)&255)
        elif op==0x13:templates[(x>>8)&127]=(x>>16)&((1<<186)-1)
        elif op==0x15:mu15+=1
        elif op==0x16:mu16+=1
    if lengths!=[104]or len(cells)!=3*104 or mu15!=3 or mu16!=32:raise ValueError('native HOST calendar/MU boot incomplete')
    want=[D.pw_header(104,page['stage'],page['start_phase']),D.pw_header(104,page['stage'],page['start_phase'],seal=True)]
    if headers!=want:raise ValueError('actual BEGIN/SEAL headers differ')
    for n,r in enumerate(page['rows']):
        if sum(cells[n,p]<<(26*p)for p in range(3))!=int(r['row76'],16):raise ValueError('actual PW row bytes differ')
    if templates!={t['i']:int(t['payload186'],16)for t in page['templates']}:raise ValueError('actual CTL payload bytes differ')

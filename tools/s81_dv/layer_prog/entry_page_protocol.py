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
from native_phase import seqhost_phase_contract,qualify_selected


def encode(page, timing, *, stage, start_phase, source_root=None, manifest=None, inventory=None, kit_issue=None, slot_gap=None, emit_mux=True):
    check_page(page)
    seqhost_phase_contract(timing)
    qualify_selected(timing,source_root,manifest,inventory)
    if page['die_sha256']!=inventory['source_top_sha256']:raise ValueError('page/native source inventory differs')
    # This selected seqhost hardwires the native issuer stage default0. A new
    # stage contract must be source-qualified before another header is emitted.
    if type(stage)is not int or type(start_phase)is not int or stage!=0 or start_phase!=0:raise ValueError('selected local proof covers native stage0/headerphase0 only')
    if timing.get('schema')!='opentallas.s81.bound_control_local.v1' or timing.get('verdict')!='PASS':raise ValueError('selected local timing PASS required')
    master=timing['masters']['dsdv_hostb_seqhost_mux'];edges=master['edges']
    if master.get('params')!={'HOSTB_ENABLE':0,'STATIC_KS6':0}:raise ValueError('different native seqhost source variant')
    delta=edges['f_ks_pin_event_plus_kit_issue_to_t_kd']-edges['f_ks_pin_event_to_age0_command']
    if delta<0:raise ValueError('selected KIT local return precedes issuer event')
    kit=max(page['source_relative_retire_not_before'],max(r['done']for r in page['rows'])+1)
    if kit_issue is not None:
        if type(kit_issue)is not int or kit_issue<kit:raise ValueError('shared KIT precedes this actual page stores')
        kit=kit_issue
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
    if slot_gap is not None:
        if type(slot_gap)is not int or slot_gap<gap or slot_gap%4:raise ValueError('shared KS gap violates local phase or page lifetime')
        gap=slot_gap
    config=dict(schema='opentallas.s81.seqhost_native_boot.v1',slot_gaps=[gap,gap],
        return_latency=kit+edges['f_ks_pin_event_plus_kit_issue_to_t_kd']-1,kit_issue=kit,
        events=[dict(kind=1,endpoint=0,delay=4+i,attributes=[dict(ab=0,land=0),dict(ab=0,land=0)])for i in range(8)])
    mux,emission=compile_boot(config,timing,allow_unbooked_launch=True,source_root=source_root,manifest=manifest,inventory=inventory)
    result['MU_initialized_in_this_page']=emit_mux
    rows=result['rows'];words=(list(mux)if emit_mux else[])+[D.csr_len(len(rows)),D.csr_pw(0,D.pw_header(len(rows),stage,start_phase))]
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
    if lengths!=[104]or len(cells)!=3*104 or mu15!=(3 if page.get('MU_initialized_in_this_page',True)else 0) or mu16!=(32 if page.get('MU_initialized_in_this_page',True)else 0):raise ValueError('native HOST calendar/MU boot incomplete')
    want=[D.pw_header(104,page['stage'],page['start_phase']),D.pw_header(104,page['stage'],page['start_phase'],seal=True)]
    if headers!=want:raise ValueError('actual BEGIN/SEAL headers differ')
    for n,r in enumerate(page['rows']):
        if sum(cells[n,p]<<(26*p)for p in range(3))!=int(r['row76'],16):raise ValueError('actual PW row bytes differ')
    if templates!={t['i']:int(t['payload186'],16)for t in page['templates']}:raise ValueError('actual CTL payload bytes differ')


def encode_programme(pages,timing,*,stage,start_phase,source_root,manifest,inventory,post_host_guard_edges=16):
    """Use one boot-only MU configuration and one fixed return/slot calendar.

    These are local pin-relative compiler bookings. No global reset release,
    first HOST/KS pin date or descriptor payload is synthesized.
    """
    if not pages or type(post_host_guard_edges)is not int or post_host_guard_edges<16:
        raise ValueError('explicit conservative local HOST-settle reservation required')
    kit=max(max(p['source_relative_retire_not_before'],max(r['done']for r in p['rows'])+1)for p in pages)
    e=timing['masters']['dsdv_hostb_seqhost_mux']['edges'];delta=e['f_ks_pin_event_plus_kit_issue_to_t_kd']-e['f_ks_pin_event_to_age0_command']
    end=kit+delta+1
    # Every page has 104 rows,102 templates, LEN+BEGIN+SEAL:417 HOST words.
    reload_words=1+1+3*104+1+102
    first_host=e['f_ks_pin_event_to_age0_command']+end+1
    gap=((first_host+5*reload_words+post_host_guard_edges+3)//4)*4
    jobs=[];streams=[]
    for index,page in enumerate(pages):
        j,words=encode(page,timing,stage=stage,start_phase=start_phase,source_root=source_root,manifest=manifest,inventory=inventory,
            kit_issue=kit,slot_gap=gap,emit_mux=index==0)
        if index and len(words)!=reload_words:raise ValueError('actual native page reload word count changed')
        # The armed slot/window trackers cannot be configured again until reset.
        if index and any(((w>>1)&255)in(0x15,0x16)for w in words):raise ValueError('MU reconfiguration after first start forbidden')
        j['local_reload_booking']=dict(relative_to_previous_KS_pin_event=True,
            first_HOST_pin_event=first_host if index else None,next_KS_pin_delta=gap,
            post_host_guard_edges=post_host_guard_edges,first_global_HOST_and_KS_pin_events=None,
            phase_relation='all KS pin events differ by a multiple of4; first must obey selected reset-relative phase',
            requires_external_matching_descriptor=True)
        jobs.append(j);streams.append(words)
    record=dict(schema='opentallas.s81.entry_native_page_sequence.v1',status='SOURCE_RELATIVE_PROTOCOL_COMPILED',
        pages=len(jobs),shared_KIT_issue=kit,shared_END_issue=end,shared_RL=kit+e['f_ks_pin_event_plus_kit_issue_to_t_kd']-1,
        shared_KS_gap=gap,initial_MU_words=35,MU_reconfigured_after_first_page=False,
        following_page_HOST_words=reload_words,first_HOST_pin_from_previous_KS=first_host,
        HOST_words=sum(map(len,streams)),local_HOST_reservation_edges=5*sum(map(len,streams)),
        post_host_guard_edges=post_host_guard_edges,all_page_stores_before_KIT=all(kit>=p['source_relative_retire_not_before']for p in pages),
        first_global_HOST_pin=None,first_global_KS_pin=None,external_descriptors=None,
        readiness_admission='registered ready && !fault && hostdone; external source contract still required',
        rootphase_qualified=False,physical_START_qualified=False,full_token=False)
    return record,jobs,streams


def main():
    import argparse,hashlib,json
    p=argparse.ArgumentParser(description=__doc__)
    for name in('pages-dir','timing','seqhost-receipt','inventory','source-root','manifest','out'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--stage',type=int,required=True);p.add_argument('--start-phase',type=int,required=True)
    a=p.parse_args();read=lambda p:json.loads(p.read_text())
    timing=read(a.timing);phase=read(a.seqhost_receipt)
    if phase.get('verdict')!='PASS' or phase.get('masters',{}).get('dsdv_hostb_seqhost_mux')!=timing['masters']['dsdv_hostb_seqhost_mux']:
        raise ValueError('selected seqhost phase receipt/master differs')
    if any(timing['source_sha256'].get(n)!=v for n,v in phase['source_sha256'].items()):raise ValueError('selected phase dependencies differ')
    contract=seqhost_phase_contract(phase)
    if any(k in timing for k in('input_clock','seqhost_input_clock'))and seqhost_phase_contract(timing)!=contract:
        raise ValueError('selected timing/phase receipt contracts conflict')
    timing=dict(timing,seqhost_input_clock=contract)
    paths=sorted(a.pages_dir.glob('job*.json'))
    record,jobs,streams=encode_programme([read(p)for p in paths],timing,stage=a.stage,start_phase=a.start_phase,
        source_root=a.source_root,manifest=a.manifest,inventory=read(a.inventory))
    a.out.mkdir(parents=True,exist_ok=False)
    for index,(j,words)in enumerate(zip(jobs,streams)):
        name=f'job{index:03d}'
        (a.out/(name+'.json')).write_text(json.dumps(j,indent=1)+'\n')
        (a.out/(name+'.host_boot.memh')).write_text(D.memh(words,515))
    record.update(input_pages=[str(p)for p in paths],selected_local_header_stage=a.stage,selected_local_header_phase=a.start_phase,
        measured_reset_relative_phase=contract['accepted_ks_pin_event_offset_from_reset_release_pin_event_mod4'],
        seqhost_phase_receipt_sha256=hashlib.sha256(a.seqhost_receipt.read_bytes()).hexdigest())
    (a.out/'manifest.json').write_text(json.dumps(record,indent=2)+'\n')
    print('NATIVE_ENTRY_PAGE_SEQUENCE',record['pages'],'pages',record['HOST_words'],'HOSTwords; global launch held')
if __name__=='__main__':main()

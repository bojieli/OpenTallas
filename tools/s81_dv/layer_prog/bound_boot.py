#!/usr/bin/env python3
"""Compose current native records into concrete, explicitly unsealed HOST boot.

No issue, completion, KIT, END, residency or reset booking is invented. The
control record must be the actual BoundDie compiler output for this programme.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT/'tools/s81_dv'),str(ROOT/'tools/s81_dv/seqhost_timing_1026')]
from native_boot import compile_boot
from dv_layer_compile import csr_len,csr_pw,csr_template,pack_row,pw_header,pw_row_words


def digest(obj):
    return hashlib.sha256(json.dumps(obj,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def seqhost_phase_contract(receipt):
    """Read the two existing source receipt key versions without a phase default."""
    current=receipt.get('seqhost_input_clock');prior=receipt.get('input_clock')
    if current is not None and prior is not None and current!=prior:
        raise ValueError('conflicting source-qualified seqhost reset/KS phase contracts')
    contract=current if current is not None else prior
    key='accepted_ks_pin_event_offset_from_reset_release_pin_event_mod4'
    if not isinstance(contract,dict) or type(contract.get(key))is not int or not 0<=contract[key]<4:
        raise ValueError('source-qualified seqhost reset/KS phase contract missing or outside mod4')
    return contract


def compose(program, control, timing, cadence, *, mux_config=None, host_booking=None, seqhost_receipt=None):
    """Return manifest and named concrete HOST word arrays; never writes SEAL.

    control is the current bound_control.compile_control JSON. Host bookings
    name sink-pin event dates; external host/reset route adoption remains held.
    Missing programme-specific MU data does not suppress actual command encoding.
    """
    if program['die_sha256']!=control['die_sha256']:
        raise ValueError('programme/control bound top identity differs')
    if control['schema']!='opentallas.s81.bound_control_compile.v1':
        raise ValueError('actual BoundDie control compilation required')
    if control.get('verdict') not in ('PASS_CONTROL_TRANSPORT','PROPOSED_CONTROL_RETIME'):
        raise ValueError('known failed control spacing/transport cannot become HOST boot')
    if control.get('blocked_paths') or any(p['status']!='PASS' for p in control['paths'].values()):
        raise ValueError('all actual per-bit bound control routes must pass')
    if cadence['schema']!='opentallas.s81.seqhost_native_csr_cadence.v1' or cadence['verdict']!='PASS':
        raise ValueError('current direct native CSR cadence proof required')
    if 5 not in cadence['tested_pin_event_word_spacing_edges']:
        raise ValueError('actual5edgeCSRspacing unmeasured')
    master=timing['masters']['dsdv_hostb_seqhost_mux']
    if cadence['params']!=master['params'] or cadence['defines']!=master['defines']:
        raise ValueError('CSR cadence and selected local timing variants differ')
    if any(timing['source_sha256'].get(k)!=v for k,v in cadence['source_sha256'].items()):
        raise ValueError('CSR cadence and selected production dependencies differ')
    if seqhost_receipt is not None:
        if seqhost_receipt.get('verdict')!='PASS' or any(timing['source_sha256'].get(k)!=v for k,v in seqhost_receipt['source_sha256'].items()):
            raise ValueError('reset-phase receipt source identity differs from selected control timing')
        if seqhost_receipt['masters']['dsdv_hostb_seqhost_mux']!=master:
            raise ValueError('reset-phase receipt seqhost timing/variant differs')
        phase_contract=seqhost_phase_contract(seqhost_receipt)
        timing=dict(timing,seqhost_input_clock=phase_contract,
                    edge_convention=seqhost_receipt['edge_convention'])
    keys=['f_ks_pin_event_to_issuer_accept','f_ks_pin_event_to_age0_command',
          'calendar_command_to_vo_n','calendar_command_to_vo_s','calendar_command_to_cw']
    ages={k:master['edges'][k] for k in keys}
    if any(type(x) is not int or x<0 for x in ages.values()):
        raise ValueError('measured explicit pin-event ages required')
    holds=['actual target5 store commit and HLOAD/GAIN readiness not supplied',
           'actual residency before NORMR/GO and NX/rstd/XQ completion not supplied',
           'actual KIT issue and fixed END/retirement rows not supplied; SEAL forbidden',
           'actual external host/reset transport and incoming descriptors not adopted']
    if 'seqhost_input_clock' not in timing:
        holds.append('source-qualified seqhost reset/KS phase receipt missing')
    files={};initial=[];mux=None
    if mux_config is not None:
        initial,mux=compile_boot(mux_config,timing)
        holds.append('MU values are supplied candidate programme data; no KIT/calendar adoption until complete rows exist')
    else:
        holds.append('programme-specific0x15gap/RL and all8x0x16event/slot attributes missing')
    rows=program.get('rows')
    jobs=[]
    if rows:
        if len(rows)>128:
            raise ValueError('caller must partition an actual calendar with more than128rows')
        templates={t['i']:t for t in program['templates']}
        if sorted(templates)!=list(range(len(templates))) or len(templates)>128:
            raise ValueError('actual local template indices must fit128entrytable')
        cmds={c['template']:c for c in control['commands']}
        for c in program['commands']:
            measured=cmds.get(c['template'])
            if not measured or measured['issue']!=c['issue'] or measured['slice']!=c['slice']:
                raise ValueError('programme differs from actual bound command arrivals')
            if measured.get('payload186')!=templates[c['template']]['payload186']:
                raise ValueError('bound command payload differs from actual template')
        # Stage/phase are explicit programme data, not inherited header defaults.
        stage=program.get('stage');start_phase=program.get('start_phase')
        begin=stage is not None and start_phase is not None
        if not begin:
            holds.append('actual calendar '+('/'.join(k for k,v in [('stage',stage),('start_phase',start_phase)] if v is None))+' identity missing; BEGIN omitted')
        words=[csr_len(len(rows))]
        if begin:
            if type(stage) is not int or not 0<=stage<128:raise ValueError('stage must fit7bits')
            if type(start_phase) is not int or not 0<=start_phase<4:raise ValueError('start_phase must fit2bits')
            words.append(csr_pw(0,pw_header(len(rows),stage,start_phase)))
        seen=set()
        for index,row in enumerate(rows):
            if row['eng']>=14:raise ValueError('this prototype accepts only actual command rows; retirement supplied separately')
            key=(row['issue'],row['eng'])
            if key in seen:raise ValueError('actual engine calendar collision')
            seen.add(key)
            value=pack_row(row['done'],row['issue'],row['eng'],row['arg'])
            if 'row76' in row and value!=int(str(row['row76']),16):
                raise ValueError('actual row76 differs from native decoded command')
            words.extend(csr_pw(a,d) for a,d in pw_row_words(index,value))
        words.extend(csr_template(i,int(t['payload186'],16)) for i,t in sorted(templates.items()))
        files['native_commands.unsealed.host_boot.memh']=initial+words
        jobs.append(dict(name='native_commands',rows=len(rows),templates=len(templates),
                         host_words=len(initial)+len(words),has_begin=begin,
                         local_csr_reservation_edges=5*(len(initial)+len(words)),
                         sealed=False,kit_row=False,end_row=False))
    else:
        writes=program.get('writes')
        if not writes:raise ValueError('actual native rows or entry writes required')
        if initial:files['mux_initialization.host_boot.memh']=initial
        holds.append('entrywrites have no real issue/ACK calendar; PW/LEN/BEGIN omitted')
        for first in range(0,len(writes),128):
            chunk=writes[first:first+128]
            words=[csr_template(i,int(w['ctl_payload186'],16)) for i,w in enumerate(chunk)]
            name=f'entry_templates_{first//128:03d}.unsealed.host_boot.memh'
            files[name]=words
            jobs.append(dict(name=name,entry_write_indices=[first,first+len(chunk)],
                             templates=len(chunk),rows=0,host_words=len(words),sealed=False))
    bookings={}
    if host_booking is not None:
        if host_booking.get('timebase')!='u_seqhost.f_host pin event after posedge':
            raise ValueError('host dates must use explicit sink-pin event timebase')
        edge=host_booking['first_host_pin_edge']
        if type(edge) is not int or edge<0:raise ValueError('explicit first host pin event required')
        for name,words in files.items():
            dates=[edge+5*i for i in range(len(words))]
            bookings[name]=dict(pin_event_edges=dates,last_pin_event=dates[-1] if dates else None)
            edge+=5*len(words)
        holds.append('host dates are candidate sink-pin bookings; external source path not qualified here')
    else:holds.append('actual first host pin event absent; word order encoded without global dates')
    report=dict(schema='opentallas.s81.bound_native_boot.v1',status='UNSEALED_PROTOTYPE',
        die_sha256=program['die_sha256'],source_asbuilt_sha256=control['source_asbuilt_sha256'],
        programme_schema=program['schema'],programme_sha256=digest(program),
        bound_control_sha256=digest(control),local_timing_sha256=digest(timing),
        measured_local_ages=ages,host_word_spacing_edges=5,
        measured_reset_phase_contract=timing.get('seqhost_input_clock'),
        actual_control_paths=control['paths'],commands=control.get('commands',[]),
        mandatory_mux_initialization=mux,source_header_contract=program.get('native_boot_contract'),
        required_mux_csrs=dict(slot_gap_and_RL='0x15',window_events='8 explicit rows via0x16'),
        jobs=jobs,host_pin_bookings=bookings,holds=holds,
        native_job_sealed=False,host_boot_encoded=True,host_boot_complete=False,
        local_csr_reservation_edges=sum(5*len(w) for w in files.values()),readiness_qualified=False,
        global_clock_transport_qualified=False,full_token=False,added_rtl_cycles=0)
    return report,files


def decode_check(program,files):
    """Decode emitted PW/template bytes and compare every actual input payload."""
    if program.get('rows'):
        words=files['native_commands.unsealed.host_boot.memh'];cells={};templates={}
        for word in words:
            data=word>>1;op=data&255
            if op==0x10:
                value=(data>>32)&((1<<28)-1);part=value>>26
                if part<3:cells[((data>>96)&127,part)]=value&((1<<26)-1)
                elif value&(1<<25):raise ValueError('unsealed prototype emitted SEAL')
            elif op==0x13:templates[(data>>8)&127]=(data>>16)&((1<<186)-1)
        if len(cells)!=3*len(program['rows']):raise ValueError('PW parts missing/extra')
        for i,row in enumerate(program['rows']):
            actual=sum(cells[i,k]<<(26*k) for k in range(3))
            if actual!=pack_row(row['done'],row['issue'],row['eng'],row['arg']):
                raise ValueError('decoded PW differs from actual native row')
        if templates!={t['i']:int(t['payload186'],16) for t in program['templates']}:
            raise ValueError('decoded CTL template differs')
    else:
        actual=[]
        for name,words in files.items():
            if name.startswith('entry_templates_'):
                actual.extend(((w>>1)>>16)&((1<<186)-1) for w in words)
        if actual!=[int(w['ctl_payload186'],16) for w in program['writes']]:
            raise ValueError('decoded entry templates differ from native writes')


def emit(program,control,timing,cadence,out,**kwargs):
    """Emit exact decoded 515-bit HOST words into a fresh compiler output."""
    report,files=compose(program,control,timing,cadence,**kwargs)
    decode_check(program,files)
    mutant={k:list(v) for k,v in files.items()}
    name=next(n for n in mutant if n!='mux_initialization.host_boot.memh')
    index=next(i for i,w in enumerate(mutant[name]) if ((w>>1)&255)==0x13)
    mutant[name][index]^=1<<17
    try:decode_check(program,mutant)
    except ValueError:report['payload_mutant']='CAUGHT'
    else:raise ValueError('payload mutant was not caught')
    out=Path(out)
    out.mkdir(parents=True,exist_ok=False)
    for name,words in files.items():
        if any(type(w) is not int or not 0<=w<1<<515 for w in words):
            raise ValueError('native HOST word exceeds actual515bit interface')
        (out/name).write_text(''.join(f'{w:0129x}\n' for w in words))
    report['files']={n:dict(words=len(w),sha256=hashlib.sha256((out/n).read_bytes()).hexdigest()) for n,w in files.items()}
    (out/'bound_boot.json').write_text(json.dumps(report,indent=1)+'\n')
    return report


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for key in ('program','control','timing','cadence','out'):
        ap.add_argument('--'+key,type=Path,required=True)
    ap.add_argument('--mux-config',type=Path)
    ap.add_argument('--host-booking',type=Path)
    ap.add_argument('--seqhost-receipt',type=Path)
    a=ap.parse_args()
    read=lambda p:json.loads(p.read_text()) if p else None
    report=emit(read(a.program),read(a.control),read(a.timing),read(a.cadence),a.out,
        mux_config=read(a.mux_config),host_booking=read(a.host_booking),seqhost_receipt=read(a.seqhost_receipt))
    print('BOUND_NATIVE_BOOT UNSEALED_PROTOTYPE',len(report['files']),'files',sum(x['words'] for x in report['files'].values()),'words exact decode + mutant caught')


if __name__=='__main__':main()

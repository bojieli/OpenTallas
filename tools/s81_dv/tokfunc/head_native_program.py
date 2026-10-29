#!/usr/bin/env python3
"""Convert an explicitly unadopted HEAD source book to native command-ROM input.

VO dates are translated only through supplied measured current seqhost timing.
ACK is explicit programme data; boot remains unsealed and has no KIT/END dates.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tools/s81_dv'))
from dv_layer_compile import ENG,pack_row


def convert(book,control,timing,ack_edges):
    if book['schema']!='opentallas.head.norm_booking.v1' or book['adoption']:
        raise ValueError('explicit unadopted native HEAD book required')
    for key in ('die_sha256','source_asbuilt_sha256'):
        if book[key]!=control[key]:raise ValueError('source identity differs: '+key)
    if control['blocked_paths'] or any(p['status']!='PASS'for p in control['paths'].values()):
        raise ValueError('all exact current native control paths required')
    if timing['schema']!='opentallas.s81.bound_control_local.v1' or timing['verdict']!='PASS':
        raise ValueError('qualified current local timing required')
    if type(ack_edges)is not int or ack_edges<=0:raise ValueError('explicit positive ACK booking required')
    ages=timing['masters']['dsdv_hostb_seqhost_mux']['edges']
    if len(book['rows'])!=98 or {kind:sum(r['kind']==kind for r in book['rows'])for kind in ('GAIN','NORMR','XFIN_GO')}!={'GAIN':2,'NORMR':80,'XFIN_GO':16}:
        raise ValueError('exact98HEADsource events required')
    templates=[];rows=[];commands=[];seen=set();leaves=set();go=set();gain=set()
    groups={g['slice']:g for g in book['groups']}
    if len(groups)!=16 or {g['sid']for g in groups.values()}!=set(range(16)):
        raise ValueError('exact16native slices required')
    for index,r in enumerate(book['rows']):
        engine=r['engine'];age=ages['calendar_command_to_vo_'+('n'if engine=='VN'else's')]
        if engine not in ('VN','VS')or type(age)is not int or age<0:raise ValueError('explicit measured native engine age required')
        issue=r['issue_vo_edge']-age;key=(engine,issue)
        if issue<0 or key in seen:raise ValueError('negative date or unsupported engine multiissue')
        seen.add(key)
        payload=r['slice_mask']|(r['target']<<16)|(r['leaf_mask']<<21)|(r['body']<<26)
        if payload!=r['ctl_payload']:raise ValueError('native186bitpayload differs from book')
        templates.append(dict(i=index,name='head.'+r['kind']+'.'+str(index),payload186=f'{payload:047x}'))
        row=dict(eng=ENG[engine],issue=issue,done=issue+ack_edges,arg=index,tix=index,what='native HEAD '+r['kind'])
        row['row76']=f'{pack_row(row["done"],issue,row["eng"],index):019x}';rows.append(row)
        targets=[(sl,g['sid'])for sl,g in groups.items()if r['slice_mask']&(1<<g['sid'])]
        if not targets:raise ValueError('nativecommand has no exact target')
        for sl,sid in targets:
            if engine!=('VN'if sid&1 else'VS'):raise ValueError('nativecommand selects wrong tier')
            c=dict(kind=r['kind'],slice=sl,sid=sid,issue=issue,template=index,source_vo_edge=r['issue_vo_edge'])
            if r['kind']=='NORMR':
                leaf=r['leaf'];leaves.add((sid,leaf));c.update(leaf=leaf,global_beat=5*sid+leaf,bf16=True,q=False)
            elif r['kind']=='XFIN_GO':go.add(sid)
            elif r['kind']=='GAIN':gain.add(sid)
            else:raise ValueError('unexpected HEAD event')
            commands.append(c)
    if leaves!={(sid,k)for sid in range(16)for k in range(5)}or go!=set(range(16))or gain!=set(range(16))or len(commands)!=112:
        raise ValueError('missing/duplicated native80normr16go16gain landings')
    return dict(schema='opentallas.s81.head_norm_native.v1',status='UNADOPTED_CANDIDATE',
        die_sha256=book['die_sha256'],source_asbuilt_sha256=book['source_asbuilt_sha256'],
        booking_sha256=hashlib.sha256(json.dumps(book,sort_keys=True).encode()).hexdigest(),
        templates=templates,rows=sorted(rows,key=lambda x:(x['issue'],x['eng'])),commands=commands,
        stage=None,start_phase=None,ack_edges=ack_edges,ack_booking_is_programme_data=True,
        pdsk_candidate=book['pdsk_candidate'],pdsk_adopted=False,
        control_span_delta_edges=book['added_control_span_edges'],
        consumer='bound_control.compile_control -> bound_boot.compose -> dsdv_hostb_seqhost_mux HOST CSR PW/templates',
        native_job_sealed=False,readiness_qualified=False,absolute_START_qualified=False,full_token=False,
        holds=['candidatePDSK signed-view and source-plan adoption','actual ACK acceptance for this complete programme',
               'KIT/END/retirement and boot/reset/residency before launch','all80actual producer values and physical clocks/START'])


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('booking','control','timing','out'):p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--ack-edges',type=int,required=True);a=p.parse_args()
    if a.out.exists():raise ValueError('preserve existing native programme')
    r=convert(json.loads(a.booking.read_text()),json.loads(a.control.read_text()),json.loads(a.timing.read_text()),a.ack_edges)
    a.out.write_text(json.dumps(r,indent=1)+'\n');print('NATIVE_HEAD_PROGRAMME98rows98templates112exactlandingsUNADOPTED')

#!/usr/bin/env python3
"""Emit unsealed candidate norm rows using actual CTL and leaf boundary routes.

No local producer latency is guessed: partial_cohort_offset excludes that common
term. The profile is an explicit unadopted parameter proposal. NX/RSTD/VQ/global
START and retirement must still be composed before BEGIN/SEAL/KIT/END can exist.
"""
import argparse
import json
from pathlib import Path
import struct
import sys
HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE),str(HERE.parent)]
import dv_layer_compile as D
from entry_write_calendar import encode_unsealed


def book(calendar,control,eps_bits,first_issue=0,families=2,pre_row=1008):
    if calendar.get('schema')!='opentallas.s81.norm_leaf_calendar.v1' or not calendar.get('proposal'):
        raise ValueError('actual leaf calendar and explicit PDSK proposal required')
    if control.get('status')!='PASS_SELECTED_EMITTED_CTL_TO_XR' or control.get('source_top_sha256')!=calendar['source_top_sha256'] or control.get('source_view_sha256')!=calendar['source_view_sha256']:
        raise ValueError('current CTL and native leaf source identities differ')
    if type(first_issue)is not int or first_issue<0 or type(families)is not int or families not in (1,2,3) or type(pre_row)is not int or not 0<=pre_row<1024:
        raise ValueError('explicit native issue/family/row fields required')
    if type(eps_bits)is not int or not 0<eps_bits<0x7f800000:
        raise ValueError('positive finite model epsilon required')
    selected=calendar['proposal']['calendars'];paths={p['slice']:p for p in control['paths']}
    if set(paths)!=set(selected) or len(control['paths'])!=16:
        raise ValueError('complete unique current16-slice control paths required')
    lat={sl:p['calendar_command_to_XR_command_edges']for sl,p in paths.items()}
    if any(type(n)is not int or n<0 for n in lat.values()):raise ValueError('actual nonnegative CTL ages required')
    commands=[];templates=[];rows=[];busy={0:set(),1:set()};go_edges=[]
    def emit(sl,kind,issue,payload,**fields):
        sid=selected[sl]['sid'];engine=0 if sid&1 else 1;i=len(templates)
        if issue in busy[engine] or issue<first_issue or issue+5>=1<<24:raise ValueError('native engine/counter collision')
        busy[engine].add(issue);templates.append(dict(i=i,name=f'norm.{kind}.{sl}.{fields.get("leaf","")}',payload186=f'{payload:047x}'))
        rows.append(dict(done=issue+5,issue=issue,eng=engine,arg=i,tix=i,row76=f'{D.pack_row(issue+5,issue,engine,i):019x}'))
        commands.append(dict(slice=sl,sid=sid,kind=kind,issue=issue,template=i,xr_command_edge=issue+lat[sl],**fields))
    # All GO commands finish traversing the actual control paths before any
    # NORMR row is issued, without assuming a 115/116/117-edge producer model.
    for sl,row in sorted(selected.items(),key=lambda item:item[1]['sid']):
        issue=first_issue+(row['sid']//2)
        emit(sl,'XFIN_GO',issue,D.ctl_payload(1<<row['sid'],1,0,D.xfin_go(eps_bits)))
        go_edges.append(issue+lat[sl])
    first_norm=max(go_edges)+1
    for sl,row in sorted(selected.items(),key=lambda item:item[1]['sid']):
        ages=row['crossing_plus_pdsk_edges'];engine=0 if row['sid']&1 else 1
        target=first_norm+lat[sl]+max(ages)
        while any(target-lat[sl]-a in busy[engine]for a in ages):target+=1
        for leaf,a in enumerate(ages):
            issue=target-lat[sl]-a
            payload=D.ctl_payload(1<<row['sid'],0,1<<leaf,D.vp_cmd(D.VP['NORMR'],a0=pre_row,a1=5*row['sid']+leaf,n=families))
            emit(sl,'NORMR',issue,payload,leaf=leaf,partial_cohort_offset_excluding_common_local_age=target)
    rows.sort(key=lambda row:(row['issue'],row['eng']))
    if len(rows)!=96 or len(templates)!=96:raise ValueError('native80NORMR+16GO cohort required')
    return dict(schema='opentallas.s81.current_norm_candidate_book.v1',status='UNSEALED_PARAMETER_CANDIDATE',
        source_top_sha256=calendar['source_top_sha256'],source_view_sha256=calendar['source_view_sha256'],
        candidate_pdsk=calendar['proposal']['pdsk'],candidate_pdsk_parameter=calendar['proposal']['parameter_value'],
        clock_ps=833,commands=commands,rows=rows,templates=templates,families=families,pre_row=pre_row,
        first_issue=first_issue,last_issue=max(r['issue']for r in rows),last_posted_ack=max(r['done']for r in rows),
        latest_go_at_XR=max(go_edges),first_norm_issue=first_norm,
        source_local_producer_age=None,partial_edge_scope='relative aligned-cohort offset plus unknown common native producer and local XR capture term',
        actual_output_edges=None,source_parameter_adopted=False,native_job_sealed=False,
        added_model_cycles=None,full_token=False,begin_emitted=False,seal_emitted=False,kit_emitted=False,end_emitted=False,
        holds=['PDSK plan event and new physical views','native leaf local producer age and complete current input residency',
               'NX injection and forwarding against CTL slots','RSTD/VQ publication/transport/retirement and actual HOST/reset/KS/START'])


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--calendar',type=Path,required=True)
    p.add_argument('--control',type=Path,required=True);p.add_argument('--config',type=Path,required=True)
    p.add_argument('--families',choices=('q','bf16','both'),required=True);p.add_argument('--first-issue',type=int,default=0)
    p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    if a.out.exists():raise ValueError('preserve previous candidate; choose a fresh output')
    eps=struct.unpack('<I',struct.pack('<f',json.loads(a.config.read_text())['norm_eps']))[0]
    result=book(json.loads(a.calendar.read_text()),json.loads(a.control.read_text()),eps,a.first_issue,{'q':1,'bf16':2,'both':3}[a.families])
    words=encode_unsealed(result);a.out.mkdir(parents=True)
    (a.out/'candidate.json').write_text(json.dumps(result,indent=1)+'\n')
    (a.out/'norm.unsealed.host_boot.memh').write_text(D.memh(words,515))
    print('CURRENT_NORM_CANDIDATE96rows',len(words),'HOSTwords UNSEALED, lastissue',result['last_issue'])

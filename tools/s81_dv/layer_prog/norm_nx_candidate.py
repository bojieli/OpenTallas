"""Retiming of unsealed current normalization books against actual NX paths.

All event dates remain relative to an unknown common cohort-to-NX latency.
This does not qualify CTL/NX coexistence, absolute RSTD, physical clock phase,
input residency, output gather, START or retirement.
"""
from collections import defaultdict
from copy import deepcopy
from pathlib import Path
import argparse,json,sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
import dv_layer_compile as D


def events(book,transport,forward_edges):
    if type(forward_edges)is not int or forward_edges<0:raise ValueError('explicit measured local forward edges required')
    if book['source_top_sha256']!=transport['source_top_sha256'] or not transport.get('snake_peer_paths_complete'):
        raise ValueError('same-source complete actual NX paths required')
    cohorts={}
    for c in book['commands']:
        if c['kind']=='NORMR':
            edge=c['partial_cohort_offset_excluding_common_local_age']
            if c['slice']in cohorts and cohorts[c['slice']]!=edge:raise ValueError('unaligned native partial cohort')
            cohorts[c['slice']]=edge
    if len(cohorts)!=16:raise ValueError('actual16-slice partial cohort required')
    result=[]
    for path in transport['snake_peer_paths']:
        leg=path['path'][-1];h=path['prior_XG_XFIN_forward_count']
        edge=cohorts[path['origin']]+path['boundary_edges_sum']-leg['edges']+forward_edges*h
        result.append(dict(origin=path['origin'],slice=leg['source'],port=leg['output'],
            relative_output_edge=edge,relative_landing_edge=edge+leg['edges'],destination=leg['destination'],
            input=leg['input'],hops_from_origin=path['hops_from_origin']))
    if len(result)!=240:raise ValueError('all240 NX output/delivery events required')
    return result


def collisions(records):
    occupied=defaultdict(list)
    for r in records:occupied[(r['slice'],r['port'],r['relative_output_edge'])].append(r['origin'])
    return [dict(slice=sl,port=port,relative_output_edge=edge,origins=origins)
            for(sl,port,edge),origins in sorted(occupied.items())if len(origins)>1]


def retime(book,transport,forward_edges,max_shift=4096):
    if book.get('native_job_sealed')or book.get('begin_emitted'):raise ValueError('only unsealed candidate books can be retimed')
    p=deepcopy(book);original=events(book,transport,forward_edges);before=collisions(original)
    by_origin=defaultdict(list)
    for r in original:by_origin[r['origin']].append(r)
    sid={c['slice']:c['sid']for c in p['commands']};rows={r['tix']:r for r in p['rows']}
    used={(r['eng'],r['issue'])for r in p['rows']};nx_used=set();shifts={}
    for sl in sorted(sid,key=sid.get):
        commands=[c for c in p['commands']if c['slice']==sl and c['kind']=='NORMR']
        if len(commands)!=5:raise ValueError('actual five-leaf native cohort required')
        slots=[(rows[c['template']]['eng'],c['issue'])for c in commands]
        used.difference_update(slots)
        for shift in range(max_shift+1):
            command_slots={(eng,edge+shift)for eng,edge in slots}
            nx_slots={(r['slice'],r['port'],r['relative_output_edge']+shift)for r in by_origin[sl]}
            if command_slots&used or nx_slots&nx_used:continue
            if max(edge for eng,edge in command_slots)+5>=1<<24:raise ValueError('retimed native row exceeds counter')
            used.update(command_slots);nx_used.update(nx_slots);shifts[sl]=shift
            for c in commands:
                c['issue']+=shift;c['xr_command_edge']+=shift;c['partial_cohort_offset_excluding_common_local_age']+=shift
                row=rows[c['template']];row['issue']+=shift;row['done']+=shift
                row['row76']=f'{D.pack_row(row["done"],row["issue"],row["eng"],row["arg"]):019x}'
            break
        else:raise ValueError('no NX/engine slot within explicit candidate shift budget')
    p['rows'].sort(key=lambda r:(r['issue'],r['eng']));p['last_issue']=max(r['issue']for r in p['rows'])
    p['last_posted_ack']=max(r['done']for r in p['rows']);after=events(p,transport,forward_edges)
    if collisions(after):raise ValueError('candidate retains an NX collision')
    p.update(status='UNSEALED_NX_RETIMED_PARAMETER_CANDIDATE',nx_cohort_shifts=shifts,
        measured_source_local_forward_edges=forward_edges,nx_events=after,nx_collisions_before=before,
        nx_collisions_after=[],relative_NX_last_landing=max(r['relative_landing_edge']for r in after),
        relative_NX_last_landing_delta=max(r['relative_landing_edge']for r in after)-max(r['relative_landing_edge']for r in original),
        native_last_issue_delta=p['last_issue']-book['last_issue'],NX_absolute_common_offset=None,
        source_NX_output_occupancy_checked=True,CTL_NX_coexistence_qualified=False)
    return p


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--book',type=Path,required=True)
    parser.add_argument('--transport',type=Path,required=True)
    parser.add_argument('--forward-proof',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    if args.out.exists():raise ValueError('preserve existing programme; choose a fresh output')
    proof=json.loads(args.forward_proof.read_text())
    if proof.get('status')!='PASS_ACTUAL_NX_FORWARD_AND_DELIVERY_COMPONENT'or proof.get('errors')!=0 or proof.get('clock_ps')!=833:
        raise ValueError('passing actual833ps local NX component proof required')
    result=retime(json.loads(args.book.read_text()),json.loads(args.transport.read_text()),proof['XG_pin_to_XG_output_forward_edges'])
    result['local_forward_proof']=str(args.forward_proof)
    from layer_prog.entry_write_calendar import encode_unsealed
    args.out.mkdir(parents=True)
    (args.out/'candidate.json').write_text(json.dumps(result,indent=1)+'\n')
    words=encode_unsealed(result)
    (args.out/'norm.unsealed.host_boot.memh').write_text(D.memh(words,515))
    print('CURRENT_NORM_NX96rows',len(words),'HOSTwords; collisions',len(result['nx_collisions_before']),'->0; unsealed')

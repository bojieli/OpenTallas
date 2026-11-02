#!/usr/bin/env python3
"""Prepare a separate unsealed native HEAD GAIN prelude and cross-job leases.

80 GAIN plus the existing96-row norm book exceed the actual128-row calendar.
No reload/START/retirement or unknown POST arrival date is manufactured here.
"""
import argparse,json,re,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
import dv_layer_compile as D
from layer_prog.entry_write_calendar import encode_unsealed


def prepare(book,gain,receipt):
    if book.get('consumer')!='head_final' or book.get('native_job_sealed')is not False or book.get('families')!=2:
        raise ValueError('explicit unsealed HEAD BF-only norm book required')
    if gain.get('tensor')!='norm.weight' or gain.get('HEADG_rows')!=[480,495] or not re.fullmatch('[0-9a-f]{64}',gain.get('FP32_gain_sha256','')):
        raise ValueError('released HEAD gain source required')
    if receipt.get('status')!='PASS_CURRENT_NATIVE_GAIN_TO_NORMR_MINIMUM_SPACING_COMPONENT' or receipt.get('minimum_GAIN_to_NORMR_command_edges')!=9:
        raise ValueError('current native GAIN command-boundary receipt required')
    norms=sorted([c for c in book['commands']if c['kind']=='NORMR'],key=lambda c:(c['sid'],c['leaf']))
    if [(c['sid'],c['leaf'])for c in norms]!=[(s,k)for s in range(16)for k in range(5)]:raise ValueError('exact80 native consumers required')
    rows=[];templates=[];commands=[];leases=[]
    for i,c in enumerate(norms):
        sid,k=c['sid'],c['leaf'];issue=5*(sid//2)+k;eng=0 if sid&1 else 1
        templates.append(dict(i=i,name=f'head.gain.{sid}.{k}',payload186=f'{D.ctl_payload(1<<sid,0,1<<k,D.vp_cmd(1,a0=480)):047x}'))
        rows.append(dict(issue=issue,done=issue+5,eng=eng,arg=i,tix=i,row76=f'{D.pack_row(issue+5,issue,eng,i):019x}'))
        commands.append(dict(kind='GAIN',slice=c['slice'],sid=sid,leaf=k,issue=issue,template=i,gain_row=480))
        leases.append(dict(sid=sid,leaf=k,gain_rows=[480,495],GAIN_input_rows_resident_before='actual registered GAIN command; upstream boot authority absent',
            GAIN_to_NORMR_registered_CV_minimum_edges=9,actual_cross_job_counter_epoch=None,
            POST_payload160=f'{D.vp_cmd(2,a0=1009,a1=448):040x}',POST_calendar_row_emitted=False,
            POST_required_inputs=['same-token combined448..463','HC post/comb1009..1013','same-token residual h'],
            NORMR_required_inputs=['same-token POST h resident','same-token pre1008','loaded HEAD gains'],
            gain_state_live_through='actual last scaled-Y weight read; not established by posted ACK',
            no_reset_or_overwrite_before_norm_and_publication=True))
    rows.sort(key=lambda r:(r['issue'],r['eng']))
    if len(rows)>D.NOPS or len(book['rows'])>D.NOPS:raise ValueError('native job capacity exceeded')
    return dict(schema='opentallas.s81.head_norm_gain_prelude.v1',status='UNSEALED_SEPARATE_NATIVE_GAIN_PRELUDE',
        source_top_sha256=book['source_top_sha256'],gain_source=gain,rows=rows,templates=templates,commands=commands,
        linked_norm_rows=len(book['rows']),combined_rows_without_reload=len(rows)+len(book['rows']),native_capacity=D.NOPS,
        same_job_merge_admissible=False,cross_job_leases=leases,
        local_minimum_spacing_directly_tested_part=receipt['native_part'],all80_native_profiles_qualified=False,
        issue_epoch='prelude-local issuer counter only; no mapping to norm book counter or physical clock epoch',
        posted_ACK_edges=5,posted_ACK_means_GAIN_complete=False,
        holds=['actual target5 HEAD gain image commit/residency','actual POST producer arrivals and per-leaf h-ready ages',
               'actual prelude retirement, HOST calendar reload and counter/START mapping','per-leaf gain/VQ/pre1008 state leases across jobs',
               'candidate K/PDSK/QDELAYS/BK6 source and physical adoption remain separate'],
        native_job_sealed=False,host_boot_complete=False,full_token=False,canonical_adopted=False)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('book','gain-source','native-receipt','out'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();r=prepare(*[json.loads(x.read_text())for x in (a.book,a.gain_source,a.native_receipt)])
    a.out.mkdir(parents=True,exist_ok=False);(a.out/'candidate.json').write_text(json.dumps(r,indent=1)+'\n')
    words=encode_unsealed(r);(a.out/'gain.unsealed.host_boot.memh').write_text(D.memh(words,515))
    print('HEAD_GAIN_PRELUDE80 separatefromnorm96; combined176 exceeds128; HOST/START held')

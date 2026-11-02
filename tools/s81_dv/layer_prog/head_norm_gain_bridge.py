#!/usr/bin/env python3
"""Add two existing tier-broadcast GAIN commands to an unsealed HEAD norm book.

Existing lower_head uses one same-row GAIN per tier, with all five leaves and
all eight tier slices selected. Unlike80 unicasts,2+96 fits native128 rows.
"""
import argparse,json,sys
from copy import deepcopy
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
import dv_layer_compile as D
from layer_prog.entry_write_calendar import encode_unsealed


def prepare(book,gain,receipt,leaf_routes=None):
    if book.get('consumer')!='head_final' or book.get('native_job_sealed')is not False or book.get('families')!=2:
        raise ValueError('unsealed HEAD BF-only book required')
    if gain.get('tensor')!='norm.weight' or gain.get('HEADG_rows')!=[480,495]:raise ValueError('released HEAD gain source required')
    if receipt.get('status')!='PASS_CURRENT_NATIVE_GAIN_TO_NORMR_MINIMUM_SPACING_COMPONENT' or receipt.get('minimum_GAIN_to_NORMR_command_edges')!=9:
        raise ValueError('current GAIN spacing receipt required')
    routes={}
    if leaf_routes is not None:
        if leaf_routes.get('verdict')!='PASS_SELECTED_BOUNDARY_WIRING' or leaf_routes.get('source_top_sha256')!=book['source_top_sha256'] or leaf_routes.get('source_view_sha256')!=book['source_view_sha256']:raise ValueError('matching actual emitted native leaf routes required')
        routes={(r['sid'],r['leaf']):r for r in leaf_routes['leaves']}
        if len(routes)!=80:raise ValueError('exact80 actual command routes required')
    p=deepcopy(book);norms=[c for c in p['commands']if c['kind']=='NORMR']
    if sorted((c['sid'],c['leaf'])for c in norms)!=[(s,k)for s in range(16)for k in range(5)]:raise ValueError('all80 HEAD consumers required')
    busy={(r['eng'],r['issue'])for r in p['rows']};leases=[]
    for parity in (0,1):
        group=[c for c in norms if c['sid']%2==parity];eng=0 if parity else 1
        issue=min(c['issue']for c in group)-9
        while (eng,issue)in busy:issue-=1
        if issue<0:raise ValueError('source book needs explicit earlier GAIN room; no epoch invented')
        busy.add((eng,issue));i=len(p['templates']);mask=sum(1<<sid for sid in range(parity,16,2))
        p['templates'].append(dict(i=i,name=f'head.GAIN.tier{parity}',payload186=f'{D.ctl_payload(mask,0,31,D.vp_cmd(1,a0=480)):047x}'))
        p['rows'].append(dict(issue=issue,done=issue+5,eng=eng,arg=i,tix=i,row76=f'{D.pack_row(issue+5,issue,eng,i):019x}'))
        p['commands'].append(dict(kind='GAIN_TIER_BROADCAST',tier='N'if parity else'S',slice_mask=mask,leaf_mask=31,gain_row=480,issue=issue,template=i))
        for c in group:
            # Same selected CTL route/leaf landing for the same receiving leaf;
            # command-path age cancels in the GAIN→NORMR difference.
            leases.append(dict(sid=c['sid'],leaf=c['leaf'],GAIN_issuer_edge=issue,NORMR_issuer_edge=c['issue'],
                source_same_route_registered_CV_spacing_edges=c['issue']-issue,
                GAIN_at_XR_command_edge=issue+c['xr_command_edge']-c['issue'],
                HEAD_gain_rows=[480,495],gain_rows_actual_boot_resident=False,
                POST_command160=f'{D.vp_cmd(2,a0=1009,a1=448):040x}',POST_calendar_row_emitted=False,
                required_POST_input='same-token combined448..463 and residual h/HC1009..1013',
                required_NORMR_input='same-token POST h and pre1008, loaded HEAD gains',
                gain_state_live_through='actual last scaled-Y weight read; unknown producer epoch'))
    if routes:
        by={(c['sid'],c['leaf']):c for c in norms}
        for lease in leases:
            key=(lease['sid'],lease['leaf']);r=routes[key];c=by[key];age=r['xr_command_to_leaf_boundary_edges']
            if type(age)is not int or age<0:raise ValueError('literal nonnegative native boundary age required')
            lease.update(source_XR_command_to_native_CV_edges=age,
                GAIN_native_CV_edge=lease['GAIN_at_XR_command_edge']+age,
                NORMR_native_CV_edge=c['xr_command_edge']+age,
                native_receiver_stages_already_included=True,external_packet3_added_again=False,
                gain_input_rows_conservative_ready_deadline=lease['GAIN_at_XR_command_edge']+age,
                POST_h_and_pre1008_conservative_ready_deadline=c['xr_command_edge']+age,
                deadline_epoch='source-relative issuer book; not observed physical mission epoch',
                actual_input_arrival_qualified=False)
    p['rows'].sort(key=lambda r:(r['issue'],r['eng']))
    if len(p['rows'])>D.NOPS or len(p['templates'])>D.NOPS:raise ValueError('native128 row/template limit')
    p.update(schema='opentallas.s81.head_norm_gain_bridge.v1',status='UNSEALED_EXISTING_TIER_GAIN_HEAD_NORM_BRIDGE',
        gain_source=gain,GAIN_broadcast_rows=2,GAIN_native_leaf_recipients=80,source_native_capacity=D.NOPS,
        source_broadcast_encoder='tools/s81_dv/layer_prog/lower_head.py:lower tier GAIN',
        minimum_GAIN_to_NORMR_edges=9,producer_leases=leases,
        local_minimum_directly_tested_part=receipt['native_part'],all80_native_profiles_qualified=False,
        gain_boot_residency_qualified=False,POST_dates_qualified=False,HOST_START_authority=False,
        native_job_sealed=False,full_token=False,source_configuration_adopted=False,
        holds=p.get('holds',[])+['actual per-leaf POST/gain/pre1008 readiness and state leases',
            'remaining per-leaf native producer timing and physical phase profiles',
            'separate K/PDSK/QDELAYS/BK6 adoption and physical phases',
            'actual HOST programme/counter/START/retirement authority'])
    return p


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('book','gain-source','native-receipt','out'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--leaf-routes',type=Path,help='actual emitted native receiver routes, whose stages already include input_q landing')
    a=p.parse_args();r=prepare(*[json.loads(x.read_text())for x in(a.book,a.gain_source,a.native_receipt)],leaf_routes=json.loads(a.leaf_routes.read_text())if a.leaf_routes else None)
    a.out.mkdir(parents=True,exist_ok=False);(a.out/'candidate.json').write_text(json.dumps(r,indent=1)+'\n')
    (a.out/'head_gain_norm.unsealed.host_boot.memh').write_text(D.memh(encode_unsealed(r),515))
    print('HEAD_GAIN_NORM98 rows fits128;2tierGAINbroadcasts cover80leaves; input/START authority held')

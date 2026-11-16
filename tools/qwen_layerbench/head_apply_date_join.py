#!/usr/bin/env python3
"""Join measured HEAD3/1 component ages to actual delivered-command edges.

No instruction or global date is invented. Input is one rank/user cohort of12
slices. All memory visibility/lease dates use the same explicit sampling-edge
origin as cmd_input_edge. The old selected8253/0 contract is unchanged.

python3 -I tools/qwen_layerbench/head_apply_date_join.py \
 --profile emission_profile_3_1.json --delivered delivered_commands.json \
 --allocation-source results/token_pass/qwen_head_resident_lease_1101/actual8rank_census.json \
 --head-object head_calendar_object.json --out head_calendar_joined.json

Delivered schema: opentallas.qwen.native-head-delivered-commands.v1; rank,user,
edge_origin,command_edge_authority,lease_authority, selected_actual_source
{source_tree_sha,flat_sha256,memory_profile,selected_stage_sha256,
qualified_component_packet_sha256}; commands
[{slice,pidx,cmd_input_edge, optional calr_issue_edge,calr_to_cmd_i_edges}], leases
[{slice,x_ready_edge,rstd_vm_visible_edge,gain_committed_edge,prog_committed_edge,
operand_lease_through_edge,x_range,rstd_range,gain_range,prog_index}]. Ranges are
half-open and exact. A CALR issue symbol resolves only with BOTH actual CALR
issue and transport ages; delivered edges alone never back-project it.
"""
from __future__ import annotations
import argparse,copy,hashlib,json,re
from pathlib import Path

PROFILE=dict(MEMORY_ALIGNMENT=3,MEMORY_READ_EXTRA=1)


def integer(value, label):
    if type(value) is not int or value<0:raise ValueError(label+' must be a nonnegative sampling edge')
    return value


def join(profile, delivered, allocation, obj):
    if profile.get('schema')!='opentallas.qwen.native-head-emission-profile.v2' or profile.get('status')!='PASS_COMPONENT' or profile.get('memory_profile')!=PROFILE:
        raise ValueError('actual measured current3/1 HEAD emission profile required')
    if delivered.get('schema')!='opentallas.qwen.native-head-delivered-commands.v1':raise ValueError('delivered command schema')
    u,r=delivered.get('user'),delivered.get('rank')
    if type(u)is not int or not 0<=u<4 or type(r)is not int or not 0<=r<8:raise ValueError('actual rank/user required')
    for k in ('edge_origin','command_edge_authority','lease_authority'):
        if not isinstance(delivered.get(k),str)or not delivered[k].strip():raise ValueError('explicit '+k+' required')
    selected=delivered.get('selected_actual_source',{})
    if not re.fullmatch('[0-9a-f]{40}',selected.get('source_tree_sha','')):raise ValueError('selected source tree sha required')
    expected=profile['source_projection_metadata']['flat_sha256']
    if selected.get('flat_sha256')!=expected or selected.get('memory_profile')!=PROFILE or selected.get('selected_stage_sha256')!=profile['stage_sha256'] or selected.get('qualified_component_packet_sha256')!=profile['source_packet_sha256']:
        raise ValueError('selected actual source/profile/stage differs from measured HEAD packet')
    cmds=delivered.get('commands',[]);leases=delivered.get('leases',[])
    for rows,label in ((cmds,'commands'),(leases,'leases')):
        if len(rows)!=12 or {x.get('slice')for x in rows}!=set(range(12)):raise ValueError('exact12 distinct '+label+' required')
    alloc=allocation['allocation']
    if len(allocation.get('selected_sources',[]))!=8:raise ValueError('actual eight-rank source census required')
    if alloc['gain_base']<=alloc['prior_crom_last']:raise ValueError('HEAD gain reservation overlaps selected source CROM')
    occupied=set(alloc['selected_prog_indices'])|set(alloc['optional_monitor_reserved_indices'])
    if alloc['apply_pidx']in occupied or alloc['apply_pidx']+1 in occupied:raise ValueError('HEAD PROG pair is not reserved')
    bank=next(x for x in alloc['users']if x['user']==u)
    if len(alloc.get('users',[]))!=4:raise ValueError('actual source user allocation required')
    measured=profile['source_allocation']
    actual=dict(vm_x_first=measured['x_base']+u*measured['VM_user_stride'],vm_rstd=measured['rstd_addr']+u*measured['VM_user_stride'],crom_first=measured['gain_base']+u*measured['CROM_user_stride'],pidx=measured['apply_pidx']+u*measured['PROG_user_stride'])
    if any(bank.get(k)!=v for k,v in actual.items()):raise ValueError('allocation source differs from measured instruction/gain/X/RSTD payload')
    source_cmds=obj.get('native_apply_commands',[])
    if len(source_cmds)!=12 or {x.get('slice')for x in source_cmds}!=set(range(12)):raise ValueError('actual HEAD relocation object commands required')
    windows=[];resolved=[]
    for sid in range(12):
        c=next(x for x in cmds if x['slice']==sid);l=next(x for x in leases if x['slice']==sid)
        p=next(x for x in profile['slices']if x['slice']==sid);a=p['command_input_ages']
        old=next(x for x in source_cmds if x['slice']==sid)
        if old['pidx']!=alloc['apply_pidx'] or ((int(old['cmd'],16)>>4)&511)!=alloc['apply_pidx'] or (int(old['cmd'],16)&15)!=3 or c.get('pidx')!=bank['pidx']:raise ValueError('actual HEAD pidx/user relocation differs')
        t=integer(c.get('cmd_input_edge'),'cmd_input_edge')
        events={k:t+integer(a[k],k)for k in ('read_age','operand_age','write_age','stream_age','last_write_age','last_stream_age')}
        n=p['FP32_words']
        for key,expected_range in [('x_range',[bank['vm_x_first'],bank['vm_x_first']+n]),('rstd_range',[bank['vm_rstd'],bank['vm_rstd']+1]),('gain_range',[bank['crom_first'],bank['crom_first']+n])]:
            if l.get(key)!=expected_range:raise ValueError(f'slice{sid} {key} differs from actual native source footprint')
        if l.get('prog_index')!=bank['pidx']:raise ValueError('PROG lease does not select user HEAD instruction')
        for key in ('x_ready_edge','rstd_vm_visible_edge','gain_committed_edge'):
            if integer(l.get(key),key)>=events['read_age']:raise ValueError(f'slice{sid} {key} not visible before native read')
        if integer(l.get('prog_committed_edge'),'prog_committed_edge')>=t:raise ValueError('PROG not committed before command')
        # The measured last VM write is a conservative upper bound on all
        # operand reads in this exact apply-H. No last-read date is fabricated.
        if integer(l.get('operand_lease_through_edge'),'operand_lease_through_edge')<events['last_write_age']:raise ValueError('operand lease expires before measured last VM write')
        beats=[dict(eaddr=b['eaddr'],receiver_edge=t+integer(b['offset'],'BF16 receiver offset'))for b in p['BF16_receiver_beats']]
        if beats[0]['receiver_edge']!=events['stream_age']or beats[-1]['receiver_edge']!=events['last_stream_age']:raise ValueError('profile stream bounds disagree')
        calr=None
        if 'calr_issue_edge'in c or 'calr_to_cmd_i_edges'in c:
            calr=integer(c.get('calr_issue_edge'),'actual CALR issue');lat=integer(c.get('calr_to_cmd_i_edges'),'actual CALR->cmd_i age')
            if calr+lat!=t:raise ValueError('CALR and delivered-command source ages disagree')
            resolved.append(dict(symbol=old['issue_symbol'],value=calr,origin=delivered['edge_origin'],delivered_cmd_input_edge=t,calr_to_cmd_i_edges=lat))
        windows.append(dict(slice=sid,user=u,pidx=c['pidx'],command_input_edge=t,
            first_memory_request=events['read_age'],first_operand_capture=events['operand_age'],
            first_vm_write=events['write_age'],last_vm_write=events['last_write_age'],
            first_BF16_receiver_edge=events['stream_age'],last_BF16_receiver_edge=events['last_stream_age'],
            BF16_receiver_beats=beats,lease=l,operand_lease_bound='through measured last VM write; conservative',
            calr_issue_edge=calr))
    out=copy.deepcopy(obj)
    if len(resolved)==12:
        out['unresolved_relocations']=[x for x in out.get('unresolved_relocations',[])if not x.startswith('HEAD_APPLY_S0..S11_ISSUE')]
    out['native_date_join']=dict(schema='opentallas.qwen.native-head-date-join.v1',rank=r,user=u,
        edge_origin=delivered['edge_origin'],command_edge_authority=delivered['command_edge_authority'],
        lease_authority=delivered['lease_authority'],selected_actual_source=selected,
        component_memory_profile=PROFILE,windows=windows,execution_relocation_bindings=resolved,
        unresolved_command_symbols=[]if len(resolved)==12 else [x['issue_symbol']for x in source_cmds if x['issue_symbol']not in {v['symbol']for v in resolved}],
        remaining=['HEAD_TABLE_INSTALL_START/exclusive loader window','retained ME/headtap/Xfill/collective readiness and global programme source join'],
        executable=False,canonical_activation=False)
    # This helper has not discharged the object's other native/calendar leases.
    out['executable']=False;out['mask_emission']='REFUSED_UNTIL_ALL_EXECUTION_RELOCATIONS_ARE_LINKED'
    return out


def guard_controls(profile, allocation, obj):
    """Fail-closed input controls using real metadata and explicitly synthetic edges."""
    base=dict(schema='opentallas.qwen.native-head-delivered-commands.v1',rank=0,user=0,
        edge_origin='SYNTHETIC_GUARD_CONTROL_ONLY',command_edge_authority='SELFTEST_ONLY',lease_authority='SELFTEST_ONLY',
        selected_actual_source=dict(source_tree_sha='f'*40,flat_sha256=profile['source_projection_metadata']['flat_sha256'],
          memory_profile=PROFILE,selected_stage_sha256=profile['stage_sha256'],qualified_component_packet_sha256=profile['source_packet_sha256']),commands=[],leases=[])
    bank=allocation['allocation']['users'][0]
    for sid in range(12):
        n=next(x['FP32_words']for x in profile['slices']if x['slice']==sid);t=10000+200*sid
        base['commands'].append(dict(slice=sid,pidx=bank['pidx'],cmd_input_edge=t,calr_issue_edge=t-3,calr_to_cmd_i_edges=3))
        base['leases'].append(dict(slice=sid,x_ready_edge=0,rstd_vm_visible_edge=0,gain_committed_edge=0,prog_committed_edge=0,
          operand_lease_through_edge=t+200,x_range=[bank['vm_x_first'],bank['vm_x_first']+n],
          rstd_range=[bank['vm_rstd'],bank['vm_rstd']+1],gain_range=[bank['crom_first'],bank['crom_first']+n],prog_index=bank['pidx']))
    positive=join(profile,base,allocation,obj)
    if len(positive['native_date_join']['windows'])!=12 or positive['executable']:raise ValueError('selftest shape failed')
    cases=[
      ('old3/0',lambda p,d,a:p.update(memory_profile=dict(MEMORY_ALIGNMENT=3,MEMORY_READ_EXTRA=0)),'3/1'),
      ('wrong_flat',lambda p,d,a:d['selected_actual_source'].update(flat_sha256='0'*64),'selected actual source'),
      ('wrong_stage',lambda p,d,a:d['selected_actual_source'].update(selected_stage_sha256='0'*64),'selected actual source'),
      ('unreserved_gain',lambda p,d,a:a['allocation'].update(prior_crom_last=a['allocation']['gain_base']),'gain reservation overlaps'),
      ('unreserved_prog',lambda p,d,a:a['allocation']['selected_prog_indices'].append(a['allocation']['apply_pidx']),'PROG pair is not reserved'),
      ('overlapping_X_RSTD',lambda p,d,a:d['leases'][0].update(rstd_range=d['leases'][0]['x_range']),'rstd_range differs'),
      ('expired_lease',lambda p,d,a:d['leases'][0].update(operand_lease_through_edge=10001),'operand lease expires'),
      ('CALR_transport_mismatch',lambda p,d,a:d['commands'][0].update(calr_to_cmd_i_edges=4),'CALR and delivered-command'),
    ];result={}
    for name,mut,need in cases:
        pp,dd,aa=copy.deepcopy(profile),copy.deepcopy(base),copy.deepcopy(allocation);mut(pp,dd,aa)
        try:join(pp,dd,aa,obj)
        except ValueError as e:
            if need not in str(e):raise ValueError(name+' refused for wrong cause: '+str(e))
            result[name]=dict(result='CAUGHT',reason=str(e))
        else:raise ValueError(name+' not caught')
    return dict(status='PASS_GUARD_CONTROLS_ONLY',synthetic_dates=True,hardware_qualification='NONE_ADDED',controls=result)


def main():
    p=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    for k in ('profile','allocation-source','head-object','out'):p.add_argument('--'+k,type=Path,required=True)
    p.add_argument('--delivered',type=Path);p.add_argument('--selftest',action='store_true')
    a=p.parse_args();read=lambda q:json.loads(q.read_text())
    if a.selftest:
        result=guard_controls(read(a.profile),read(a.allocation_source),read(a.head_object));a.out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));return
    if a.delivered is None:p.error('--delivered required except for --selftest')
    result=join(read(a.profile),read(a.delivered),read(a.allocation_source),read(a.head_object))
    result['native_date_join']['inputs_sha256']={str(q):hashlib.sha256(q.read_bytes()).hexdigest()for q in [a.profile,a.delivered,a.allocation_source,a.head_object]}
    a.out.write_text(json.dumps(result,indent=2)+'\n')
    x=result['native_date_join'];print(json.dumps(dict(windows=len(x['windows']),resolved=len(x['execution_relocation_bindings']),unresolved=x['unresolved_command_symbols'],executable=False)))

if __name__=='__main__':main()

"""Compose TARGET5 source-relative VP commit dates; never seal or launch a job."""
import copy,hashlib,re
from pathlib import Path
from layer_prog.bound_control import BoundControl


def compose(control, transport, inventory, receipt, source_root, manifest):
    for item in (transport,inventory):
        die=item.get('die_sha256',item.get('source_top_sha256'))
        if die!=control.get('die_sha256') or item.get('source_asbuilt_sha256')!=control.get('source_asbuilt_sha256'):
            raise ValueError('TARGET5 requires identical actual control/transport/inventory source')
    if control.get('verdict')!='PASS_CONTROL_TRANSPORT' or transport.get('vp_local_intake',{}).get('verdict')!='PASS_UNCHANGED_LOCAL_BODY_INTAKE':
        raise ValueError('passing current control and VP local intake required')
    if receipt.get('schema')!='opentallas.s81.xrt_target5.v1' or receipt.get('status')!='PASS' or receipt.get('clock_period_ps')!=833:
        raise ValueError('qualified target5 measurement required')
    if receipt.get('checks')!={'base':0,'payload_mutant':1,'age_mutant':1}:
        raise ValueError('target5 positive and both caught controls required')
    root=Path(source_root).resolve()
    for name,wanted in receipt['source_sha256'].items():
        path=(root/name).resolve()
        if not path.is_relative_to(root) or hashlib.sha256(path.read_bytes()).hexdigest()!=wanted:
            raise ValueError('target5 measured source changed: '+name)
    from layer_prog.slice_source import manifest_selection
    import bind_elab
    selection=manifest_selection(root,manifest)
    for master in receipt['masters']:
        picked,ambiguous=bind_elab.pick(selection[2],master,selection[3])
        if ambiguous or not picked or Path(picked).resolve()!=root/'rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xrt.sv':
            raise ValueError('selected target5 implementation changed')
    guards=set()
    for name in receipt['source_sha256']:
        guards.update(re.findall(r'^\s*`(?:ifdef|ifndef)\s+(\w+)',(root/name).read_text(),re.M))
    if guards&set(selection[1].get('defines',[])):
        raise ValueError('target5 selected conditional differs from measured body')
    out=copy.deepcopy(control);destinations={}
    for row in transport['leaves']:
        sl=row['slice'];unit=inventory['units'][row['xr']];entry=receipt['masters'].get(unit['master'])
        if not entry or {k:BoundControl._integer(v) for k,v in unit.get('params',{}).items()}!=entry['params']:
            raise ValueError('target5 measured wrapper/parameter mismatch: '+row['xr'])
        p=control['paths'][sl]
        if p.get('status')!='PASS':raise ValueError('target5 control route blocked')
        port={'vi':'V','ri_e':'W','ri_w':'E'}[p['entry_port']]
        age=entry['edges'][port]
        if type(age)is not int or age<0:raise ValueError('missing measured target5 input age')
        # Origin is an actual seqhost output edge. Calendar-to-output remains
        # the separately qualified per-command term already emitted by control.
        offset=p['xr_input_edge']+age+row['from_xr_target5_output_to_vp_store_commit_edges']
        destinations[(sl,row['leaf'])]=dict(slice=sl,leaf=row['leaf'],xr=row['xr'],vp=row['vp'],
            from_seqhost_output_to_vp_store_commit_edges=offset,xrt_target5_decode_edges=age,
            target5_transport_edges=row['target5_transport_edges'],vp_commit_edges=row['local_vp_store_commit_edges'])
    if len(destinations)!=80:raise ValueError('all80 distinct actual target5 destinations required')
    for c in out['commands']:
        if c.get('kind')!='TARGET5':continue
        if c.get('status')=='BLOCKED':raise ValueError('blocked TARGET5 issuer')
        payload=int(c['payload186'],16)
        if (payload>>16)&31!=5:raise ValueError('mislabeled TARGET5 template')
        d=destinations[(c['slice'],c['leaf'])]
        if (payload>>21)&31!=1<<c['leaf']:raise ValueError('TARGET5 destination differs from payload')
        c['leaf_store_commit_edge']=c['seqhost_output_edge_from_age0_command']+d['from_seqhost_output_to_vp_store_commit_edges']
        c['hold']='source-relative VP commit only; residency/reload, VN capture, root phase and launch remain unqualified'
    out['target5_store_destinations']=list(destinations.values())
    out['target5_stage_receipt']=copy.deepcopy(receipt)
    out.update(root_boot_phase_qualified=False,leaf_store_residency_qualified=False,native_job_sealed=False,full_token=False)
    return out


def lower_page(page, control, local_control):
    """Lower one native page against existing exact routes and selected local stages.

    local_control is BoundControl for the same source/inventory; its local()
    checks selected body, parameters, defines and measured dependency hashes.
    """
    if page.get('die_sha256')!=control.get('die_sha256') or local_control.die.die_sha!=control.get('die_sha256'):
        raise ValueError('TARGET5 page/control source differs')
    if local_control.die.inventory['source_asbuilt_sha256']!=control.get('source_asbuilt_sha256'):
        raise ValueError('TARGET5 local inventory differs')
    out=copy.deepcopy(control);out['commands']=[]
    templates={t['i']:t['payload186']for t in page['templates']}
    # Validate the two selected issuer stages once per page, not per write.
    stages={port:local_control.local('u_seqhost','calendar_command_to_'+port)
            for port in ('vo_n','vo_s')}
    for command in page['commands']:
        if command.get('kind')!='TARGET5':raise ValueError('entry page must contain actual TARGET5 commands')
        sl=command['slice'];path=control['paths'][sl]
        if path.get('status')!='PASS':raise ValueError('entry page control route blocked')
        sid=local_control.die.slices()[sl]['sid']
        if command['sid']!=sid:raise ValueError('entry page SID differs from source')
        local=stages['vo_n'if sid&1 else'vo_s']
        tx=command['issue']+local['edges']
        out['commands'].append(dict(command,status='PARTIAL',payload186=templates[command['template']],
            seqhost_output_edge_from_age0_command=tx,
            xr_input_edge_from_age0_command=tx+path['xr_input_edge'],
            xr_command_pin_edge_from_age0_command=tx+path['xr_command_pin_edge']))
    return out


def main():
    import argparse,json
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('control','transport','inventory','receipt','source-root','manifest','out'):
        p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args()
    if a.out.exists():raise ValueError('preserve prior result; choose fresh output')
    read=lambda p:json.loads(p.read_text())
    r=compose(read(a.control),read(a.transport),read(a.inventory),read(a.receipt),a.source_root,a.manifest)
    a.out.write_text(json.dumps(r,indent=1)+'\n')
    print('TARGET5_ARRIVALS',len(r['target5_store_destinations']),'destinations; residency/launch held')
if __name__=='__main__':main()

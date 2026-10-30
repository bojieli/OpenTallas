"""Attach exact split VN store commits to the source-relative VP load outputs."""
import copy,hashlib
from pathlib import Path
from layer_prog.bound_control import BoundControl


def attach(transport, vp_vn, inventory, proof, source_root, manifest):
    if transport.get('vp_local_intake',{}).get('verdict')!='PASS_UNCHANGED_LOCAL_BODY_INTAKE' or vp_vn.get('verdict')!='PASS_BOUND_VP_VN_TRANSPORT':
        raise ValueError('actual qualified VP local and VP/VN transport required')
    for item in(vp_vn,inventory):
        if item.get('die_sha256',item.get('source_top_sha256'))!=transport['die_sha256'] or item.get('source_asbuilt_sha256')!=transport['source_asbuilt_sha256']:
            raise ValueError('VN intake source identities differ')
    if proof.get('schema')!='opentallas.s81.vn_local_commit.v1' or proof.get('status')!='PASS' or proof.get('clock_period_ps')!=833 or proof.get('checks')!={'base':0,'payload_mutant':1,'age_mutant':1}:
        raise ValueError('actual selected VN positive and caught payload/age controls required')
    if proof.get('parameters')!={'LM':5,'LA':6,'HW_STAGE':0} or proof.get('fullword_checks')!=64:
        raise ValueError('exact tested VN defaults and fullword checks required')
    edges=proof.get('commit_edges',{})
    if set(edges)!={'H_A','H_B','GAIN_A','GAIN_B'} or any(type(v)is not int or v<0 for v in edges.values()):
        raise ValueError('all four actual VN store commit ages required')
    root=Path(source_root).resolve()
    required={'rtl/dsrom_sys/s81_dv/slice/ot_s81sl_vn.sv','physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v'}
    if not required<=set(proof.get('source_sha256',{})):raise ValueError('VN and actual SRAM identities required')
    for name,digest in proof['source_sha256'].items():
        path=(root/name).resolve()
        if not path.is_relative_to(root) or hashlib.sha256(path.read_bytes()).hexdigest()!=digest:
            raise ValueError('VN qualified dependency changed: '+name)
    from layer_prog.slice_source import manifest_selection
    import bind_elab
    selected=manifest_selection(root,manifest)
    if set(selected[1].get('defines',[]))!=set(proof['defines']) or hashlib.sha256(selected[0].read_bytes()).hexdigest()!=proof['selected_manifest_sha256']:
        raise ValueError('VN selected manifest/defines changed')
    for master,name in [('ot_s81sl_vn_a','rtl/dsrom_sys/s81_dv/slice/ot_s81sl_vn.sv'),('ot_s81sl_vn_b','rtl/dsrom_sys/s81_dv/slice/ot_s81sl_vn.sv'),('ot_sram_1r1w_128x256_m1_r2c2',next(n for n in required if n.endswith('.v')))]:
        picked,ambiguous=bind_elab.pick(selected[2],master,selected[3])
        if ambiguous or not picked or Path(picked).resolve()!=root/name:
            raise ValueError('selected VN dependency differs: '+master)
    routes={(r['slice'],r['leaf']):r for r in vp_vn['leaves']}
    out=copy.deepcopy(transport)
    if len(routes)!=80 or len(out['leaves'])!=80:raise ValueError('all80 actual VN/VP leaves required')
    for row in out['leaves']:
        route=routes[(row['slice'],row['leaf'])]
        if route.get('status')!='PASS' or route['vp']!=row['vp']:raise ValueError('VN load leaf identity differs')
        ages={'H':[],'GAIN':[]}
        for half in('a','b'):
            h=route['halves'][half];unit=inventory['units'].get(h['vn'],{})
            wanted=dict(LM=5,LA=6)
            if half=='b':wanted['HW_STAGE']=0
            params={k:BoundControl._integer(v)for k,v in unit.get('params',{}).items()}
            if unit.get('master')!='ot_s81sl_vn_'+half or params!=wanted:
                raise ValueError('actual evaluated VN parameter differs: '+h['vn'])
            for group,fields,transport_key,commit_key in [('H',('hw_v','hw_j','hw_hf','hw_d'),'HW_transport_edges','H_'+half.upper()),('GAIN',('wl_v','wl_i','wl_d'),'WL_transport_edges','GAIN_'+half.upper())]:
                age=h[transport_key]
                if type(age)is not int or age<0 or any(h['fields'][p]['age_edges']!=age for p in fields):raise ValueError('VN transport word ages incoherent')
                ages[group].append(age+edges[commit_key])
        hready=row['local_vp_hload_last_output_edges']+max(ages['H'])
        gready=row['local_vp_gain_last_output_edges']+max(ages['GAIN'])
        row.update(local_hload_readiness_edges=hready,local_gain_readiness_edges=gready,
            from_xr_command_output_to_vn_h_store_last_commit_edges=row['command_transport_edges']+hready,
            from_xr_command_output_to_vn_gain_store_last_commit_edges=row['command_transport_edges']+gready)
    out['vn_local_intake']=dict(verdict='PASS_SELECTED_FUNCTIONAL_VN_STORE_INTAKE',instances=160,
        source_sha256=proof['source_sha256'],commit_edges=edges,defines=proof['defines'],
        scope='VP command input to actual VN store commit from composed local bodies and exact bound transfers; source-relative only',
        physical_clocks_qualified=False,root_boot_phase_qualified=False)
    out.update(readiness_qualified=False,native_job_sealed=False,full_token=False)
    return out


def main():
    import argparse,json
    p=argparse.ArgumentParser(description=__doc__)
    for key in('transport','vp-vn','inventory','proof','source-root','manifest','out'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args()
    if a.out.exists():raise ValueError('preserve prior output')
    read=lambda p:json.loads(p.read_text())
    result=attach(read(a.transport),read(a.vp_vn),read(a.inventory),read(a.proof),a.source_root,a.manifest)
    a.out.write_text(json.dumps(result,indent=1)+'\n')
    print('VN_LOCAL_INTAKE',len(result['leaves']),'leaves; physical phase/launch held')
if __name__=='__main__':main()

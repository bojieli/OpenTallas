#!/usr/bin/env python3
"""Materialize SOURCE-ONLY named parent graft fragments, never an adopted top.

Uses actual post-compose Binder identities and emitted parent expressions.
The new ingress/egress routes are explicitly unbound. No retired lane credit.
"""
import argparse,hashlib,json,re
from pathlib import Path

def instance(text,name):
    pat=r'(?m)^\s*(\w+)(?:\s*#\(([^;]*?)\))?\s+'+re.escape(name)+r'\s*\((.*?)\);'
    m=re.search(pat,text,re.S)
    if not m:raise ValueError('Exact existing instance absent: '+name)
    ports=dict(re.findall(r'\.(\w+)\s*\((.*?)\)(?:\s*,|\s*$)',m[3],re.S))
    return m[1],m[2] or '',ports

def render(master,params,name,ports):
    return master+' #('+params+') '+name+' (\n'+',\n'.join(' .'+p+'('+v+')'for p,v in ports.items())+'\n);\n'

def make(graph_path,fields_path,hubdir,out):
    if out.exists():raise ValueError('New output required')
    graph=json.loads(graph_path.read_text());fields=json.loads(fields_path.read_text())
    cells={c['canonical']:c for c in graph['cells']}
    out.mkdir(parents=True)
    old=fields['actual_old_collar_instantiation'];assert '.prm(w_u_col_idx_prm)'in old
    root='// Prospective replacement of actual col_idx/u_u_col_idx only. Add a NEW49-bit root output route.\nwire[817:0] idxq_prm818_prospective;\n'+old.replace('ot_hbm_static_cfg_collar_idx256r','ot_hbm_static_cfg_collar_idxq818').replace('.prm(w_u_col_idx_prm)','.prm(idxq_prm818_prospective)')+'\nassign w_u_col_idx_prm=idxq_prm818_prospective[768:0];\nassign idxq_fields49_o=idxq_prm818_prospective[817:769];\n'
    (out/'root_collar_818.svfrag').write_text(root)
    connections=[];compact=[];boundaries=[];frags={}
    for q,sid,rt in [('SW',0,171),('SE',1,171),('NW',2,173),('NE',3,171)]:
        c=cells['hb_idx__op_'+q];t=cells['hb_idx__qctl_'+q]
        assert c['explicit_parameters']['VM_RT_EXTRA']==str(rt)
        assert sum(p['width']for p in c['ports'].values())==3286
        assert 'WEIGHT_FP32'not in c['parameter_defaults']
        side='nw'if q in ('SW','NW')else'ne'
        text=(hubdir/('hbm_arch_q_hub__q_hub_'+side+'.sv')).read_text()
        rlocal='u_'+re.sub('_+','_',c['local_instance']);tlocal='u_'+re.sub('_+','_',t['local_instance'])
        om,op,reader=instance(text,rlocal);tm,tp,ctl=instance(text,tlocal)
        assert om==c['module'] and tm==t['module']
        qid='q0'if q in ('SW','SE')else'q1';prefix='idxq_'+qid
        frame=ctl['frame_start'];sf=c['ports']['weight_slot']['bits'][0]['source']
        assert sf['canonical_cell']==t['canonical'] and sf['port']=='weight_slot'
        prm=t['ports']['length']['bits'][0]['source'];assert prm['canonical_cell']=='col_idx'and prm['port']=='prm'
        scf=t['ports']['scf']['bits'][0]['source']
        assert scf['canonical_cell'].startswith('hb_idx__s_'+q+'.')and scf['port']=='Y'
        reader.update(frame_start=frame,weight_row_stride='idxq_fields49_i[32:17]',query_row_stride='idxq_fields49_i[48:33]')
        ctl.update(n_rows='idxq_fields49_i[4:0]',row_pitch='idxq_fields49_i[16:5]',kbf=ctl['scf'],
                   key_v=prefix+'_key_v',key_row=prefix+'_key_row',pre_v=prefix+'_pre_v',
                   pre_index=prefix+'_pre_index',row_start=prefix+'_row_start')
        decl=f'\n// {q}: new49 ingress shared by both quarter roles in this hub; no old L124 route.\nwire {prefix}_key_v,{prefix}_pre_v,{prefix}_row_start;\nwire[4:0] {prefix}_key_row;wire[7:0] {prefix}_pre_index;\n'
        body=decl+render('ot_hnx_idxq_qctl',f'.K(8),.S(4),.CW(2),.DELIVERED_RESET(1),.ROW_CLEAR_DELAY({rt-2})',tlocal,ctl)
        body+=render('ot_hnx_idx_vm_query_static_n12',f'.VM_RT_EXTRA({rt}),.WEIGHT_FP32(1)',rlocal,reader)
        kbports=dict(frame_start=frame,key_v=prefix+'_key_v',key_index=ctl['key_index'],key_row=prefix+'_key_row',pre_v_in=prefix+'_pre_v',pre_index_in=prefix+'_pre_index')
        for port in ['clear','live_v','live_index','pre_v','pre_index','replay_v','replay_index']:
            name='native_required__hb_idx__s_'+q+'__'+port
            f=fields['ports'][name];assert f['direction']=='input'
            output='idxq_'+q+'_'+port+'_o';kbports[port]=output
            body+='wire'+('['+str(f['width']-1)+':0] 'if f['width']>1 else' ')+output+';\n'
            boundaries.append(dict(old_TOP=name,width=f['width'],exact_consumers=f['consumers'],
                source_candidate=dict(canonical='hb_idx__kbc_'+q,master='ot_hnx_idxn_kb_ctl',port=port),
                new_hub_output=output,new_physical_route=None))
        body+='ot_hnx_idxn_kb_ctl '+prefix+'_kb_ctl (\n'+',\n'.join(' .'+p+'('+v+')'for p,v in kbports.items())+'\n);\n'
        body+='// REQUIRED new row-clear route: '+prefix+'_row_start -> actual query.frame_start; not reader.frame_start.\n'
        frags.setdefault(side,[]).append(body)
        for port in ['frame_start','weight_row_stride','query_row_stride']:
            source=dict(canonical=t['canonical'],local_instance=tlocal,port='frame_start',bit=0,
                        current_observed_source=t['ports']['frame_start']['bits'][0]['source'])if port=='frame_start'else dict(canonical='col_idx',local_instance='u_u_col_idx',master='ot_hbm_static_cfg_collar_idxq818',port='prm',low=786 if port=='weight_row_stride' else 802,width=16,current_bits_exist=False)
            connections.append(dict(consumer_canonical=c['canonical'],partition=c['partition'],local_instance=rlocal,
                current_master=om,prospective_master='ot_hnx_idx_vm_query_static_n12',port=port,width=1 if port=='frame_start' else 16,
                actual_parent_expression=reader[port],source=source,new_route_required=True,retired_L124_credit=False))
        compact.append(dict(canonical=c['canonical'],partition=c['partition'],local_instance=rlocal,
            old_master=om,old_params=c['explicit_parameters'],prospective_params=dict(VM_RT_EXTRA=rt,WEIGHT_FP32=1),
            old_pin_bits=3286,new_pin_bits=3319,retained={p:c['ports'][p]for p in ['clk','rst_n','sid']},
            real_qctl=t['canonical'],qctl_start=t['ports']['start'],qctl_clock=t['ports']['clk_program'],qctl_reset=t['ports']['rst_n'],
            existing_scf_includes_keybuf_fault=scf,new_kbf_expression=ctl['scf']))
    assert len(boundaries)==28 and sum(b['width']for b in boundaries)==112
    for side,parts in frags.items():(out/('hub_'+side+'_reader_controls.svfrag')).write_text('// Prospective INSTANCE REPLACEMENTS only. Add new49 ingress,112 total keybuf outputs and row-clear routes to parent interface.\n'+''.join(parts))
    report=dict(schema='opentallas.hbm.idxq.named_parent_overlay.v1',status='SOURCE_ONLY_PARTIAL_GRAFT_NOT_ADOPTED',
        source_observations={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in [graph_path,fields_path]},
        current_graph_changed=False,may_generate_physical=False,collar=dict(canonical='col_idx',local_instance='u_u_col_idx',
            current_master='ot_hbm_static_cfg_collar_idx256r',prospective_master='ot_hbm_static_cfg_collar_idxq818',
            old_prm_bits=769,new_prm_bits=818,target='RETAIN EXACT S_u_col_idx_tgt[7:0]; no new target'),
        quarters=compact,new_reader_connections=connections,prospective_native_IDX_sources=boundaries,
        source_derived_cohort=dict(provenance='Exact CW2 qctl RTL and qualified VP1 instruction0 weight/instruction17 query; NOT routed measurement',
            frame_to_first_weight_edges=3,frame_to_first_query_edges=20,
            new_frame_transport_minus_existing_weight_transport_max_edges=2,
            stride_valid='By reader frame_start sampling; held through all rows',global_route_dates=None),
        unresolved=['New49-bit root→NW_hub/NE_hub routes and local fanout; no retired L124 reuse',
            'New row_start→query clear routes; all four selectors/new row-slot link/root calendar still required before functional full graph',
            'Native28controls now have exact prospective producers/consumers, but actual new routes/bit mapping not adopted',
            'South keys/global shard lowering, actual per-SID/mirror residency and legal BF16-widened source values',
            'Actual global cohort dates/reset clock-model closure; current3319 physical work remains PREP/profile/pinmap only'])
    (out/'named_parent_overlay.json').write_text(json.dumps(report,indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--graph',type=Path,required=True);p.add_argument('--native-fields',type=Path,required=True);p.add_argument('--hubdir',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();make(a.graph,a.native_fields,a.hubdir,a.out)

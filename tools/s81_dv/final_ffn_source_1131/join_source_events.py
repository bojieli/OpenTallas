#!/usr/bin/env python3
"""Join a compiled source field to measured components without inventing epochs."""
from pathlib import Path
import argparse,hashlib,json,re,sys
ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT/'tools/s81_slice'),str(ROOT/'tools/s81')]
import cap_model as CM

def join(field,capture,boundary,cap_scope,cap_native,cw_log,ledger):
    f=json.load(open(field));caps=json.load(open(capture));routes=json.load(open(boundary));scope=json.load(open(cap_scope));native=json.load(open(cap_native))
    assert f['frame']=='u_f_0L01' and f['slice_index']==0
    ret_path=next(r for r in routes['frame_returns'] if r['frame']==f['frame']);leaf_path=next(r for r in routes['leaves'] if r['sid']==0 and r['leaf']==0)
    assert ret_path['CAP_family']=='ot_s81sl_capc5r_e6' and ret_path['CAP_port']=='rt_w' and ret_path['CAP_lane']==0
    # Calibrate this exact functional wrapper on the actual selected input train.
    sample=scope[0];lanes=[{} for _ in range(8)]
    lanes[0]={x['edge']:(x['tag'],x['data'],0,[i]) for i,x in enumerate(sample['inputs'])}
    model=CM.model(lanes,[(0,sample['cfg'])]);assert not model['faults']
    observed=[w for w in native['profiles'][0]['writes'] if w['family']==0]
    delta=set()
    for w in observed:
        m=next(x for x in model['writes'] if x[3]==w['address']);assert m[4]==w['data'];delta.add(w['edge']-m[0])
    assert len(delta)==1;wrapper=delta.pop();assert wrapper==8
    configs={(p['mat'],p['chunk']):next(s['cfg'] for s in p['slices'] if s['slice_index']==0) for p in caps['phases']}
    words=[];native_cw_to_store=2
    for ph in f['phases']:
        if ph['op']!='ffn.down':continue
        assert ph['plan']['single_frame_cap_score']==0 and ph.get('kslot',1)==1
        cfg=configs[ph['mat'],ph['chunk']];lanes=[{} for _ in range(8)]
        for i,(edge,tag,data,error) in enumerate(ph['ret']):
            row=ph['row_index'][(tag>>13)&16383];actual=(row<<13)|(tag&8191)
            lanes[0][edge+ret_path['source_boundary_to_CAP_input_edges']]=(actual,data,error,[i])
        result=CM.model(lanes,[(0,cfg)]);assert not result['faults'] and len(result['writes'])==ph['rows']
        for edge,leaf,port,address,data,row,*rest in result['writes']:
            assert leaf==0
            cw=edge+wrapper;registered=cw+leaf_path['CAP_output_to_registered_leafdn_edges'];commit=registered+native_cw_to_store
            words.append(dict(frame=f['frame'],phase=ph['phase'],expert=ph['mat'][:-3],global_row_rank0=row,source_sid=0,source_leaf=0,
                CAP_word_address=address,SRAM_row=address//4,word_in_row=address%4,BF16_in_FP32_hex=f'{data:08x}',
                compiler_model_CAP_CW_edge_n=cw,composed_registered_CW_edge_n=registered,composed_SRAM_commit_edge_n=commit,
                unknown_epoch=f'TAU_native_frame_source_minus_model_edge_n[{f["frame"]},phase{ph["phase"]}]',
                production_absolute_commit_edge=None,native_storage_mechanism_qualified=True,actual_frame_capture_executed=False))
    assert len(words)==126
    text=Path(cw_log).read_text();assert 'errors0 clock833' in text and 'ready1' in text
    measured=[(int(a),v.lower()) for a,v in re.findall(r'CW_SEAM_NATIVE age(\d+) data([0-9a-fA-F]{64})',text)];assert [x[0] for x in measured]==[5,6]
    results=[]
    for line in Path(ledger).read_text().splitlines():
        r=json.loads(line)
        if (r['source_rank'],r['expert_slot'],r['source_sid'],r['source_leaf'])!=(0,6,0,0):continue
        row=r['source_row_pair'][0]
        if row not in (224,226):continue
        beat=(row-224)//2;assert r['expected_256bit_native_RD_payload_le'].lower()==measured[beat][1]
        word_events=[]
        for offset,address in enumerate(r['source_CW_word_addresses']):
            w=next(x for x in words if x['expert']=='shared' and x['CAP_word_address']==address)
            n=address-896;j=(n//8)*4+(n%4);component_commit=134+j
            word_events.append(dict(CAP_word_address=address,phase=w['phase'],global_row_rank0=w['global_row_rank0'],
                component_registered_CW_edge=132+j,component_actual_SRAM_commit_edge=component_commit,
                composed_commit_edge_n=w['composed_SRAM_commit_edge_n'],unknown_epoch=w['unknown_epoch']))
        results.append(dict(ledger_i=r['i'],source_row_pair=r['source_row_pair'],destination_row_pair=r['destination_row_pair'],expected_payload=r['expected_256bit_native_RD_payload_le'],
            component_RDOUT_count=2,component_RDOUT_registered_CV_edge=156,component_actual_native_LO_edge=156+measured[beat][0],component_actual_public_LO_edge=157+measured[beat][0],
            component_value_identity_verified=True,word_events=word_events,
            sufficient_readiness_constraint='registered_RDOUT_CV >= max(all source-word commit expressions); conservative, earliest SRAM read not measured',
            production_RD_issue_epoch=None,production_RD_command_group_binding=None,production_absolute_publication_edge=None,global_source_lease=None))
    assert len(results)==2
    return dict(status='PASS_SELECTED_COMPONENT_AND_MODEL_RELATIVE_JOIN',source_compiler='2b8caf13b',independent_field_order_proof='cd51ee550',ledger_commit='cd51ee550',emitter_reference='4034b8b18',
        field_sha256=hashlib.sha256(Path(field).read_bytes()).hexdigest(),bound_top_sha256=routes['source_top_sha256'],
        model_origin='compiler/frame-bench edge_n, not an assumed physical GO epoch',
        calibration=dict(native_observed_e6_W0_rows=len(observed),wrapper_edges_over_logical_CAP_model=wrapper,frame_source_to_CAP_input_emitted_edges=ret_path['source_boundary_to_CAP_input_edges'],
            CAP_output_to_registered_native_CW_emitted_edges=leaf_path['CAP_output_to_registered_leafdn_edges'],registered_CW_to_SRAM_native_measured_edges=2,native_input_q_counted_once=True),
        words=words,RD_pairs=results,native_storage_failure_blocker=None,
        holds=['actual XS/frame publication epoch and source input readiness','simultaneous other-frame FIN traffic and CFG lifetime','production RD command group/issue binding','global source/destination leases','all80 native profiles and physical functional-view alignment'],
        actual_mission_capture_qualified=False,global_leases_qualified=False,full_token=False)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('field','capture','boundary','cap_scope','cap_native','cw_log','ledger','out'):p.add_argument('--'+n.replace('_','-'),type=Path,required=True)
    a=p.parse_args()
    if a.out.exists():raise ValueError('preserve previous join verdict')
    r=join(a.field,a.capture,a.boundary,a.cap_scope,a.cap_native,a.cw_log,a.ledger);a.out.write_text(json.dumps(r,indent=2)+'\n');print(r['status'],len(r['words']),len(r['RD_pairs']))

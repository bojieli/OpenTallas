#!/usr/bin/env python3
"""Bind actual 104/56 word ownership to final VS13/POST/GAIN/NORM operands.

This emits assignments and conditional command deadlines. The known CW word1..3
payload seam failure, actual SRAM/RD leases and physical epochs remain open.
"""
import argparse,json,hashlib,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import dv_layer_compile as D
from layer_prog.lower_vs import vs_imm


def sha(data):return hashlib.sha256(data).hexdigest()


def build(inputs,values,deadlines,normbook,plans,ordercheck,out):
    if out.exists():raise ValueError('fresh assignment output required')
    raw=np.fromfile(values,'<u4').reshape(7,5120)
    if np.any(raw&65535):raise ValueError('down-source words must be BF16 in FP32')
    records=[json.loads(x)for x in(inputs/'word_map.jsonl').read_text().splitlines()]
    by={(m['expert'],m['global_element']):m for m in records}
    if len(by)!=35840 or len(records)!=35840:raise ValueError('actual35840 distinct source word assignments required')
    prof=json.loads((inputs/'profile.json').read_text());spans=prof['source_spans']
    meta=json.loads((inputs/'meta.json').read_text());experts=['exp'+str(x)for x in meta['experts']]+['shared']
    y=np.fromfile(inputs/'combined_y.u32','<u4').reshape(5120);post=np.fromfile(inputs/'post_h.u32','<u4').reshape(4,5120)
    norm=np.fromfile(inputs/'norm_y.u32','<u4').reshape(5120);gain=np.fromfile(inputs/'head_norm_w.f32','<u4').reshape(5120)
    residual=np.fromfile(inputs/'residual_h.bin','<u4').reshape(4,5120);prepost=np.fromfile(inputs/'HCpre_post.bin','<u4');comb=np.fromfile(inputs/'HCcomb.bin','<u4').reshape(4,4)
    partials=[int(s,16)for s in(inputs/'partial80.hex').read_text().split()]
    arith=json.loads((inputs/'source_arithmetic.json').read_text())
    if len(partials)!=80 or arith['RSTD']!='412a6100':raise ValueError('fresh normative arithmetic source required')
    if ordercheck['status']!='PASS_INDEPENDENT_FRESH_SOURCE_RETURN_FOREST_ORDER':raise ValueError('new source placement numerical witness required')
    if normbook['consumer']!='head_final' or normbook['native_job_sealed']is not False:raise ValueError('unsealed HEAD native consumer required')
    ready={(r['sid'],r['leaf']):r for r in deadlines['leases']};normcmd={(c['sid'],c['leaf']):c for c in normbook['commands']if c['kind']=='NORMR'}
    nativecap=json.loads((inputs/'cap_native_check.json').read_text());capscope=json.loads((inputs/'cap_native_scope.json').read_text())
    sourceplans={p['frame']:p for p in plans};observed={}
    for scope in capscope:
        p=sourceplans[scope['frame']];base=min(x['edge']for x in scope['inputs'])-min(w[0]for w in p['plan']['ret'])
        for row in scope['source_rows']:
            src=by[6,row];address=4*src['source_row']+src['source_word'];obs=[]
            for profile in nativecap['profiles']:
                for w in profile['writes']:
                    if w['family']==scope['family']and w['address']==address:
                        if w['data']!=int(raw[6,row]):raise ValueError('actual CAP output value differs from fresh input')
                        obs.append(dict(e6_lane_profile=profile['e6_lane'],native_bench_edge=w['edge'],port=w['port'],
                            candidate_frame_GO_relative_edge=w['edge']-base,actual_global_epoch=None))
            if len(obs)!=3:raise ValueError('three native CAP profiles required for each selected source word')
            observed[row]=dict(frame=scope['frame'],phase=p['phase'],source_sid=src['source_sid'],source_leaf=src['source_leaf'],CW_word_address=address,
                word_slot=src['source_word'],fresh_BF16_in_FP32=f'{int(raw[6,row]):08x}',observations=obs,
                date_basis='isolated native CAP input was shifted by a known constant from source-plan ret dates; physical field GO is unknown',
                actual_CW_to_SRAM_commit_qualified=False)
    pairs=[];leaves=[]
    combine=D.vp_cmd(13,a0=320,n=8,imm=vs_imm(ob=448));postop=D.vp_cmd(2,a0=1009,a1=448)
    if combine!=0x1c00800140d:raise ValueError('measured native VS13 command differs')
    for beat in range(80):
        sid,leaf=divmod(beat,5);start=64*beat;ids=[]
        for expert in range(7):
            for offset in range(0,64,8):
                n=start+offset;words=[by[expert,n+j]for j in range(8)];m=words[0];rank=n//1280;local=n%1280
                srcsid,base=next((s,a)for s,(a,count)in enumerate(spans)if a<=local<a+count)
                off=local-base
                for j,w in enumerate(words):
                    want=(srcsid,(off+j)//64,128+16*expert+((off+j)%64)//4,(off+j)%4)
                    if tuple(w[k]for k in('source_sid','source_leaf','source_row','source_word'))!=want:raise ValueError('source capture assignment changed')
                    if (w['sid'],w['leaf'],w['row'],w['word'])!=(sid,leaf,320+16*expert+(offset+j)//4,(offset+j)%4):raise ValueError('canonical64 native assignment changed')
                if m['source_word']!=0 or m['source_row']%2:raise ValueError('aligned native two-row RD assignment required')
                i=len(pairs);ids.append(i);data=sum(int(raw[expert,n+j])<<(32*j)for j in range(8))
                pairs.append(dict(i=i,expert_slot=expert,expert=experts[expert],global_words=[n,n+7],source_rank=rank,
                    source_sid=m['source_sid'],source_leaf=m['source_leaf'],source_row_pair=[m['source_row'],m['source_row']+1],
                    source_CW_word_addresses=list(range(4*m['source_row'],4*m['source_row']+8)),
                    destination_rank=rank,destination_sid=sid,destination_leaf=leaf,destination_row_pair=[m['row'],m['row']+1],
                    expected_256bit_native_RD_payload_le=f'{data:064x}',actual_source_commit_edge=None,actual_RD_issue_edge=None,actual_destination_commit_edge=None))
        rng=slice(start,start+64);halfrows=[]
        for step in range(16):
            data=sum((int(post[h,start+4*step+j])>>16)<<(16*(4*h+j))for h in range(4)for j in range(4))
            halfrows.append(dict(hw_j=step//2,hw_hf=step%2,expected256=f'{data:064x}'))
        wl=[f'{sum(int(gain[start+8*j+k])<<(32*k)for k in range(8)):064x}'for j in range(8)]
        c=normcmd[sid,leaf];t=normbook['templates'][c['template']];body=int(t['payload186'],16)>>26
        if body!=D.vp_cmd(7,a0=1008,a1=128+beat,n=2):raise ValueError('actual HEAD NORMR assignment differs')
        leaves.append(dict(native_part=f's_{sid//2}{"N"if sid%2 else"S"}_L{leaf}',sid=sid,leaf=leaf,global_beat=beat,global_features=[start,start+63],
            down_and_combine_owner_TP_rank=beat//20,required_h_replica_TP_ranks=[0,1,2,3],
            RD_assignment_indices=ids,assembled_expert_rows=[[320+16*e,335+16*e]for e in range(7)],expert_accumulation_order=experts,
            VS13=dict(body160=f'{combine:040x}',execute_only_on_TP_owner=True,combined_rows=[448,463],expected_combined64_sha256=sha(y[rng].tobytes()),
                measured_one_profile_output_last_write_edges=74,actual_combined_SRAM_resident_edge=None),
            peer_broadcasts=[dict(destination_TP_rank=r,source_rows=[[448,455],[456,463]],row_pairs_per_half=4,actual_arrival_edge=None)for r in range(4)if r!=beat//20],
            POST=dict(body160=f'{postop:040x}',execute_after_local_or_peer_combined_ready_on_each_replica=True,
                HC_pre_row1008_words=[f'{int(v):08x}'for v in prepost[:4]],HC_post_row1009_words=[f'{int(v):08x}'for v in prepost[4:]],
                HC_comb_rows1010_to1013=[[f'{int(v):08x}'for v in row]for row in comb],
                expected_residual4x64_sha256=sha(residual[:,rng].tobytes()),expected_native_HW_halfrows=halfrows,
                native_CV_issue_edge=None,actual_h_resident_edge=None,measured_one_profile_last_HW_edge=62,
                one_profile_h_resident64_is_source_derived_not_global_profile=True),
            GAIN=dict(body160=f'{D.vp_cmd(1,a0=480):040x}',source_rows=[480,495],expected_VN_WL8=wl,conditional_native_CV=ready[sid,leaf]['GAIN_native_CV_edge'],
                actual_gain_row_commit_edge=None,actual_VN_gain_RF_ready_edge=None),
            NORMR=dict(body160=f'{body:040x}',head_index=128+beat,conditional_native_CV=ready[sid,leaf]['NORMR_native_CV_edge'],
                expected_partial32=f'{partials[beat]:08x}',expected_HEAD_BF16_payload1024=f'{sum((int(norm[start+j])>>16)<<(16*j)for j in range(64)):0256x}',
                actual_input_residency_qualified=False,measured_one_profile_partial_age=116),
            leases=dict(capture='actual CAP SRAM commit until completed native RD read',assembled='each of112rows until corresponding VS13 read consumed',
                combined='until local POST plus all three peer-broadcast reads consumed',residual_h='until POST read and replacement retire',
                HC_rows='same-token pre/post/comb until relevant native reads retire',HEAD_gain_SRAM_rows='until GAIN read consumes rows480..495',
                VN_gain_RF='through final delayed scaled-Y weight read',POST_h='through NORMR normalization reads',VQ_metadata_and_buffers='through delayed last Q/BF headers/fragments',
                all_actual_begin_end_edges=None)))
    if len(pairs)!=4480 or len(leaves)!=80 or sum(len(l['RD_assignment_indices'])for l in leaves)!=4480:raise ValueError('complete producer assignment required')
    out.mkdir(parents=True)
    (out/'RD_pair_assignments.jsonl').write_text(''.join(json.dumps(p,separators=(',',':'))+'\n'for p in pairs))
    (out/'leaf_producers.json').write_text(json.dumps(leaves,indent=1)+'\n')
    result=dict(status='SOURCE_BOUND_FINAL_POST_GAIN_NORM_ASSIGNMENT_ONLY',leaves=80,experts=7,words=35840,RD_pairs=4480,ordered_native_POST_halfrows=1280,GAIN_WL_rows=640,
        native_CAP_selected_words=observed,source_spans=spans,source_top_sha256=normbook['source_top_sha256'],selected_consumer_rank_physical_mapping=None,
        final_FFN_fresh_arithmetic=arith,actual_final_layer_HEAD_state=False,
        logical_TP_contract='each W2 shard owner combines20beats then broadcasts combined halves to other3 full-h replicas; POST follows on each replica; current80-leafbook is one selected consumer replica, not four bound dies',
        source_word_map_sha256=sha((inputs/'word_map.jsonl').read_bytes()),source_values_sha256=sha(values.read_bytes()),
        actual_ret_score_new_order_check=ordercheck['status'],new_placement_numeric_scope_rows=ordercheck['checked_rows'],
        CW_payload_seam=dict(status='GENUINE_WORD1_TO3_MASK_SEMANTICS_FAILURE_PENDING_OWNER_FIX',correct_SRAM_commit_for_all_words=False,source_assignment_not_a_workaround=True),
        unknowns=['actual CW payload seam fixed source/adoption','all CAP commits and native RD leases','TP peer provider/route/arrival bindings','native VS13 combined SRAM commit ages','actual residual/HC/HEAD gain residency',
                  'per-leaf POST h-ready ages','real issuer-to-mission epoch and physical phases','HOST START and retirement'],
        absolute_producer_dates_qualified=False,physical_phase_qualified=False,HOST_START_authority=False,canonical_adopted=False)
    (out/'summary.json').write_text(json.dumps(result,indent=1)+'\n');print(result['status'],'80leaves/4480RDpairs/35840words; CWseamheld')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in('inputs','values','deadlines','normbook','ordercheck','out'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--plans',type=Path,nargs='+',required=True);a=p.parse_args()
    build(a.inputs,a.values,json.loads(a.deadlines.read_text()),json.loads(a.normbook.read_text()),[json.loads(f.read_text())for f in a.plans],json.loads(a.ordercheck.read_text()),a.out)

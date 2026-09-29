#!/usr/bin/env python3
"""Conservative complete-layer-stage payload audit and candidate spill moves.
Unknown dense partitions remain fully replicated, hence no false free space.
"""
import argparse,hashlib,json,math,struct
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def derive(snapshot):
    ip=snapshot/'model.safetensors.index.json';idx=json.loads(ip.read_text())['weight_map'];hs={};pins={}
    def meta(k):
        f=idx[k]
        if f not in hs:
            with open(snapshot/f,'rb') as fd:n=struct.unpack('<Q',fd.read(8))[0];raw=fd.read(n)
            hs[f]=json.loads(raw);pins[f]=hashlib.sha256(raw).hexdigest()
        return hs[f][k]
    ownerpath=ROOT/'results/arch/v41_stage_owner_preflight.json';owners=json.loads(ownerpath.read_text())
    place=json.loads((ROOT/'results/arch/v41_die_placement.json').read_text()); cap=math.floor(place['rom_bytes_per_die'])
    complete=json.loads((ROOT/'results/floorplan/v41_stage17_complete_reservation.json').read_text()); spill=complete['spill_proposal'];q,rem=divmod(spill['layer_spill_rows'],112)
    expert_headers_checked=0
    for name in idx:
        if name.startswith('layers.') and int(name.split('.')[1]) < 40 and '.ffn.experts.' in name and name.endswith('.weight'):
            family=name.split('.')[-2];expected=[5120,1152] if family=='w2' else [2304,2560]
            w=meta(name);sc=meta(name[:-7]+'.scale')
            assert w['dtype']=='I8' and w['shape']==expected
            assert sc['dtype']=='F8_E8M0' and sc['shape']==[expected[0],expected[1]//16]
            expert_headers_checked+=1
    stages=[]
    for stage in range(28):
        dense_layers=[o['layer'] for o in owners['layer_owners'] if o['dense_owner_stage']==stage]
        exp=sum(r['expert_ids'][1]-r['expert_ids'][0]+1 for o in owners['layer_owners'] for r in o['routed_expert_candidate_owners'] if r['stage']==stage)
        entries=[];used=set()
        for layer in dense_layers:
            for name in sorted(k for k in idx if k.startswith(f'layers.{layer}.') and '.ffn.experts.' not in k and '.engram.embed.' not in k):
                if name in used or (name.endswith('.scale') and name[:-6]+'.weight' in idx):continue
                m=meta(name);r=m['shape'];size=m['data_offsets'][1]-m['data_offsets'][0];mode='conservative_full_replication';sources=[name]
                if m['dtype']=='F8_E4M3' and name.endswith('.weight') and len(r)==2:
                    rows,cols=r;scale=name[:-7]+'.scale';sm=meta(scale);sources.append(scale);used.add(scale)
                    local=name.split(f'layers.{layer}.')[1]
                    if local in ['attn.wq_a.weight','attn.wkv.weight','attn.wq_b.weight','ffn.shared_experts.w1.weight','ffn.shared_experts.w3.weight','ffn.shared_experts.w2.weight']:
                        assert rows%4==0;rows//=4;mode='validated_output_row_quarter'
                    elif local=='attn.wo_b.weight':assert cols%4==0;cols//=4;mode='validated_K_quarter'
                    if local=='attn.wo_a.weight':rows//=4;size=rows*cols*2;mode='BF16_expanded_output_groups_quarter'
                    else:
                        assert cols%32==0
                        size=rows*(cols+cols//32)
                        mode+=' with repeated_per_row_scales'
                elif name.endswith('ffn.gate.weight') or name.endswith('attn.attn_sink'):
                    assert size%4==0;size//=4;mode='validated_output_row_quarter'
                entries.append(dict(tensor=name,source_tensors=sources,payload_upper_bound_bytes=size,mode=mode));used.update(sources)
        dense=sum(e['payload_upper_bound_bytes'] for e in entries);expert=exp*4700160
        # Four rank-specific spill rows avoid losing the remainder rows.
        ranks=[]
        for rank in range(4):
            ord=stage*4+rank;sr=q+(ord<rem);total=dense+expert+sr*264
            ranks.append(dict(rank=rank,spill_rows=sr,payload_upper_bound_bytes=total,free_bytes=cap-total))
        stages.append(dict(stage=stage,dense_layers=dense_layers,expert_count=exp,expert_payload_bytes=expert,dense_upper_bound_bytes=dense,dense_tensors=entries,ranks=ranks))
    # Preserve full expert boundaries. Search exact integer capacity; distance
    # is stage-edge count only, not route timing or a proof of optimal latency.
    source=stages[17]['ranks'][0];remove=math.ceil(max(0,-source['free_bytes'])/264);choices=[]
    for s in stages:
        for r in s['ranks']:
            if s['stage']==17:continue
            rowcap=max(0,r['free_bytes']//264)
            if rowcap>=remove:
                choices.append(dict(stage=s['stage'],rank=r['rank'],rows=remove,destination_free_before_bytes=r['free_bytes'],destination_free_after_bytes=r['free_bytes']-remove*264,stage_distance=abs(s['stage']-17)))
    choices.sort(key=lambda c:(c['stage_distance'],c['stage'],c['rank']))
    proposed=choices[0] if choices else None
    if proposed:
        interval=complete['spill_proposal']['intervals'][0];end=interval['row_end'];proposed.update(table=interval['tensor'],row_begin=end-remove,row_end=end,bytes_moved=remove*264,
            added_request_response_bytes_per_access=0,forwarded_row_bytes_per_access=264,route_timing_claim=False,
            routing='Update gather ownership lookup; request goes directly to destination. Stage distance is a heuristic, not actual routed latency.')
    return dict(schema='opentallas.v41.spill_relocation.v1',status='candidate_capacity_audit_not_physical_binding',index_sha256=hashlib.sha256(ip.read_bytes()).hexdigest(),checkpoint_header_sha256=pins,owner_sha256=hashlib.sha256(ownerpath.read_bytes()).hexdigest(),capacity_bytes=cap,expert_matrix_headers_checked=expert_headers_checked,stages=stages,source_stage=17,source_rank=0,required_rows_to_move=remove,eligible_destinations=choices,proposed_move=proposed,
        all_layer_stages_fit_before=all(r['free_bytes']>=0 for s in stages for r in s['ranks']),total_layer_deficit_bytes=sum(max(0,-r['free_bytes']) for s in stages for r in s['ranks']),total_conservative_layer_spare_bytes=sum(max(0,r['free_bytes']) for s in stages for r in s['ranks']),
        unresolved=['unknown dense splits conservatively replicated; macro port/physical binding remains unproved','head allocation retained from mean model: exact head image capacity still required','full layer-stage spill redistribution required if other stages fail','actual gather endpoint/route timing unavailable, cannot prove minimum added critical-path latency'])

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--snapshot',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.write_text(json.dumps(derive(a.snapshot),indent=2)+'\n')

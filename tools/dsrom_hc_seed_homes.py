"""Source-owned proposed distributed HC seed homes, not an adopted dispatch."""
import hashlib
import json
from pathlib import Path


def model(owner_root):
    root=Path(owner_root)
    provider=root/'results/uarch/dsrom_s81_released_binding_20261004/canonical/providers.json'
    providers=json.loads(provider.read_text())
    sources=[]
    for layer,stage in ((37,74),(38,76),(39,78)):
        anchors=[p for p in providers if p['layer']==layer and p['kind'] in ('HE','CROM')]
        assert len(anchors)==2 and all(p['stage']==stage for p in anchors)
        for rank in range(4):
            sources.append(dict(layer=layer,stage=stage,rank=rank,die_id=4*stage+rank,
                canonical_anchors=[dict(kind=p['kind'],pairs=p['pairs']) for p in anchors],
                reader='ot_dsrom_hc_input_reader',capture='ot_dsrom_hc_mean_capture',
                SINGLE_CAPTURE=1,capture_index=layer-37,join_rank=rank,
                H_layout=dict(source='tools/hdc_replay_v41.py ShapeLayout(tp_exact=True)',
                    logical_H_element_base=0,VM_row_base=0,
                    runtime_binding='require selected stage input-context restore and protected H lease; allocator address alone is not ownership',
                    copy_row_stride=320,rank_row_offset=80*rank,rows_per_copy=80,
                    copies=4,expanded_F32_reads=320,input_bytes=20480),
                output=dict(payload_flits=40,payload_bytes=2560,header_bytes=64,
                    identity='user10/position21/epoch4/capture2/frame6'),
                trigger='after layer input H restore/fence, before hc_pre; release H lease only after capture reads complete'))
    return dict(schema='opentallas.dsrom.hc-seed-homes.v1',adopted=False,
        canonical_provider_sha256=hashlib.sha256(provider.read_bytes()).hexdigest(),
        physical_home_basis='canonical HE/CROM anchors; input-VM service home remains an explicit proposed binding',
        sources=sources,joins=[dict(rank=r,proposed_primary_head=f'h{r}',
            master='ot_dsrom_hc_seed_join',captures=[37,38,39],payload_flits=120,
            output='MT_SEED native engine5; semantic rank1280 of three5120-wide means',
            seed_engine_binding_qualified=False) for r in range(4)],
        replicas=dict(readers=12,captures=12,joins=4),
        area=dict(reader_slot_um=[500,400],capture_slot_um=[1000,1000],
            join_slot_um=[500,500],total_slot_mm2=15.4,
            capture_and_join_SRAM256x256_macros=48,
            actual_macro_outline_um=[172.824,41.064],
            actual_macro_area_um2=172.824*41.064,
            capture_and_join_raw_SRAM_area_mm2=48*172.824*41.064/1e6),
        ports=dict(reader_bits_per_cycle=512,capture_link_bits_per_cycle=512,
            payload_bytes_per_cycle=64,protected_buffer_bits=576,
            link_tracks=512,channel_capacity=None),
        transport=dict(proposal='three independently framed 40-flit SIDE messages per rank; never a120-flit message through46-word VMX staging',
            messages=12,global_payload_bytes=30720,global_header_bytes=768,
            each_message_staging_words=41,VMX_existing_words=46,
            source_and_forwarding_native_endpoints_qualified=False,
            stage_hops=None,route_coordinates=None,
            serialization_cycles_per_message_lower_bound=41,
            link_hop_cycles=None,added_single_user_cycles=None),
        pending=['selected source-plan H restore and pre-hc_pre dispatch fence',
            'real VM arbiter request/rvalid/fault binding and slot lease',
            'physical local placement at each canonical stage/rank die',
            'source and forwarding SIDE endpoint identity/credits/CRC contract',
            'actual primary head join landing and MT_SEED5 feed',
            'measured full-rank seed phases and composed token latency'],
        qualification='planning composition; no physical or exposed-latency credit')


if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser();ap.add_argument('--owner-root',required=True);ap.add_argument('--out',required=True)
    a=ap.parse_args();out=Path(a.out);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(model(a.owner_root),indent=2)+'\n')

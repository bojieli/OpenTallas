"""Source-bound address audit and partial service price, not connected timing."""
import hashlib
import json
import math
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
COMMIT='609af8387'
PATH='results/rtl/w19_checkpoint_production_20261001/resident-service-candidate-r1.json'


def generate():
    blob=subprocess.check_output(['git','show',f'{COMMIT}:{PATH}'],cwd=ROOT)
    c=json.loads(blob)
    checked={}
    for path,expected in c['source_pins'].items():
        actual=hashlib.sha256(subprocess.check_output(['git','show',f'{COMMIT}:{path}'],cwd=ROOT)).hexdigest()
        assert actual==expected,path
        checked[path]=actual
    maxend=0; physicalbytes=0; non_sm=0; region_count=0
    for rank in c['ranks']:
        end=rank['weight_end'][:]
        physicalbytes+=sum(end)
        assert len(rank['regions'])==133
        for region in rank['regions']:
            region_count+=1
            assert sum(region['extent'])>=region['bytes']
            for controller in range(4):
                base=region['base'][controller]; extent=region['extent'][controller]
                assert base%256==0 and extent%256==0 and base>=end[controller]
                end[controller]=base+extent
                non_sm+=extent
        assert end==rank['stack_end']
        maxend=max(maxend,*end)
        physicalbytes+=sum(end)-sum(rank['weight_end'])
    assert maxend==c['max_stack_end']==3175215616
    sectors=(maxend+31)//32
    bits=(sectors-1).bit_length()
    assert bits==c['required_sector_bits_candidate']==27
    hc=c['hc_compute']; service=c['hc_service']; schedule=c['service_schedule']
    issue=hc['issue_cycles']; tail=hc['pipeline_tail_cycles']
    assert issue==(hc['norm_tasks']+hc['coefficient_tasks']) and issue==2000
    assert tail==31+hc['ML']+3*int(math.log2(hc['W']))+3*hc['TL']==69
    requests=math.ceil(service['operator_bytes']/4/512)
    assert requests==schedule['hc_ingress_floor_cycles_operator']==960
    ingress_ns=requests*c['ports']['controller']['proposed']['CLK_PS']/1000
    compute_ns=(issue+tail)*1e9/hc['clock_hz']
    return dict(schema='opentallas.w16.w19.resident-service-partial-price.v1',
        source_commit=COMMIT,source_record=PATH,source_record_sha256=hashlib.sha256(blob).hexdigest(),
        verified_source_pins=checked,
        verdict='ADDRESS_POLICY_ARITHMETIC_VALID_SERVICE_MODEL_INCOMPLETE',
        adoption=False,physical_build_admitted=False,connected_rate_credit=False,
        address_policy=dict(ranks=96,controllers_per_rank=4,regions_checked=region_count,
            max_stack_end_exclusive_bytes=maxend,sector_bits_candidate=bits,
            bulk_line_bits_candidate=((maxend+127)//128-1).bit_length(),
            total_reserved_controller_extents_bytes=physicalbytes,
            non_sm_reserved_extents_bytes_including_padding=non_sm,
            full_stack_address_width_qualified=None,
            note='Disjoint aligned allocation under declared one-user1M+1/full-HC-copy/embedding-striping policies. All candidate regions checked; no full-context longevity, operational writer/reader acceptance or qualification inferred.'),
        hc_partial_price=dict(operators_per_token=80,parallel_rank_replicas=96,
            coefficient_bytes_per_rank_token=service['bytes_rank_token'],
            coefficient_bytes_all_ranks_token=service['bytes_rank_token']*96,
            operator_ingress_request_floor_stream_cycles=requests,
            operator_ingress_request_floor_ns=ingress_ns,
            operator_issue_cycles_serial_domain=issue,operator_tail_cycles_serial_domain=tail,
            operator_issue_and_tail_ns=compute_ns,
            no_overlap_ingress_plus_issue_tail_floor_ns=ingress_ns+compute_ns,
            per_user_token_80operator_floor_us=80*(ingress_ns+compute_ns)/1000,
            note='Candidate serial phase schedule. 96 ranks work in parallel: do not multiply elapsed time by96. Coefficient ingress request floor plus issue/tail is partial cost, not complete latency; activation transfer, queue service, staging scatter, norm/SFU/Sinkhorn and barriers remain unpriced.'),
        ports=dict(hcp_coefficient_read_bits_cycle=hc['coefficient_read_bits_cycle'],
            hcp_activation_read_bits_cycle=hc['activation_read_bits_cycle'],
            hcp_staging_bytes_per_rank=hc['staging_coefficient_bytes']+hc['staging_activation_bytes'],
            hcp_staging_bytes_all_ranks=96*(hc['staging_coefficient_bytes']+hc['staging_activation_bytes']),
            required_coefficient_read_GB_s_per_rank=hc['coefficient_read_bits_cycle']/8*hc['clock_hz']/1e9,
            required_activation_read_GB_s_per_rank=hc['activation_read_bits_cycle']/8*hc['clock_hz']/1e9,
            su_read_bits_cycle=c['ports']['SU']['read_bits_cycle'],
            width_and_clock_not_qualified=True),
        area_and_routes=dict(hcp_replicas=96,fp32_product_lanes_per_rank=hc['lanes'],
            fp32_product_lanes_total=96*hc['lanes'],bank_word_bits=hc['coefficient_bank_word_bits'],
            coefficient_banks_per_rank=8,coefficient_words_per_bank=hc['coefficient_bank_words'],
            sram_macro_area_mm2=None,compute_area_mm2=None,die_slot_fit=None,
            crossing_bits_cycle=None,noc_traffic_bits_token=None,routing_tracks=None,
            reason='Byte capacity is not ported SRAM area. Qualified bank abstracts and actual scatter/fanout/topology/clock crossings must supply area and routing; no ROM element area or infinite-bandwidth SRAM substitution.'),
        full_token_latency=None,
        completion_dependencies=schedule['missing']+[
            'SU N16/LV7 full-program legality is open: full norm5120 and hcpost20480 need legal source-bound profiles; fixed port description is not consumer coverage.',
            'HCP norm/rsqrt/scaling/output drain and sigmoid/Sinkhorn complete cycles and exact rounding.',
            'Coefficient+activation staging DMA bank scatter finite throughput; explicit SU staging contention and result service.',
            'All nonSM table/state service and RMW-write completion, no acceptance-as-commit substitution.',
            'Unified-model field/SM/hub slots, ported SRAM area, replica fanout/mux costs, NoC link bits/cycle and tracks.',
            'Connected complete token cycles and golden exactness; new hardware contextual SS/FF before adoption.'])


if __name__=='__main__':
    (HERE/'partial_price.json').write_text(json.dumps(generate(),indent=2)+'\n')

#!/usr/bin/env python3
"""Preserve CKV physical failure; price a conditional serial staging baseline."""
import argparse,gzip,hashlib,json,subprocess
from decimal import Decimal as D
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
FAILED='a332f6033b95e9c2e6409865df0acb78c670cca5'
BASE='results/physical_abi3/asap7/chip/w11_ckv_merge_finish_20261001/'
CURRENT='73d79c123b823e7e47e134d5d9752b34812be761'
PATHS=('rtl/chip/ot_chip_v41x_ckv_stream_merge.sv','rtl/chip/physical/ot_v41_ckv_merge_phys.sv')
def blob(c,p):return subprocess.check_output(['git','show',c+':'+p],cwd=ROOT)
def sha(b):return hashlib.sha256(b).hexdigest()

def packets(window,selected,port_bits=256):
    if type(window) is not int or type(selected) is not int or not 0<=window<=128 or not 0<=selected<=512:raise ValueError('row extent outside actual CKV contract')
    if type(port_bits) is not int or port_bits<=0:raise ValueError('unpriced transport width')
    out=[]
    # Exact source row order; sixteen32-element groups/row. No arithmetic or
    # qdq rounding changes. Header is explicitly proposed, not existing RTL.
    for first in range(0,window+selected,4):
        n=min(4,window+selected-first);nw=sum(first+i<window for i in range(n));nc=n-nw
        for group in range(16):
            bits=nw*264+nc*144+36
            out.append(dict(beat=first//4,group=group,first_row=first,rows=n,window_rows=nw,ckv_rows=nc,
                raw_payload_bits=nw*264+nc*144,header_bits=36,packet_bits=bits,serialization_cycles=(bits+port_bits-1)//port_bits))
    return out

def price(window,selected,port_bits=256):
    ps=packets(window,selected,port_bits)
    inbits=window*4224+selected*2304
    # Conservative no overlap: actual input row arrival plus all packet service.
    input_cycles=(inbits+port_bits-1)//port_bits
    output_cycles=sum(p['serialization_cycles'] for p in ps)
    return dict(window_rows=window,selected_rows=selected,raw_input_bits=inbits,
        raw_input_serialization_cycles=input_cycles,packets=len(ps),packet_bits=sum(p['packet_bits'] for p in ps),
        output_serialization_cycles=output_cycles,conservative_no_overlap_service_cycles=input_cycles+output_cycles,
        physical_clock_qualified=False,connected_cycles=None,
        excluded=['actual ingress latency/stalls','CDC','consumer tile writes and done/credit delay','attention compute','descriptor/route/setup/hold/wake costs'])

def build():
    raw=blob(FAILED,BASE+'measurement.json');m=json.loads(raw);refs={BASE+'measurement.json':dict(commit=FAILED,sha256=sha(raw))}
    for path,expected in m['source_binding'][0]['source_sha256'].items():
        b=blob(CURRENT,path)
        if sha(b)!=expected:raise ValueError('failed component source differs from current candidate audit')
        refs[path]=dict(commit=CURRENT,sha256=sha(b),scope='Byte identity to retained failed source; no qualification refresh')
    for name,entry in m['archives'].items():
        b=blob(FAILED,BASE+entry['artifact']);key='gzip_sha256' if entry['artifact'].endswith('.gz') else 'sha256'
        if sha(b)!=entry[key]:raise ValueError('failed archive identity')
        if key=='gzip_sha256' and sha(gzip.decompress(b))!=entry['raw_sha256']:raise ValueError('raw failure archive identity')
        refs[BASE+entry['artifact']]=dict(commit=FAILED,sha256=sha(b))
    pricing_path='tools/common_hbm_backend_provider_contract.py';pricing_commit='6e1158394262bc47773993e04efce0672ac4552e'
    refs[pricing_path]=dict(commit=pricing_commit,sha256=sha(blob(pricing_commit,pricing_path)),scope='Analytical sizing coefficients only, no CKV physical transfer')
    metrics=m['metrics'];cfg=m['measured_configuration']
    if metrics['setup_worst_slack_ps']>=0 or metrics['hold_worst_slack_ps']>=0:raise ValueError('failure criteria changed')
    merger=blob(CURRENT,PATHS[0])
    for token in (b'reg [4*16*265-1:0] beat0, beat1',b'reg [4*4224-1:0] w_rows_q',b'reg [4*2304-1:0] c_rows_q'):
        if token not in merger:raise ValueError('merger storage interface changed')
    oldbits=2*4*16*265+4*4224+4*2304
    # Separate prospective baseline: two raw-beat ingress buffers, two full
    # consumer-local beat buffers, two padded five256bit group packets. This
    # retains full consumer staging; does not claim disappearance of storage.
    storage=2*4*4224+2*4*16*265+2*5*256
    storage_area=D(storage)*D('.2916')/D('.5')/D('1000000')
    # Four row-lane CKV selectors144bit*3mux equivalents +1056bit source select.
    muxbits=4*144*3+4*264
    mux_area=D(muxbits)*D('.2')/D('.5')/D('1000000')
    return dict(schema='opentallas.w11.ckv-required-staging-feasibility.v1',source_pins=refs,
        status='COMPONENT_PHYSICAL_FAIL_REQUIRED_BASELINE_CANDIDATE_UNQUALIFIED',
        preserved_failure=dict(verdict=m['verdict'],metrics=metrics,constraints=cfg,physical_admission=False,adopt=False,
            independent_FF_PASS=False,M2_M5_hub_acceptance=False,no_retry_or_tune=True,
            measured_wrapper_area_not_merge_only=True,ISA_runtime_exactness_separate=True,
            original_source_checkout_available=False,original_commit_object_available=False),
        existing_interface=dict(window_row_bits=4224,ckv_row_bits=2304,output_beat_bits=16960,
            rows_per_beat=4,groups_per_row=16,source_storage_bits_excluding_control=oldbits,
            output_beats_max=160,two_beat_buffers=True,baseline_max_no_stall_output_service_cycles=160,
            scope='Ports/storage and throughput quantities only; startup/stall/token cycles not measured'),
        required_baseline_candidate=dict(policy='Serialize exact raw32-element groups over one256bit source port, expand source format only inside consumer tiles, preserve row/group order and golden qdq; no arithmetic reassociation',
            candidate_header_bits=36,candidate_header_fields={'job':16,'beat':8,'group':4,'row_mask':4,'row_format_flags':4},
            source_port_payload_bits_per_cycle=256,replicas=1,aggregate_payload_bits_per_cycle=256,
            queue_packet_capacity=2,maximum_padded_packet_bits=1280,storage_bits=storage,
            storage_footprint_floor_mm2=str(storage_area),mux_bit_equivalents=muxbits,mux_footprint_floor_mm2=str(mux_area),known_floor_mm2=str(storage_area+mux_area),
            area_scope='Analytical .2916um2/register and.2um2/muxbit at50% density; storage/mux FLOOR only, excludes control, decode, clock, CDC, RF ports/routes. Not measured area or fit.',
            packet_credit_release='Actual complete serialization, CDC landing, destination group write and consumerdone; no accept/timer release',
            actual_consumer_interface_changed=True,consumer_ports_and_enable_costs=None,boundary_routing_tracks=None,channel_capacity_tracks=None,
            actual_SS_FF_latency_cycles=None,power_IR=None,slot_fit=None,exact_gate_passed=False,
            priced_extents=[price(128,0),price(128,512),price(127,512)]),
        feasibility='UNPROVEN: explicit storage/transport lower costs, missing legal physical/consumer contracts; not ready to build',
        required=['Freeze ROM consumer tile port/group-write/mask contract; HBM uses GPU shared/SIMT path, no transfer of this ROM merger',
            'Price control/mux/fanout/routes/CDC/clock/PG and fullconsumer staging in unifiedmodel',
            'Bind actual data arrival and finalconsumerdone to finite queue calendar','Independent classA bit-exact sourceformat/order gate before RTL adoption',
            'Model slot/channel fit and unchanged SS/FF constraints before build'],
        physical_admission=False,engine_RTL_build_ready=False,adopt=False,full_token_cycles=None,full_token_rate=None,jobs_launched=0)
if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(build(),indent=2)+'\n')

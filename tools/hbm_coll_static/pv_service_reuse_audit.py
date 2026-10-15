#!/usr/bin/env python3
"""Source-pinned capacity, physical-port and lifetime audit. No reuse RTL claim."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

REF='8615bcdb9dd7dab560f694c57470877fedf147f7'
PREFIX='rtl/hbm_accel/loader/service_native/'
NAMES=['ot_hbm_svc_sm8_landing_bank.sv','ot_hbm_svc_sm4pc_cdc.sv',
       'ot_hbm_svc_sm_feed_programmed.sv','ot_hbm_svc_static_sm_packed136.sv',
       'ot_hbm_svc_prefetch_mapped4_owner.sv','ot_hbm_svc_native_sector_pipeline_stack.sv',
       'run_sm_stack_programmed.sh','tb_hbm_svc_sm_stack_programmed.sv']
EXTRA=['rtl/chip/ot_chip_v41x_hbm3e_phy.sv','rtl/hbm_accel/sm/static/ot_smh_calendar_static.sv']

def require(source, snippets):
    for snippet in snippets:
        assert snippet in source, 'source contract changed: '+snippet


def ports(events):
    occupied={}
    for cycle,bank,kind,label in events:
        key=(cycle,bank,kind)
        assert key not in occupied, f'port collision {key}: {occupied.get(key)} / {label}'
        occupied[key]=label
    return len(occupied)


def validate_partition(base,total=272):
    hbm={(o%8,o//8) for o in range(total)}
    pv={(o%8,o//8) for o in range(base,base+128)}
    assert all(0<=r<64 for _,r in pv), 'reserved region exceeds physical buffer bank'
    assert hbm.isdisjoint(pv), 'reserved region aliases full HBM block'


def gather(block,head,half,group,base=320,stripe=lambda beat:beat%8):
    addresses=[]
    for dim in range(group*8,group*8+8):
        ordinal=base+block*64+dim
        addresses.append((stripe(dim),ordinal//8,2*head+half))
    assert len({b for b,_,_ in addresses})==8, 'parallel gather exceeds one read per SRAM lane'
    assert len({r for _,r,_ in addresses})==1
    return addresses


def rejects(name,fn,mutants):
    try:
        fn()
    except AssertionError as e:
        mutants.append(dict(name=name,verdict='REJECTED',reason=str(e)))
    else:
        raise AssertionError('mutant survived: '+name)


def credit_invariant(limit=32,allow_full_post=False):
    states=transitions=0
    for aq in range(limit+1):
        for pending in range(limit+1-aq):
            for returned in range(limit+1-aq-pending):
                reserved=aq+pending+returned
                states+=1
                for post in range(2):
                    if post and not (reserved<limit or allow_full_post):continue
                    for issue in range(min(1,aq)+1):
                        for response in range(min(1,pending)+1):
                            for take in range(min(1,returned)+1):
                                aa=aq+post-issue
                                pp=pending+issue-response
                                qq=returned+response-take
                                rr=reserved+post-take
                                assert rr==aa+pp+qq and max(aa,pp,qq,rr)<=limit, 'native response reservation overflow'
                                transitions+=1
    return dict(states=states,transitions=transitions,limit=limit,
                meaning='reserved = posted AQ not issued + DRAM in flight + returned/held SRAM words',
                scope='abstract source-derived credit conservation, not a native-controller-to-service RTL join')


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out',required=True)
    a=ap.parse_args()
    root=Path(__file__).resolve().parents[2]
    paths=[PREFIX+n for n in NAMES]+EXTRA
    src={n:subprocess.check_output(['git','-C',str(root),'show',REF+':'+n],text=True) for n in paths}
    landing=src[PREFIX+NAMES[0]]; cdc=src[PREFIX+NAMES[1]]
    feed=src[PREFIX+NAMES[2]]; cache=src[PREFIX+NAMES[3]]
    native=src[PREFIX+NAMES[5]]; runner=src[PREFIX+NAMES[6]]
    require(landing,['parameter integer RESPONSE_DEPTH=8','wire [5:0] row=ordinal[8:3]',
        'wire landing_write=packet_v&&!stop&&!sticky&&identity_ok',
        'assign packet_take=packet_v&&!stop&&!sticky',
        '.r_addr_in({read_bank,read_row})','.w_addr_in({bank,row})'])
    require(cdc,['reserve_total<=512','!allocated[reserve_bank]','drain_phase==4?3\'d1:3\'d4',
        'g<8;g=g+1','allocated[drain_bank]<=0','fifo_wr_ready[l]',
        '.stop(fault)','.read_v(draining&&candidate<drain_ordinal+drain_count'])
    require(feed,['reserve_rows<=64','reserve_total==expected_sectors','!cache_owned[reserve_bank]',
        'ot_smh_calendar_static #(.W(135))','programme_v?programme[82:0]:83\'d0'])
    require(cache,['p<5;p=p+1','.r_ce_in(read_ok)','.w_ce_in(row_write)',
        'wire [1279:0] padded_row={192\'b0,row_data}'])
    require(native,['read_reserved<32','read_reserved<=read_reserved+(posted_read?6\'d1:6\'d0)-(response_take?6\'d1:6\'d0)',
         'ot_sram_1r1w_128x256_m1_r2c2 u_response_payload','response_take=kr_v[p]&&kr_rdy[p]',
         'else if(response_take)head_valid<=0'])
    require(src[EXTRA[1]],["W>223","captured[255:240]==16'hc7a1","captured[233:224]==pc1","captured[223:W]==0"])
    require(runner,['rtl/chip/ot_chip_v41x_hbm3e_phy.sv'])
    assert 'ot_hbm_svc_native_sector_pipeline_stack.sv' not in runner
    require(src[EXTRA[0]],['BEHAVIOURAL STAND-IN','.QD(64)'])
    mutants=[]
    validate_partition(320)
    maxima=[]
    for rows in range(1,65):
        sectors=((rows*136+127)//128)*4
        assert sectors<=272 and sectors<=320
        maxima.append(sectors)
    count=0
    for buffer in range(2):
        for block in range(2):
            for head in range(4):
                for half in range(2):
                    for group in range(8):
                        address=gather(block,head,half,group)
                        assert all(40<=r<=55 and 0<=b<8 and 0<=w<8 for b,r,w in address)
                        assert all(buffer*64+r<128 for _,r,_ in address)
                        count+=1
    # Actual source copy cadence occupies a subset of read ports at EVERY edge.
    drain=[];ordinal=0;cycle=0
    while ordinal<272:
        n=min(1 if cycle%5==4 else 4,272-ordinal)
        drain += [(cycle,(ordinal+j)%8,'R','cache copy') for j in range(n)]
        ordinal+=n;cycle+=1
    assert cycle==80 and len(drain)==272
    ports(drain)
    writes=[(100+b,b%8,'W','PV publication') for b in range(128)]
    reads=[(228+v,b,'R','PV eight-lane gather') for v in range(128) for b in range(8)]
    ports(drain+writes+reads)
    rejects('capacity region starts inside HBM payload',lambda:validate_partition(256),mutants)
    rejects('capacity region crosses physical buffer bank',lambda:validate_partition(448),mutants)
    rejects('direct producer MAX512 caller aliases live PV partition',lambda:validate_partition(320,total=512),mutants)
    def programme():
        assert 192+52<=223, 'native attention192 plus service52 needs244 protected bits; maximum223'
    rejects('treat protected programme as raw256bit calendar',programme,mutants)
    rejects('non-striped paired beats require two reads of same lane',lambda:gather(0,0,0,0,stripe=lambda b:(b//2)%8),mutants)
    rejects('gather overlaps fixed cache-copy read',lambda:ports(drain+[(0,b,'R','PV gather') for b in range(8)]),mutants)
    rejects('PV and HBM landing write same physical lane',lambda:ports(writes+[(100,0,'W','HBM response')]),mutants)
    def lifetime():
        pv_epoch=7;hbm_epoch=7
        pv_owned=True
        # Source releases producer allocation at last copy; cache retire201
        # permits reserve202, before old arithmetic publishes220..347.
        hbm_epoch=8
        assert not pv_owned or hbm_epoch==pv_epoch, 'HBM reserve relabels live PV epoch'
    rejects('reuse source bank epoch after cache retire',lifetime,mutants)
    def fifo_capacity():
        assert 34<=8, '34 responses exceed FIFO8 without propagating backpressure'
    rejects('assume FIFO8 absorbs unbackpressured full-bank responses',fifo_capacity,mutants)
    credit=credit_invariant()
    rejects('native controller posts beyond reserved response capacity',lambda:credit_invariant(allow_full_post=True),mutants)
    hashes={n:hashlib.sha256(s.encode()).hexdigest() for n,s in src.items()}
    report=dict(schema='pv-service-staging-reuse-source-audit-v1',source_commit=REF,
      verdict='CAPACITY_AND_PROSPECTIVE_CALENDAR_PASS_NATIVE_REUSE_UNIMPLEMENTED',
      scope='source-pinned address/port/lifetime audit and model counterexamples; no shared RTL, clock, physical or performance adoption',
      sources_sha256=hashes,
      capacity=dict(landing_macros_per_SM=8,landing_macro='128x256 1R1W',buffer_banks=2,sectors_per_buffer=512,
        full64_packed136_sectors=max(maxima),full_payload_bytes=272*32,spare_sectors=240,spare_bytes_per_buffer=240*32,
        PV_sectors_per_buffer=128,PV_bytes_per_buffer=4096,PV_ordinal_interval=[320,447],per_lane_rows=[40,55],
        row_cache_macros=5,programme_macros=1,engine_total=13,including_programme_total=14,
        row_cache_unused_physical_bytes_per_buffer=64*24,row_cache_slack_insufficient_for_PV=True),
      programme=dict(physical_bits=256,protected_payload_max_bits=223,current_SM_bits=83,current_service_metadata_bits=52,current_width=135,protected_spare_bits=88,native_attention_bits=192,attention_plus_service_bits=244,excess_before_PV_bits=21,ABI_join_implemented=False),
      gather=dict(exhaustive_vectors=count,logical_row='320+64*blockslot+beat',SRAM_lane='beat%8',
        SRAM_address='{buffer_bank,40+8*blockslot+floor(beat/8)}',
        vector='eight consecutive beats from eight lanes at same SRAM row; each chooses32-bit word2*head+half',
        physical_read_bits_per_vector=2048,selected_result_bits=256,unqualified_new_mux_and_fanout=True),
      ports=dict(cache_copy_edges=80,cache_copy_sectors=272,copy_cadence=[4,4,4,4,1],
        no_idle_copy_edge=True,gather_requires_all8_read_ports=True,
        publication_requires_one_write_port_on_lane_beat_mod8=True,
        source_has_no_PV_hold_or_selector=True,prospective_serial_events=len(drain+writes+reads),
        prospective_calendar=dict(copy=[0,79],PV_write=[100,227],PV_gather=[228,355],PV_release=356,
          note='synthetic feasibility witness only; the existing source does not implement this schedule or a PV lease')),
      finite_response=dict(landing_FIFO_depth=8,full_block_max_responses_per_lane=34,
        owner_entries_per_PC=32,owner_max_burst_beats=4,owner_tag_capacity_not_payload_queue=True,
        current_programmed_bench='behavioural hard PHY idx_hbm QD64/ready',
        actual_native_controller='32 reserved read responses per PC with real response SRAM; unjoined to sm4pc producer',
        source_derived_credit_invariant=credit,reuse_hold_qualified=False),
      lifecycle=dict(current_release='producer allocated clears at last cache-copy beat; cache owned clears on explicit retire; neither waits for PV consumers',
        missing=['PV per-buffer/two-block valid masks and producer epoch','separate PV lifetime independent of HBM/cache reserve epoch, or whole-bank hold through last PV consumer',
          'per-lane write-port reservations and off-die backpressure propagation','compiler forbids every cache-copy/gather read collision',
          '8-lane registered gather and output identity/capture','source-native finite physical response join and pause/resume/reset mutants',
          '192-bit SM attention command plus service/PV control ABI; 192+52 exceeds223 protected payload by21 bits beforePV. Current programme W135 exposes original83 only',
          'two explicit stream-bank clock roots remain physically related; new gather capture/selector routing and clock roots must be priced']),
      alternatives=[
        dict(name='dedicated primary',extra_macros_per_SM=2,extra_macros_per_die=64,
          hardware='two64x512 stager SRAMs/SM with independent ports and epochs; owned by statehelper',
          benefits='separates HBM/cache ports from fixed PV calendar',
          costs='8192bytes/SM (4096bytes per buffer bank), macro placement/control and four512row reads for an eight-contiguous-dimension vector in current two-beat packing',
          status='distinct source/proof under statehelper; no physical adoption inferred'),
        dict(name='phase-isolated shared landing',extra_macros_per_SM=0,
          hardware='reserve320..447 in both landing buffers, add PV ownership/epoch and an8lane read/capture face',
          rule='prove all HBM responses drained and forbid new reserve through PV writes; forbid cache copy until all PV gathers retire',
          benefits='no port arbitration or runtime delay inside fixed PV epoch; structurally easiest reuse proof',
          costs='loses prefetch overlap through explicit hold; actual added latency must be composed; ports/clock/metadata new RTL',
          status='capacity and prospective serial-port witness only'),
        dict(name='per-lane reserved shared landing',extra_macros_per_SM=0,
          hardware='add per-lane HBM-FIFO pop inhibition on compiler PV-write slots, payload selector, all8lane read selector and independent PV epochs',
          rule='HBM arbitrary readiness remains outside fixed PV slots; cache-copy starts only outside all8lane gather reservations; join finite native response storage before accepting holds',
          benefits='can retain HBM landing overlap while PV writes occupy one lane per edge;8contiguous-dimension gather one parallel read',
          costs='new arbitration/credit-calendar join,2048b gather face, control/clock routing and source-specific physical proof',
          status='not implemented or admitted; capacity alone is insufficient')],
      ABI_alternatives=['Keep programme protection unchanged and derive service epoch/tag/read-row from explicitly configured per-bank context/counters; programme carries bounded read/retire controls. New state/bounds/identity gates and source-specific timing are required.', 'Two protected words or a separately priced metadata programme leaf; admit added storage/ports and measure delivery cadence. Do not duplicate an already counted programme macro.', 'Revision of protected programme format is a separate validity contract and must retain equivalent identity/bounds checks; no gate relaxation is assumed.'],
      mutants=mutants,
      excluded_free_slack='row-cache192paddingbits give1536B per buffer, too little; programme unused bits share always-active read port and immutable configuration lifetime, not a free PV store')
    out=Path(a.out);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,indent=2)+'\n')
    print('PV_SERVICE_REUSE_AUDIT PASS source='+REF[:9]+' capacity_vectors='+str(count)+' credit_transitions='+str(credit['transitions'])+' mutants='+str(len(mutants))+' native_reuse=UNIMPLEMENTED')

if __name__=='__main__':main()

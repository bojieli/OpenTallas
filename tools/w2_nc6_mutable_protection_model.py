#!/usr/bin/env python3
"""One prospective protected NC6 implementation; no engine RTL/build emitted.

F0 interleaved extended Hamming72, sealed physical word identity, clean current
word gating, staged CAM, finite correction/scrub and deferred debt retirement.
"""
import argparse,hashlib,json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
D=ROOT/'results/uarch/w2_nc6_mutable_protection_20261003'
POSITIONS=tuple(p for p in range(1,72) if p&(p-1))
MASKS=tuple(sum(1<<(p-1) for p in range(1,72) if p&(1<<i)) for i in range(7))

def check(v,w):
    if type(v)!=int or not 0<=v<1<<w:raise ValueError('width')
    return v

def encode(value):
    check(value,64)
    word=sum(((value>>j)&1)<<(p-1) for j,p in enumerate(POSITIONS))
    for i,m in enumerate(MASKS):word|=((word&m).bit_count()&1)<<((1<<i)-1)
    return word|((word.bit_count()&1)<<71)

def syndrome(cw):
    check(cw,72)
    return sum(((cw&m).bit_count()&1)<<i for i,m in enumerate(MASKS)),cw.bit_count()&1

def decode(cw):
    syn,odd=syndrome(cw)
    if (syn and not odd) or (odd and syn>71):return None,'DUE',None
    fixed=cw ^ ((1<<(syn-1) if syn else 1<<71) if odd else 0)
    value=sum(((fixed>>(p-1))&1)<<j for j,p in enumerate(POSITIONS))
    return value,('CE' if odd else 'CLEAN'),fixed

def systematic_wire(cw):
    # Pure wire permutation into original ROM decoder ABI, no old timing credit.
    check(cw,72)
    data=sum(((cw>>(p-1))&1)<<j for j,p in enumerate(POSITIONS))
    parity=sum(((cw>>((1<<i)-1))&1)<<i for i in range(7))
    return data|(parity<<64)|(((cw>>71)&1)<<71)

def seal(payload,PC,word_index,kind):
    return encode(check(payload,44)|(check(PC,7)<<44)|(check(word_index,10)<<51)|(check(kind,3)<<61))

def unseal(cw,PC,word_index,kind,payload_bits=44):
    value,status,fixed=decode(cw)
    if status=='DUE':return None,'DUE',None
    expected=(check(PC,7)<<44)|(check(word_index,10)<<51)|(check(kind,3)<<61)
    if value>>44!=expected>>44:return None,'LOCATION_FAULT',None
    payload=value&((1<<44)-1)
    if not 0<payload_bits<=44 or payload>>payload_bits:return None,'PADDING_FAULT',None
    return payload,status,fixed


def layout():
    records=[]
    def add(name,bits,kind,count=1):
        for i in range(count):
            width=bits
            for chunk in range(math.ceil(bits/44)):
                n=min(44,width);width-=n
                records.append(dict(index=len(records),record=name,instance=i,chunk=chunk,payload_bits=n,kind=kind))
    # All persistent state, including explicit ownership versions/locks.
    add('table',39+4+1,0,96)
    add('request_holder',335,1);add('read_query',297,1);add('write_query',41,1)
    add('read_delivery',300,2);add('write_selection',5,3,6)
    add('outstanding_cache',5,4,6);add('round_robin',3,4);add('sticky_fault',1,4)
    primary=len(records)
    # Selected-client16row mask + exact39key + slot4/version4/valid1/bad1.
    add('query_pipeline',16+39+4+4+1+1,5,6)  # Three ports x two stages.
    # Six bank engines + two utility engines: single error in one utility
    # context can be repaired by the other. No unpriced self-repair recursion.
    add('correction_context',72+10+7+1+3+2+1,6,8)
    # Accepted event/retirement ledger: conserve until target write commits.
    add('prepared_write',72+10+4+1,7,9)
    add('protected_scheduler',79,4)
    assert primary==133 and len(records)==189
    return records


class Scrub:
    """Snapshot/reference protocol; no claim that these Python receipts exist."""
    def __init__(self,cw,PC,index,kind):
        self.word=cw;self.PC,self.index,self.kind=PC,index,kind
        self.pending=None;self.fault=False;self.retired=False
    def begin(self):
        value,status,fixed=unseal(self.word,self.PC,self.index,self.kind)
        if status in ('DUE','LOCATION_FAULT','PADDING_FAULT'):self.fault=True;return status
        if status=='CE':self.pending=(self.word,fixed)
        return status
    def finish(self):
        if self.fault or self.pending is None:return False
        original,fixed=self.pending
        if self.word!=original:self.fault=True;return False
        value,status,_=unseal(fixed,self.PC,self.index,self.kind)
        if status!='CLEAN':self.fault=True;return False
        self.word=fixed;self.pending=None;return True
    def consume(self):
        # Current word is checked on the actual consumer edge, never a cached
        # syndrome alone. CE cannot bypass correction/scrub; DUE fails closed.
        _,status,_=unseal(self.word,self.PC,self.index,self.kind)
        if self.fault or self.pending is not None or status!='CLEAN':return False
        self.retired=True;return True


def model():
    pins=json.loads((D/'source_manifest.json').read_text())
    for r in pins['inputs']:
        assert hashlib.sha256((ROOT/r['archive']).read_bytes()).hexdigest()==r['sha256']
        assert hashlib.sha256((ROOT/r['path']).read_bytes()).hexdigest()==r['sha256']
    rows=layout();total=len(rows)*72
    facts=json.loads((D/'inputs/results/uarch/w2_pc_exact_completion_20261003/inputs/cell_prices.json').read_text())['facts']
    A=lambda cell:facts[cell]['SS']['area_um2']
    F='DFFASRHQNx1_ASAP7_75t_R';I='INVx1_ASAP7_75t_R';N='NAND2x1_ASAP7_75t_R';B='BUFx4_ASAP7_75t_R'
    # Encoder bits that genuinely vary. Static seal bits are physical storage;
    # their known reset values are not variable encoder XOR inputs.
    encoder_xors=0
    for row in rows:
        counts=[sum(bool(p&(1<<i)) for p in POSITIONS[:row['payload_bits']]) for i in range(7)]
        encoder_xors+=sum(max(0,n-1) for n in counts)+max(0,row['payload_bits']+sum(n>0 for n in counts)-1)
    clean_xors=len(rows)*(sum(m.bit_count()-1 for m in MASKS)+71)
    # Explicit simple2cell construction. Full actual allowed-XOR mapping and
    # drive strength must replace this budget once measured, not768/word reuse.
    codec_nands=4*(encoder_xors+clean_xors)
    correction_nands=8*(72*12+72*4+64)
    source_raw_gross=.01295873316
    hold_bit_area=A(F)+2*A(I)+3*A(N)+2*A(B)+.04374
    extra_hold=(total-4779)*hold_bit_area
    tree=lambda n:sum(math.ceil(n/(8**i)) for i in range(1,1+math.ceil(math.log(max(2,n),8))))
    tree_area=2*(tree(total)-tree(4779))*A(B)
    fixed_logic_budget_nands=468+9*128+6*16*24+8*128+79*32
    body=source_raw_gross+(extra_hold+tree_area+(codec_nands+correction_nands+fixed_logic_budget_nands)*A(N)+194*A(I))/1e6
    resets={}
    for pc in range(128):
        ones=sum(seal(0,pc,r['index'],r['kind']).bit_count() for r in rows)
        resets[str(pc)]=dict(encoded_reset_ones=ones,encoded_reset_zeroes=total-ones,
            reset_load_SS_fF=(total-ones)*facts[F]['SS']['pins']['RESETN']['cap_fF']+ones*facts[F]['SS']['pins']['SETN']['cap_fF'])
    return dict(schema='w2.nc6.prospective.mutable-protection.v1',source_pins=pins,
        scope='ONE source-owned prospective component model before new RTL; no build/adoption',
        exceptional_interface=dict(repair_busy_output_bits=1,
            enrolled=False,registered_state='one bit included in protected_scheduler79; not an extra unprotected flop',
            rule='CE discovery immediately suppresses all normal transfer enables through current-clean gate; repair_busy reports quarantine; held records and debt remain owned',
            held_protocol='healthy ready-held valid/data stable; error quarantine explicitly permits valid suppression until scrub and current recheck; this is a new opt-in exceptional interface contract, not legacy ready-valid compatibility',
            consumer_obligation='accept only qualified valid on actual edge; never infer release from repair_busy; no producer payload reissue or early credit',
            timing='current clean failclose is combinational loaded gate; repair_busy state is registered and cannot itself authorize a same-edge transfer',
            physical_boundary_delta='one output perPC plus actual buffer/route load remains unqualified'),
        geometry=dict(NC=6,MAX_OUT=16,CTAG=32,GEN=4,scoped_tag=39,PC_ID=7,new_directory_client=False),
        codec=dict(K=64,R=7,N=72,packing='F0 interleaved positions1..71 plusoverall72',
            ROM_decoder_direct_wire_compatible=False,systematic_adapter='constant lossless72wire permutation; no gate or old SS/FF transfer',
            seal=dict(payload=44,PC=7,physical_word_index=10,kind=3),
            single_correctable_positions=72,double_in_same_word_failclosed=True,
            independent_crossword_single_errors_not_SECDED_DUE_guarantee=True,
            legal_reencoded_identity_mutations_require_owner_match_not_ECC=True),
        storage=dict(old_target_bits=9144,sealed_primary_words=133,sealed_primary_bits=9576,
            physical_words=len(rows),protected_bits_perPC=total,protected_bits_128PC=total*128,
            delta_vs_old_target_perPC=total-9144,layout=rows,
            all_constant_seal_padding_FFs_must_be_preserved_and_fault_observable=True,
            unprotected_sequential_state_allowed=0),
        ports=dict(table_lookup_ports=3,rows_per_selected_client=16,query_pipeline_records=6,
            normal_table_updates_max_peredge=9,prepared_write_seats=9,protected_words_per_write_seat=2,
            scheduler_bits=dict(repair_busy=1,client_round_robin=3,engine_arbitration=24,journal_reservations=9,journal_commit_phases=18,utility_selector=2,rearm_generation=4,lookup_controllers=9,scrub_write_pending=8,rearm_pending=1),
            correction_engines=8,correction_context_words_each=3,
            correction_groups='6 client banks plus2 utility/utilityrepair; no extra correction arrival FIFO',
            dirty_backlog='retained original codeword; refuse overwrite/mutators until scrub or fault',
            scrub_ports='1 per engine, only corresponding locked word; normal write sameword refused',
            deferred_retirement='consumer handshake journaled; table/count credit stays owned until matched codedwrite commit',
            accepted_not_yet_table_committed_debt='protected write journal, reservation and oldtable jointly conserve; no countcache-only admission'),
        calendar=dict(target_period_ps=833.333333,setup_uncertainty_ps=60,hold_uncertainty_ps=25,
            lookup_stages=['capture codedprimary','current word check/addressseal andpartialkey compare','unique16rowmatch/protected rowlock','prepare coded journal/targetword','codedcommit/outputholding'],
            clean_request_selection_to_backend_min_edges=5,clean_read_capture_to_client_min_edges=5,
            clean_write_capture_to_client_min_edges=6,baseline_request_read_write=[1,2,3],delta=[4,3,3],
            conservative_new_lookup_II_edges=5,read_or_request_bytes_per_service_edge_upper=32/5,
            release_credit_reusable_after_client_edge_min=4,
            CE_detection_to_scrub_min_edges=4,CE_retry_then_complete_adds_normal_pipeline=True,
            CE_multiple_samebank_adds_serial_scrub_service=True,loaded_edge_bounds_qualified=False,
            wrap='rowversion4 and sourcegen4 independently refuse reuse while any indexed query/journal/held/correction debt or provider copy survives; no run cap'),
        loaded_paths=dict(required_before_RTL=['K64 boundary encoder to actual held72bit FF load',
            'Current-word clean detector + seal/held-valid finalfailclose (cannot use old pipelinedcheck after new bitfault)',
            '16row key/equality partial/reduction cuts with actual protected FF loads',
            'small delta-coded rowlock/heldvalid/version/reset feedback paths',
            'global stickyfault fanout, clk/reset trees inclnonzero encoded reset SETN',
            'correction4cycle stablehold/repair/scrub path andsample-staleness check'],
            maximum_logic_plus_wire_budget_ps='833.333333-60-actualCLKQ-actualsetup-actualskew; no assumed SS<=budget',
            FF_hold_repair='measured shortestpaths >=25ps plus actualhold/skew;2BUFperbit isarea floor only',
            K256_K272_prior_results_transferred=False,physical_slot_channel_capacity=None),
        cell_price=dict(encoder_XOR2_operations=encoder_xors,clean_XOR2_operations=clean_xors,
            XOR2_constructive_NAND2_each=4,codec_NAND2=codec_nands,fullcorrection_NAND2_budget=correction_nands,
            noncodec_arbitration_feedback_NAND2_budget=fixed_logic_budget_nands,
            gross_body_mm2_perPC_ASSUMED=body,gross_128PC_50pct_mm2_ASSUMED=body*256,
            net_F0_replacement_debit=None,old_768_perword_codec_allowance_replaced_not_added=True,
            clock_load_SS_fF=total*facts[F]['SS']['pins']['CLK']['cap_fF'],reset_examples=resets,
            reset_all128_SS_fF=sum(r['reset_load_SS_fF'] for r in resets.values()),
            reset_all128_encoded_ones=sum(r['encoded_reset_ones'] for r in resets.values()),
            reset_all128_encoded_zeroes=sum(r['encoded_reset_zeroes'] for r in resets.values()),
            exceptional_output_buffer_NAND_budget_included=True,exceptional_output_wire_load_unknown=True,
            actual_codec_mapping_routes_CLK_PG_SS_FF_qualified=False),
        fault_fixture=dict(physical_singlebit_cases=total,physical_sameword_double_cases=len(rows)*72*71//2,
            required='every72physicalbit inclparity/seal/padding ineveryprimary/query/correction/journal/control word while live orheld, plusall2556doublepairs/word',
            control_cases=['CEwhileheldandreadyasserts: no uncheckedconsume','DUEblocksallnormalreleaseatdiscovery','stale scrub sample refuses overwrite','address/stage validcode alias refuses','utilitycontext singlebit repairs throughotherutility','rearm/reset with allowned/journal/correction/pipeline debt refuses'],
            RTL_fault_campaign_executed=False),
        readiness=dict(RTL_ready=False,reason='ExactdirectK64loaded encoder/current-clean/feedback cones must meet selectedcuts, and accepted-journal/row-lock allocation plus exceptional repair-held protocol need modelgate and interface enrollment before RTL',
            next_gate='Source-compatible K64 encoder/check/fullcorrector + typedcurrentclean/feedback and16rowquery cone characterization under actualSSFFloads; no fullcore/bridge or clockrelaxation',
            whole_caller_dependency=False,protected_functional_or_physical_qualification=False))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path);a=p.parse_args();text=json.dumps(model(),indent=2,sort_keys=True)+'\n'
    if a.output:a.output.write_text(text)
    else:print(text,end='')

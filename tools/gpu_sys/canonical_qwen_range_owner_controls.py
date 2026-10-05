"""One finite native-range owner, sized before its default-off RTL.

This module is a model/typed port specification, never a runtime authority.
Positive publication and retirement are intentionally NOT specified from a
host dictionary: their enrollment awaits the actual native issuer contract.
"""
from dataclasses import dataclass, asdict
import hashlib
import math
import json
from pathlib import Path
from tools.gpu_sys.canonical_qwen_source_mapping import uint
ROOT=Path(__file__).resolve().parents[2]
ROWS=7
SMS=64

# Every field is held physically; no opaque181-bit bucket and no native64
# identity repurposed as a32-bit backend owner or as a source session.
ROW_FIELDS=dict(live=1,published=1,fault=1,producer_terminal=1,producer_reverse=1,
    consumer_live=1,consumer_terminal=1,consumer_reverse=1,
    session=64,version=11,RF_first=9,RF_length=7,owner46=46,
    birth_PC=11,retire_PC=11,consumer_count=9,consumer_ordinal=9,
    consumer_PC=11,native_tag=64,native_generation=64,
    producer_ACK_bitmap=32)
QUERY_FIELDS=dict(valid=1,operation=3,rank=1,SM=5,session=64,version=11,RF_slot=9,
    source_PC=11,native_tag=64,native_generation=64,owner46=46,
    RF_first=9,RF_length=7,birth_PC=11,retire_PC=11,consumer_count=9,expected_consumer_PC=11)
RESULT_FIELDS=dict(valid=1,fault=1,row=3,rank=1,SM=5,session=64,version=11,RF_slot=9,
    owner46=46,source_PC=11,native_tag=64,native_generation=64)
# Two rescue-capable held repair records. Target observed-CW comparison is
# mandatory before scrub; CE in one holder stalls its use until self-repair
# becomes CLEAN. DUE/location/padding faults cannot release a lease or query.
REPAIR_FIELDS=dict(valid=1,row=3,word=4,observed=72,candidate=72,phase=3)
GLOBAL_FIELDS=dict(session_live=1,session=64,current_PC=11,fault=1,
    reset_quarantine=1,query_busy=1,selected_row=3,query_phase=3,
    repair_busy=1,repair_choice=1,repair_phase=3)
PIN_FIELDS=dict(
    command={'valid':1,'ready':1,**QUERY_FIELDS},
    held_query={'valid':1,'ready':1,**RESULT_FIELDS},
    issuer_PC={'current':11,'advance_valid':1,'advance_ready':1,'next_PC':11},
    session={'valid':1,'ready':1,'session':64,'allcopies_fenced':1},
    RF_ACK={'valid':1,'ready':1,'slot':9,'owner46':46,'identity_fault':1},
    producer_terminal={'session':64,'PC':11,'tag':64,'generation':64,'rank':1,'SM':5,
        'version':11,'RF_first':9,'RF_length':7,'owner46':46,'actual_output_visible':1,'implemented':False},
    consumer_terminal={'session':64,'PC':11,'tag':64,'generation':64,'rank':1,'SM':5,
        'version':11,'RF_first':9,'RF_length':7,'owner46':46,'implemented':False},
    matched_reverse={'session':64,'PC':11,'tag':64,'generation':64,'rank':1,'SM':5,
        'version':11,'RF_first':9,'RF_length':7,'owner46':46,'implemented':False})


def words(fields):return math.ceil(sum(fields.values())/44)


def control_model(placement=None):
    from tools.gpu_sys.canonical_qwen_source_mapping import SourcePlacement
    placement=placement or SourcePlacement.released()
    by_sm=[sum(h.rank*32+h.sm==i for h in placement.rf.values()) for i in range(64)]
    consumer_entries=sum(len(v) for v in {h.version:h.consumers for h in placement.rf.values()}.values())
    ROM_nand_all=sum(n*(5*11+3*49) for n in by_sm)+SMS*consumer_entries*(5*20+3*12)
    cells='results/uarch/w2_nc6_mutable_protection_20261003/inputs/results/uarch/w2_pc_exact_completion_20261003/inputs/cell_prices.json'
    f=json.loads((ROOT/cells).read_text())['facts']
    area=lambda n:f[n]['SS']['area_um2']
    ff='DFFASRHQNx1_ASAP7_75t_R';nand='NAND2x1_ASAP7_75t_R';inv='INVx1_ASAP7_75t_R';buf='BUFx4_ASAP7_75t_R'
    from tools.gpu_sys.canonical_qwen_range_owner_rtl import ROW,GLOBAL,BIND,QUERY
    bank=[]
    def add(name,fields,count):
        w=words(fields)
        bank.append(dict(name=name,count=count,fields=fields,payload_bits=sum(fields.values()),
                         sealed_words_each=w,physical_bits=count*w*72))
    add('range_rows',ROW,ROWS)
    add('accepted_input_binding',BIND,1)
    add('held_query_result',QUERY,1)
    add('global_barrier',GLOBAL,1)
    bits=sum(x['physical_bits'] for x in bank)
    # Decoder capture is coded again; unprotected decode-stage FFs are not free.
    # No seven-context downstream queue: one query/result seat retained until
    # actual consumer accepts. Existing RF4096/8192 buses are not duplicated.
    compare=ROWS*(64+11+9+6+1)
    # Explicit bounded gate budget, separate from the FF floor. Actual netlist
    # and loaded SS/FF must replace this estimate before any clock claim.
    selector_nand=3*(ROWS-1)*sum(ROW.values())
    from tools.w2_nc6_mutable_protection_model import POSITIONS,MASKS
    current_check_xors=sum(m.bit_count()-1 for m in MASKS)+71
    encoder_xors=sum(max(0,sum(bool(p&(1<<i)) for p in POSITIONS[:44])-1) for i in range(7))+44+7-1
    physical_words=sum(x['sealed_words_each']*x['count'] for x in bank)
    current_check_nand=4*physical_words*(current_check_xors+encoder_xors)
    full_corrector_nand=physical_words*(72*12+72*4+64)
    context_logic_nand=8*compare+512
    total_nand=selector_nand+current_check_nand+context_logic_nand+full_corrector_nand
    ff_floor=bits*area(ff)
    physical_hold_floor=bits*(area(ff)+2*area(inv)+3*area(nand)+2*area(buf))
    control_area=(physical_hold_floor+total_nand*area(nand))/1e6
    return dict(schema='canonical-qwen-native-range-controls',rows_per_SM=ROWS,SMs=SMS,
        state_banks=bank,protected_bits_per_SM=bits,protected_bits_all_SM=bits*SMS,
        FF_body_area_mm2_floor=ff_floor*SMS/1e6,
        control_body_estimate_mm2=control_area*SMS+ROM_nand_all*area(nand)/1e6,
        immutable_case_ROM=dict(metadata_rows_all_SM=len(placement.rf),metadata_width=49,rows_per_SM=by_sm,consumer_rows_per_SM=consumer_entries,consumer_index_bits=20,consumer_data_bits=12,NAND2_budget_all_SM=ROM_nand_all,ECC_required=False,additional_FFs=0,provider="source-generated constant case logic; no unspecified SRAM"),
        CLK_SS_cap_fF=bits*SMS*f[ff]['SS']['pins']['CLK']['cap_fF'],
        current_check_and_selector_NAND2_budget_per_SM=total_nand,
        query_ports_per_SM=1,held_results_per_SM=1,repair_holders_per_SM=0,
        query_input_bits=239+11+9+1,query_output_bits=239+46+9,
        internal_row_mux_bits=sum(ROW.values()),row_match_fanout=ROWS,
        prospective_calendar=dict(command_accept_to_coded_row_capture_edges=1,
            capture_to_checked_current_edges=3,checked_to_held_result_edges=1,
            query_service_edges=5,query_II_edges=5,consumer_hold_unbounded_until_actual_ready=True,
            CE_detect_to_verified_scrub_min_edges=1,CE_retry_includes_whole_query=True,
            clean_publication_edges=None,clean_retirement_edges=None),
        required_physical_barrier='nextPC admission refuses any live row retire_PC<nextPC; only real source_native_retire clears a row; GO also requires captured whole input association and actual issuer ready',
        range_capacity_rule='7 only with this barrier wired to actual issuer GO; otherwise use fully priced direct seats',
        source_clock='retain actual enclosing clock; prospective edges are not an SS/FF clock qualification',
        pins=PIN_FIELDS,positive_terminal_contract_enrolled=False,required_new_ABI_received=True,RTL_build_admitted=False,functional_component_enrollment_only=True,
        repair_contract='Every codeword owns an existing full combinational sealed decoder; CE stalls ALL handshakes and scrubs only the current decoder candidate on its next edge. No secondary repair queue or shared-port scheduling. All DUE/seal/padding failures retain state and block release. Physical decoder latency is unqualified.',
        codec_replication=dict(decoders=physical_words,encoders=physical_words,parallel_scrub_ports=physical_words),
        hierarchy=dict(ranks=2,PCs_per_rank=128,total_PCs=256,inner_PC_width=7,outer_reverse_rank_width=1),
        track_and_slot_fit=None,SS_FF_loaded_timing=None,
        source_pins=[dict(path=cells,sha256=hashlib.sha256((ROOT/cells).read_bytes()).hexdigest())],
        source_fault_policy='freeze new admissions, retain accepted query/row/repair debt; reset never silently erases leases',
        generation_reuse='requires positive matched reverse/allcopy fence, never age or timer')


@dataclass(frozen=True)
class SourceQuery:
    rank:int
    SM:int
    session:int
    version:int
    RF_slot:int
    source_PC:int
    native_tag:int
    native_generation:int
    owner46:int
    RF_first:int
    RF_length:int
    birth_PC:int
    retire_PC:int
    consumer_count:int
    expected_consumer_PC:int

    def __post_init__(self):
        for k,w in QUERY_FIELDS.items():
            if k not in ('valid','operation'):uint(getattr(self,k),w,k)

    @property
    def width(self):return sum(QUERY_FIELDS[k] for k in asdict(self))

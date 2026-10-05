"""Owned minimum W11 reservation/RMW/publication control sizing and ABI.

No RTL or runtime grants. Physical choice assigned by root: NB2/RC6/K4/WQD4/
RDREG1. Raw W6 codec construction is the exact pricing basis. Maxwell supplies
actual macro/parity ports and positive codec cuts before this model admits RTL.
"""
from pathlib import Path
import argparse,hashlib,json,math
ROOT=Path(__file__).resolve().parents[1]

def codebits(n):return 72*math.ceil(n/64)

def row_mask(group,bank,row,base,length):
    if not 0<=group<128 or not 0<=bank<2 or not 0<=row<256:raise ValueError('W11 physical coordinates')
    if length<=0 or not 0<=base<base+length<=1<<19:raise ValueError('AW19 extent')
    return sum(1<<c for c in range(8) if base <= ((row*16+bank*8+c)*128+group) < base+length)

def prepare(source_root):
    r=Path(source_root)
    inputs=('results/uarch/dsrom_s81_native_vm_ports_20261004/inputs/ot_v41_vm_group_phys.sv',
      'results/uarch/dsrom_native_masked_backend_prepare_20261003/inputs/w6_codec.sv',
      'results/uarch/dsrom_native_masked_backend_prepare_20261003/model.json',
      'tools/dsrom_s81_capture_parent.py',
      'results/uarch/dsrom_native_masked_backend_prepare_20261003/inputs/cell_prices.json')
    cm=json.loads((r/inputs[2]).read_text())['SRAM_protection_candidate']
    # Every descriptor word independently encoded; no implied sharing with r4.
    records={
      'phase_header':dict(count=1,raw=124,fields='identity57,source_obase19,range_base19,range_length19,group7,active1,go1,fault1'),
      'bank_range':dict(count=2,raw=17,fields='first_row8,last_row8,valid1'),
      'fixed_row_metadata':dict(count=8,raw=35,fields='row8,expected8,received8,published8,state3'),
      'fixed_row_payload':dict(count=8,raw=256,fields='8 unchanged FP32 columns'),
      'active_RMW':dict(count=2,raw=100,fields='owner83,state4,copy_commit6,copy_verified6,valid1'),
      'old_checked_row':dict(count=2,raw=256,fields='old data, four independent64-bit W6 stripes'),
      'merged_checked_row':dict(count=2,raw=256,fields='merged new data, four independent64-bit W6 stripes'),
      'held_count_receipt':dict(count=2,raw=104,fields='owner83,root_ids14,root_counts6,valid1')}
    for x in records.values():x.update(coded_each=codebits(x['raw']),coded_total=x['count']*codebits(x['raw']))
    ff=sum(x['coded_total'] for x in records.values())
    pairs=sum(x['coded_total']//72 for x in records.values())
    gates=cm['one_source_encoder_decoder_pair_gate_counts']
    codec_area=pairs*cm['pair_cell_body_um2']/1e6
    # Finite explicit no-CSE mux/equality floor only, not loaded timing.
    # 8 row metadata records (hold/reserve/receive/service/receipt/cold),
    # 8 payload rows (hold/receive/cold); 2 active contexts (8 state paths).
    muxbits=8*35*5+8*256*2+2*100*7+2*512*3+2*104*3+124*3+2*17*2
    # Four slots per bank, four arrival lanes: exact address8/identity57 checks.
    compare_bits=2*4*4*(8+57)+2*6*83*2
    comparisons=2*4*4*2+2*6*2
    mux_select_inv=8*5+8*2+2*7+2*3+2*3+3+2*2
    padding=sum(x['count']*(x['coded_each']//72*64-x['raw']) for x in records.values())
    padded_records=sum(x['count'] for x in records.values() if x['coded_each']//72*64>x['raw'])
    padding_or=padding-padded_records
    cg={'NAND2x1_ASAP7_75t_R':3*muxbits+5*compare_bits-comparisons+padding_or,
        'INVx1_ASAP7_75t_R':mux_select_inv+2*compare_bits-comparisons+2*padding_or}
    facts=json.loads((r/inputs[4]).read_text())['facts']
    ctrl_area=sum(n*facts[k]['SS']['area_um2'] for k,n in cg.items())/1e6
    ff_area=ff*facts['DFFHQNx1_ASAP7_75t_R']['SS']['area_um2']/1e6
    return dict(schema='dsrom.s81.W11.owned_publication_control.v1',
      ownership={'Nash':'preGO reservation/RMW bankowner/all6copy publication/count receipts, modelthenRTL',
        'Maxwell':'minimum protected group clocks, macro/check ports, positive codec cuts, slot+route costs',
        'Archimedes':'source GO/command-ready/fieldidle/native enclosing hooks',
        'bank4':'functional vehicle ONLY'},
      source_pins={p:hashlib.sha256((r/p).read_bytes()).hexdigest() for p in inputs},
      target={'NB':2,'RC':6,'K':4,'WQD':4,'RDREG':1,'write_clock_GHz':.9,
        'clock_scope':'Assigned serial policy target, not SS qualified',
        'setup_SS_ps':60,'hold_FF_ps':25,'source_phase_positions':1},
      records=records,state_total_coded_FF=ff,
      cost={'minimum_control_only_cell_mm2_floor':ff_area+codec_area+ctrl_area,
        'minimum_control_only_placement_mm2_floor_50pct':2*(ff_area+codec_area+ctrl_area),
        'raw_W6_encode_decode_pairs':pairs,'pair_gate_counts':gates,
        'actual_W6_codec_no_CSE_body_mm2':codec_area,
        'source_update_compare_padding_gate_counts':cg,
        'source_update_compare_padding_body_mm2':ctrl_area,
        'state_FF_body_mm2':ff_area,'padding_bits_checked':padding,
        'raw_update_mux_bit_floor':muxbits,
        'owner_address_equal_bit_floor':compare_bits,
        'excluded':['semantic/bounds/state-decode and loaded control/fanout mapping','macro/check storage+ports','codec cut pipeline FF',
          'CDC/frame retention/two routes','clock/reset/PG/route buffers'],
        'not_summed_with_joint_r4':True},
      ABI={
       'reserve':'held identity57,source_obase19,range_base19,length19,group7 + real writer/reader exclusion + gear/route/count-return seats reserved',
       'command_ready':'loading command does NOT require reservation; phase_GO requires atomically retained reservation',
       'field_arrival':'NB*K records, valid/error,identity57,address19,root7,row16,position3,raw32; accept only exact row/column and identity; duplicate column faults',
       'RMW_read':'2 valid/ready, owner83,row8; matching checked64-stripe oldrow response required; actual read/check-port owner, no borrowedRC for free',
       'data_check_write':'2 held owner83,row8,merged_data256,check32; actual all6copy qualified writes observed per-copy',
       'copy_commit':'12 qualified actual per-copy events, each fullowner83; wrong/duplicate event faults; never count firstcopy as global publication',
       'copy_verified':'12 actual checked publication events, each fullowner83; all6 data+check-copy matches required',
       'count_receipt':'2 held coded144 packets: owner83 +2root IDs7 +2counts3 +valid1; source captured counter updates before positive return',
       'owner_layout':'identity57,group7,bank1,slot2,row8,mask8 =83; group not silently inferred across routed receipt boundary',
       'count_receipt_return':'2 fullowner83 matched positive reverse capture; not outputready or localempty; releases corresponding row only',
       'field_idle/C8quiet':'all expected columns received, allcopy published, all counted returns captured, no phase/ring/route/bank/reverse debt',
       'warm_reset':'quarantine without deleting accepted words/owners; pre-reserved phase-image holder retains every NOREADY suffix',
       'cold_reset':'authoritative allcopy fence and no external debt; not constructor zero as proof'},
      scheduling={
       'allocation':'four fixed slots/bank by row-first_row, no pop/compaction or automatic oldhead m_we',
       'expected_mask':'exact W11 reconstructed address within captured phase extent, not 0xff default',
       'COLLECT':'accumulate each expected rawFP32 column once; preserve source writer ordering via actual exclusion',
       'RMW':'start only after received==expected; at most one active row per bank; complete boundary stripe checked-old sibling merge',
       'publication':'do not retire any column until all6 actual data/check commits and checked publication matches',
       'RETIRE':'hold exact per-root count receipt and row lease until matched positive returned capture',
       'per_root_count_per_bank_max':4,'banks_per_group':2,
       'bank_pipeline_capacity_rows':1,
       'bank_service_II':'full selected read/check/merge/encode/commit/verify/receipt-return sequence; NEVER inferred1',
       'row_completion_wait':'actual last expected column arrival; no invented simultaneous/fullmask arrival',
       'input_alias_gate':'field X input/source reads must have exact retained read-old/exclusion contract; whole-row batching is not universal consumer-order proof',
       'unmatched_duplicate_poison':'sticky quarantine, ownership retained, no publication or rearm',
       'service_edges':None,'absolute_consumer_deadline':None},
      required_Maxwell_inputs=['RMW read/parity port ownership',
        'positive decode_old/merge_encode/commit/checked_publication stage cuts',
        'source-bound stage II and returned-count seat/crossing bounds',
        'minimum group codec/control slot, physical loads and routing',
        'actual spine/adapter/core/consumer domain and next consumer bound'],
      RTL_admission=False,RTL_written=False,jobs_launched=False)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source-root',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();m=prepare(a.source_root);a.out.mkdir(parents=True,exist_ok=False)
    (a.out/'model.json').write_text(json.dumps(m,sort_keys=True,indent=2)+'\n')
    print(json.dumps({'coded_FF':m['state_total_coded_FF'],'cost':m['cost'],'ABI':m['ABI']},indent=2))

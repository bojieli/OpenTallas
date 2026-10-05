#!/usr/bin/env python3
"""Selected CODE-only paired leaf binding; no whole array or storage adoption."""
import argparse,hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];SOURCE='a59187cd5293f7003f5bd5f2468d8bea6ce9e86c'
def build():
    paths=['rtl/hbm_accel/service/ot_hbm_accel_owned_crossing.sv','physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v','rtl/hdc/ot_qwen_rom_tile_w12.sv','rtl/test/qwen_rom_runtime/qwen_hbmacc_rt_w12.cpp','rtl/model_ready_hbm_r14/ot_hbm_r14_pkg.sv','rtl/hbm_accel/qwen/payload/ot_qwen_hbm_code_payload_pair.sv','rtl/test/qwen_rom_runtime/ot_qwen_hbmacc_rt_die_w12.sv','tools/qwen_hbmacc_rt_token_w12.py']
    pins={p:hashlib.sha256(subprocess.check_output(['git','show',f'{SOURCE}:{p}'],cwd=ROOT)).hexdigest() for p in paths}
    return dict(source_commit=SOURCE,source_pins=pins,default_enabled=False,adopted=False,
      scope='ONE selected CODE leaf columns0/1 only, no KV expansion, no installed whole array or fulltoken',
      source=dict(tile=0,paired_columns=2,data_bits=256,source_word_range=[0,512],
        source_bytes='(sourceword*6144+tile*4+2*pair)*16;32B takes actual8U32 image words',
        install='actual source installer packs only these two unchanged columns per word into a contiguous two-sector-per-row span; base/stack comes from real allocator, not an assumed live aperture',
        sector='returned id.sector already includes physical beat; never add beat'),
      destination=dict(row_bits=13,column_bits=12,columns=[0,1],capacity_rows=4496,
        paired_payload_bytes=2*4496*32,active_selected_source_rows=512,
        macro='ot_sram_1r1w_1024x256_m2_r2c2',macro_count=20,bank='row[12:10]',macro_row='row[9:0]',
        macro_body_mm2_proxy=0.1620578664,read_mux_cell_um2_estimate=4*2*256*4,
        write_decoder_cell_um2_estimate=2*5*3*4,read_capture_ff_bits=936,
        read_capture_body_um2=936*.2916,
        read_binding='actual virtual24 address selects unique seg_base/len/kind; checked installed segment ordinal/base/len/sidx/kind maps physicalrow=firstrow+virtual-base. Resident sidx0 is NOT allocator index. All five virtual banks supported only with matching installed grant. CODE private kind0 explicit from programkind1/2. Two-edge SRAM/protected response + delayed bankselect, MEM_EXTRA remains separate original capture.',
        installed_array_macro_count=None,SSFF_closed=False),
      span_translation=dict(physical_span='stack2, first_sector34, rows14<=4496, first_row13, first_column12==0, op64,phase32,rank7; immutable during delivery/read leases',
        byte_order='private source installer packs two unchanged32B pair-column sectors per source word; delta=returnedsector-firstsector,row=firstrow+(delta>>1),col=delta[0]',
        required_real_owner='expected identity192 supplied by actual hardware issuer/tag owner, exact comparison, not Python certified callback',
        positive_compare_cell_um2_estimate=(192+34+13+12)*4,shift_add_decode_cell_um2_estimate=13*4+14*4,
        mapper_ff_bits=1,mapper_register_body_um2=.2916,extra_payload_queue_entries=0),
      CDC=dict(module='ot_hbm_accel_owned_crossing',service_period_ps=1024,core_period_ps=833.333,
        original_owned_bits=465,forward_coded_bits=576,reverse_coded_bits=288,two_entry_coded_storage_bits=2*(576+288),
        storage_body_um2_proxy=2*(576+288)*.2916,codec_seals_sync_cost='existing crossing source counted, not zero; actual source netlist footprint from family context',
        ir='service release only decoded matched reverse ACK',ore='CORE private SRAM visible receipt, not CDC acceptance/rd_freed'),
      API=dict(destination_packet_bits=593,packet='operation64,phase32,globalrank7,row13,column12,owned465',
        private_visible_key_bits=337,visible_key='operation64,phase32,globalrank7,row13,column12,identity192,physical_tag12,beat5',
        owned_ready='only exact private-visible-key match; wrong metadata/identity holds and faults',
        global_publication='Sagan owns fullword3072sector completeness and destination leases; private leaf receipt alone not A_count'),
      latency='original crossing forward/reverse phase-dependent cycles + actual w_ce capture/readvisibility + actual leaf2edges (delta+1) + separate MEM_EXTRA; no free admission/clockheadline, price against Hubble+15287edge control sensitivity',
      whole_storage=dict(code_source_bytes=441974784,code_coded_bytes=497221632,code_padded_bytes=566231040,conditional_pair_replicas=1536,conditional_code_macros=30720,scale_u32=50112,scale_bytes=50112*4,CROM_u32=541953,CROM_bytes=541953*4,VM_u32=177808,VM_bytes=177808*4,KV_u32=8388608,KV_bytes=8388608*4,extra_bytes_outside_code=(50112+541953+177808+8388608)*4,installed_whole_array=False,capacity='conditional Erdos20macro replication only, not Kant alternative3072sidecar proposal or installed physical fit; allocator/port/mux/clock/PG costs remain positive and require selected wholemodel'),
      source_segment_price=dict(NSEG=8,parallel_range_checks=8,compare_add_mux_gate_equivalents_estimate=8*(24*4+25*4+2*4)+32*4+24*4+13*4,gate_um2_proxy=4,source_descriptor_bits=3+24+24+32+2+13+14+34+2,descriptor_owner='existing hardware issuer held pins, no new namespace/software grant',read_response_extra_edges=1,extra_read_alignment='peer Erdos prices bankvalid/hold and MEM_EXTRA, not free'),
      hooks='Erdos writes leaf+readbinding; Sagan installs checked source span/identity/striping/globalpublication; Kant prices ARRAY only after selected primitive/current footprints')
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);a=ap.parse_args();p=Path(a.out);p.mkdir(parents=True,exist_ok=True);(p/'model.json').write_text(json.dumps(build(),indent=2)+'\n');print('selected paired CODE leaf20macros, not wholeARRAY')
if __name__=='__main__':main()

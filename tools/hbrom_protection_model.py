#!/usr/bin/env python3
"""Price SRAM protection without changing engine RTL. NC1 shape, actual ingress mapping."""
import argparse, hashlib, json, math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def build():
    leaves=[]
    for sp in range(4):
        groups={}
        for b in range(788):
            f=(sp*2+b//266)*266+b%266 if b<532 else 8*266+sp*256+b-532
            groups.setdefault(f//2048,[]).append({'leaf_bit':b,'ingress_bit':f%2048})
        codewords=[]
        for beat,items in sorted(groups.items()):
            for i in range(0,len(items),64):
                codewords.append({'beat':beat,'code_offset':len(codewords)*72,'bits':items[i:i+64],'zero_pad':64-len(items[i:i+64])})
        assert len(codewords)*72<=1024
        assert sorted(x['leaf_bit'] for c in codewords for x in c['bits'])==list(range(788))
        for cw in codewords:
            runs=[]
            for bit in cw.pop('bits'):
                if runs and bit['leaf_bit']==runs[-1]['leaf_start']+runs[-1]['length'] and bit['ingress_bit']==runs[-1]['ingress_start']+runs[-1]['length']:
                    runs[-1]['length']+=1
                else:
                    runs.append({'leaf_start':bit['leaf_bit'],'ingress_start':bit['ingress_bit'],'length':1})
            cw['runs']=runs
        leaves.append({'leaf':sp,'codewords':codewords,'encoded_bits':72*len(codewords),'macro_count':4})
    n=sum(len(x['codewords']) for x in leaves)
    # Explicit unshared XOR implementation; decoder correction uses per-position compares.
    data_positions=[p for p in range(1,72) if p&(p-1)]
    enc_xor=sum(sum(bool(p&(1<<k)) for p in data_positions)-1 for k in range(7))+70
    dec_xor=sum(sum(bool(p&(1<<k)) for p in range(1,72))-1 for k in range(7))+71+64
    sources=['rtl/hbm_accel/sm/ot_hbm_accel_sm_v.sv','rtl/hbm_accel/epilogue/ot_hbm_accel_bulk_copy.sv','rtl/gpu/ot_gpu_rf_service.sv','rtl/gpu/ot_gpu_scratch_service.sv','rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv','results/floorplan/qwen_o4_unit_areas.json']
    banks={'activation':{'encoders':n,'decoders':n,'codewords':n,'extra_macro_count':0},'ring':{'encoders':17,'decoders':17,'codewords':17,'extra_macro_count':0},'shared_rf':{'encoders':64,'decoders':128,'codewords':128,'extra_macro_count':16},'shared_scratch':{'encoders':8,'decoders':8,'codewords':8,'extra_macro_count':1}}
    for v in banks.values():
        v['xor2_count_unshared']=v['encoders']*enc_xor+v['decoders']*dec_xor
        v['decode_7bit_equality_count']=v['decoders']*64
        v['encoder_pipeline_bits']=v['encoders']*(64+7+72)
        v['decoder_pipeline_bits']=v['decoders']*(72+8+66)
        v['pipeline_flop_area_mm2']=(v['encoder_pipeline_bits']+v['decoder_pipeline_bits'])*.2916/1e6
        v['logic_area_allowance_mm2']=((v['xor2_count_unshared']+v['decode_7bit_equality_count']*7)*.3)/1e6
        v['area_allowance_packed_50pct_mm2']=2*(v['pipeline_flop_area_mm2']+v['logic_area_allowance_mm2'])
    return {'schema':'hbrom.protection-plan.v1','status':'PRICED_PROPOSAL_NOT_IMPLEMENTED_OR_QUALIFIED','shape':{'NC':1,'SUB':4,'LBS':2,'LSB':16,'XD':128,'IL':8},'sources_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in sources},'activation_layout':leaves,'codec':{'source':'ot_gpu_w6_secded_pkg encode64/decode64','code':'extended Hamming(72,64) SECDED','single_bit':'correct data before use','double_bit':'sticky fault and suppress issue/results; do not silently use corrupted data','per_encoder_xor2_unshared':enc_xor,'per_decoder_xor2_unshared':dec_xor,'partial_write':'Codewords contain only bits from one independently written 2048-bit ingress beat. Encode padded word; mask all72 bits atomically. Macros may split codewords but update on same edge. No RMW or assembly; legal out-of-order/repeated beat writes retained.'},'blocks':banks,'cycles':{'activation_write_extra':2,'activation_read_extra':2,'ring_response_to_committed_extra':2,'ring_read_to_valid_extra':2,'rf_read_extra':2,'rf_write_ack_extra':2,'scratch_read_extra':2,'scratch_write_ack_extra':2,'activation_steady_Bpc':394,'ring_steady_Bpc':136,'throughput_condition':'parallel codec per word, all stages pipelined; control,weight,tag delayed same2 cycles with activation; next phase slot timing must remain aligned. SS/FF measurement can reject stage budget.'},'area_basis':{'dff_um2':.2916,'xor2_and_twoinput_gate_allowance_um2':.3,'allowance_status':'Explicit uncharacterized gate allowance, not measured area or guaranteed upper bound. Decoder equality priced7 gates/position. Control fault gates, buffers, CTS and metadata seal not included; do not claim complete signoff area.'},'integration':[{'file':'rtl/hbm_accel/sm/ot_hbm_accel_sm_v.sv','module':'ot_hbm_accel_smv_leaf','seams':['Replace g_wb wd_n/wd_m/wm_m mapping by beat-aligned encode map. Delay wa/we by2 codec stages.','Keep four u_x macros. Decode xrd into original788bit ix layout; add2 matching control and weight stages at E4.','Propagate decoder UE to leaf gf and suppress affected validity. Keep data fault latch sticky.','Top start readiness must include write-retirement fence; delay original accepted start by2 and reject invalid or incompletely written row.']},{'file':'rtl/hbm_accel/epilogue/ot_hbm_accel_bulk_copy.sv','module':'ot_hbm_accel_bulk_copy','seams':['Encode rsp_data into1224b; delay rsp_v AND rsp_tag by2 before ALL full bitmap/headfull/credit return updates. Width1280 physical unaffected.','Capture codeword then pipeline decode2 stages before output queue valid. Grow queue credit accounting by2 in-flight stages; preserve at least3+2=5 slots.','Validate return slot allocated/not already full and transaction identity before accepting; freeze on UE/identity mismatch.','Protect full bitmap, alloc/cons/used/outstanding and descriptor state; existing raw control is not exempt.']},{'file':'rtl/gpu/ot_gpu_rf_service.sv','module':'ot_gpu_rf_service','seams':['Encode4096bit write once to4608b, mirror both operand copies,18 width banks rather than16 perpage.','Keep4page select per copy; decode128 codewords before rsp_valid.','Hold lease until decoded response consumption; ack after both encoded writes commit.']},{'file':'rtl/gpu/ot_gpu_scratch_service.sv','module':'ot_gpu_scratch_service','seams':['Encode512b to576b across3x256 macros; decode before done; preserve single outstanding lease.']}],'remaining_mandatory_gates':['Mutable control protection: duplicate sealed control image or SECDED state, including x write/valid bitmap, descriptors, ring ownership. Needs exact state inventory/area before qualification.','Read pipeline poison and no stale result after fault.','Fault inject every data+check bit; prove single correction and all double-bit detection; pointer/tag fault cases.','All partial writes including leaf3 split and repeated/out-of-order groups compared against original raw layout.','Full AR shape exactness and stalled finite streams; source-pinned synthesis and contextual SS/FF.']}
def main():
 p=argparse.ArgumentParser();p.add_argument('--output',default='results/uarch/hbrom/protection_plan.json');a=p.parse_args();out=ROOT/a.output;out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(build(),indent=2)+'\n')
if __name__=='__main__':main()

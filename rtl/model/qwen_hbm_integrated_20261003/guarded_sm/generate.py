"""Literal guarded copy of owned W4fullSM; no arithmetic modification.

Default OPT_CONTEXT delegates to byte-identical original module. Opt-in actual
RFports and controller handshakes honor Popperr2 permits. Model precedes source.
"""
import hashlib,importlib.util,json
from pathlib import Path
D=Path(__file__).resolve().parent;ROOT=D.parents[3]
BASE=D.parent
ORIGINAL=ROOT/'results/uarch/Euclid_W4_RFACK_identity_contract_20261003/selfcontained-peer-r10/design/ot_gpu_full_sm_service.sv'

INPUTS=dict(simd_context_permit=1,rd_permit=1,wr_permit=1,rf_rsp_allow=1,rf_ack_allow=1,
 simd_binding_valid=1,simd_KV_related=1,simd_source_identity=64,simd_key=20,
 host_rd_binding_valid=1,host_rd_KV_related=1,host_rd_identity=64,host_rd_key=20,
 host_wr_binding_valid=1,host_wr_KV_related=1,host_wr_identity=64,host_wr_key=20,
 host_rd_continuation_valid=1,host_wr_continuation_valid=1)
OUTPUTS=dict(rf_write_accept=1,rf_write_owner55=55,rf_ack_valid=1,rf_ack_accept=1,rf_ack_owner55=55,rf_ack_fault=1,
 rf_read_accept=1,rf_read_a=9,rf_read_b=9,rf_rsp_valid=1,rf_rsp_accept=1,
 simd_context_accept=1,simd_context_owner55=55,simd_context_retire=1,simd_retire_owner55=55,
 wr_continuation_valid=1,wr_continuation_source=1,rd_continuation_valid=1,rd_continuation_source=1,rd_context_owner55=55,
 wr_context_identity=64,wr_context_key=20,wr_context_binding_valid=1,wr_context_KV_related=1,
 rd_context_identity=64,rd_context_key=20,rd_context_binding_valid=1,rd_context_KV_related=1)


def one(s,a,b):
 if s.count(a)!=1:raise ValueError('literal source drift '+a[:60])
 return s.replace(a,b)


def main():
 model=json.loads((D/'model.json').read_text());raw=ORIGINAL.read_text()
 if hashlib.sha256(ORIGINAL.read_bytes()).hexdigest()!=model['source_sha256'][str(ORIGINAL.relative_to(ROOT))]:raise ValueError('unpriced source')
 raw=raw[:raw.index('`timescale 1ns/1ps\n// Additive')]
 spec=importlib.util.spec_from_file_location('original_generator',BASE/'generate.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 ports=m.leaf_ports(ORIGINAL,'ot_gpu_full_sm_service')
 extras=[dict(name=n,bits=w,direction='input') for n,w in INPUTS.items()]+[dict(name=n,bits=w,direction='output') for n,w in OUTPUTS.items()]
 def decl(p):return f" {p['direction']} wire "+('' if p['bits']==1 else f"[{p['bits']-1}:0] ")+p['name']
 header=',\n'.join(decl(p) for p in ports+extras)
 s=one(raw,'module ot_gpu_full_sm_service #','module ot_gpu_full_sm_service_guarded_context #')
 s=one(s,'parameter integer ACK_ID=0)','parameter integer ACK_ID=0,parameter integer INSTANCE_ID=0)')
 pos=s.index('input wire clk,rst_n,');s=s[:pos]+',\n'.join(decl(p) for p in extras)+',\n '+s[pos:]
 # Only identity branch is selected by guarded wrapper. Do not sell original
 # ACK_ID0 as these observer/tap ports; require actual common identity ACK.
 s=one(s,'generate if(ACK_ID==0)', 'initial if(ACK_ID!=1)$fatal(1,"guarded context requires actual ACK_ID1");\ngenerate if(ACK_ID==0)')
 s=one(s,'  wire choose_simd=simd_valid &&', '  wire choose_simd=simd_valid && simd_context_permit && ctx_clean &&')
 s=one(s,'assign host_rd_ready=idle && !choose_simd && rr;', 'assign host_rd_ready=idle && !choose_simd && rr && rd_permit && ctx_clean;')
 s=one(s,'assign host_wr_ready=idle && !choose_simd && wr;', 'assign host_wr_ready=idle && !choose_simd && wr && wr_permit && ctx_clean;')
 s=one(s,'.rd_valid(state==READ || (idle && !choose_simd && host_rd_valid))', '.rd_valid((state==READ || (idle && !choose_simd && host_rd_valid)) && rd_permit && ctx_clean)')
 s=one(s,'.wr_valid(state==WRITE || (idle && !choose_simd && host_wr_valid))', '.wr_valid((state==WRITE || (idle && !choose_simd && host_wr_valid)) && wr_permit && ctx_clean)')
 s=one(s,'.rsp_ready(state==OPERATE || (idle && host_rsp_ready))', '.rsp_ready((state==OPERATE || (idle && host_rsp_ready)) && rf_rsp_allow && ctx_clean)')
 s=one(s,'&& !identity_fault),','&& !identity_fault && rf_ack_allow && ctx_clean),')
 s=s.replace('state==OPERATE && rv','state==OPERATE && rv && rf_rsp_allow && ctx_clean')
 s=one(s,'READ: if(rr)', 'READ: if(rr && rd_permit && ctx_clean)')
 s=one(s,'OPERATE: if(rv)', 'OPERATE: if(rv && rf_rsp_allow && ctx_clean)')
 s=one(s,'WRITE: if(wr)', 'WRITE: if(wr && wr_permit && ctx_clean)')
 s=one(s,'ACK: if(wack && !identity_fault', 'ACK: if(wack && rf_ack_allow && ctx_clean && !identity_fault')
 s=one(s,'assign identity_fault=identity_mismatch_fault', 'assign identity_fault=!ctx_clean || identity_mismatch_fault')
 taps='''
  wire [85:0] ctx;
  wire ctx_clean;
  wire ctx_retire=state==DONE && simd_done_ready;
  ot_gpu_qwen_guard_context_record #(.BITS(86),.INDEX(INSTANCE_ID)) context_record(
   .clk(clk),.por_n(rst_n),.write_enable(sg || ctx_retire),
   .next_data(ctx_retire ? 86'b0 : {simd_binding_valid,simd_KV_related,simd_key,simd_source_identity}),.data(ctx),.clean(ctx_clean));
  assign rf_read_accept=(state==READ || (idle && !choose_simd && host_rd_valid)) && rd_permit && ctx_clean && rr;
  assign rf_write_accept=(state==WRITE || (idle && !choose_simd && host_wr_valid)) && wr_permit && ctx_clean && wr;
  assign rf_read_a=idle ? host_a : a_q;assign rf_read_b=idle ? host_b : b_q;
  assign rf_write_owner55=idle ? {host_owner,host_dst} : simd_identity[54:0];
  assign rf_ack_valid=wack;assign rf_ack_owner55={rf_ack_owner,rf_ack_slot};assign rf_ack_fault=identity_fault;
  assign rf_ack_accept=wack && (((state==ACK && SIMD_ACK_match) || (idle && host_ack_ready)) && !identity_fault && rf_ack_allow && ctx_clean);
  assign rf_rsp_valid=rv;assign rf_rsp_accept=rv && (state==OPERATE || (idle && host_rsp_ready)) && rf_rsp_allow && ctx_clean;
  assign simd_context_accept=sg;assign simd_context_owner55={simd_owner,simd_dst};
  assign simd_context_retire=ctx_retire;assign simd_retire_owner55=simd_identity[54:0];
  assign wr_continuation_valid=idle ? host_wr_continuation_valid : state==WRITE;
  assign wr_continuation_source=!idle;
  assign rd_continuation_valid=idle ? host_rd_continuation_valid : state==READ;
  assign rd_continuation_source=!idle;
  assign rd_context_owner55=idle ? {host_owner,host_dst} : simd_identity[54:0];
  assign wr_context_identity=idle ? host_wr_identity : ctx[63:0];assign wr_context_key=idle ? host_wr_key : ctx[83:64];
  assign wr_context_KV_related=idle ? host_wr_KV_related : ctx[84];assign wr_context_binding_valid=idle ? host_wr_binding_valid : ctx[85];
  assign rd_context_identity=idle ? host_rd_identity : ctx[63:0];assign rd_context_key=idle ? host_rd_key : ctx[83:64];
  assign rd_context_KV_related=idle ? host_rd_KV_related : ctx[84];assign rd_context_binding_valid=idle ? host_rd_binding_valid : ctx[85];
'''
 s=one(s,'  wire sg=simd_valid && simd_ready;', '  wire sg=simd_valid && simd_ready;\n'+taps)
 zeros='\n'.join('assign '+n+"='0;" for n in OUTPUTS)
 s=one(s,' end else begin:g_disabled', ' end else begin:g_disabled\n'+zeros)
 wrapper='`timescale 1ps/1ps\nmodule ot_gpu_full_sm_service_guarded #(parameter integer ENABLE=0,ACK_ID=0,INSTANCE_ID=0,parameter bit OPT_CONTEXT=0)(\n'+header+'\n);\n'
 old_conn=',\n'.join('.'+p['name']+'('+p['name']+')' for p in ports)
 ctx_conn=',\n'.join('.'+p['name']+'('+p['name']+')' for p in ports+extras)
 wrapper+='generate if(!OPT_CONTEXT)begin:original\n'+zeros+'\not_gpu_full_sm_service #(.ENABLE(ENABLE),.ACK_ID(ACK_ID)) baseline('+old_conn+');\n'
 wrapper+='end else begin:guarded\not_gpu_full_sm_service_guarded_context #(.ENABLE(ENABLE),.ACK_ID(ACK_ID),.INSTANCE_ID(INSTANCE_ID)) actual('+ctx_conn+');\nend endgenerate\nendmodule\n'
 record=(BASE/'issuer/ot_gpu_qwen_full_issuer.sv').read_text()
 record=record[record.index('module ot_gpu_qwen_issuer_record'):record.index('module ot_gpu_qwen_full_issuer_sm')]
 record=record.replace('ot_gpu_qwen_issuer_record','ot_gpu_qwen_guard_context_record').replace('BITS=301','BITS=86').replace("3'd7","3'd6")
 (D/'ot_gpu_full_sm_service_guarded.sv').write_text(wrapper+s+'\n'+record)

if __name__=='__main__':main()

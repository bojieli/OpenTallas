"""Bound-input/range-publication successor of pinned issuer r1.

Frame retirement is not source-lease retirement. The allocator alone owns
published RF leases and actual all-page ACK aggregation/last-consumer debt.
"""
import hashlib,json
from pathlib import Path
D=Path(__file__).resolve().parent;P=D.parent

def main():
 raw=(P/'ot_gpu_qwen_full_issuer.sv').read_text()
 s=raw[raw.index('module ot_gpu_qwen_full_issuer_sm'):]
 s=s.replace('ot_gpu_qwen_full_issuer_sm','ot_gpu_qwen_full_issuer_sm_r2').replace('module ot_gpu_qwen_full_issuer #','module ot_gpu_qwen_full_issuer_r2 #')
 # Keep the proven actual whole-identity/ready logic and extend stored handles.
 s=s.replace('producer_result','producer_visible').replace('rf_ack','rf_range_ack').replace('retire_valid','frame_retire_valid').replace('retire_ready','frame_retire_ready').replace('retire_tuple','frame_retire_tuple').replace('retire_owner','frame_retire_owner')
 for a,b in [('state[300]','state[341]'),('state[299]','state[338]'),('state[298]','state[337]'),('state[297]','state[336]'),('state[296]','state[335]'),('state[295]','state[334]'),('state[294]','state[333]'),('state[293:55]','state[332:94]'),('state[54:0]','state[93:39]')]:s=s.replace(a,b)
 s=s.replace('[300:0]','[341:0]').replace('.BITS(301)','.BITS(342)')
 s=s.replace("{7'b0000001,issue_tuple,issue_owner}","{9'b000000001,issue_tuple,issue_owner,inputs_bound_mask,issue_output_page_mask}")
 s=s.replace('wire legal_issue=','wire legal_issue=inputs_bound_valid && inputs_bound_tuple==issue_tuple && issue_output_page_mask!=0 &&')
 s=s.replace('wire ack_match=rf_range_ack_owner==held_owner;','wire ack_match=rf_range_ack_owner==held_owner && rf_range_ack_tuple==held_tuple && rf_range_ack_page_mask==state[31:0];')
 s=s.replace('assign frame_retire_valid=active && !unexpected && busy && state[336] && state[337] && state[338];',
  'assign frame_retire_valid=active && !unexpected && busy && state[336] && state[337] && state[338] && state[339] && state[340];')
 marker=' assign publish_tuple=held_tuple;'
 inject=''' assign inputs_bound_ready=issue_valid && issue_ready;
 assign input_terminal_valid=active && !unexpected && busy && state[336] && !state[339];
 assign input_reverse_valid=active && !unexpected && busy && state[337] && !state[340];
 assign input_terminal_tuple=held_tuple;assign input_reverse_tuple=held_tuple;
 assign input_terminal_mask=state[38:32];assign input_reverse_mask=state[38:32];
 assign publish_page_mask=state[31:0];
'''
 s=s.replace(marker,inject+marker)
 s=s.replace('    if(publish_valid && publish_ready)', '    if(input_terminal_valid && input_terminal_ready)next_state[339]=1;\n    if(input_reverse_valid && input_reverse_ready)next_state[340]=1;\n    if(publish_valid && publish_ready)')
 # New physical ports, separately packed for each of64realSM contexts.
 leaf=''' input wire inputs_bound_valid,
 input wire [238:0] inputs_bound_tuple,
 input wire [6:0] inputs_bound_mask,
 input wire [31:0] issue_output_page_mask,
 output wire inputs_bound_ready,
 input wire [238:0] rf_range_ack_tuple,
 input wire [31:0] rf_range_ack_page_mask,
 output wire [31:0] publish_page_mask,
 output wire input_terminal_valid,input_reverse_valid,
 input wire input_terminal_ready,input_reverse_ready,
 output wire [238:0] input_terminal_tuple,input_reverse_tuple,
 output wire [6:0] input_terminal_mask,input_reverse_mask,
'''
 wrapper=leaf.replace('input wire inputs_bound_valid','input wire [63:0] inputs_bound_valid').replace('output wire inputs_bound_ready','output wire [63:0] inputs_bound_ready')
 wrapper=wrapper.replace('[238:0]','[64*239-1:0]').replace('[6:0]','[64*7-1:0]').replace('[31:0]','[64*32-1:0]')
 wrapper=wrapper.replace('output wire input_terminal_valid','output wire [63:0] input_terminal_valid').replace('input wire input_terminal_ready','input wire [63:0] input_terminal_ready')
 # Exactly one insertion in each distinct header, not inner signals.
 idx=s.index(' input wire clk,por_n,run_enable,session_valid,');s=s[:idx]+leaf+s[idx:]
 idx=s.index(' input wire clk,por_n,run_enable,\n');s=s[:idx]+wrapper+s[idx:]
 connect=[]
 for n,w in [('inputs_bound_valid',1),('inputs_bound_tuple',239),('inputs_bound_mask',7),('issue_output_page_mask',32),('inputs_bound_ready',1),('rf_range_ack_tuple',239),('rf_range_ack_page_mask',32),('publish_page_mask',32),('input_terminal_valid',1),('input_reverse_valid',1),('input_terminal_ready',1),('input_reverse_ready',1),('input_terminal_tuple',239),('input_reverse_tuple',239),('input_terminal_mask',7),('input_reverse_mask',7)]:
  connect.append('.'+n+'('+n+('[sm]' if w==1 else f'[sm*{w}+:{w}]')+')')
 old='leaf(\n   .clk(clk)';new='leaf(\n   '+',\n   '.join(connect)+',\n   .clk(clk)'
 if s.count(old)!=1:raise ValueError('r1 source instance changed')
 s=s.replace(old,new)
 # R1 remains byte-identical; record utility comes from originalsourcefile.
 text='`timescale 1ps/1ps\n// R2 FRAMEONLY retirement. Published sourcelease stays with actual allocator.\n'+s
 (D/'ot_gpu_qwen_full_issuer_r2.sv').write_text(text)

if __name__=='__main__':main()

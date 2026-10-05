#!/usr/bin/env python3
"""Exact source slices of the DEC_LA sequencer/decode; arithmetic stays outside."""
import argparse,hashlib,json,re
from pathlib import Path
import qwen_rom_core_dec_emit_w12 as E
ROOT=Path(__file__).resolve().parents[1]

def inputs():
    return [Path(E.__file__),Path(E.V.__file__),Path(E.V.E.__file__),E.V.E.CORE,E.V.E.CORE.parent/'ot_hdc_isa.svh']

def model():
    baseline=E.V.emit(E.V.E.CORE.read_text())
    body=baseline[baseline.index(E.DEC_START)+len(E.DEC_START):baseline.index(E.DEC_END)]
    dynsel=sorted(set(re.findall(r'`DYNS\(`F\((\w+)\)\)',body)))
    return dict(schema='qwen.rom.core_takeover.v1',candidate='preserved Claude WIP, DEC_LA=1',
      source_pins={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs()},
      actual_screen=dict(host='ot-epyc1tb',run='core_d1v0g',SS_setup_ps=-64.189598,clock_ps=833,uncertainty_ps=60,
                         path='d_chase_n[2] -> chase/issue/load enable fanout -> run_val[7]',physical_signoff=False),
      change='read predecoded chase count from held NEXT FIFO entry; use registered DYN selects; retained startup E1/E2/E3 tables ready before earliest E4 push',
      instruction_semantics='unaltered fields at tested 8K positions/offsets; invalid split, held FIFO, ready/idle/barrier, actual chunked argmax END/reset; generic NW wrap not qualified',
      state=dict(decoded_entry_bits=878,entry_count=8,decoded_FIFO_bits=878*8+3*8,staged_instruction_bits=1024,
                 dyn_selector_count=len(dynsel),dyn_selection_regs_bits=len(dynsel)*24,
                 incremental_vs_previous_CLAUDE_screen_bits=len(dynsel)*(24-8)-16,
                 storage_upper_bound_basis='declared registers before constant pruning; full cost includes tables/kept adders/mux/CTS and must be measured'),
      latency=dict(added_edges_expected=0,first_push_earliest_edge=4,tables_ready_edge=3,
                   per_instruction_added_edges_expected=0,token_extra_ns_expected=0,measured_for_this_WIP=False),
      ports=dict(new_memory_bytes_per_cycle=0,new_external_bits=0,MACs_per_cycle=0,
                 unchanged_program_read_bits=1024,internal_decoded_boundary_bits=878),
      routing=dict(new_external_tracks=0,FIFO_read_mux='8:1 per field, 3-bit held la_nx',
                   local_enable_fanout='LOAD control omits16 chase count sinks; field output loads retained',
                   slot_fit=False,channel_capacity=None),
      replicas='one core per retained TP rank, four ranks; no new die/engine',
      clock=dict(period_ps=833,SS_setup_uncertainty_ps=60,FF_hold_uncertainty_ps=25,qualified=False),
      adoption=False,default_DEC_LA=0,baseline_P0_edited=False)

def component(bounded=False,chaseq=False,counter_la=False,am_commit=False):
    text=E.emit(E.V.E.CORE.read_text())
    if bounded or chaseq or counter_la or am_commit:
        from qwen_rom_core_dec_bound_emit_w12 import apply
        text=apply(text)
    if chaseq or counter_la or am_commit:
        from qwen_rom_core_dec_chaseq_emit_w12 import apply
        text=apply(text)
    if counter_la or am_commit:
        from qwen_rom_core_dec_counter_emit_w12 import apply
        text=apply(text)
    if am_commit:
        from qwen_rom_core_dec_commit_emit_w12 import apply
        text=apply(text)
    seq=text[text.index('    localparam integer LW'):text.index('    always @(posedge clk or negedge rst_n) begin\n        if (!rst_n) begin kvd_v')]
    seq=seq.replace('    wire       me_ready, me_idle, su_ready, su_idle;','')
    seq=seq.replace('    wire [15:0] su_progress, me_progress, su_rows;','')
    for declaration in ('    wire [NW-1:0] am_idx;\n','    wire [31:0] am_val;\n','    wire       am_any;\n'):
        assert seq.count(declaration)==1
        seq=seq.replace(declaration,'')
    argmax=text[text.index('    // The chunked weight program'):text.index('    // DYN offsets derived once per token.')]
    dyn=text[text.index('    // DYN offsets derived once per token.'):text.index('    // -- units')]
    baseline=E.V.emit(E.V.E.CORE.read_text())
    body=baseline[baseline.index(E.DEC_START)+len(E.DEC_START):baseline.index(E.DEC_END)]
    fields=[name for name,_ in E._statements(body)]
    helpers=text[text.index('// a > b on 32-bit unsigned keys'):]
    header='''module decode_component #(parameter DEC_LA=0, VPOS=0, DEC_LA_BOUND=0, DEC_LA_CHASE_Q=0, DEC_LA_COUNT_LA=0, DEC_LA_AM_COMMIT=0)(
input clk,rst_n,start, input [17:0] token,pos,
input me_ready,me_idle,su_ready,su_idle,
input [15:0] me_progress,su_progress,su_rows,
input [1023:0] prog_q,
input [17:0] am_idx,input [31:0] am_val,input am_any,
output reg prog_re,output reg [11:0] prog_addr,
output reg done,output reg [31:0] cycles,
output reg [17:0] next_token,output reg [31:0] next_val,
output [877:0] decoded,output accepted,output invalid_at_load);
localparam AW=24,NW=18,PAW=12,W=16,IL=1,G=6144,HID=4096,HD=128,HALF=64,
INSTR_BITS=1024,KV_HBM=1,W_HBM=1,KV_VEC_WRITE_BRIDGE=1,QWEN_FULLSHAPE=1;
`include "ot_hdc_isa.svh"
assign me_en=1;
wire kv_ok=1,kvd_v=0,w_ok=1,wd_v=0,emb_ok=1,kv_write_drained=1;
wire [15:0] kv_we=0; wire kv_write_flush;
assign accepted=issue; assign invalid_at_load=dyn_tiles_bad_instruction;
'''
    if am_commit:
        seq=seq.replace('    wire me_en;\n','')
        header=header.replace('input me_ready,me_idle,su_ready,su_idle,', 'input me_ready,me_idle,su_ready,su_idle,\ninput me_en,kv_ok,w_ok,emb_ok,kv_write_drained,')
        header=header.replace('assign me_en=1;\n','').replace('wire kv_ok=1,kvd_v=0,w_ok=1,wd_v=0,emb_ok=1,kv_write_drained=1;', 'wire kvd_v=0,wd_v=0;')
    return (header+seq+argmax+dyn+'\nassign decoded={'+','.join(fields)+'};\nendmodule\n'+helpers).replace('`include "ot_hdc_isa.svh"',(E.V.E.CORE.parent/'ot_hdc_isa.svh').read_text())

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--model',action='store_true');p.add_argument('--out',type=Path);p.add_argument('--bounded',action='store_true');p.add_argument('--chaseq',action='store_true');p.add_argument('--counter-la',action='store_true');p.add_argument('--am-commit',action='store_true');a=p.parse_args()
    if a.model:print(json.dumps(model(),indent=2,sort_keys=True))
    else:a.out.write_text(component(a.bounded,a.chaseq,a.counter_la,a.am_commit))

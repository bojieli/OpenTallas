#!/usr/bin/env python3
"""Emit the opt-in full-shape die stage controller and immutable ISA templates.

Run on an admitted compute host. No checkpoint tensors are opened.
The historical sequencer master is an input and is never edited.
"""
import os
os.environ['QWEN_O4_TP'] = '4'
os.environ['HDC_SU_WIDTH'] = '64'
os.environ['QWEN_O4_AR_WORDS'] = '256'
import argparse
import ast
import hashlib
import json
import re
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import hdc_program as P
import hdc_qwen_fullshape_program_w12 as FP
import hdc_qwen_fullshape_isa_w12 as QI
import hdc_isa as I
from hdc_qwen_fullshape_placement_w12 import matrix, placement
from qwen_system.ctl_golden import stage_table, stab_bits

# Execute the exact shape-only golden function without importing checkpoint IO packages.
_binding_ast = ast.parse((ROOT / 'tools/qwen_o4_fulltoken_binding_w12.py').read_text())
_shape_fn = next(n for n in _binding_ast.body if isinstance(n, ast.FunctionDef) and n.name == 'compact_rows')
_shape_globals = dict(TP=4,GROUPS=6144,matrix=matrix,I=I,PINNED={})
exec(compile(ast.Module(body=[_shape_fn],type_ignores=[]),str(ROOT / 'tools/qwen_o4_fulltoken_binding_w12.py'),'exec'),_shape_globals)
compact_rows = _shape_globals['compact_rows']
HEAD_ROWS = 151936 // 4
_rope = 2 * 4096 + (32 // 4 + 8 // 4) * 128 + 1
POST_SCALE_BASES = (_rope + FP.TMAX * 64, _rope + FP.TMAX * 64 + 4096)


def emit(out):
    out.mkdir(parents=True, exist_ok=True)
    rows = placement()['matrices_per_die'][:4]
    lay = FP.LayerZero(placement(), 0)
    lay.emb_word = 0
    with FP.program_geometry(FP.vm_map()[0]):
        eprog = P.build_program(lay, layers=[], embed=True, head=False, scale_bases=True)
    ew, ed = QI.encode_segments(eprog)
    layer = FP.profile(0, post_scale_bases=POST_SCALE_BASES)
    hr = matrix(0, 'lm_head', HEAD_ROWS, 4096)
    hr['scale_base'] = 0
    heads = [FP.profile_lm_head(d, hr, 0) for d in range(4)]
    lw = [int(x, 16) for x in layer['program_hex']]
    ld = [int(x, 16) for x in layer['descriptor_hex']]
    hw = [int(x, 16) for x in heads[0]['program_hex']]
    hd = [[int(x, 16) for x in h['descriptor_hex']] for h in heads]
    assert all(h['program_hex'] == heads[0]['program_hex'] for h in heads)
    print('Measured template lengths:',[len(ew),len(lw),len(hw)],'descriptor lengths:',[len(ed),len(ld),len(hd[0])],flush=True)
    assert len(ew) + len(lw) + len(hw) <= 64
    assert len(ed) + len(ld) + len(hd[0]) <= 8
    code_words = max(r['end'] for r in rows)
    scale_words = sum(r['rounds'] * (6144 // r['split']) * I.INTERLEAVE for r in rows)
    print('Measured compact image words:',code_words,scale_words,flush=True)
    # The default physical program uses its original ROM allocation. It is deliberately
    # distinct from compact_rows; adopting compact packing requires a native image manifest.
    code_capacity,scale_capacity=5*4096,48*4096
    head_code_words=hr['words']
    head_scale_words=hr['rounds']*(6144//hr['split'])*I.INTERLEAVE
    assert 36*code_words+head_code_words <= code_capacity
    assert 36*scale_words+head_scale_words <= scale_capacity
    print('Physical image totals:',36*code_words+head_code_words,36*scale_words+head_scale_words,flush=True)
    words = list(ew) + lw + hw
    offsets = [0, len(ew), len(ew) + len(lw)]
    stages = stage_table()
    # This new opt-in physical vehicle uses the actual TP4 image geometry. The historical
    # controller golden retains its old padded strides and committed evidence unchanged.
    for i,e in enumerate(stages):
        layer_index=0 if i==0 else 36 if i==37 else i-1
        e['code']=layer_index*code_words
        e['scale']=layer_index*scale_words
    rom = ['// Generated immutable TP4/G6144 templates; local descriptor program bases are preserved.',
           f"localparam [2127:0] SYS_STAB = 2128'h{stab_bits(stages):0532x};",
           'function automatic [1023:0] sys_program(input [1:0] bank, input [11:0] addr);',
           'reg [12:0] index; begin',
           f"index = {{1'b0,addr}} + (bank == 0 ? 13'd{offsets[0]} : bank == 1 ? 13'd{offsets[1]} : 13'd{offsets[2]});",
           "sys_program = 0;",
           f"if ((bank == 0 && addr < {len(ew)}) || (bank == 1 && addr < {len(lw)}) || (bank == 2 && addr < {len(hw)})) case (index)"]
    rom += [f"13'd{i}: sys_program = 1024'h{w:0256x};" for i, w in enumerate(words)]
    rom += ['default: sys_program = 0; endcase', 'end endfunction',
            'function automatic [63:0] sys_descriptor(input [1:0] bank, input [5:0] addr);',
            "begin sys_descriptor = 0; case ({bank,addr})"]
    for bank, ds in enumerate([list(ed), ld, hd[0]]):
        for i, w in enumerate(ds):
            if bank == 2:
                expr = "(DIE_RANK == 0 ? 64'h%016x : DIE_RANK == 1 ? 64'h%016x : DIE_RANK == 2 ? 64'h%016x : 64'h%016x)" % tuple(h[i] for h in hd)
            else:
                expr = f"64'h{w:016x}"
            rom.append(f"8'd{bank*64+i}: sys_descriptor = {expr};")
    rom += ['default: sys_descriptor = 0; endcase end endfunction',
            'function automatic sys_program_valid(input [1:0] bank,input [11:0] addr);',
            '// Controller fetch may prefetch past END. Logical padding is a valid zero END word;',
            '// it is constant-folded and consumes no additional mutable or ROM storage.',
            'begin sys_program_valid=(bank<3 && addr<64); end endfunction',
            'function automatic sys_descriptor_valid(input [1:0] bank,input [5:0] addr);',
            f'begin sys_descriptor_valid=(bank==0 && addr<{len(ed)}) || (bank==1 && addr<{len(ld)}) || (bank==2 && addr<{len(hd[0])}); end endfunction']
    (out / 'sequencer_sys_templates.svh').write_text('\n'.join(rom) + '\n')
    src = ROOT / 'rtl/qwen_sys/missing_masters_20261007/gen/ot_qfd_sp_constants_sequencer.sv'
    s = src.read_text()
    s = s[s.index('module ot_qfd_sp_constants_sequencer'):]
    s = s.replace('module ot_qfd_sp_constants_sequencer #(', 'module ot_qfd_sp_constants_sequencer_sys #(\n    parameter integer SYS_ENABLE = 0, parameter integer SYS_BASE_MUT = 0, parameter integer DIE_RANK = 0, parameter integer WDOG = 1 << 20,')
    s = s.replace('parameter integer FQ_HEAD = 0', 'parameter integer FQ_HEAD = 1').replace('parameter integer MSTN = 0', 'parameter integer MSTN = 1')
    oldports = ['h_start', 'tp_token', 'tp_pos', 'pw_v', 'pw_addr', 'pw_data', 'dw_v', 'dw_addr', 'dw_data']
    for n in oldports:
        s = re.sub(r'^    input  wire .*\b' + n + r',\n', '', s, flags=re.M)
    ports = '''    input wire d_start,
    input wire [NW-1:0] d_token, d_pos,
    input wire [1:0] d_gen,
    output wire d_done, d_drained, d_fault,
    output wire [1:0] d_done_gen,
    output wire [NW-1:0] d_next_token,
    output wire [31:0] d_next_val, d_cycles,
    output wire [3:0] d_fault_code,
    output wire [5:0] stage, st_layer, st_next_layer, st_crom,
'''
    s = s.replace('    input  wire clk,', ports + '    input  wire clk,', 1)
    # Remove boot input stations: no mutable program/configuration path exists in the successor.
    for n in oldports[3:]:
        s = re.sub(r'^    wire .*\bq_' + n + r';\n    ot_hdc_delay .*\bu_i_' + n + r' .*\n', '', s, flags=re.M)
    a = s.index('    reg [1023:0] prog_mem')
    b = s.index('    wire wrom_re_w;', a)
    s = s[:a] + '''    wire [11:0] prog_a = prog_base + prog_addr;
    reg template_fault;
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) template_fault<=0;
        else if((prog_re && !sys_program_valid(q_st_prog,prog_a)) ||
                (desc_re && !sys_descriptor_valid(q_st_prog,desc_addr))) template_fault<=1;
    end
    always @(posedge clk) begin
        if (prog_re) prog_q <= sys_program(q_st_prog, prog_a);
        if (desc_re) desc_q <= sys_descriptor(q_st_prog, desc_addr);
    end
''' + s[b:]
    insert = '''    `include "sequencer_sys_templates.svh"
    wire h_start;
    wire [NW-1:0] tp_token, tp_pos;
    wire [1:0] st_prog;
    wire [AW-1:0] st_code, st_scale;
    wire [1:0] q_st_prog, q_generation;
    wire [5:0] q_stage;
    wire [AW-1:0] q_st_code, q_st_scale;
    ot_hdc_delay #(.W(2), .D(IS)) u_i_st_prog (.clk(clk),.rst_n(rst_n),.d(st_prog),.q(q_st_prog));
    ot_hdc_delay #(.W(2), .D(IS)) u_i_generation (.clk(clk),.rst_n(rst_n),.d(d_done_gen),.q(q_generation));
    ot_hdc_delay #(.W(6), .D(IS)) u_i_stage (.clk(clk),.rst_n(rst_n),.d(stage),.q(q_stage));
    ot_hdc_delay #(.W(AW), .D(IS)) u_i_code (.clk(clk),.rst_n(rst_n),.d(st_code),.q(q_st_code));
    ot_hdc_delay #(.W(AW), .D(IS)) u_i_scale (.clk(clk),.rst_n(rst_n),.d(st_scale),.q(q_st_scale));
    ot_qfd_dctl #(.NW(NW),.AW(AW),.NS(38),.WDOG(WDOG),.STAB(SYS_STAB)) u_dctl (
        .clk(clk),.rst_n(rst_n),.d_start(d_start && SYS_ENABLE != 0),
        .d_token(d_token),.d_pos(d_pos),.d_gen(d_gen),.d_done(d_done),.d_done_gen(d_done_gen),
        .d_next_token(d_next_token),.d_next_val(d_next_val),.d_drained(d_drained),
        .d_fault(d_fault),.d_fault_code(d_fault_code),.d_cycles(d_cycles),
        .h_start(h_start),.tp_token(tp_token),.tp_pos(tp_pos),.stage(stage),.st_prog(st_prog),
        .st_layer(st_layer),.st_next_layer(st_next_layer),.st_crom(st_crom),.st_code(st_code),.st_scale(st_scale),
        .s_done(s_done),.seq_ntok(seq_ntok),.seq_nval(seq_nval),.s_fault(s_fault),
        .core_fault(core_fault),.coll_fault(r_err),.kv_write_drained(kv_write_drained));
    // Bases are folded before the existing station. KV descriptors retain their own addressing.
    wire [AW-1:0] sys_wbase = b_po_me_i_wbase + (b_po_me_i_wsrc || SYS_BASE_MUT ? {AW{1'b0}} : q_st_code);
    wire [AW-1:0] sys_wcs = b_po_me_i_wcs + (b_po_me_i_wsrc || SYS_BASE_MUT ? {AW{1'b0}} : q_st_scale);
'''
    s = s.replace('    wire rs;', insert + '    wire rs;', 1)
    s = s.replace('    `include "sequencer_sys_templates.svh"', '\n'.join(rom))
    s = s.replace('.d(b_po_me_i_wbase),', '.d(sys_wbase),').replace('.d(b_po_me_i_wcs),', '.d(sys_wcs),')
    s = s.replace('ot_qwen_tp_seq_w12 #(', 'ot_qwen_tp_seq_w12_fs #(')
    s = s.replace('assign b_core_fault = core_fault_w;', 'assign b_core_fault = core_fault_w || template_fault;')
    s = s.replace('.core_fault(core_fault_w), .prog_base(prog_base),', '.core_fault(core_fault_w || template_fault), .prog_base(prog_base),')
    s = s.replace('.start(q_h_start), .token(q_tp_token), .pos(q_tp_pos),', '.start(q_h_start), .token(q_tp_token), .pos(q_tp_pos), .tag_stage(q_stage), .tag_gen(q_generation),')
    (out / 'ot_qfd_sp_constants_sequencer_sys.sv').write_text('`timescale 1ns/1ps\n// Generated by tools/qwen_system/emit_sequencer_sys.py. SYS_ENABLE is off by default.\n' + s)
    record = dict(schema='opentallas.qwen_sequencer_sys_templates.v1', shape=dict(TP=4,G=6144,SW=64,AR_WORDS=256),
                  template_lengths=[len(ew),len(lw),len(hw)], descriptor_lengths=[len(ed),len(ld),len(hd[0])],
                  stage_table=stages, historical_master_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),
                  code_words=code_words,scale_words=scale_words,code_slot_words=code_words,scale_slot_words=scale_words,
                  head_code_words=head_code_words,head_scale_words=head_scale_words,
                  code_capacity_words=code_capacity,scale_capacity_words=scale_capacity,
                  programs=dict(E=[f'{w:0256x}' for w in ew],L=layer['program_hex'],H=heads[0]['program_hex']),
                  descriptors=dict(E=[f'{w:016x}' for w in ed],L=layer['descriptor_hex'],H=[h['descriptor_hex'] for h in heads]))
    (out / 'templates.json').write_text(json.dumps(record,indent=2)+'\n')
    print('SEQUENCER_SYS_EMIT_PASS words=%d descriptors=%d stages=%d' % (len(words),len(ed)+len(ld)+len(hd[0]),len(stages)))

if __name__ == '__main__':
    a = argparse.ArgumentParser()
    a.add_argument('--out',type=Path,required=True)
    emit(a.parse_args().out)

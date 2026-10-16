#!/usr/bin/env python3
"""Derive the TT functional CORE/SCALE split without changing any data edge.

The two SRAM depth banks are not two independent control engines. Move the
complete scale-request pipeline instead, including its own pretag SRAM pair.
Keep the unsplit source and its default instantiations untouched. Generated
modules are candidates until exact composition and physical gates pass.
"""
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'rtl/qwen_sys/tt_tree_partition_20261015'
SP = ROOT / 'rtl/hdc/ot_qwen_me_spine_h_w12.sv'
CT = ROOT / 'rtl/qwen_sys/static_schedule_20261014/ot_qfd_tt_ctl_static.sv'
TR = ROOT / 'rtl/qwen_sys/static_schedule_20261014/ot_qfd_tt_ctlm_split_static.sv'
TW = '(1+1+1+1+1+4+24+24+3*(18+1)+1+3+1+24+24)'


def module(text, name):
    start = text.index('module ' + name + ' #(')
    return text[start:text.index('endmodule', start) + len('endmodule')]


def remove_scale_ports(text):
    return re.sub(r'^\s*output\s+(?:wire|reg)\s+(?:\[[^\n]*?\]\s*)?scale_(?:re|gre|addr),[^\n]*\n', '', text, flags=re.M)


def seam_ports(text, tag_width, nw):
    marker = re.search(r'^\s*input\s+wire\s+rst_n,\s*$', text, re.M)
    assert marker
    return text[:marker.end()] + f'\n    output wire [{tag_width}-1:0] scale_tag,\n    output wire scale_v,\n    ' + text[marker.end():]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    src = SP.read_text()
    sp = module(src, 'ot_qwen_me_spctl_w12')
    begin = sp.index('    // -- post-scale:')
    end = sp.index('    // -- result tag', begin)
    block = sp[begin:end]
    assert 'pre_vline' not in sp[end:]
    assert 'pre_tag' not in sp[end:]
    sp = sp[:begin] + '    assign scale_tag={s3_tag[166],s3_tag[163:158],s3_tag[109:53],s3_tag[51:49],s3_tag[23:0]};\n    assign scale_v=s3_v;\n\n' + sp[end:]
    sp = sp.replace('module ot_qwen_me_spctl_w12 #(', 'module ot_qwen_tt_core_spctl #(', 1)
    sp = seam_ports(remove_scale_ports(sp), '91', 'NW')
    (OUT / 'ot_qwen_tt_core_spctl.sv').write_text('`timescale 1ns/1ps\n' + sp + '\n')

    # Fixed production TT parameters, copied from qfd_tt_ctlm_tree_static/u_tt.
    # Both tag delays still instantiate the real mapped 128x256 SRAM models.
    scale = '''`timescale 1ns/1ps
module qfd_tt_scale_leaf (
    input wire clk, input wire rst_n,
    input wire [90:0] tag_payload, input wire s3_v,
    output reg scale_re, output reg [23:0] scale_gre,
    output reg [575:0] scale_addr
);
    localparam integer W=16, IL=8, AW=24, NW=18, GT=3072, TCUT=7,
      SMIN=7, SMAX=11, XD=105, RX=5, ACC_LAT=7, TREE_LAT=7,
      MUL_LAT=6, SCALE_LOCAL=0, SPRE=2, SC=1, BANDF=1, RDMEM=1;
    localparam integer GOUT=GT>>SMIN, NPG=GOUT, LW=$clog2(W), LG=$clog2(GT),
      SD=MUL_LAT+ACC_LAT, TL=TREE_LAT+1, OD=TL*LG, XDD=XD,
      TW=1+1+1+1+1+4+AW+AW+3*(NW+1)+1+3+1+AW+AW;
    wire [31:0] gb=0;
    wire [17:0] s3_t=0;
    wire [166:0] s3_tag={tag_payload[90],2'b0,tag_payload[89:84],48'd0,
      tag_payload[83:27],1'b0,tag_payload[26:24],1'b0,24'd0,tag_payload[23:0]};
'''
    # Guard the externally visible width against accidental copied literals.
    assert eval(TW) == 167
    (OUT / 'qfd_tt_scale_leaf.sv').write_text(scale + block + '\nendmodule\n')

    ctl = module(CT.read_text(), 'ot_qfd_tt_ctl_static')
    ctl = ctl.replace('module ot_qfd_tt_ctl_static #(', 'module ot_qwen_tt_core_ctl #(', 1)
    ctl = seam_ports(remove_scale_ports(ctl), '91', 'NW')
    ctl = ctl.replace('parameter integer AMI = 0', 'parameter integer PORT_AM_EXTRA_EDGES = 0,\n    parameter integer AMI = 0', 1)
    ctl = ctl.replace('.XADDR(XADDR)', '.PORT_AM_EXTRA_EDGES(PORT_AM_EXTRA_EDGES), .XADDR(XADDR)', 1)
    ctl = ctl.replace('ot_qwen_me_spctl_w12 #(', 'ot_qwen_tt_core_spctl #(', 1)
    ctl = ctl.replace('.scale_re(c_scale_re), .scale_gre(c_sgre), .scale_addr(c_saddr),', '.scale_tag(scale_tag), .scale_v(scale_v),')
    # Remove the scale members from both sides of the output station tuples;
    # the core's other stations and their exact pipeline edges stay unchanged.
    for old in ['c_scale_re, ', 'c_sgre, ', 'c_saddr, ', 'scale_re, ', 'scale_gre, ', 'scale_addr, ']:
        ctl = ctl.replace(old, '')
    ctl = ctl.replace('9 + NPG + 2*(LG+1)', '8 + 2*(LG+1)')
    ctl = ctl.replace('2 + AW + NPG*AW + AW + AW + 4 + FW + NW + 32 + AW + W + W*32 + 16', '2 + AW + AW + AW + 4 + FW + NW + 32 + AW + W + W*32 + 16')
    (OUT / 'ot_qwen_tt_core_ctl.sv').write_text('`timescale 1ns/1ps\n' + ctl + '\n')

    tree = module(TR.read_text(), 'qfd_tt_ctlm_tree_static')
    tree = tree.replace('module qfd_tt_ctlm_tree_static #(', 'module qfd_tt_core_leaf #(parameter integer PORT_AM_EXTRA_EDGES=0,', 1)
    tree = seam_ports(remove_scale_ports(tree), '91', '18')
    tree = tree.replace('    wire rs;', '    output_marker\n    wire rs;', 1).replace('    output_marker\n', '')
    tree = tree.replace('ot_qfd_tt_ctl_static #(', 'ot_qwen_tt_core_ctl #(.PORT_AM_EXTRA_EDGES(PORT_AM_EXTRA_EDGES),', 1)
    tree = tree.replace('.scale_re(scale_re), .scale_gre(scale_gre), .scale_addr(scale_addr),', '.scale_tag(scale_tag), .scale_v(scale_v),')
    # Export the existing tree reset station. The scale leaf must use exactly
    # this reset phase, not a new independently delayed release.
    tree = tree.replace('    output wire scale_v,', '    output wire scale_v,\n    output wire scale_rst_n,', 1)
    tree = tree.replace('    wire rs;', '    wire rs;\n    assign scale_rst_n=rs;', 1)
    (OUT / 'qfd_tt_core_leaf.sv').write_text('`timescale 1ns/1ps\n' + tree + '\n')

    # OS=1 contributes the existing scale output station. Preserve it in the
    # SCALE leaf, so neither external pins nor compiler timing moves.
    scale_path = OUT / 'qfd_tt_scale_leaf.sv'
    text = scale_path.read_text().replace('module qfd_tt_scale_leaf (', 'module ot_qwen_tt_scale_body (', 1)
    text += '''
module qfd_tt_scale_leaf (
    input wire clk, input wire rst_n,
    input wire [90:0] tag_payload, input wire s3_v,
    output reg scale_re, output reg [23:0] scale_gre,
    output reg [575:0] scale_addr
);
    wire raw_re; wire [23:0]raw_gre; wire [575:0]raw_addr;
    ot_qwen_tt_scale_body u_scale(.clk(clk),.rst_n(rst_n),.tag_payload(tag_payload),
      .s3_v(s3_v),.scale_re(raw_re),.scale_gre(raw_gre),.scale_addr(raw_addr));
    always @(posedge clk or negedge rst_n)
      if(!rst_n)begin scale_re<=0;scale_gre<=0;end
      else begin scale_re<=raw_re;scale_gre<=raw_gre;end
    always @(posedge clk)scale_addr<=raw_addr;
endmodule
'''
    scale_path.write_text(text)
    original_tree = module(TR.read_text(), 'qfd_tt_ctlm_tree_static')
    header = original_tree[:original_tree.index('\n);') + 3]
    header = header.replace('module qfd_tt_ctlm_tree_static #(', 'module qfd_tt_tree_partition #(parameter integer MUT=0, PORT_AM_EXTRA_EDGES=0,', 1)
    header = header.replace('input wire  clk,', 'input wire ck_core, input wire ck_scale,')
    names = re.findall(r'^\s*(?:input|output)\s+wire\s+(?:\[[^\n]*?\]\s*)?(\w+)\s*(?:[,\n]|$)', original_tree[:original_tree.index('\n);')], re.M)
    assert 'cmd' in names and 'scale_addr' in names and 'clk' in names
    core_names = [n for n in names if n not in ('clk', 'scale_re', 'scale_gre', 'scale_addr')]
    wrapper = header + '\n    wire [90:0] scale_tag; wire scale_v; wire scale_rst_n;\n'
    wrapper += '    qfd_tt_core_leaf #(.PORT_AM_EXTRA_EDGES(PORT_AM_EXTRA_EDGES)) u_core(.clk(ck_core),\n      ' + ','.join('.'+n+'('+n+')' for n in core_names) + ',\n      .scale_tag(scale_tag),.scale_v(scale_v),.scale_rst_n(scale_rst_n));\n'
    wrapper += '''    wire [90:0] scale_tag_m=scale_tag ^ ((MUT==1) ? 91'd1 : 91'd0);
    generate if(MUT==2)begin:g_mut_station
      ot_qwen_tt_scale_body u_scale(.clk(ck_scale),.rst_n(scale_rst_n),.tag_payload(scale_tag_m),
        .s3_v(scale_v),.scale_re(scale_re),.scale_gre(scale_gre),.scale_addr(scale_addr));
    end else begin:g_scale
      qfd_tt_scale_leaf u_scale(.clk(ck_scale),.rst_n(scale_rst_n),.tag_payload(scale_tag_m),
        .s3_v(scale_v),.scale_re(scale_re),.scale_gre(scale_gre),.scale_addr(scale_addr));
    end endgenerate
endmodule
'''
    (OUT / 'qfd_tt_tree_partition.sv').write_text('`timescale 1ns/1ps\n' + wrapper)
    manifest = {'schema': 'opentallas.tt_functional_partition.v1',
      'source_sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in (SP, CT, TR)},
      'data_cycles_added': 0, 'status': 'candidate_unqualified',
      'seam': {'scale_tag': 91, 'scale_v': 1, 'scale_rst_n': 1},
      'memory_inventory': {'core': 'u_tag: two 128x256 SRAM depth banks',
                           'scale': 'u_pretag: two 128x256 SRAM depth banks'},
      'limits': {'launch_ps': 220, 'capture_ps': 190, 'spread_ps': 80}}
    (OUT / 'source_manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(OUT)


if __name__ == '__main__':
    main()

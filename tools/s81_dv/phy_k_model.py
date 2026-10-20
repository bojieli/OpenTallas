#!/usr/bin/env python3
"""BIND/mu4: derive rtl/dsrom_sys/s81_link/ot_hbm3e_phy_v41x_aw30_e8p5_k.sv (K-only S81 HBM macro model) from the generic
model.  Run with cwd = rtl/dsrom_sys/s81_link.  Abstract views: tools/s81_dv/phy_k_variant.py."""
from pathlib import Path
import re
s=Path('ot_hbm3e_phy_v41x_aw30_e8p5.sv').read_text()
body=s[s.index('module ot_hbm3e_phy_v41x_aw30_e8p5 #('):]
out='''`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------
// ot_hbm3e_phy_v41x_aw30_e8p5_k (BIND/mu4 2026-10-19): the S81 die's HBM3E macro, K-ONLY variant -- same K port, same
// controller RTL (ot_s81_hbm_pcc) over the same behavioural PHY + device as ot_hbm3e_phy_v41x_aw30_e8p5, with the W port
// (the QE weight region, unused on S81: weights are in the ROM field) and the model counters (refreshes / w_reads) removed
// at the source instead of tied / left open on the die (strict bind OUTPUT_OPEN).  Abstract: physical/asap7_memory_macros_v2/
// ot_hbm3e_phy_v41x_aw30_e8p5_k/ (tools/s81_dv/phy_k_variant.py).  k_oor (sticky K request past the 2^30-sector stack) is a
// real status output: the binder wires it to a die status pin.  n_refreshes is an internal net for benches (hierarchical).
// Derived from ot_hbm3e_phy_v41x_aw30_e8p5.sv (K generate loop and k_oor logic byte-identical).
// ---------------------------------------------------------------------------------------------------------------
'''
b=body.replace('module ot_hbm3e_phy_v41x_aw30_e8p5 #(','module ot_hbm3e_phy_v41x_aw30_e8p5_k #(',1)
for d in ['    input  wire w_v,\n','    output wire w_rdy,\n','    input  wire [23:0] w_addr,\n','    input  wire [5:0] w_len,\n','    input  wire [9:0] w_tag,\n',
          '    output wire [7:0] w_room,\n','    output wire [7:0] wr_v,\n','    input  wire [7:0] wr_rdy,\n','    output wire [79:0] wr_tag,\n',
          '    output wire [39:0] wr_beat,\n','    output wire [2047:0] wr_data,\n','    output reg  w_oor,\n','    output wire [63:0] refreshes,\n']:
    assert b.count(d)==1,d; b=b.replace(d,'',1)
o='    output reg  k_oor,\n    output wire [31:0] w_reads\n);'; assert b.count(o)==1; b=b.replace(o,'    output reg  k_oor\n);',1)
i=b.index('    // W port: request to channel w_addr[2:0]'); j=b.index('    end endgenerate\n',i)+len('    end endgenerate\n')
b=b[:i]+b[j:]
o='    wire [31:0] kref [0:31]; wire [31:0] krd [0:31]; wire [31:0] wref [0:7]; wire [31:0] wrd [0:7];\n    wire [31:0] kviol, wviol;'
assert b.count(o)==1; b=b.replace(o,'    wire [31:0] kref [0:31]; wire [31:0] krd [0:31];\n    wire [31:0] kviol;')
old='''    reg [63:0] rs; reg [31:0] wr_s;
    always @* begin
        rs = 64'd0; wr_s = 32'd0;
        for (i = 0; i < 32; i = i + 1) rs = rs + kref[i];
        for (i = 0; i < 8; i = i + 1) wr_s = wr_s + wrd[i];
    end
    assign refreshes = rs; assign w_reads = wr_s;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin k_oor <= 1'b0; w_oor <= 1'b0; end
        else begin
            for (i = 0; i < 32; i = i + 1)
                if (k_v[i] && k_rdy[i] && ({1'b0, k_addr[30*i +: 30]} + k_len[4*i +: 4] > 31'h40000000)) k_oor <= 1'b1;
            if (w_v && w_len == 0) w_oor <= 1'b1;
        end'''
new='''`ifndef SYNTHESIS
    reg [63:0] n_refreshes;                     // bench observability only (tb_s81_hbm PHY_K reads dut.n_refreshes)
    always @* begin n_refreshes = 64'd0; for (i = 0; i < 32; i = i + 1) n_refreshes = n_refreshes + kref[i]; end
`endif
    always @(posedge clk or negedge rst_n)
        if (!rst_n) k_oor <= 1'b0;
        else
            for (i = 0; i < 32; i = i + 1)
                if (k_v[i] && k_rdy[i] && ({1'b0, k_addr[30*i +: 30]} + k_len[4*i +: 4] > 31'h40000000)) k_oor <= 1'b1;'''
assert b.count(old)==1; b=b.replace(old,new)
bad=re.findall(r'.*(?:\bw_(?:v|rdy|addr|len|tag|room|oor|reads)\b|(?<!\.)\bwr_|\brefreshes\b|wviol|wref|\bwrd\b).*', b)
assert not bad, bad[:5]
Path('ot_hbm3e_phy_v41x_aw30_e8p5_k.sv').write_text(out+b)

#!/usr/bin/env python3
"""Generate a combined real programme-ROM source/CPIN candidate, no alias views."""
import re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
p=ROOT/'rtl/dsrom_sys/s81_suhc/static/ot_s81_hc_cpin_calendar.sv'
s=p.read_text();header=s[:s.index(');')+2];header=header[header.index('module '):]
ports=re.findall(r'\b(?:input|output)\s+(?:wire|reg)\s*(?:\[[^\]]+\]\s*)?(\w+)',header)
# Multi-name declarations carry additional actual ports on each declaration.
ports=[]
for decl in re.findall(r'\b(?:input|output)\s+(?:wire|reg)\s*(?:\[[^\]]+\]\s*)?([^\n;]+)',header):
 ports += [n.strip().strip(',') for n in decl.split(',') if n.strip()]
header=header.replace('module ot_s81_hc_cpin_calendar','module ot_s81_hc_programme_cpin')
header=header.replace('parameter integer COMMAND_POST_AGES = 0,','parameter integer COMMAND_POST_AGES = 1,\n    parameter string IMAGE = "",')
header=header.replace('input  wire                cck, crs, sk, srs,','input wire stream_ck,stream_rst_n,sk,srs,rom_ck,\n    input wire[84:0]c2,\n    output wire[8:0]stream_done,\n    output wire programme_fault,')
header=header.replace('    input wire [639:0] command_post_ages,\n','')
header=header.replace('y_tag,command_y_tag,command_done_age,command_ss_age,command_scalar_age','y_tag')
header=header.replace('    input  wire                c_cmd_v,\n','').replace('    input  wire [83:0]         c_cmd_d,\n','')
# Serial done is consumed internally by the actual completion bridge.
header=header.replace('    output reg                 c_done_v,\n','').replace('    output reg  [7:0]          c_done_tag,\n','')
header=header.replace('output reg','output wire')
# CPIN source uses localparams below the port list; reproduce literal geometry.
locals='''
    localparam integer NS = NG / GS;
    localparam integer NP = (NS + NCOL - 1) / NCOL;
    localparam integer L1 = (NS - 2 * NP > 0) ? NS - 2 * NP : 0;
    localparam integer YS1 = (L1 > 0) ? L1 * GS * 32 : 1;
'''
wires='''
    wire[84:0]hc_command;wire[8:0]serial_done;
    wire[31:0]command_y_tag,command_done_age,command_ss_age,command_scalar_age;
    wire[639:0]command_post_ages;
    initial if(COMMAND_POST_AGES!=1)$fatal(1,"combined source requires explicit per-command POST ages");
    ot_s81_hc_programme_endpoint #(.IMAGE(IMAGE),.RAW_ROM_CLOCK(1))u_programme(
      .stream_ck(stream_ck),.stream_rst_n(stream_rst_n),.serial_ck(sk),.serial_rst_n(srs),
      .rom_ck(rom_ck),.c2(c2),.hc_command(hc_command),.hc_done_age(command_done_age),.hc_ss_age(command_ss_age),
      .hc_scalar_age(command_scalar_age),.hc_y_tag(command_y_tag),.hc_post_ages(command_post_ages),
      .serial_done(serial_done),.stream_done(stream_done),.fault(programme_fault));
'''
connections={'cck':'sk','crs':'srs','c_cmd_v':'hc_command[84]','c_cmd_d':'hc_command[83:0]','c_done_v':'serial_done[8]','c_done_tag':'serial_done[7:0]'}
body='    ot_s81_hc_cpin_calendar #(.NG(NG),.NCOL(NCOL),.GS(GS),.S_RD(S_RD),.TH(TH),.COMMAND_POST_AGES(1))u_cpin(\n'
body+=',\n'.join('      .'+name+'('+connections.get(name,name)+')'for name in ports)+'\n    );\n'
result='// Combined candidate: actual programme ROM + actual CPIN; no inherited closed view.\n`timescale 1ns/1ps\n'+header+'\n'+locals+wires+body+'endmodule\n'
(ROOT/'rtl/dsrom_sys/s81_suhc/static/ot_s81_hc_programme_cpin.sv').write_text(result)

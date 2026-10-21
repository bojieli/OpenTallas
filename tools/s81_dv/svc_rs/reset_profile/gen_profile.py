#!/usr/bin/env python3
"""Construct distinct source-only G4 profile parents from exact current modules."""
from pathlib import Path
import re,json,hashlib
R=Path(__file__).resolve().parents[4]
def module(path,name):
 s=(R/path).read_text();a=s.index('module '+name+' ');b=s.index('\nendmodule',a)+len('\nendmodule');return s[a:b]
def put(path,text):
 p=R/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('`timescale 1ns/1ps\n// GENERATED SOURCE CANDIDATE by tools/s81_dv/svc_rs/reset_profile/gen_profile.py\n// No default adoption or native/physical claim.\n'+text+'\n')
p='rtl/dsrom_sys/s81_dv/svc_rs/'
a=module(p+'dsdv_svc_att.sv','dsdv_svc_att');a=a.replace('module dsdv_svc_att #','module dsdv_svc_att_reset9 #',1);x='input wire rst_n,';assert x in a;a=a.replace(x,x+' input wire reset_early9,',1);x='    dsdv_svc_att_core #(';assert x in a;a=a.replace(x,"    wire[131:0]reset_leaf132;wire[511:0]reset_leaf9={380'd0,reset_leaf132};\n    ot_s81svc_reset132_n32 u_reset9(.clk(clk),.reset_early9(reset_early9),.reset_leaf(reset_leaf132));\n    dsdv_svc_att_core #(.RESET_PROFILE(1),",1);x='.clk(clk), .rst_n(rst_n), .sid(sid)';assert x in a;a=a.replace(x,'.clk(clk), .rst_n(rst_n), .reset_leaf(reset_leaf9), .sid(sid)',1);put(p+'dsdv_svc_att_reset9.sv',a)
a=module(p+'dsdv_svc_rs_glue.sv','dsdv_svc_rs_attw1');a=a.replace('module dsdv_svc_rs_attw1 #','module dsdv_svc_rs_attw1_r9 #',1);x='    input  wire             rst,';assert x in a;a=a.replace(x,x+'\n    input wire reset_early11,',1);x='    dsdv_svc_att #(';assert x in a;a=a.replace(x,"    dsdv_svc_att_reset9 #(",1);x='.clk(ck), .rst_n(rn), .sid(sid)';assert x in a;a=a.replace(x,'.clk(ck), .rst_n(rn), .reset_early9(reset_early11), .sid(sid)',1);put(p+'dsdv_svc_rs_attw1_r9.sv',a)
a=module(p+'attw/lp/dsdv_svc_attw_n1_f_lp.sv','dsdv_svc_attw_n1_f_lp');a=a.replace('module dsdv_svc_attw_n1_f_lp #','module dsdv_svc_attw_n1_r9_lp #',1);x='    wire lpr_c;';assert x in a;a=a.replace(x,"    // LPearly2+forest9=11C assertion; per-leaf ASR2 release=13C, exact u_rl.\n    wire lpr_early11;ot_pl_pad #(.W(1),.N(1))u_lpr_early11(.ck(ck_c),.d(lpr_root),.q(lpr_early11));\n"+x,1);a=a.replace('    dsdv_svc_rs_attw1 #(','    dsdv_svc_rs_attw1_r9 #(',1);x='.ck(ck_c), .rst(lpr_c_u_c), .sid(sid)';assert x in a;a=a.replace(x,'.ck(ck_c), .rst(lpr_c_u_c), .reset_early11(lpr_early11), .sid(sid)',1);put(p+'attw/lp/dsdv_svc_attw_n1_r9_lp.sv',a)
print('G4_RESET9_SOURCE_GENERATED LP2+forest9+ASR2: assertion11C/release13C; othercore/landing/t0reset paths unchanged')

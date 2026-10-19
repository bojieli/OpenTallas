#!/usr/bin/env python3
from pathlib import Path
import sys,json,hashlib
out=Path(sys.argv[1]); out.mkdir(parents=True,exist_ok=True)
root=Path('.')
paths=['rtl/hbm_accel/loader/service_native/ot_hbm_svc_sm_feed_programmed_rel_id.sv','rtl/hbm_accel/loader/service_native/ot_hbm_xcal_prog_native.sv']
for svg,path in enumerate(reversed(paths)):
 s=Path(path).read_text(); is_svg='feed_programmed' in path
 width,xw=(135,46) if is_svg else (173,5)
 head=f"module banked_app_reference_{'svg' if is_svg else 'xc'} #(parameter PREL=1)(input wire clk,rst_n,cfg_we,input wire[10:0]cfg_addr,input wire[255:0]cfg_data,input wire start_v,input wire[10:0]start_base,input wire[11:0]start_limit,input wire[15:0]start_loops,input wire[{xw-1}:0]start_ctx,output wire[{width-1}:0]app,output wire app_v,active,done,fault);\n"
 if is_svg:
  wire='wire[134:0]word;wire[45:0]wctx;wire[15:0]wit;wire wlast,word_v;wire[31:0]ordinal;wire cf;\n'
  rc=s[s.index(' // RELOC (P2).'):s.index(' assign programme_observe=programme;')].replace('stream_clk','clk').replace('stream_rst_n','rst_n')
  # programme_v is an alias name in the qualified source snippet.
  wire+='wire programme_v;\n';tail='assign app=programme;assign app_v=programme_v;assign fault=cf||inj_f;\n'
  cal='.calendar(word),.calendar_ctx(wctx),.calendar_iter(wit),.calendar_lastit(wlast),.calendar_v(word_v),.ordinal(ordinal)'
 else:
  wire='wire[172:0]word0;wire[4:0]wctx;wire[31:0]word_ord;wire cal_v;localparam MUT=0;wire[108:0]cmd_ext;wire[63:0]kv_desc;wire cf;\n'
  rc=s[s.index('    // RELOC mirror'):s.index('endmodule')]
  tail='assign app={kv_desc,cmd_ext};assign app_v=cal_v;assign fault=cf;\n'
  cal='.calendar(word0),.calendar_ctx(wctx),.calendar_iter(),.calendar_lastit(),.calendar_v(cal_v),.ordinal(word_ord)'
 core=f"ot_smh_calendar_static_x #(.W({width}),.AW(11),.XW({xw})) cal(.clk(clk),.rst_n(rst_n),.cfg_we(cfg_we),.cfg_addr(cfg_addr),.cfg_data(cfg_data),.start_v(start_v),.start_base(start_base),.start_limit(start_limit),.start_loops(start_loops),.start_ctx(start_ctx),{cal},.active(active),.done(done),.fault(cf));\n"
 (out/f"reference_{'svg' if is_svg else 'xc'}.sv").write_text('`timescale 1ns/1ps\n'+head+wire+core+rc+tail+'endmodule\n')
(out/'reference_provenance.json').write_text(json.dumps({p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in paths},indent=2)+'\n')

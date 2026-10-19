#!/usr/bin/env python3
"""Generate explicit opt-in regional bridge composition; legacy source unchanged."""
from pathlib import Path
import hashlib
import json
import re

base = Path('rtl/hbm_accel/generic/adapters/static_su')
old = base / 'programme/multirate_bridge_split.sv'
source = old.read_text()
out = ['`timescale 1ns/1ps\n`default_nettype none\n',
       '// Model: results/rtl/hbm_pgstream_safe_1019/MODEL.md\n',
       '// Kept regions contain actual local counter/phase/warm state, not buffers.\n']
for side in ('q', 's'):
    name = 'ot_hbm_su_multirate_bridge_' + side
    start = source.index('module ' + name)
    end = source.index(');', start) + 2
    header = source[start:end].replace(name, name + '_regional')
    header = header.replace('parameter integer MUT=0', 'parameter integer SAFE_COPY=0, MUT=0')
    header = header.replace('output reg', 'output wire')
    out.append(header + '\n')
    ports = ('serial_clk,rst_n,serial_rq,serial_wq,serial_rr,serial_done,rq_b0,rq_b1,wq_b0,wq_b1,rr_b0,rr_b1,dn_b0,dn_b1' if side == 'q' else
             'stream_clk,rst_n,rq_b0,rq_b1,wq_b0,wq_b1,rr_b0,rr_b1,dn_b0,dn_b1,stream_rq,stream_wq,stream_rr,stream_done,fault')
    out.append('if(SAFE_COPY==0)begin:g_legacy\n' + name + ' #(.RQ_BITS(RQ_BITS),.WQ_BITS(WQ_BITS),.RR_BITS(RR_BITS),.READ_RETURN(READ_RETURN),.WRITE_RETURN(WRITE_RETURN),.MUT(MUT)) u_original(' + ','.join('.%s(%s)' % (p,p) for p in ports.split(',')) + ');\nend else begin:g_safe\n')
    if side == 'q':
        out.append('''wire [RQ_BITS+WQ_BITS-1:0] request={serial_wq,serial_rq};
wire [RQ_BITS+WQ_BITS-1:0] bank0,bank1;
assign {wq_b0,rq_b0}=bank0; assign {wq_b1,rq_b1}=bank1;
for(genvar r=0;r<(RQ_BITS+WQ_BITS+14)/15;r=r+1)begin:req
 localparam integer W=((RQ_BITS+WQ_BITS-r*15)>15)?15:RQ_BITS+WQ_BITS-r*15;
 ot_hbm_pgs_request_q_region #(.W(W),.ID(r),.READ_RETURN(READ_RETURN),.WRITE_RETURN(WRITE_RETURN),.MUT(MUT)) u_copy(
  .clk(serial_clk),.rst_n(rst_n),.d(request[r*15+:W]),.b0(bank0[r*15+:W]),.b1(bank1[r*15+:W]));
end
for(genvar r=0;r<(RR_BITS+14)/15;r=r+1)begin:ret
 localparam integer W=((RR_BITS-r*15)>15)?15:RR_BITS-r*15;
 ot_hbm_pgs_return_q_region #(.W(W),.ID(r),.READ_RETURN(READ_RETURN),.WRITE_RETURN(WRITE_RETURN),.MUT(MUT)) u_copy(
  .clk(serial_clk),.rst_n(rst_n),.b0(rr_b0[r*15+:W]),.b1(rr_b1[r*15+:W]),.d(serial_rr[r*15+:W]));
end
// A one-bit canonical done path; no payload fanout from this copy.
ot_hbm_su_multirate_bridge_q #(.RQ_BITS(1),.WQ_BITS(1),.RR_BITS(1),.READ_RETURN(READ_RETURN),.WRITE_RETURN(WRITE_RETURN),.MUT(MUT)) u_done(
 .serial_clk(serial_clk),.rst_n(rst_n),.serial_rq(1'b0),.serial_wq(1'b0),.serial_rr(),.serial_done(serial_done),
 .rq_b0(),.rq_b1(),.wq_b0(),.wq_b1(),.rr_b0(1'b0),.rr_b1(1'b0),.dn_b0(dn_b0),.dn_b1(dn_b1));
end
wire rsel;
if(SAFE_COPY==0)assign rsel=g_legacy.u_original.rsel;
else assign rsel=g_safe.ret[0].u_copy.u_q.rsel;
''')
    else:
        out.append('''wire [RQ_BITS+WQ_BITS-1:0] bank0={wq_b0,rq_b0},bank1={wq_b1,rq_b1};
wire [RQ_BITS+WQ_BITS-1:0] launched;
assign {stream_wq,stream_rq}=launched;
for(genvar r=0;r<(RQ_BITS+WQ_BITS+14)/15;r=r+1)begin:req
 localparam integer W=((RQ_BITS+WQ_BITS-r*15)>15)?15:RQ_BITS+WQ_BITS-r*15;
 ot_hbm_pgs_request_s_region #(.W(W),.ID(r),.READ_RETURN(READ_RETURN),.WRITE_RETURN(WRITE_RETURN),.MUT(MUT)) u_copy(
  .clk(stream_clk),.rst_n(rst_n),.b0(bank0[r*15+:W]),.b1(bank1[r*15+:W]),.d(launched[r*15+:W]));
end
for(genvar r=0;r<(RR_BITS+14)/15;r=r+1)begin:ret
 localparam integer W=((RR_BITS-r*15)>15)?15:RR_BITS-r*15;
 ot_hbm_pgs_return_s_region #(.W(W),.ID(r),.READ_RETURN(READ_RETURN),.WRITE_RETURN(WRITE_RETURN),.MUT(MUT)) u_copy(
  .clk(stream_clk),.rst_n(rst_n),.d(stream_rr[r*15+:W]),.b0(rr_b0[r*15+:W]),.b1(rr_b1[r*15+:W]));
end
// Original actual valid/calendar fault equations; data copies do not invent validity.
ot_hbm_su_multirate_bridge_s #(.RQ_BITS(1),.WQ_BITS(1),.RR_BITS(1),.READ_RETURN(READ_RETURN),.WRITE_RETURN(WRITE_RETURN),.MUT(MUT)) u_monitor(
 .stream_clk(stream_clk),.rst_n(rst_n),.rq_b0(rq_b0[RQ_BITS-1]),.rq_b1(rq_b1[RQ_BITS-1]),
 .wq_b0(wq_b0[WQ_BITS-1]),.wq_b1(wq_b1[WQ_BITS-1]),.rr_b0(),.rr_b1(),.dn_b0(dn_b0),.dn_b1(dn_b1),
 .stream_rq(),.stream_wq(),.stream_rr(stream_rr[RR_BITS-1]),.stream_done(stream_done),.fault(fault));
end
wire rd_v,rd_b;
if(SAFE_COPY==0)begin assign rd_v=g_legacy.u_original.rd_v; assign rd_b=g_legacy.u_original.rd_b;end
else begin assign rd_v=g_safe.req[0].u_copy.u_s.rd_v; assign rd_b=g_safe.req[0].u_copy.u_s.rd_b;end
''')
    out.append('endmodule\n')

# Each unique parameterized retained region contains state with its own recurrence.
# Flatten only after all opt/ABC passes to inspect the actual complete mapped graph.
regions = {
 'request_q': ('input wire clk,rst_n,input wire [W-1:0] d,output wire [W-1:0] b0,b1', 'q', '1', 'W', '1', '.serial_clk(clk),.rst_n(rst_n),.serial_rq(1\'b0),.serial_wq(d),.serial_rr(),.serial_done(),.rq_b0(),.rq_b1(),.wq_b0(b0),.wq_b1(b1),.rr_b0(1\'b0),.rr_b1(1\'b0),.dn_b0(1\'b0),.dn_b1(1\'b0)'),
 'return_q': ('input wire clk,rst_n,input wire [W-1:0] b0,b1,output wire [W-1:0] d', 'q', '1', '1', 'W', '.serial_clk(clk),.rst_n(rst_n),.serial_rq(1\'b0),.serial_wq(1\'b0),.serial_rr(d),.serial_done(),.rq_b0(),.rq_b1(),.wq_b0(),.wq_b1(),.rr_b0(b0),.rr_b1(b1),.dn_b0(1\'b0),.dn_b1(1\'b0)'),
 'request_s': ('input wire clk,rst_n,input wire [W-1:0] b0,b1,output wire [W-1:0] d', 's', 'W', '1', '1', '.stream_clk(clk),.rst_n(rst_n),.rq_b0(b0),.rq_b1(b1),.wq_b0(1\'b0),.wq_b1(1\'b0),.rr_b0(),.rr_b1(),.dn_b0(),.dn_b1(),.stream_rq(d),.stream_wq(),.stream_rr(1\'b0),.stream_done(1\'b0),.fault()'),
 'return_s': ('input wire clk,rst_n,input wire [W-1:0] d,output wire [W-1:0] b0,b1', 's', '1', '1', 'W', '.stream_clk(clk),.rst_n(rst_n),.rq_b0(1\'b0),.rq_b1(1\'b0),.wq_b0(1\'b0),.wq_b1(1\'b0),.rr_b0(b0),.rr_b1(b1),.dn_b0(),.dn_b1(),.stream_rq(),.stream_wq(),.stream_rr(d),.stream_done(1\'b0),.fault()'),
}
for kind,(ports,side,rq,wq,rr,conn) in regions.items():
    out.append('(* keep_hierarchy = 1 *) module ot_hbm_pgs_'+kind+'_region #(parameter integer W=15,ID=0,READ_RETURN=18,WRITE_RETURN=15,MUT=0)('+ports+');\n')
    out.append('ot_hbm_su_multirate_bridge_'+side+' #(.RQ_BITS('+rq+'),.WQ_BITS('+wq+'),.RR_BITS('+rr+'),.READ_RETURN(READ_RETURN),.WRITE_RETURN(WRITE_RETURN),.MUT(MUT)) u_'+side+'('+conn+');\nendmodule\n')
out.append('`default_nettype wire\n')
dst=base/'programme/multirate_bridge_regional.sv';dst.write_text(''.join(out))

oldtop=base/'top/ot_hbm_su_static_pg_stream_split.sv'
text=oldtop.read_text()
for module in ('q','s','split'):
    original='ot_hbm_su_static_pg_stream_'+module
    text=re.sub(r'\b'+original+r'\b', original+'_regional', text)
text=text.replace('parameter integer READ_RETURN=10,WRITE_RETURN=7,MUT=0', 'parameter integer SAFE_COPY=0,READ_RETURN=10,WRITE_RETURN=7,MUT=0')
text=text.replace('parameter integer QID=1,G=2,READ_RETURN=10,WRITE_RETURN=7,MUT=0', 'parameter integer SAFE_COPY=0,QID=1,G=2,READ_RETURN=10,WRITE_RETURN=7,MUT=0')
text=text.replace('ot_hbm_su_multirate_bridge_q #(', 'ot_hbm_su_multirate_bridge_q_regional #(.SAFE_COPY(SAFE_COPY),')
text=text.replace('ot_hbm_su_multirate_bridge_s #(', 'ot_hbm_su_multirate_bridge_s_regional #(.SAFE_COPY(SAFE_COPY),')
text=text.replace('ot_hbm_su_static_pg_stream_q_regional #(', 'ot_hbm_su_static_pg_stream_q_regional #(.SAFE_COPY(SAFE_COPY),')
text=text.replace('ot_hbm_su_static_pg_stream_s_regional #(', 'ot_hbm_su_static_pg_stream_s_regional #(.SAFE_COPY(SAFE_COPY),')
text=text.replace('module ot_hbm_su_static_pg_stream_q_regional #(.SAFE_COPY(SAFE_COPY),', 'module ot_hbm_su_static_pg_stream_q_regional #(')
text=text.replace('module ot_hbm_su_static_pg_stream_s_regional #(.SAFE_COPY(SAFE_COPY),', 'module ot_hbm_su_static_pg_stream_s_regional #(')
newtop=base/'top/ot_hbm_su_static_pg_stream_regional.sv';newtop.write_text('// GENERATED by tools/hbm_static/pgstream_safe/generate.py; legacy byte-identical.\n'+text)

bench=Path('rtl/test/hbm_accel/generic/tb_hbm_su_pg_stream_split.sv')
b=bench.read_text().replace('module tb_hbm_su_pg_stream_split;', 'module tb_hbm_su_pg_stream_regional;')
b=b.replace('ot_hbm_su_static_pg_stream_split #(', 'ot_hbm_su_static_pg_stream_split_regional #(.SAFE_COPY(1),')
newbench=bench.with_name('tb_hbm_su_pg_stream_regional.sv');newbench.write_text(b)
manifest={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (old,oldtop,bench,dst,newtop,newbench,Path(__file__))}
Path('results/rtl/hbm_pgstream_safe_1019/source_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')

#!/usr/bin/env python3
"""Generate full production32-PC K boundary with replicated local finite leases."""
from pathlib import Path
R=Path(__file__).resolve().parents[1]
P=R/'rtl/hbm_accel/loader/service_native/ot_hbm_loader_service_boundary.sv'
# Explicit ports mirror actual ot_hbm_svc_core K interface, plus native read.
s=['`default_nettype none','module ot_hbm_loader_service_boundary #(parameter integer ENABLE=0,NPC=32)(',
' input wire clk,rst_n,input wire [NPC-1:0] normal_pending_write,',
' input wire [NPC-1:0] normal_v,output wire [NPC-1:0] normal_rdy,input wire [NPC-1:0] normal_we,',
' input wire [NPC*30-1:0] normal_addr,input wire [NPC*4-1:0] normal_len,input wire [NPC*17-1:0] normal_tag,',
' input wire [NPC*256-1:0] normal_wdata,input wire [NPC*32-1:0] normal_wstrb,',
' output wire [NPC-1:0] normal_rsp_v,input wire [NPC-1:0] normal_rsp_rdy,output wire [NPC*17-1:0] normal_rsp_tag,',
' output wire [NPC*4-1:0] normal_rsp_beat,output wire [NPC*256-1:0] normal_rsp_data,',
' input wire native_v,output wire native_rdy,input wire [4:0] native_pc,input wire [29:0] native_addr,input wire [15:0] native_tag,',
' output wire native_rsp_v,input wire native_rsp_rdy,output wire [4:0] native_rsp_pc,output wire [15:0] native_rsp_tag,',
' output wire [3:0] native_rsp_beat,output wire [255:0] native_rsp_data,',
' output wire [NPC-1:0] k_v,input wire [NPC-1:0] k_rdy,output wire [NPC-1:0] k_we,output wire [NPC*30-1:0] k_addr,',
' output wire [NPC*4-1:0] k_len,output wire [NPC*17-1:0] k_tag,output wire [NPC*256-1:0] k_wdata,output wire [NPC*32-1:0] k_wstrb,',
' input wire [NPC-1:0] kr_v,output wire [NPC-1:0] kr_rdy,input wire [NPC*17-1:0] kr_tag,input wire [NPC*4-1:0] kr_beat,input wire [NPC*256-1:0] kr_data,',
' input wire [NPC-1:0] k_wr_done,output wire [NPC-1:0] native_busy,output wire fault',');',
' initial if(NPC!=32)$fatal(1,"production32-PC stack shape required");',
' wire [NPC-1:0] nr,nrv,pfault;wire [NPC*16-1:0] nrt;wire [NPC*4-1:0] nrb;wire [NPC*256-1:0] nrd;',
' reg active;reg[4:0]pc_q;',
' always @(posedge clk or negedge rst_n)if(!rst_n)begin active<=0;pc_q<=0;end else begin',
' if(native_v&&native_rdy)begin active<=1;pc_q<=native_pc;end',
' if(native_rsp_v&&native_rsp_rdy)active<=0;',
' end',
' assign native_rdy=ENABLE!=0&&!active&&nr[native_pc];',
' assign native_rsp_v=active&&nrv[pc_q];assign native_rsp_pc=pc_q;',
' assign native_rsp_tag=nrt[pc_q*16+:16];assign native_rsp_beat=nrb[pc_q*4+:4];assign native_rsp_data=nrd[pc_q*256+:256];',
' assign fault=|pfault;',
' for(genvar p=0;p<NPC;p=p+1)begin:pc',
' ot_hbm_loader_pc_service_lease #(.ENABLE(ENABLE)) u_lease(',
' .clk(clk),.rst_n(rst_n),.normal_pending_write(normal_pending_write[p]),']
widths={'v':1,'rdy':1,'we':1,'addr':30,'len':4,'tag':17,'wdata':256,'wstrb':32,'rsp_v':1,'rsp_rdy':1,'rsp_tag':17,'rsp_beat':4,'rsp_data':256}
for n,w in widths.items():s.append(f' .normal_{n}(normal_{n}[p{f"*{w}+:{w}" if w>1 else ""}]),')
s+=[' .native_v(native_v&&!active&&native_pc==p),.native_rdy(nr[p]),.native_addr(native_addr),.native_tag(native_tag),',
' .native_rsp_v(nrv[p]),.native_rsp_rdy(active&&pc_q==p&&native_rsp_rdy),.native_rsp_tag(nrt[p*16+:16]),',
' .native_rsp_beat(nrb[p*4+:4]),.native_rsp_data(nrd[p*256+:256]),']
for n,w in {'k_v':1,'k_rdy':1,'k_we':1,'k_addr':30,'k_len':4,'k_tag':17,'k_wdata':256,'k_wstrb':32,'kr_v':1,'kr_rdy':1,'kr_tag':17,'kr_beat':4,'kr_data':256,'k_wr_done':1,'native_busy':1}.items():s.append(f' .{n}({n}[p{f"*{w}+:{w}" if w>1 else ""}]),')
s+=[' .fault(pfault[p]));',' end','endmodule','`default_nettype wire','']
P.write_text('\n'.join(s))

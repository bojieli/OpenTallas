// KV-CDC2 (2026-10-18): leaf-local CDC fork of rtl/qwen_sys/host_20261013/qkd_host_visibility_fence.sv for the HOST-cluster CDC leaves (qkd_hr_cdc_host /
// qkd_hr_ingest_qm, tools/qwen_kv_die/host_cluster/gen_cluster.py FORKS). The shared original is unchanged (it binds
// the closed core children and the flat root). Same ports and parameters as the original. Change: every clk_h register takes rst_n through an ot_reset_sync on
// clk_h; the ck registers keep rst_n (core family).

`timescale 1ns/1ps
// True controller host-write completions (ack_n) are counted in ck. A held
// snapshot crosses into clk_h using a toggle/ack MCP handshake, so multi-event
// increments cannot tear a Gray word. Done count is the engine cumulative
// sector count. Flop completion storage and control need no ECC or mirrors.
module qkd_hr_visibility_fence_cdc #(parameter integer ENABLE=1,MUT=0)(
 input wire rst_n,ck,clk_h,input wire[7:0] ack_n,
 input wire in_v,input wire[63:0] in_d,output reg in_cr,
 output reg out_v,output reg[63:0] out_d,input wire out_cr,
 output wire fault,output wire[31:0] landed_debug
);
 generate if(!ENABLE)begin:g_off
  assign fault=0;assign landed_debug=0;
  always @(*)begin in_cr=0;out_v=0;out_d=0;end
 end else begin:g_on
  reg[31:0] commits,snapshot;reg req;
  reg ack_host,ac1,ac2;reg fc;
  reg rc1,rc2,fc1,fc2;reg[31:0] landed;reg fh;

 reg[7:0]ack_q;reg iv_q,ocr_q,fault_q;reg[63:0]id_q;
 always @(posedge ck or negedge rst_n)if(!rst_n)ack_q<=0;else ack_q<=ack_n;
 always @(posedge clk_h)id_q<=in_d;
 // host-family registers: rst_n (core family) asserts asynchronously and releases synchronised to clk_h
 wire rn_h;
 ot_reset_sync u_rsh(.clk(clk_h),.async_rst_n(rst_n),.sync_rst_n(rn_h));
 always @(posedge clk_h or negedge rn_h)if(!rn_h)begin iv_q<=0;ocr_q<=0;fault_q<=0;end
 else begin iv_q<=in_v;ocr_q<=out_cr;fault_q<=fc2|fh;end
  wire[32:0] add={1'b0,commits}+ack_q;
  always @(posedge ck or negedge rst_n)begin
   if(!rst_n)begin commits<=0;snapshot<=0;req<=0;ac1<=0;ac2<=0;fc<=0;end
   else begin
    ac1<=ack_host;ac2<=ac1;
    if(add[32])fc<=1;
    if(!fc)begin
     commits<=add[31:0];
     if(req==ac2&&commits!=snapshot)begin snapshot<=commits;req<=~req;end
    end
   end
  end
  reg[63:0] q[0:7];reg[2:0] wp,rp;reg[3:0] count;
  reg[2:0] host_credits;
  wire[63:0] head=q[rp];
  wire is_done=head[63:56]==8'h01;
  wire pop=count!=0&&host_credits!=0&&!fh&&!fc2&&(!is_done||MUT!=0||landed>=head[31:0]);
  assign fault=fault_q;assign landed_debug=landed;
  reg[2:0] nw,nr,nh;reg[3:0] nc;
  always @(posedge clk_h or negedge rn_h)begin
   if(!rn_h)begin rc1<=0;rc2<=0;ack_host<=0;fc1<=0;fc2<=0;landed<=0;fh<=0;
    wp<=0;rp<=0;count<=0;host_credits<=4;in_cr<=0;out_v<=0;out_d<=0;
   end else begin
    rc1<=req;rc2<=rc1;fc1<=fc;fc2<=fc1;in_cr<=0;out_v<=0;
    if(rc2!=ack_host)begin
     if(snapshot<landed)fh<=1;
     else begin landed<=snapshot;end
     ack_host<=rc2;
    end
    nw=wp;nr=rp;nc=count;nh=host_credits;
    if(!fh&&!fc2)begin
     if(iv_q)begin
      if(count==8&&!pop)fh<=1;
      else begin q[wp]<=id_q;nw=wp+1'b1;nc=nc+1'b1;end
     end
     if(ocr_q)begin if(host_credits==4&&!pop)fh<=1;else nh=host_credits+1'b1;end
     if(pop)begin
      out_v<=1;out_d<=head;in_cr<=1;nr=rp+1'b1;nc=nc-1'b1;nh=nh-1'b1;
     end
    end
    wp<=nw;rp<=nr;count<=nc;host_credits<=nh;
    if(fh||fc2)begin out_v<=0;in_cr<=0;end
   end
  end
 end endgenerate
endmodule

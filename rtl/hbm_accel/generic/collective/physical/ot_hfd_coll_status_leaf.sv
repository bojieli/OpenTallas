`timescale 1ns/1ps
module ot_hfd_coll_status_leaf #(parameter integer NPT=9,SESSION_W0=47)(
 input wire clk,rst_n,input wire[39:0]hgi_cfg,input wire ep_fault,snk_fault,
 input wire[NPT-1:0]lk_fault,lk_locked,
 output reg[NPT*24-1:0]lk_session,output reg[2*NPT-1:0]lk_status,output reg fault
);
 wire[31:0]sess_w;
 ot_hgi_cfg_rx #(.W0(SESSION_W0),.NW(1),.RST(32'd0))u_sess(.clk(clk),.rst_n(rst_n),.bus(hgi_cfg),.act(sess_w));
 always @(posedge clk)lk_session<={NPT{sess_w[23:0]}};
 always @(posedge clk or negedge rst_n)
  if(!rst_n)begin fault<=0;lk_status<='0;end
  else begin fault<=ep_fault|snk_fault|(|lk_fault);lk_status<={lk_locked,lk_fault};end
endmodule
module ot_hfd_coll_reset_leaf(input wire clk,por,output wire rst_n);
 reg[1:0]rst_s;always @(posedge clk)rst_s<={rst_s[0],por};
 assign rst_n=~rst_s[1];
endmodule
// Preserve the wrapper's deliberately retained 94+18 observability flops in their own leaf.
module ot_hfd_coll_monitor_leaf(input wire clk,input wire[111:0]d,output wire[111:0]q);
 (* keep *)reg[111:0]r;always @(posedge clk)r<=d;assign q=r;
endmodule

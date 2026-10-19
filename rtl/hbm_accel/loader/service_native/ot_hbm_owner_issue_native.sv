`default_nettype none
(* keep_hierarchy = "yes" *)
module ot_hbm_owner_issue_slice #(parameter integer W=6,MUT=0)(
 input wire clk,first_rst_n,input wire in_v,in_ready,k_v,k_ready,
 input wire [W-1:0] in_data,output reg [W-1:0] out_data
);
 reg rst_q;always @(posedge clk or negedge first_rst_n)if(!first_rst_n)rst_q<=0;else rst_q<=1;
 reg [W-1:0] input_q;reg [W-1:0] slots[0:3];
 (* keep = "yes" *) reg [1:0] wp,rp;
 reg v_q,ir_q,kv_q,kr_q;
 wire push=v_q&&ir_q;wire pop=kv_q&&((MUT==3)?k_ready:kr_q);
 wire [1:0] next_rp=rp+(pop?2'd1:2'd0);
 always @(posedge clk)begin input_q<=in_data;if(push)slots[wp]<=input_q;out_data<=slots[next_rp];end
 always @(posedge clk or negedge rst_q)
  if(!rst_q)begin wp<=0;rp<=0;v_q<=0;ir_q<=0;kv_q<=0;kr_q<=0;end
  else begin wp<=wp+(push?2'd1:2'd0);rp<=next_rp;v_q<=in_v;ir_q<=in_ready;kv_q<=k_v;kr_q<=k_ready;end
endmodule

module ot_hbm_owner_issue_native #(parameter integer MUT=0)(
 input wire clk,rst_n,in_v,input wire [50:0] in_request,output reg in_ready,
 input wire k_ready,output reg k_v,output wire [50:0] k_request,
 input wire stop,output reg fault,output wire [2:0] occupancy
);
 wire [1:0] first_rst;
 for(genvar b=0;b<2;b=b+1)begin:g_first
  ot_hbm_owner_link_first_reset u_first(.clk(clk),.rst_n(rst_n),.q(first_rst[b]));
 end
 wire [50:0] request_q;
 for(genvar k=0;k<9;k=k+1)begin:g_slice
  localparam integer W=(k==8)?3:6;
  ot_hbm_owner_issue_slice #(.W(W),.MUT(MUT)) u_slice(.clk(clk),.first_rst_n(first_rst[k/5]),
   .in_v(in_v),.in_ready(in_ready),.k_v(k_v),.k_ready(k_ready),
   .in_data(in_request[k*6+:W]),.out_data(request_q[k*6+:W]));
 end
 assign k_request=request_q^((MUT==4)?51'd1:51'd0);
 reg ctrl_rst;always @(posedge clk or negedge first_rst[0])if(!first_rst[0])ctrl_rst<=0;else ctrl_rst<=1;
 reg v_q,ir_q,kv_q,kr_q,stop_q;reg [2:0] count;
 wire push=v_q&&ir_q;wire pop=kv_q&&((MUT==3)?k_ready:kr_q);
 wire [2:0] next_count=count+3'(push)-3'(pop);
 assign occupancy=count;
 always @(posedge clk or negedge ctrl_rst)
  if(!ctrl_rst)begin v_q<=0;ir_q<=0;kv_q<=0;kr_q<=0;stop_q<=0;count<=0;in_ready<=0;k_v<=0;fault<=0;end
  else begin
   v_q<=in_v;ir_q<=in_ready;kv_q<=k_v;kr_q<=k_ready;stop_q<=stop;
   if(fault||stop_q)begin count<=0;in_ready<=0;k_v<=0;end
   else begin
    count<=next_count;in_ready<=next_count<((MUT==2)?4:3);
    if(k_v&&MUT!=1)k_v<=0;else k_v<=count>3'(pop);
    if((pop&&count==0)||(push&&count==4&&!pop))fault<=1;
   end
  end
endmodule
`default_nettype wire

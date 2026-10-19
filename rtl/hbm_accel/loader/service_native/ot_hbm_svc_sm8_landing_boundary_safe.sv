// Opt-in structural fanout candidate; original masters preserved. See fanout model.
`default_nettype none
(* keep_hierarchy="yes" *) module ot_hbm_landing_reset_active(input wire clk,active_reset,output wire landed_n);
 (* async_reg="true" *) reg [1:0] q;
 always @(posedge clk or posedge active_reset)if(active_reset)q<=0;else q<={q[0],1'b1};
 assign landed_n=q[1];
endmodule
(* keep_hierarchy="yes" *) module ot_hbm_landing_safe_slice #(parameter integer W=8)(
 input wire clk,active_reset,push,pop,input wire [W-1:0] data_in,output wire [W-1:0] data_out);
 wire rst_n;
 ot_hbm_landing_reset_active u_reset(.clk(clk),.active_reset(active_reset),.landed_n(rst_n));
 (* keep="true" *) reg [1:0] wp,rp;
 reg push_q;reg [W-1:0] pin_data,slot0,slot1,slot2;
 always @(posedge clk)begin
  pin_data<=data_in;
  if(push_q)case(wp)0:slot0<=pin_data;1:slot1<=pin_data;default:slot2<=pin_data;endcase
 end
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin wp<=0;rp<=0;push_q<=0;end
  else begin
   push_q<=push;
   if(push_q)wp<=wp==2?0:wp+1'b1;
   if(pop)rp<=rp==2?0:rp+1'b1;
  end
 end
 assign data_out=rp==0?slot0:rp==1?slot1:slot2;
endmodule
(* keep_hierarchy="yes" *) module ot_hbm_landing_safe_group #(parameter integer W=32)(
 input wire clk,raw_rst_n,in_v,in_ready,input wire [1:0] used,input wire pending,core_ready,
 input wire [W-1:0] data_in,output wire [W-1:0] data_out);
 wire active_reset;
 ot_hbm_landing_field_inverse #(.W(1)) u_reset_polarity(.field(raw_rst_n),.inverse(active_reset));
 wire push=in_v&&in_ready;
 wire pop=(used[1]||(used[0]&&!pending))&&core_ready;
 genvar i;generate for(i=0;i<(W+7)/8;i=i+1)begin:g_slice
  localparam integer SW=W-8*i>=8?8:W-8*i;
  ot_hbm_landing_safe_slice #(.W(SW)) u_slice(.clk(clk),.active_reset(active_reset),.push(push),.pop(pop),
   .data_in(data_in[8*i+:SW]),.data_out(data_out[8*i+:SW]));
 end endgenerate
endmodule
(* keep_hierarchy="yes" *) module ot_hbm_svc_sm8_landing_boundary_safe #(
 parameter [2:0] BANK=0, parameter integer RESPONSE_DEPTH=8,LBANKS=4,FMUT=0,
 parameter integer BMUT=0,LB=(LBANKS>2)?2:1,IW=283+LB
)(
 input wire hbm_clk,hbm_rst_n,stream_clk,stream_rst_n,
 input wire in_v,output reg in_ready,input wire [IW-1:0] in_data,output reg overflow,
 input wire reserve_v,input wire [LB-1:0] reserve_bank,input wire [15:0] reserve_epoch,
 input wire [11:0] reserve_total,input wire stop,
 output reg complete_v,output reg [LB-1:0] complete_bank,output reg fault,
 input wire read_v,input wire [LB-1:0] read_bank,input wire [5:0] read_row,
 output reg [255:0] read_data
);
 (* async_reg = "true" *) reg [1:0] hr,sr;
 always @(posedge hbm_clk or negedge hbm_rst_n)
  if(!hbm_rst_n)hr<=0;else hr<={hr[0],1'b1};
 always @(posedge stream_clk or negedge stream_rst_n)
  if(!stream_rst_n)sr<=0;else sr<={sr[0],1'b1};
 wire hreset=hr[1],sreset=sr[1];
 wire core_ready,core_overflow,core_complete,core_fault;
 wire [LB-1:0] core_bank;
 wire [255:0] core_data;
 wire [IW-1:0] head;
 reg [1:0] used;
 reg ingress_fault,pending;
 wire push=in_v&&in_ready;
 wire pop=(used>{1'b0,pending})&&core_ready;
 wire [1:0] used_next=used+{1'b0,push}-{1'b0,pop};
 always @(posedge hbm_clk or negedge hreset)begin
  if(!hreset)begin used<=0;pending<=0;in_ready<=0;ingress_fault<=0;overflow<=0;end
  else begin
   used<=used_next;pending<=push;
   // BMUT=1 deliberately omits the pending pin reservation; bench must catch loss.
   in_ready<=BMUT==1?(used_next-{1'b0,pending}<3):(used_next<3);
   if(in_v&&!in_ready)ingress_fault<=1;
   overflow<=ingress_fault||core_overflow;
  end
 end
 genvar g;
 generate for(g=0;g<(IW+31)/32;g=g+1)begin:g_pin
  localparam integer W=(IW-32*g>=32)?32:IW-32*g;
  ot_hbm_landing_safe_group #(.W(W)) u_group(
   .clk(hbm_clk),.raw_rst_n(hbm_rst_n),.in_v(in_v),.in_ready(in_ready),
   .used(used),.pending(pending),.core_ready(core_ready),
   .data_in(in_data[32*g+:W]),.data_out(head[32*g+:W]));
 end endgenerate
 reg rv_q,stop_q,read_q;
 reg [LB-1:0] rb_q,readb_q;
 reg [15:0] re_q;
 reg [11:0] rt_q;
 reg [5:0] row_q;
 // Data has no ownership before its corresponding valid control. No reset-as-enable.
 always @(posedge stream_clk)begin
  rb_q<=reserve_bank;re_q<=reserve_epoch;rt_q<=reserve_total;
  readb_q<=read_bank;row_q<=read_row;complete_bank<=core_bank;read_data<=core_data;
 end
 always @(posedge stream_clk or negedge sreset)begin
  if(!sreset)begin rv_q<=0;stop_q<=1;read_q<=0;complete_v<=0;fault<=0;end
  else begin rv_q<=reserve_v;stop_q<=stop;read_q<=read_v;complete_v<=core_complete;fault<=core_fault;end
 end
 ot_hbm_svc_sm8_landing_bank_sram285_safe #(.BANK(BANK),.RESPONSE_DEPTH(RESPONSE_DEPTH),
  .LBANKS(LBANKS),.FMUT(FMUT),.LB(LB),.IW(IW)) u_core(
  .hbm_clk(hbm_clk),.hbm_rst_n(hreset),.stream_clk(stream_clk),.stream_rst_n(sreset),
  .in_v(pop),.in_ready(core_ready),.in_data(head),.overflow(core_overflow),
  .reserve_v(rv_q),.reserve_bank(rb_q),.reserve_epoch(re_q),.reserve_total(rt_q),.stop(stop_q),
  .complete_v(core_complete),.complete_bank(core_bank),.fault(core_fault),
  .read_v(read_q),.read_bank(readb_q),.read_row(row_q),.read_data(core_data));
endmodule
`default_nettype wire

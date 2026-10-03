`timescale 1ns/1ps
`default_nettype none
// Arithmetic completion seats ONLY. No opcode/identity/tile/transaction controller.
// Existing sources are instantiated byte-identically. Fault data is fail-closed0.
module ot_qwen_native_fp32_lanes #(parameter integer OPT=0)(
 input wire clk, rst_n,
 input wire [3:0] lane_valid,
 output wire [3:0] lane_ready,
 input wire [3:0] select_add, select_mul, select_div, select_sqrt,
 input wire [127:0] a, b,
 input wire [3:0] canonical_zero,
 output wire [3:0] result_valid,
 input wire [3:0] result_ready,
 output wire [127:0] result_bits,
 output wire [7:0] result_error,
 output wire [3:0] protocol_error
);
 generate if (OPT==0) begin:g_off
  assign lane_ready=0;assign result_valid=0;assign result_bits=0;
  assign result_error=0;assign protocol_error=0;
 end else begin:g_on
  for(genvar i=0;i<4;i=i+1)begin:g_lane
   wire [31:0] ai=a[32*i+:32],bi=b[32*i+:32];
   wire [3:0] sel={select_sqrt[i],select_div[i],select_mul[i],select_add[i]};
   wire onehot=(sel==4'b0001)||(sel==4'b0010)||(sel==4'b0100)||(sel==4'b1000);
   reg pending,held,canon,zero_sign,div_argument;
   reg [31:0] value;
   reg [1:0] error;
   assign lane_ready[i]=rst_n&&!pending&&onehot;
   assign protocol_error[i]=rst_n&&lane_valid[i]&&!onehot;
   wire accept=lane_valid[i]&&lane_ready[i];
   wire av,mv,dv,sv,df,sf;
   wire [31:0] ay,my,dy,sy;
   wire [1:0] ae,me;
   ot_fp32_add_rne_pipe u_add(.clk(clk),.rst_n(rst_n),.valid_in(accept&&select_add[i]),.a(ai),.b(bi),.y(ay),.err(ae),.valid_out(av));
   ot_fp32_mul_rne_pipe u_mul(.clk(clk),.rst_n(rst_n),.valid_in(accept&&select_mul[i]),.a(ai),.b(bi),.y(my),.err(me),.valid_out(mv));
   ot_hdc_fdiv u_div(.clk(clk),.rst_n(rst_n),.v(accept&&select_div[i]),.a(ai),.b(bi),.y(dy),.vo(dv),.fault(df));
   ot_hdc_fsqrt u_sqrt(.clk(clk),.rst_n(rst_n),.v(accept&&select_sqrt[i]),.a(ai),.y(sy),.vo(sv),.fault(sf));
   wire complete=av||mv||dv||sv;
   wire [31:0] completed=av?ay:mv?my:dv?dy:sy;
   wire [1:0] completed_error=av?ae:mv?me:dv?(df?(div_argument?2'd1:2'd2):2'd0):(sf?2'd1:2'd0);
   assign result_valid[i]=rst_n&&held;
   assign result_bits[32*i+:32]=value;
   assign result_error[2*i+:2]=error;
   always @(posedge clk or negedge rst_n)begin
    if(!rst_n)begin pending<=0;held<=0;canon<=1;zero_sign<=0;div_argument<=0;value<=0;error<=0;end
    else begin
     if(held&&result_ready[i])begin held<=0;pending<=0;end
     if(accept)begin
      pending<=1;canon<=canonical_zero[i];
      zero_sign<=select_add[i]?(ai[31]&&bi[31]&&ai[30:0]==0&&bi[30:0]==0):
                 select_sqrt[i]?ai[31]:(ai[31]^bi[31]);
      div_argument<=ai[30:23]==8'hff||bi[30:23]==8'hff||bi[30:0]==0;
     end
     if(pending&&complete)begin
      held<=1;error<=completed_error;
      if(completed_error!=0)value<=0;
      else if(completed[30:0]==0)value<={(canon?1'b0:zero_sign),31'd0};
      else value<=completed;
     end
    end
   end
  end
 end endgenerate
endmodule
`default_nettype wire

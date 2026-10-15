`timescale 1ns/1ps
// K256/PINREG1/CUT511/SPLIT9 native physical decomposition. No data/valid epoch added.
// Native capture at the pins (B6 s81-elemB 2026-10-14): every leaf input lands in a register at the leaf pin; the body
// runs one cycle later with one arithmetic cut fewer (fadd: steps 5+6 share a stage, CUT 9'b1_1101_1111; mul: ot_v41_bmul2 =
// bmul3 minus its 2a/2b cut), so each leaf's latency and every cluster-port cycle are unchanged.
module ot_s81_markov_ctl_native (
 input wire clk,rst_n,start,input wire[31:0] head_logit,input wire in_valid,
 input wire[255:0] weight_bf16,embed_bf16,input wire out_ready,
 input wire[15:0] pf,bad_chunk,input wire[4:0] bad_tree,
 input wire jv,input wire[31:0] jd,input wire[1:0] je,
 output wire start_ready,in_ready,output reg out_valid,output reg[31:0] out_bits,output reg fault,
 output wire mul_fire,output wire[255:0] mul_weight,mul_embed,output reg[31:0] head,output wire pv_last
);
 `ifdef OT_S81_MARKOV_CTL_MUT
 localparam integer WORDS=8;
`else
 localparam integer WORDS=16;
`endif
 reg busy;reg[4:0] count;
 assign start_ready=!busy&&!fault;
 assign in_ready=busy&&!out_valid&&count<WORDS&&!fault;
 wire fire=in_valid&&in_ready;
 reg accepted;reg[255:0] weight_q,embed_q;
 always @(posedge clk or negedge rst_n)
  if(!rst_n) accepted<=0;else accepted<=fire;
 always @(posedge clk) if(fire) begin weight_q<=weight_bf16;embed_q<=embed_bf16;end
 assign mul_fire=accepted;assign mul_weight=weight_q;assign mul_embed=embed_q;
 reg[5:0] pv;
 always @(posedge clk or negedge rst_n)
  if(!rst_n) pv<=0;else pv<={pv[4:0],mul_fire};
 assign pv_last=pv[5];
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin busy<=0;count<=0;head<=0;out_valid<=0;out_bits<=0;fault<=0;end
  else begin
   if(start && !start_ready) fault<=1;
   if(start && start_ready) begin busy<=1;count<=0;head<=head_logit;end
   if(fire) count<=count+1'b1;
   if((pv[5] && |pf) || |bad_chunk || |bad_tree || (jv && je!=0)) fault<=1;
   if(jv) begin
    if(!busy || count!=WORDS || out_valid || je!=0 || fault) begin fault<=1;out_valid<=0;end
    else begin out_valid<=1;out_bits<=jd;end
   end
   if(fault) out_valid<=0;
   if(out_valid && out_ready) begin out_valid<=0;busy<=0;end
  end
 end
endmodule
module ot_s81_markov_mul_native_body (
 input wire clk,rst_n,v,input wire[15:0] a,b,output wire[31:0] y,output wire fault
);
 ot_v41_bmul2 u_native (.clk(clk),.rst_n(rst_n),.v(v),.a({a,16'b0}),.b({
`ifdef OT_S81_MARKOV_MUL_MUT
16'b0
`else
b
`endif
,16'b0}),.y(y),.fault(fault));
endmodule
module ot_s81_markov_mul_native (
 input wire clk,rst_n,v,input wire[15:0] a,b,output wire[31:0] y,output wire fault
);
 // leaf reset conditioner (pc2): the die reset is asynchronous at the pin, released here after two edges
 reg[1:0] rs_q;wire rl_n=rs_q[1];
 always @(posedge clk or negedge rst_n) if(!rst_n) rs_q<=2'b00;else rs_q<={rs_q[0],1'b1};
 reg v_q;
 always @(posedge clk or negedge rl_n) if(!rl_n) v_q<=0;else v_q<=v;
 reg[15:0] a_q,b_q;
 always @(posedge clk) begin a_q<=a;b_q<=b;end
 ot_s81_markov_mul_native_body u_b (.clk(clk),.rst_n(rl_n),.v(v_q),.a(a_q),.b(b_q),.y(y),.fault(fault));
endmodule

module ot_s81_markov_chunk0_native_body (
 input wire clk,rst_n,vin,input wire[31:0] sum,p,
 output wire[31:0] y,output wire vout,output wire bad
);
 wire[31:0] pd=p;
 wire[1:0] err;
 ot_v41_fadd #(.CUT(9'b1_1101_1111),.SPLIT9(1)) u_native (.clk(clk),.rst_n(rst_n),.valid_in(vin),.a(sum),.b(
`ifdef OT_S81_MARKOV_CHUNK_MUT_STAGE
 (`OT_S81_MARKOV_CHUNK_MUT_STAGE==0)?32'b0:pd
`else
 pd
`endif
),.y(y),.valid_out(vout),.err(err));
 assign bad=vout&&(err!=0);
endmodule
module ot_s81_markov_chunk0_native (
 input wire clk,rst_n,vin,input wire[31:0] p,
 output wire[31:0] y,output wire vout,output wire bad
);
 // chain head: the running sum enters as +0 inside the leaf (the 'sum' port was tied to 0 by the cluster: NO-STUBS)
 // leaf reset conditioner (pc2): the die reset is asynchronous at the pin, released here after two edges
 reg[1:0] rs_q;wire rl_n=rs_q[1];
 always @(posedge clk or negedge rst_n) if(!rst_n) rs_q<=2'b00;else rs_q<={rs_q[0],1'b1};
 reg v_q;
 always @(posedge clk or negedge rl_n) if(!rl_n) v_q<=0;else v_q<=vin;
 reg[31:0] p_q;
 always @(posedge clk) p_q<=p;
 ot_s81_markov_chunk0_native_body u_b (.clk(clk),.rst_n(rl_n),.vin(v_q),.sum(32'b0),.p(p_q),.y(y),.vout(vout),.bad(bad));
endmodule

module ot_s81_markov_chunk1_native_body (
 input wire clk,rst_n,vin,input wire[31:0] sum,p,
 output wire[31:0] y,output wire vout,output wire bad
);
 localparam integer D=11;
`ifdef OT_S81_MARKOV_DELAY_MUT_STAGE
 localparam integer N=D-1+(`OT_S81_MARKOV_DELAY_MUT_STAGE==1);
`else
 localparam integer N=D-1;
`endif
 reg[N-1:0] ptr;reg[31:0] slot[0:N-1];reg[31:0] q,rd;integer d;
 always @(posedge clk or negedge rst_n)
  if(!rst_n) ptr<={{(N-1){1'b0}},1'b1};else ptr<={ptr[N-2:0],ptr[N-1]};
 always @* begin rd=0;for(d=0;d<N;d=d+1) rd=rd|({32{ptr[d]}}&slot[d]);end
 always @(posedge clk) begin
  for(d=0;d<N;d=d+1) if(ptr[d]) slot[d]<=p;
  q<=rd;
 end
 wire[31:0] pd=q;
 wire[1:0] err;
 ot_v41_fadd #(.CUT(9'b1_1101_1111),.SPLIT9(1)) u_native (.clk(clk),.rst_n(rst_n),.valid_in(vin),.a(sum),.b(
`ifdef OT_S81_MARKOV_CHUNK_MUT_STAGE
 (`OT_S81_MARKOV_CHUNK_MUT_STAGE==1)?32'b0:pd
`else
 pd
`endif
),.y(y),.valid_out(vout),.err(err));
 assign bad=vout&&(err!=0);
endmodule
module ot_s81_markov_chunk1_native (
 input wire clk,rst_n,vin,input wire[31:0] sum,p,
 output wire[31:0] y,output wire vout,output wire bad
);
 // leaf reset conditioner (pc2): the die reset is asynchronous at the pin, released here after two edges
 reg[1:0] rs_q;wire rl_n=rs_q[1];
 always @(posedge clk or negedge rst_n) if(!rst_n) rs_q<=2'b00;else rs_q<={rs_q[0],1'b1};
 reg v_q;
 always @(posedge clk or negedge rl_n) if(!rl_n) v_q<=0;else v_q<=vin;
 reg[31:0] s_q,p_q;
 always @(posedge clk) begin s_q<=sum;p_q<=p;end
 ot_s81_markov_chunk1_native_body u_b (.clk(clk),.rst_n(rl_n),.vin(v_q),.sum(s_q),.p(p_q),.y(y),.vout(vout),.bad(bad));
endmodule

module ot_s81_markov_chunk2_native_body (
 input wire clk,rst_n,vin,input wire[31:0] sum,p,
 output wire[31:0] y,output wire vout,output wire bad
);
 localparam integer D=22;
`ifdef OT_S81_MARKOV_DELAY_MUT_STAGE
 localparam integer N=D-1+(`OT_S81_MARKOV_DELAY_MUT_STAGE==2);
`else
 localparam integer N=D-1;
`endif
 reg[N-1:0] ptr;reg[31:0] slot[0:N-1];reg[31:0] q,rd;integer d;
 always @(posedge clk or negedge rst_n)
  if(!rst_n) ptr<={{(N-1){1'b0}},1'b1};else ptr<={ptr[N-2:0],ptr[N-1]};
 always @* begin rd=0;for(d=0;d<N;d=d+1) rd=rd|({32{ptr[d]}}&slot[d]);end
 always @(posedge clk) begin
  for(d=0;d<N;d=d+1) if(ptr[d]) slot[d]<=p;
  q<=rd;
 end
 wire[31:0] pd=q;
 wire[1:0] err;
 ot_v41_fadd #(.CUT(9'b1_1101_1111),.SPLIT9(1)) u_native (.clk(clk),.rst_n(rst_n),.valid_in(vin),.a(sum),.b(
`ifdef OT_S81_MARKOV_CHUNK_MUT_STAGE
 (`OT_S81_MARKOV_CHUNK_MUT_STAGE==2)?32'b0:pd
`else
 pd
`endif
),.y(y),.valid_out(vout),.err(err));
 assign bad=vout&&(err!=0);
endmodule
module ot_s81_markov_chunk2_native (
 input wire clk,rst_n,vin,input wire[31:0] sum,p,
 output wire[31:0] y,output wire vout,output wire bad
);
 // leaf reset conditioner (pc2): the die reset is asynchronous at the pin, released here after two edges
 reg[1:0] rs_q;wire rl_n=rs_q[1];
 always @(posedge clk or negedge rst_n) if(!rst_n) rs_q<=2'b00;else rs_q<={rs_q[0],1'b1};
 reg v_q;
 always @(posedge clk or negedge rl_n) if(!rl_n) v_q<=0;else v_q<=vin;
 reg[31:0] s_q,p_q;
 always @(posedge clk) begin s_q<=sum;p_q<=p;end
 ot_s81_markov_chunk2_native_body u_b (.clk(clk),.rst_n(rl_n),.vin(v_q),.sum(s_q),.p(p_q),.y(y),.vout(vout),.bad(bad));
endmodule

module ot_s81_markov_chunk3_native_body (
 input wire clk,rst_n,vin,input wire[31:0] sum,p,
 output wire[31:0] y,output wire vout,output wire bad
);
 localparam integer D=33;
`ifdef OT_S81_MARKOV_DELAY_MUT_STAGE
 localparam integer N=D-1+(`OT_S81_MARKOV_DELAY_MUT_STAGE==3);
`else
 localparam integer N=D-1;
`endif
 reg[N-1:0] ptr;reg[31:0] slot[0:N-1];reg[31:0] q,rd;integer d;
 always @(posedge clk or negedge rst_n)
  if(!rst_n) ptr<={{(N-1){1'b0}},1'b1};else ptr<={ptr[N-2:0],ptr[N-1]};
 always @* begin rd=0;for(d=0;d<N;d=d+1) rd=rd|({32{ptr[d]}}&slot[d]);end
 always @(posedge clk) begin
  for(d=0;d<N;d=d+1) if(ptr[d]) slot[d]<=p;
  q<=rd;
 end
 wire[31:0] pd=q;
 wire[1:0] err;
 ot_v41_fadd #(.CUT(9'b1_1101_1111),.SPLIT9(1)) u_native (.clk(clk),.rst_n(rst_n),.valid_in(vin),.a(sum),.b(
`ifdef OT_S81_MARKOV_CHUNK_MUT_STAGE
 (`OT_S81_MARKOV_CHUNK_MUT_STAGE==3)?32'b0:pd
`else
 pd
`endif
),.y(y),.valid_out(vout),.err(err));
 assign bad=vout&&(err!=0);
endmodule
module ot_s81_markov_chunk3_native (
 input wire clk,rst_n,vin,input wire[31:0] sum,p,
 output wire[31:0] y,output wire vout,output wire bad
);
 // leaf reset conditioner (pc2): the die reset is asynchronous at the pin, released here after two edges
 reg[1:0] rs_q;wire rl_n=rs_q[1];
 always @(posedge clk or negedge rst_n) if(!rst_n) rs_q<=2'b00;else rs_q<={rs_q[0],1'b1};
 reg v_q;
 always @(posedge clk or negedge rl_n) if(!rl_n) v_q<=0;else v_q<=vin;
 reg[31:0] s_q,p_q;
 always @(posedge clk) begin s_q<=sum;p_q<=p;end
 ot_s81_markov_chunk3_native_body u_b (.clk(clk),.rst_n(rl_n),.vin(v_q),.sum(s_q),.p(p_q),.y(y),.vout(vout),.bad(bad));
endmodule

module ot_s81_markov_chunk4_native_body (
 input wire clk,rst_n,vin,input wire[31:0] sum,p,
 output wire[31:0] y,output wire vout,output wire bad
);
 localparam integer D=44;
`ifdef OT_S81_MARKOV_DELAY_MUT_STAGE
 localparam integer N=D-1+(`OT_S81_MARKOV_DELAY_MUT_STAGE==4);
`else
 localparam integer N=D-1;
`endif
 reg[N-1:0] ptr;reg[31:0] slot[0:N-1];reg[31:0] q,rd;integer d;
 always @(posedge clk or negedge rst_n)
  if(!rst_n) ptr<={{(N-1){1'b0}},1'b1};else ptr<={ptr[N-2:0],ptr[N-1]};
 always @* begin rd=0;for(d=0;d<N;d=d+1) rd=rd|({32{ptr[d]}}&slot[d]);end
 always @(posedge clk) begin
  for(d=0;d<N;d=d+1) if(ptr[d]) slot[d]<=p;
  q<=rd;
 end
 wire[31:0] pd=q;
 wire[1:0] err;
 ot_v41_fadd #(.CUT(9'b1_1101_1111),.SPLIT9(1)) u_native (.clk(clk),.rst_n(rst_n),.valid_in(vin),.a(sum),.b(
`ifdef OT_S81_MARKOV_CHUNK_MUT_STAGE
 (`OT_S81_MARKOV_CHUNK_MUT_STAGE==4)?32'b0:pd
`else
 pd
`endif
),.y(y),.valid_out(vout),.err(err));
 assign bad=vout&&(err!=0);
endmodule
module ot_s81_markov_chunk4_native (
 input wire clk,rst_n,vin,input wire[31:0] sum,p,
 output wire[31:0] y,output wire vout,output wire bad
);
 // leaf reset conditioner (pc2): the die reset is asynchronous at the pin, released here after two edges
 reg[1:0] rs_q;wire rl_n=rs_q[1];
 always @(posedge clk or negedge rst_n) if(!rst_n) rs_q<=2'b00;else rs_q<={rs_q[0],1'b1};
 reg v_q;
 always @(posedge clk or negedge rl_n) if(!rl_n) v_q<=0;else v_q<=vin;
 reg[31:0] s_q,p_q;
 always @(posedge clk) begin s_q<=sum;p_q<=p;end
 ot_s81_markov_chunk4_native_body u_b (.clk(clk),.rst_n(rl_n),.vin(v_q),.sum(s_q),.p(p_q),.y(y),.vout(vout),.bad(bad));
endmodule

module ot_s81_markov_chunk5_native_body (
 input wire clk,rst_n,vin,input wire[31:0] sum,p,
 output wire[31:0] y,output wire vout,output wire bad
);
 localparam integer D=55;
`ifdef OT_S81_MARKOV_DELAY_MUT_STAGE
 localparam integer N=D-1+(`OT_S81_MARKOV_DELAY_MUT_STAGE==5);
`else
 localparam integer N=D-1;
`endif
 reg[N-1:0] ptr;reg[31:0] slot[0:N-1];reg[31:0] q,rd;integer d;
 always @(posedge clk or negedge rst_n)
  if(!rst_n) ptr<={{(N-1){1'b0}},1'b1};else ptr<={ptr[N-2:0],ptr[N-1]};
 always @* begin rd=0;for(d=0;d<N;d=d+1) rd=rd|({32{ptr[d]}}&slot[d]);end
 always @(posedge clk) begin
  for(d=0;d<N;d=d+1) if(ptr[d]) slot[d]<=p;
  q<=rd;
 end
 wire[31:0] pd=q;
 wire[1:0] err;
 ot_v41_fadd #(.CUT(9'b1_1101_1111),.SPLIT9(1)) u_native (.clk(clk),.rst_n(rst_n),.valid_in(vin),.a(sum),.b(
`ifdef OT_S81_MARKOV_CHUNK_MUT_STAGE
 (`OT_S81_MARKOV_CHUNK_MUT_STAGE==5)?32'b0:pd
`else
 pd
`endif
),.y(y),.valid_out(vout),.err(err));
 assign bad=vout&&(err!=0);
endmodule
module ot_s81_markov_chunk5_native (
 input wire clk,rst_n,vin,input wire[31:0] sum,p,
 output wire[31:0] y,output wire vout,output wire bad
);
 // leaf reset conditioner (pc2): the die reset is asynchronous at the pin, released here after two edges
 reg[1:0] rs_q;wire rl_n=rs_q[1];
 always @(posedge clk or negedge rst_n) if(!rst_n) rs_q<=2'b00;else rs_q<={rs_q[0],1'b1};
 reg v_q;
 always @(posedge clk or negedge rl_n) if(!rl_n) v_q<=0;else v_q<=vin;
 reg[31:0] s_q,p_q;
 always @(posedge clk) begin s_q<=sum;p_q<=p;end
 ot_s81_markov_chunk5_native_body u_b (.clk(clk),.rst_n(rl_n),.vin(v_q),.sum(s_q),.p(p_q),.y(y),.vout(vout),.bad(bad));
endmodule

module ot_s81_markov_chunk6_native_body (
 input wire clk,rst_n,vin,input wire[31:0] sum,p,
 output wire[31:0] y,output wire vout,output wire bad
);
 localparam integer D=66;
`ifdef OT_S81_MARKOV_DELAY_MUT_STAGE
 localparam integer N=D-1+(`OT_S81_MARKOV_DELAY_MUT_STAGE==6);
`else
 localparam integer N=D-1;
`endif
 reg[N-1:0] ptr;reg[31:0] slot[0:N-1];reg[31:0] q,rd;integer d;
 always @(posedge clk or negedge rst_n)
  if(!rst_n) ptr<={{(N-1){1'b0}},1'b1};else ptr<={ptr[N-2:0],ptr[N-1]};
 always @* begin rd=0;for(d=0;d<N;d=d+1) rd=rd|({32{ptr[d]}}&slot[d]);end
 always @(posedge clk) begin
  for(d=0;d<N;d=d+1) if(ptr[d]) slot[d]<=p;
  q<=rd;
 end
 wire[31:0] pd=q;
 wire[1:0] err;
 ot_v41_fadd #(.CUT(9'b1_1101_1111),.SPLIT9(1)) u_native (.clk(clk),.rst_n(rst_n),.valid_in(vin),.a(sum),.b(
`ifdef OT_S81_MARKOV_CHUNK_MUT_STAGE
 (`OT_S81_MARKOV_CHUNK_MUT_STAGE==6)?32'b0:pd
`else
 pd
`endif
),.y(y),.valid_out(vout),.err(err));
 assign bad=vout&&(err!=0);
endmodule
module ot_s81_markov_chunk6_native (
 input wire clk,rst_n,vin,input wire[31:0] sum,p,
 output wire[31:0] y,output wire vout,output wire bad
);
 // leaf reset conditioner (pc2): the die reset is asynchronous at the pin, released here after two edges
 reg[1:0] rs_q;wire rl_n=rs_q[1];
 always @(posedge clk or negedge rst_n) if(!rst_n) rs_q<=2'b00;else rs_q<={rs_q[0],1'b1};
 reg v_q;
 always @(posedge clk or negedge rl_n) if(!rl_n) v_q<=0;else v_q<=vin;
 reg[31:0] s_q,p_q;
 always @(posedge clk) begin s_q<=sum;p_q<=p;end
 ot_s81_markov_chunk6_native_body u_b (.clk(clk),.rst_n(rl_n),.vin(v_q),.sum(s_q),.p(p_q),.y(y),.vout(vout),.bad(bad));
endmodule

module ot_s81_markov_chunk7_native_body (
 input wire clk,rst_n,vin,input wire[31:0] sum,p,
 output wire[31:0] y,output wire vout,output wire bad
);
 localparam integer D=77;
`ifdef OT_S81_MARKOV_DELAY_MUT_STAGE
 localparam integer N=D-1+(`OT_S81_MARKOV_DELAY_MUT_STAGE==7);
`else
 localparam integer N=D-1;
`endif
 reg[N-1:0] ptr;reg[31:0] slot[0:N-1];reg[31:0] q,rd;integer d;
 always @(posedge clk or negedge rst_n)
  if(!rst_n) ptr<={{(N-1){1'b0}},1'b1};else ptr<={ptr[N-2:0],ptr[N-1]};
 always @* begin rd=0;for(d=0;d<N;d=d+1) rd=rd|({32{ptr[d]}}&slot[d]);end
 always @(posedge clk) begin
  for(d=0;d<N;d=d+1) if(ptr[d]) slot[d]<=p;
  q<=rd;
 end
 wire[31:0] pd=q;
 wire[1:0] err;
 ot_v41_fadd #(.CUT(9'b1_1101_1111),.SPLIT9(1)) u_native (.clk(clk),.rst_n(rst_n),.valid_in(vin),.a(sum),.b(
`ifdef OT_S81_MARKOV_CHUNK_MUT_STAGE
 (`OT_S81_MARKOV_CHUNK_MUT_STAGE==7)?32'b0:pd
`else
 pd
`endif
),.y(y),.valid_out(vout),.err(err));
 assign bad=vout&&(err!=0);
endmodule
module ot_s81_markov_chunk7_native (
 input wire clk,rst_n,vin,input wire[31:0] sum,p,
 output wire[31:0] y,output wire vout,output wire bad
);
 // leaf reset conditioner (pc2): the die reset is asynchronous at the pin, released here after two edges
 reg[1:0] rs_q;wire rl_n=rs_q[1];
 always @(posedge clk or negedge rst_n) if(!rst_n) rs_q<=2'b00;else rs_q<={rs_q[0],1'b1};
 reg v_q;
 always @(posedge clk or negedge rl_n) if(!rl_n) v_q<=0;else v_q<=vin;
 reg[31:0] s_q,p_q;
 always @(posedge clk) begin s_q<=sum;p_q<=p;end
 ot_s81_markov_chunk7_native_body u_b (.clk(clk),.rst_n(rl_n),.vin(v_q),.sum(s_q),.p(p_q),.y(y),.vout(vout),.bad(bad));
endmodule

module ot_s81_markov_pair_native_body (
 input wire clk,rst_n,vin,input wire[31:0] a,b,
 output wire[31:0] y,output wire vout,output wire bad
);
 wire[1:0] err;
 ot_v41_fadd #(.CUT(9'b1_1101_1111),.SPLIT9(1)) u_native (.clk(clk),.rst_n(rst_n),.valid_in(vin),.a(a),.b(
`ifdef OT_S81_MARKOV_PAIR_MUT
32'b0
`else
b
`endif
),.y(y),.valid_out(vout),.err(err));
 assign bad=vout&&(err!=0);
endmodule
module ot_s81_markov_pair_native (
 input wire clk,rst_n,vin,input wire[31:0] a,b,
 output wire[31:0] y,output wire vout,output wire bad
);
 // leaf reset conditioner (pc2): the die reset is asynchronous at the pin, released here after two edges
 reg[1:0] rs_q;wire rl_n=rs_q[1];
 always @(posedge clk or negedge rst_n) if(!rst_n) rs_q<=2'b00;else rs_q<={rs_q[0],1'b1};
 reg v_q;
 always @(posedge clk or negedge rl_n) if(!rl_n) v_q<=0;else v_q<=vin;
 reg[31:0] a_q,b_q;
 always @(posedge clk) begin a_q<=a;b_q<=b;end
 ot_s81_markov_pair_native_body u_b (.clk(clk),.rst_n(rl_n),.vin(v_q),.a(a_q),.b(b_q),.y(y),.vout(vout),.bad(bad));
endmodule

module ot_s81_markov_fold_native_body (
 input wire clk,rst_n,vin,input wire[31:0] x,
 output wire[31:0] y,output wire vout,output wire bad
);
 reg have;reg[31:0] held;
 always @(posedge clk or negedge rst_n)
  if(!rst_n) have<=0;else if(vin) have<=!have;
 always @(posedge clk) if(vin&&!have) held<=x;
 wire[1:0] err;
 ot_v41_fadd #(.CUT(9'b1_1101_1111),.SPLIT9(1)) u_native (.clk(clk),.rst_n(rst_n),.valid_in(vin&&have),.a(
`ifdef OT_S81_MARKOV_FOLD_MUT
32'b0
`else
held
`endif
),.b(x),.y(y),.valid_out(vout),.err(err));
 assign bad=vout&&(err!=0);
endmodule
module ot_s81_markov_fold_native (
 input wire clk,rst_n,vin,input wire[31:0] x,
 output wire[31:0] y,output wire vout,output wire bad
);
 // leaf reset conditioner (pc2): the die reset is asynchronous at the pin, released here after two edges
 reg[1:0] rs_q;wire rl_n=rs_q[1];
 always @(posedge clk or negedge rst_n) if(!rst_n) rs_q<=2'b00;else rs_q<={rs_q[0],1'b1};
 reg v_q;
 always @(posedge clk or negedge rl_n) if(!rl_n) v_q<=0;else v_q<=vin;
 reg[31:0] x_q;
 always @(posedge clk) x_q<=x;
 ot_s81_markov_fold_native_body u_b (.clk(clk),.rst_n(rl_n),.vin(v_q),.x(x_q),.y(y),.vout(vout),.bad(bad));
endmodule

module ot_s81_markov_join_native_body #(parameter integer MUTANT_FOLD=0) (
 input wire clk,rst_n,vin,input wire[31:0] head,x,
 output wire[31:0] y,output wire vout,output wire[1:0] err
);
 ot_v41_fadd #(.CUT(9'b1_1101_1111),.SPLIT9(1)) u_native (.clk(clk),.rst_n(rst_n),.valid_in(vin),.a(MUTANT_FOLD?32'b0:head),.b(x),.y(y),.valid_out(vout),.err(err));
endmodule
module ot_s81_markov_join_native #(parameter integer MUTANT_FOLD=0) (
 input wire clk,rst_n,vin,input wire[31:0] head,x,
 output wire[31:0] y,output wire vout,output wire[1:0] err
);
 // leaf reset conditioner (pc2): the die reset is asynchronous at the pin, released here after two edges
 reg[1:0] rs_q;wire rl_n=rs_q[1];
 always @(posedge clk or negedge rst_n) if(!rst_n) rs_q<=2'b00;else rs_q<={rs_q[0],1'b1};
 reg v_q;
 always @(posedge clk or negedge rl_n) if(!rl_n) v_q<=0;else v_q<=vin;
 reg[31:0] h_q,x_q;
 always @(posedge clk) begin h_q<=head;x_q<=x;end
 ot_s81_markov_join_native_body #(.MUTANT_FOLD(MUTANT_FOLD)) u_b (.clk(clk),.rst_n(rl_n),.vin(v_q),.head(h_q),.x(x_q),.y(y),.vout(vout),.err(err));
endmodule

module ot_s81_markov_k256_native #(parameter integer MUTANT_FOLD=0) (
 input wire clk,rst_n,input wire[37:0] clk_leaf,input wire start,
 output wire start_ready,input wire[31:0] head_logit,input wire in_valid,output wire in_ready,
 input wire[255:0] weight_bf16,embed_bf16,output wire out_valid,input wire out_ready,
 output wire[31:0] out_bits,output wire fault
);
 wire mul_fire,pv_last;wire[255:0] mul_weight,mul_embed;wire[31:0] head;
 wire[15:0] pf,bad_chunk;wire[4:0] bad_tree;wire jv;wire[31:0] jd;wire[1:0] je;
 ot_s81_markov_ctl_native u_ctl (.clk(clk),.rst_n(rst_n),.start(start),.head_logit(head_logit),.in_valid(in_valid),
  .weight_bf16(weight_bf16),.embed_bf16(embed_bf16),.out_ready(out_ready),.pf(pf),.bad_chunk(bad_chunk),.bad_tree(bad_tree),
  .jv(jv),.jd(jd),.je(je),.start_ready(start_ready),.in_ready(in_ready),.out_valid(out_valid),.out_bits(out_bits),.fault(fault),
  .mul_fire(mul_fire),.mul_weight(mul_weight),.mul_embed(mul_embed),.head(head),.pv_last(pv_last));
 wire[31:0] p[0:15];
 generate for(genvar lane=0;lane<16;lane=lane+1) begin:g_mul
  ot_s81_markov_mul_native u_mul (.clk(clk_leaf[lane]),.rst_n(rst_n),.v(mul_fire),
   .a(mul_weight[16*lane +: 16]),.b(mul_embed[16*lane +: 16]),.y(p[lane]),.fault(pf[lane]));
 end endgenerate
 wire[31:0] cs[0:1][0:8];wire cv[0:1][0:8];
 assign cv[0][0]=pv_last;
 ot_s81_markov_chunk0_native u_c0s0 (.clk(clk_leaf[16]),.rst_n(rst_n),.vin(cv[0][0]),
  .p(p[0]),.y(cs[0][1]),.vout(cv[0][1]),.bad(bad_chunk[0]));
 ot_s81_markov_chunk1_native u_c0s1 (.clk(clk_leaf[17]),.rst_n(rst_n),.vin(cv[0][1]),
  .sum(cs[0][1]),.p(p[1]),.y(cs[0][2]),.vout(cv[0][2]),.bad(bad_chunk[1]));
 ot_s81_markov_chunk2_native u_c0s2 (.clk(clk_leaf[18]),.rst_n(rst_n),.vin(cv[0][2]),
  .sum(cs[0][2]),.p(p[2]),.y(cs[0][3]),.vout(cv[0][3]),.bad(bad_chunk[2]));
 ot_s81_markov_chunk3_native u_c0s3 (.clk(clk_leaf[19]),.rst_n(rst_n),.vin(cv[0][3]),
  .sum(cs[0][3]),.p(p[3]),.y(cs[0][4]),.vout(cv[0][4]),.bad(bad_chunk[3]));
 ot_s81_markov_chunk4_native u_c0s4 (.clk(clk_leaf[20]),.rst_n(rst_n),.vin(cv[0][4]),
  .sum(cs[0][4]),.p(p[4]),.y(cs[0][5]),.vout(cv[0][5]),.bad(bad_chunk[4]));
 ot_s81_markov_chunk5_native u_c0s5 (.clk(clk_leaf[21]),.rst_n(rst_n),.vin(cv[0][5]),
  .sum(cs[0][5]),.p(p[5]),.y(cs[0][6]),.vout(cv[0][6]),.bad(bad_chunk[5]));
 ot_s81_markov_chunk6_native u_c0s6 (.clk(clk_leaf[22]),.rst_n(rst_n),.vin(cv[0][6]),
  .sum(cs[0][6]),.p(p[6]),.y(cs[0][7]),.vout(cv[0][7]),.bad(bad_chunk[6]));
 ot_s81_markov_chunk7_native u_c0s7 (.clk(clk_leaf[23]),.rst_n(rst_n),.vin(cv[0][7]),
  .sum(cs[0][7]),.p(p[7]),.y(cs[0][8]),.vout(cv[0][8]),.bad(bad_chunk[7]));
 assign cv[1][0]=pv_last;
 ot_s81_markov_chunk0_native u_c1s0 (.clk(clk_leaf[24]),.rst_n(rst_n),.vin(cv[1][0]),
  .p(p[8]),.y(cs[1][1]),.vout(cv[1][1]),.bad(bad_chunk[8]));
 ot_s81_markov_chunk1_native u_c1s1 (.clk(clk_leaf[25]),.rst_n(rst_n),.vin(cv[1][1]),
  .sum(cs[1][1]),.p(p[9]),.y(cs[1][2]),.vout(cv[1][2]),.bad(bad_chunk[9]));
 ot_s81_markov_chunk2_native u_c1s2 (.clk(clk_leaf[26]),.rst_n(rst_n),.vin(cv[1][2]),
  .sum(cs[1][2]),.p(p[10]),.y(cs[1][3]),.vout(cv[1][3]),.bad(bad_chunk[10]));
 ot_s81_markov_chunk3_native u_c1s3 (.clk(clk_leaf[27]),.rst_n(rst_n),.vin(cv[1][3]),
  .sum(cs[1][3]),.p(p[11]),.y(cs[1][4]),.vout(cv[1][4]),.bad(bad_chunk[11]));
 ot_s81_markov_chunk4_native u_c1s4 (.clk(clk_leaf[28]),.rst_n(rst_n),.vin(cv[1][4]),
  .sum(cs[1][4]),.p(p[12]),.y(cs[1][5]),.vout(cv[1][5]),.bad(bad_chunk[12]));
 ot_s81_markov_chunk5_native u_c1s5 (.clk(clk_leaf[29]),.rst_n(rst_n),.vin(cv[1][5]),
  .sum(cs[1][5]),.p(p[13]),.y(cs[1][6]),.vout(cv[1][6]),.bad(bad_chunk[13]));
 ot_s81_markov_chunk6_native u_c1s6 (.clk(clk_leaf[30]),.rst_n(rst_n),.vin(cv[1][6]),
  .sum(cs[1][6]),.p(p[14]),.y(cs[1][7]),.vout(cv[1][7]),.bad(bad_chunk[14]));
 ot_s81_markov_chunk7_native u_c1s7 (.clk(clk_leaf[31]),.rst_n(rst_n),.vin(cv[1][7]),
  .sum(cs[1][7]),.p(p[15]),.y(cs[1][8]),.vout(cv[1][8]),.bad(bad_chunk[15]));
 wire[4:0] tv;wire[31:0] td[0:4];
 ot_s81_markov_pair_native u_pair (.clk(clk_leaf[32]),.rst_n(rst_n),.vin(cv[0][8]),.a(cs[0][8]),.b(cs[1][8]),
  .y(td[0]),.vout(tv[0]),.bad(bad_tree[0]));
 generate for(genvar k=0;k<4;k=k+1) begin:g_tree
  ot_s81_markov_fold_native u_fold (.clk(clk_leaf[33+k]),.rst_n(rst_n),.vin(tv[k]),.x(td[k]),
   .y(td[k+1]),.vout(tv[k+1]),.bad(bad_tree[k+1]));
 end endgenerate
 ot_s81_markov_join_native #(.MUTANT_FOLD(MUTANT_FOLD)) u_join (.clk(clk_leaf[37]),.rst_n(rst_n),.vin(tv[4]),
  .head(head),.x(td[4]),.y(jd),.vout(jv),.err(je));
endmodule

`timescale 1ns/1ps
`default_nettype none
// Fixed-edge 16-lane FP32 reduction. No readiness, queue or dynamic issue.
// Input data is sampled at load/read edges; compiler metadata is sampled at
// publication read. Native arithmetic is real LAT8 hardware from the ring.
module ot_hgi_coll_reduce_static #(parameter integer MUT_TAG=0,MUT_BF16=0)(
 input wire clk_control,input wire [15:0] clk_state,clk_add,
 input wire rst_n,clear,in_v,input wire [544:0] in_flit,
 input wire load_v,input wire [3:0] load_tag,
 input wire add_read,input wire [3:0] read_tag,input wire add_issue,
 input wire pub_read,input wire [3:0] pub_tag_a,pub_tag_b,
 input wire pub_bf16,input wire [32:0] pub_meta,input wire pub_release,pub_issue,
 output reg out_v,output reg [544:0] out_flit,
 output wire fault,output reg [7:0] fault_cause
);
 reg [15:0] valid,pending;
 reg read_v,pub_v;
 reg [3:0] read_tag_q,pub_a_q,pub_b_q;
 reg pub_bf_q,pub_release_q;
 reg [32:0] pub_meta_q;
 reg [7:0] pipe_v;
 reg [3:0] pipe_tag[0:7];
 wire wb=pipe_v[7];
 wire [3:0] wb_tag=pipe_tag[7] ^ (MUT_TAG?4'd1:4'd0);
 wire [511:0] acc,operand,sum,pub_a,pub_b;
 wire [15:0] add_valid;
 function automatic [15:0] bf16(input [31:0] x);
  reg [31:0] rounded;
  begin
   // IEEE finite RNE and preserved infinity/canonical quiet NaN payload.
   if(x[30:23]==8'hff)bf16={x[31:16]} | ((|x[22:0])?16'h0040:16'h0000);
   else begin
    rounded=x+(MUT_BF16?32'h8000:(32'h7fff+{31'b0,x[16]}));
    bf16=rounded[31:16];
   end
  end
 endfunction
 wire [511:0] bf_packed;
 for(genvar l=0;l<16;l=l+1)begin:g_lane
  ot_hgi_coll_reduce_static_state_lane u_state(
   .clk(clk_state[l]),.load_v(load_v),.load_tag(load_tag),.load_data(in_flit[l*32+:32]),
   .wb(wb),.wb_tag(wb_tag),.wb_data(sum[l*32+:32]),
   .add_read(add_read),.read_tag(read_tag),.external_data(in_flit[l*32+:32]),
   .pub_read(pub_read),.pub_tag_a(pub_tag_a),.pub_tag_b(pub_tag_b),
   .acc(acc[l*32+:32]),.operand(operand[l*32+:32]),
   .pub_a(pub_a[l*32+:32]),.pub_b(pub_b[l*32+:32]));
  ot_hgi_coll_pring_static_add_lane #(.LAT(8)) u_add(
   .clk(clk_add[l]),.rst_n(rst_n),.valid_in(add_issue),
   .a(acc[l*32+:32]),.b(operand[l*32+:32]),.y(sum[l*32+:32]),.valid_out(add_valid[l]));
  assign bf_packed[l*16+:16]=bf16(pub_a[l*32+:32]);
  assign bf_packed[256+l*16+:16]=bf16(pub_b[l*32+:32]);
 end
 assign fault=|fault_cause;
 // Sticky fault reasons: ingress, reservation, unavailable, conflict,
 // occupied load, illegal clear, arithmetic validity, writeback identity.
 always @(posedge clk_control or negedge rst_n)begin:control
  reg [7:0] nf;
  if(!rst_n)begin
   valid<=0;pending<=0;read_v<=0;pub_v<=0;pipe_v<=0;
   read_tag_q<=0;pub_a_q<=0;pub_b_q<=0;pub_bf_q<=0;pub_release_q<=0;pub_meta_q<=0;
   out_v<=0;fault_cause<=0;
   for(integer k=0;k<8;k=k+1)pipe_tag[k]<=0;
  end else begin
   nf=0;
   if(in_v!==(load_v|add_read))nf[0]=1;
   if(add_issue!==read_v || pub_issue!==pub_v)nf[1]=1;
   if(add_read && (!valid[read_tag]||pending[read_tag]))nf[2]=1;
   if(pub_read && (!valid[pub_tag_a]||pending[pub_tag_a]||
      (pub_bf16 && (!valid[pub_tag_b]||pending[pub_tag_b]))))nf[2]=1;
   if(load_v && (valid[load_tag]||pending[load_tag]))nf[4]=1;
   if(load_v && add_read)nf[3]=1;
   if(load_v && wb && load_tag==wb_tag)nf[3]=1;
   if(add_issue && ((wb&&wb_tag==read_tag_q)||(load_v&&load_tag==read_tag_q)))nf[3]=1;
   if(add_read && add_issue && read_tag==read_tag_q)nf[3]=1;
   if(pub_read && add_issue && (pub_tag_a==read_tag_q||(pub_bf16&&pub_tag_b==read_tag_q)))nf[3]=1;
   if(pub_read && pub_issue && pub_release_q &&
      (pub_tag_a==pub_a_q||(pub_bf_q&&pub_tag_a==pub_b_q)||
       (pub_bf16&&(pub_tag_b==pub_a_q||(pub_bf_q&&pub_tag_b==pub_b_q)))))nf[3]=1;
   if(add_read && ((load_v&&load_tag==read_tag)||(wb&&wb_tag==read_tag)))nf[3]=1;
   if(pub_read && ((load_v&&(load_tag==pub_tag_a||(pub_bf16&&load_tag==pub_tag_b)))||
      (wb&&(wb_tag==pub_tag_a||(pub_bf16&&wb_tag==pub_tag_b)))))nf[3]=1;
   if(add_issue && pub_issue && pub_release_q &&
      (read_tag_q==pub_a_q||(pub_bf_q&&read_tag_q==pub_b_q)))nf[3]=1;
   if(add_read && pub_issue && pub_release_q &&
      (read_tag==pub_a_q||(pub_bf_q&&read_tag==pub_b_q)))nf[3]=1;
   if(clear && ((|pending)||(|pipe_v)||read_v||pub_v||load_v||add_read||pub_read||add_issue||pub_issue))nf[5]=1;
   if(add_valid!={16{wb}})nf[6]=1;
   if(wb && (!pending[wb_tag]||valid[wb_tag]))nf[7]=1;
   fault_cause<=fault_cause|nf;
   read_v<=add_read;read_tag_q<=read_tag;
   pub_v<=pub_read;pub_a_q<=pub_tag_a;pub_b_q<=pub_tag_b;
   pub_bf_q<=pub_bf16;pub_meta_q<=pub_meta;pub_release_q<=pub_release;
   pipe_v<={pipe_v[6:0],add_issue};pipe_tag[0]<=read_tag_q;
   for(integer k=1;k<8;k=k+1)pipe_tag[k]<=pipe_tag[k-1];
   // Per-tag combined updates avoid a priority mux concealing conflicts.
   for(integer t=0;t<16;t=t+1)begin
    if(clear)begin valid[t]<=0;pending[t]<=0;end
    else begin
     if((load_v&&load_tag==t)||(wb&&wb_tag==t)||
        (add_issue&&read_tag_q==t)||(pub_issue&&pub_release_q&&(pub_a_q==t||(pub_bf_q&&pub_b_q==t))))
      valid[t]<=((load_v&&load_tag==t)||(wb&&wb_tag==t)) &&
        !(add_issue&&read_tag_q==t) && !(pub_issue&&pub_release_q&&(pub_a_q==t||(pub_bf_q&&pub_b_q==t)));
     if((add_issue&&read_tag_q==t)||(wb&&wb_tag==t))
      pending[t]<=(add_issue&&read_tag_q==t) && !(wb&&wb_tag==t);
    end
   end
   out_v<=pub_issue;
  end
 end
 // Data registers have no reset/clear fanout. Invalid traces fault; commands
 // still execute at their assigned edges, and consumers must discard the epoch.
 always @(posedge clk_control)out_flit<={pub_meta_q,pub_bf_q?bf_packed:pub_a};
endmodule
module ot_hgi_coll_reduce_static_state_lane(
 input wire clk,load_v,input wire [3:0] load_tag,input wire [31:0] load_data,
 input wire wb,input wire [3:0] wb_tag,input wire [31:0] wb_data,
 input wire add_read,input wire [3:0] read_tag,input wire [31:0] external_data,
 input wire pub_read,input wire [3:0] pub_tag_a,pub_tag_b,
 output reg [31:0] acc,operand,pub_a,pub_b
);
 reg [31:0] state[0:15];
 always @(posedge clk)begin
  for(integer t=0;t<16;t=t+1)
   if((load_v&&load_tag==t)||(wb&&wb_tag==t))
    state[t]<=({32{load_v&&load_tag==t}}&load_data)|({32{wb&&wb_tag==t}}&wb_data);
  if(add_read)begin acc<=state[read_tag];operand<=external_data;end
  if(pub_read)begin pub_a<=state[pub_tag_a];pub_b<=state[pub_tag_b];end
 end
endmodule
`default_nettype wire

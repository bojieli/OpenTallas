// Additive full-depth CDC; model tools/hbm_collective_cdc_model.py.
// AW6 scales the preserved AW3 predecessor. Default disabled.
`timescale 1ns/1ps
// AW3/SYNC2 retained. FIFO storage is encoded at the write edge. The read
// domain captures the original codes before checking/correction: no encode of
// unchecked data, no scrub writes across clocks and no premature credit return.
// Local binary pointers/head phase use W6. Registered Gray/complement rails
// retain one Gray transition per transfer; incoherent synchronizer samples
// suppress permission, never supply a guessed pointer or release debt.
module ot_hbm_collective_protected_cdc #(parameter integer ENABLE=0,W=545,AW=6)(
 input wire wclk,wrst_n,in_v,output wire in_r,input wire [W-1:0] in_d,
 input wire rclk,rrst_n,output wire out_v,input wire out_r,
 output wire [W-1:0] out_d,output wire wempty,rempty,fault
);
 generate if(!ENABLE)begin:g_off
  assign in_r=0;assign out_v=0;assign out_d=0;assign wempty=0;assign rempty=0;assign fault=0;
 end else begin:g_on
 initial if(AW<3||AW>12||AW+3>64)$fatal(1,"protectedCDC parameter shape");
 import ot_gpu_w6_secded_pkg::*;
 localparam integer N=(W+63)/64;
 reg [N*72-1:0] mem[0:(1<<AW)-1];
 wire [63:0] wq,rq;wire wn,rn,wf,rf,hn,hf;
 wire [AW:0] wb=wq[AW:0],rb=rq[AW:0];wire [1:0] hp=rq[AW+2:AW+1];
 wire [N*64-1:0] hq;wire [N*64-1:0] padded={{(N*64-W){1'b0}},in_d};
 (* keep=1, dont_touch=1 *) reg [AW:0] wg,wgi,rg,rgi;
 (* keep=1, dont_touch=1, async_reg=1 *) reg [AW:0] rg_sync[0:1],rgi_sync[0:1],wg_sync[0:1],wgi_sync[0:1];
 wire rcoherent=(rg_sync[1]^rgi_sync[1])=={(AW+1){1'b1}};
 wire wcoherent=(wg_sync[1]^wgi_sync[1])=={(AW+1){1'b1}};
 wire wlocal=(wg^wgi)=={(AW+1){1'b1}}&&wg==(wb^(wb>>1));
 wire rlocal=(rg^rgi)=={(AW+1){1'b1}}&&rg==(rb^(rb>>1));
 wire full=wg=={~rg_sync[1][AW:AW-1],rg_sync[1][AW-2:0]};
 wire empty=rg==wg_sync[1];
 assign in_r=wn&&wlocal&&rcoherent&&!full;
 assign out_v=rn&&rlocal&&wcoherent&&hp==2&&hn;
 assign out_d=hq[W-1:0];
 assign wempty=wn&&wlocal&&rcoherent&&wg==rg_sync[1];
 assign rempty=rn&&rlocal&&wcoherent&&hp==0&&empty;
 assign fault=wf||rf||hf||(wn&&!wlocal)||(rn&&!rlocal)||hp==3;
 wire push=in_v&&in_r,pop=out_v&&out_r;
 wire [AW:0] wb_next=wb+1'b1,rb_next=rb+1'b1;
 wire capture=rn&&rlocal&&wcoherent&&hp==0&&!empty&&hn;
 reg [63:0] rd;
 always @*begin
  rd=rq;
  if(capture)rd[AW+2:AW+1]=1;
  else if(hp==1&&hn)rd[AW+2:AW+1]=2;
  else if(pop)begin rd[AW:0]=rb_next;rd[AW+2:AW+1]=0;end
 end
 ot_hbm_w2_protected_bank #(.WORDS(1)) u_write_pointer(
  .clk(wclk),.por_n(wrst_n),.load(push),.load_encoded(1'b0),.fatal(wn&&!wlocal),
  .d(64'(wb_next)),.encoded_d(72'b0),.q(wq),.encoded_q(),.normal(wn),.fault(wf),.repairing());
 ot_hbm_w2_protected_bank #(.WORDS(1)) u_read_pointer(
  .clk(rclk),.por_n(rrst_n),.load(rn),.load_encoded(1'b0),.fatal(rn&&(!rlocal||hp==3)),
  .d(rd),.encoded_d(72'b0),.q(rq),.encoded_q(),.normal(rn),.fault(rf),.repairing());
 ot_hbm_w2_protected_bank #(.WORDS(N)) u_head(
  .clk(rclk),.por_n(rrst_n),.load(capture),.load_encoded(1'b1),.fatal(1'b0),
  .d({N*64{1'b0}}),.encoded_d(mem[rb[AW-1:0]]),.q(hq),.encoded_q(),.normal(hn),.fault(hf),.repairing());
 integer j;
 always @(posedge wclk)if(push)
  for(j=0;j<N;j=j+1)mem[wb[AW-1:0]][j*72+:72]<=encode64(padded[j*64+:64]);
 always @(posedge wclk or negedge wrst_n)begin
  if(!wrst_n)begin wg<=0;wgi<={(AW+1){1'b1}};for(integer i=0;i<2;i=i+1)begin rg_sync[i]<=0;rgi_sync[i]<={(AW+1){1'b1}};end end
  else begin
   rg_sync[0]<=rg;rgi_sync[0]<=rgi;rg_sync[1]<=rg_sync[0];rgi_sync[1]<=rgi_sync[0];
   if(push)begin wg<=wb_next^(wb_next>>1);wgi<=~(wb_next^(wb_next>>1));end
  end
 end
 always @(posedge rclk or negedge rrst_n)begin
  if(!rrst_n)begin rg<=0;rgi<={(AW+1){1'b1}};for(integer i=0;i<2;i=i+1)begin wg_sync[i]<=0;wgi_sync[i]<={(AW+1){1'b1}};end end
  else begin
   wg_sync[0]<=wg;wgi_sync[0]<=wgi;wg_sync[1]<=wg_sync[0];wgi_sync[1]<=wgi_sync[0];
   if(pop)begin rg<=rb_next^(rb_next>>1);rgi<=~(rb_next^(rb_next>>1));end
  end
 end
 end endgenerate
endmodule

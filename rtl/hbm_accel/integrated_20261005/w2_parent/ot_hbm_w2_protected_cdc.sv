`timescale 1ns/1ps
// AW3/SYNC2 retained. FIFO storage is encoded at the write edge. The read
// domain captures the original codes before checking/correction: no encode of
// unchecked data, no scrub writes across clocks and no premature credit return.
// Local binary pointers/head phase use W6. Registered Gray/complement rails
// retain one Gray transition per transfer; incoherent synchronizer samples
// suppress permission, never supply a guessed pointer or release debt.
module ot_hbm_w2_protected_afifo #(parameter integer W=337)(
 input wire wclk,wrst_n,in_v,output wire in_r,input wire [W-1:0] in_d,
 input wire rclk,rrst_n,output wire out_v,input wire out_r,
 output wire [W-1:0] out_d,output wire wempty,rempty,fault
);
 import ot_gpu_w6_secded_pkg::*;
 localparam integer N=(W+63)/64;
 reg [N*72-1:0] mem[0:7];
 wire [63:0] wq,rq;wire wn,rn,wf,rf,hn,hf;
 wire [3:0] wb=wq[3:0],rb=rq[3:0];wire [1:0] hp=rq[5:4];
 wire [N*64-1:0] hq;wire [N*64-1:0] padded={{(N*64-W){1'b0}},in_d};
 (* keep=1, dont_touch=1 *) reg [3:0] wg,wgi,rg,rgi;
 (* keep=1, dont_touch=1, async_reg=1 *) reg [3:0] rg_sync[0:1],rgi_sync[0:1],wg_sync[0:1],wgi_sync[0:1];
 wire rcoherent=(rg_sync[1]^rgi_sync[1])==4'hf;
 wire wcoherent=(wg_sync[1]^wgi_sync[1])==4'hf;
 wire wlocal=(wg^wgi)==4'hf&&wg==(wb^(wb>>1));
 wire rlocal=(rg^rgi)==4'hf&&rg==(rb^(rb>>1));
 wire full=wg=={~rg_sync[1][3:2],rg_sync[1][1:0]};
 wire empty=rg==wg_sync[1];
 assign in_r=wn&&wlocal&&rcoherent&&!full;
 assign out_v=rn&&rlocal&&wcoherent&&hp==2&&hn;
 assign out_d=hq[W-1:0];
 assign wempty=wn&&wlocal&&rcoherent&&wg==rg_sync[1];
 assign rempty=rn&&rlocal&&wcoherent&&hp==0&&empty;
 assign fault=wf||rf||hf||(wn&&!wlocal)||(rn&&!rlocal)||hp==3;
 wire push=in_v&&in_r,pop=out_v&&out_r;
 wire [3:0] wb_next=wb+1'b1,rb_next=rb+1'b1;
 wire capture=rn&&rlocal&&wcoherent&&hp==0&&!empty&&hn;
 reg [63:0] rd;
 always @*begin
  rd=rq;
  if(capture)rd[5:4]=1;
  else if(hp==1&&hn)rd[5:4]=2;
  else if(pop)begin rd[3:0]=rb_next;rd[5:4]=0;end
 end
 ot_hbm_w2_protected_bank #(.WORDS(1)) u_write_pointer(
  .clk(wclk),.por_n(wrst_n),.load(push),.load_encoded(1'b0),.fatal(wn&&!wlocal),
  .d({60'b0,wb_next}),.encoded_d(72'b0),.q(wq),.encoded_q(),.normal(wn),.fault(wf),.repairing());
 ot_hbm_w2_protected_bank #(.WORDS(1)) u_read_pointer(
  .clk(rclk),.por_n(rrst_n),.load(rn),.load_encoded(1'b0),.fatal(rn&&(!rlocal||hp==3)),
  .d(rd),.encoded_d(72'b0),.q(rq),.encoded_q(),.normal(rn),.fault(rf),.repairing());
 ot_hbm_w2_protected_bank #(.WORDS(N)) u_head(
  .clk(rclk),.por_n(rrst_n),.load(capture),.load_encoded(1'b1),.fatal(1'b0),
  .d({N*64{1'b0}}),.encoded_d(mem[rb[2:0]]),.q(hq),.encoded_q(),.normal(hn),.fault(hf),.repairing());
 integer j;
 always @(posedge wclk)if(push)
  for(j=0;j<N;j=j+1)mem[wb[2:0]][j*72+:72]<=encode64(padded[j*64+:64]);
 always @(posedge wclk or negedge wrst_n)begin
  if(!wrst_n)begin wg<=0;wgi<=4'hf;for(integer i=0;i<2;i=i+1)begin rg_sync[i]<=0;rgi_sync[i]<=4'hf;end end
  else begin
   rg_sync[0]<=rg;rgi_sync[0]<=rgi;rg_sync[1]<=rg_sync[0];rgi_sync[1]<=rgi_sync[0];
   if(push)begin wg<=wb_next^(wb_next>>1);wgi<=~(wb_next^(wb_next>>1));end
  end
 end
 always @(posedge rclk or negedge rrst_n)begin
  if(!rrst_n)begin rg<=0;rgi<=4'hf;for(integer i=0;i<2;i=i+1)begin wg_sync[i]<=0;wgi_sync[i]<=4'hf;end end
  else begin
   wg_sync[0]<=wg;wgi_sync[0]<=wgi;wg_sync[1]<=wg_sync[0];wgi_sync[1]<=wgi_sync[0];
   if(pop)begin rg<=rb_next^(rb_next>>1);rgi<=~(rb_next^(rb_next>>1));end
  end
 end
endmodule

module ot_hbm_w2_protected_mreq_cdc(
 input wire clk_s,rst_s_n,clk_m,rst_m_n,
 input wire s_req_v,output wire s_req_rdy,input wire s_req_we,
 input wire [31:0] s_req_addr,input wire [255:0] s_req_wdata,
 input wire [31:0] s_req_wstrb,input wire [15:0] s_req_tag,
 output wire s_rsp_v,input wire s_rsp_rdy,output wire [15:0] s_rsp_tag,
 output wire s_rsp_we,output wire [255:0] s_rsp_data,
 output wire m_req_v,input wire m_req_rdy,output wire m_req_we,
 output wire [31:0] m_req_addr,output wire [255:0] m_req_wdata,
 output wire [31:0] m_req_wstrb,output wire [15:0] m_req_tag,
 input wire m_rsp_v,output wire m_rsp_rdy,input wire [15:0] m_rsp_tag,
 input wire m_rsp_we,input wire [255:0] m_rsp_data,
 output wire drained_s,fault
);
 wire f0,f1,req_empty_s,rsp_empty_s;
 ot_hbm_w2_protected_afifo #(.W(337)) u_req(
  .wclk(clk_s),.wrst_n(rst_s_n),.in_v(s_req_v),.in_r(s_req_rdy),
  .in_d({s_req_we,s_req_addr,s_req_wdata,s_req_wstrb,s_req_tag}),
  .rclk(clk_m),.rrst_n(rst_m_n),.out_v(m_req_v),.out_r(m_req_rdy),
  .out_d({m_req_we,m_req_addr,m_req_wdata,m_req_wstrb,m_req_tag}),
  .wempty(req_empty_s),.rempty(),.fault(f0));
 ot_hbm_w2_protected_afifo #(.W(273)) u_rsp(
  .wclk(clk_m),.wrst_n(rst_m_n),.in_v(m_rsp_v),.in_r(m_rsp_rdy),
  .in_d({m_rsp_tag,m_rsp_we,m_rsp_data}),
  .rclk(clk_s),.rrst_n(rst_s_n),.out_v(s_rsp_v),.out_r(s_rsp_rdy),
  .out_d({s_rsp_tag,s_rsp_we,s_rsp_data}),
  .wempty(),.rempty(rsp_empty_s),.fault(f1));
 assign drained_s=req_empty_s&&rsp_empty_s&&!fault;assign fault=f0||f1;
endmodule

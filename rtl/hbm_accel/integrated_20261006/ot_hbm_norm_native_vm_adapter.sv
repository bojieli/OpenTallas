`timescale 1ns/1ps
`default_nettype none
// Finite readyless vectorVM -> ONE held native root. Addresses remain in the
// frozen child. W6 read/write packets and control only; no provider/SRAM copy.
module ot_hbm_norm_native_vm_adapter #(
 parameter integer ENABLE=0,N=64,D=4096,AW=24
)(
 input wire clk,por_n,enroll,bind_accept,retained,owner_valid,input wire [72:0] frame,
 input wire [6:0] rank,
 input wire [4*N*AW-1:0] rd_addr,input wire [4*N-1:0] rd_re,
 output wire [4*N*32-1:0] rd_q,
 input wire [N-1:0] wr_we,input wire [N*AW-1:0] wr_addr,input wire [N*32-1:0] wr_data,
 output wire child_enable,read_permit,drained,publication_checked,fault,
 output wire read_v,input wire read_r,output wire [31:0] read_addr,
 output wire [7:0] read_tag,output wire [6:0] read_rank,
 input wire rsp_v,output wire rsp_r,input wire [1023:0] rsp_data,
 input wire [72:0] rsp_frame,input wire [7:0] rsp_tag,input wire [6:0] rsp_rank,
 output wire pub_v,input wire pub_r,output wire [31:0] pub_addr,
 output wire [1023:0] pub_data,
 input wire ACK_v,output wire ACK_r,input wire [72:0] ACK_frame,input wire [31:0] ACK_addr
);
 generate if(!ENABLE)begin:g_off
 assign rd_q=0;assign child_enable=1;assign read_permit=1;assign drained=1;
 assign publication_checked=0;assign fault=0;assign read_v=0;assign read_addr=0;assign read_tag=0;
 assign read_rank=0;assign rsp_r=0;assign pub_v=0;assign pub_addr=0;assign pub_data=0;assign ACK_r=0;
 end else begin:g_on
 initial if(N%32!=0||D%N!=0||AW>32||N<32||4*N>65535)$fatal(1,"native norm finite packet shape");
 localparam [3:0] IDLE=0,SCAN=1,REQ=2,RSP=3,READ_EDGE=4,REPLY_EDGE=5,WREQ=6,WACK=7,WRITE_EDGE=8;
 wire [127:0] q;reg [127:0] nq;wire cg,cc,cu,rg,rc,ru,wg,wc,wu;
 wire [3:0] state=q[3:0];wire [15:0] idx=q[19:4];wire [31:0] checked=q[51:20];
 wire [4*N*32-1:0] data;reg [4*N*32-1:0] nd;
 wire [N*32-1:0] write_data;
 wire good=cg&&rg&&wg;
 wire owned=retained&&owner_valid;
 assign fault=cu||ru||wu||q[52]||(state!=IDLE&&!owned);
 wire permission=good&&!fault&&owned;
 assign rd_q=data;
 assign drained=good&&!fault&&state==IDLE&&!(|rd_re)&&!(|wr_we);
 assign publication_checked=good&&!fault&&checked==D&&state==IDLE;
 assign child_enable=!ENABLE||(!retained&&good&&!fault)||
   (permission&&((state==IDLE&&!(|rd_re)&&!(|wr_we))||state==READ_EDGE||state==REPLY_EDGE||state==WRITE_EDGE));
 assign read_permit=state==READ_EDGE;
 wire [31:0] word_addr={{(32-AW){1'b0}},rd_addr[idx*AW+:AW]};
 assign read_addr={word_addr[31:5],5'b0};assign read_tag=idx[7:0];assign read_rank=q[59:53];
 assign read_v=permission&&state==REQ;
 assign rsp_r=permission&&state==RSP;
 assign pub_addr={{(32-AW){1'b0}},wr_addr[idx*AW+:AW]};
 assign pub_data=write_data[idx*32+:1024];
 assign pub_v=permission&&state==WREQ;
 assign ACK_r=permission&&state==WACK;
 wire reply_ok=rsp_frame==frame&&rsp_tag==read_tag&&rsp_rank==read_rank;
 wire ack_ok=ACK_frame==frame&&ACK_addr==pub_addr;
 reg shape_ok;
 always @*begin
  shape_ok=1;
  for(integer k=0;k<N;k=k+1)
   if(!wr_we[k]||wr_addr[k*AW+:AW]!=wr_addr[0+:AW]+k)shape_ok=0;
  if(|wr_addr[0+:5])shape_ok=0;
 end
 always @*begin
  nq=q;nd=data;
  if(!owned&&state!=IDLE)nq[52]=1;
  if(bind_accept&&state==IDLE)nq[59:53]=rank;
  if(enroll&&state==IDLE)begin nq[51:20]=0;nq[19:4]=0;end
  if(permission)case(state)
   IDLE:begin
    if(|wr_we)begin
     if(!shape_ok||checked+N>D)nq[52]=1;
     else begin nq[19:4]=0;nq[3:0]=WREQ;end
    end else if(|rd_re)begin nq[19:4]=0;nq[3:0]=SCAN;end
   end
   SCAN:if(idx==4*N)nq[3:0]=READ_EDGE;
        else if(rd_re[idx])nq[3:0]=REQ;
        else nq[19:4]=idx+1;
   REQ:if(read_v&&read_r)nq[3:0]=RSP;
   RSP:if(rsp_v&&rsp_r)begin
    if(!reply_ok)nq[52]=1;
    else begin nd[idx*32+:32]=rsp_data[word_addr[4:0]*32+:32];nq[19:4]=idx+1;nq[3:0]=SCAN;end
   end
   READ_EDGE:nq[3:0]=REPLY_EDGE;
   REPLY_EDGE:nq[3:0]=IDLE;
   WREQ:if(pub_v&&pub_r)nq[3:0]=WACK;
   WACK:if(ACK_v&&ACK_r)begin
    if(!ack_ok)nq[52]=1;
    else begin nq[51:20]=checked+32;
     if(idx+32==N)nq[3:0]=WRITE_EDGE;
     else begin nq[19:4]=idx+32;nq[3:0]=WREQ;end
    end
   end
   WRITE_EDGE:nq[3:0]=IDLE;
   default:nq[52]=1;
  endcase
 end
 ot_hbm_accel_gu_metadata #(.WIDTH(128)) control(.clk(clk),.rst_n(por_n),.we(cg&&nq!=q),.next_data(nq),.data(q),.good(cg),.ce(cc),.due(cu));
 ot_hbm_accel_gu_metadata #(.WIDTH(4*N*32)) read_packet(.clk(clk),.rst_n(por_n),.we(permission&&state==RSP&&rsp_v&&reply_ok),.next_data(nd),.data(data),.good(rg),.ce(rc),.due(ru));
 ot_hbm_accel_gu_metadata #(.WIDTH(N*32)) write_packet(.clk(clk),.rst_n(por_n),.we(permission&&state==IDLE&&(|wr_we)&&shape_ok),.next_data(wr_data),.data(write_data),.good(wg),.ce(wc),.due(wu));
 end endgenerate
endmodule
`default_nettype wire

`timescale 1ns/1ps
`default_nettype none
// Finite readyless vectorVM -> ONE held native root. Addresses remain in the
// frozen child. W6 read/write packets and control only; no provider/SRAM copy.
module ot_hbm_norm_native_vm_adapter #(
 parameter integer ENABLE=0,N=64,D=4096,AW=24,PUBLISH_QUANT=0,INPUT_CP=0
)(
 input wire clk,por_n,enroll,bind_accept,retained,owner_valid,input wire [72:0] frame,
 input wire [6:0] rank,
 input wire [4*N*AW-1:0] rd_addr,input wire [4*N-1:0] rd_re,
 output wire [4*N*32-1:0] rd_q,
 input wire [N-1:0] wr_we,input wire [N*AW-1:0] wr_addr,input wire [N*32-1:0] wr_data,
 input wire q_valid,input wire [7:0] q_index,input wire [N*8-1:0] q_codes,
 input wire [(N/32)*10-1:0] q_exp,input wire [N*16-1:0] q_bf16,
 input wire [72:0] q_frame,input wire [31:0] quant_base,
 output wire cp_req_v,input wire cp_req_r,output wire [336:0] cp_req,
 input wire cp_rsp_v,output wire cp_rsp_r,input wire [272:0] cp_rsp,
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
 assign cp_req_v=0;assign cp_req=0;assign cp_rsp_r=0;
 assign rd_q=0;assign child_enable=1;assign read_permit=1;assign drained=1;
 assign publication_checked=0;assign fault=0;assign read_v=0;assign read_addr=0;assign read_tag=0;
 assign read_rank=0;assign rsp_r=0;assign pub_v=0;assign pub_addr=0;assign pub_data=0;assign ACK_r=0;
 end else begin:g_on
 initial if(N%32!=0||D%N!=0||AW>32||(INPUT_CP&&AW>30)||N<32||4*N>65535||(PUBLISH_QUANT&&D/N>256))$fatal(1,"native norm finite packet shape");
 localparam [3:0] IDLE=0,SCAN=1,REQ=2,RSP=3,READ_EDGE=4,REPLY_EDGE=5,WREQ=6,WACK=7,WRITE_EDGE=8,QREQ=9,QACK=10,QEDGE=11;
 localparam integer QB=N*24+(N/32)*10,CR=(N*8+1023)/1024,ER=((N/32)*10+1023)/1024,BR=(N*16+1023)/1024,QR=CR+ER+BR;
 localparam integer CW=PUBLISH_QUANT?160:128;
 wire [159:0] q;reg [159:0] nq;
 if(!PUBLISH_QUANT)assign q[159:128]=0;wire cg,cc,cu,rg,rc,ru,wg,wc,wu;
 wire [3:0] state=q[3:0];wire [15:0] idx=q[19:4];wire [31:0] checked=q[51:20];
 wire [4*N*32-1:0] data;reg [4*N*32-1:0] nd;
 wire [N*32-1:0] write_data;
 wire [QB-1:0] quant_data;wire qg,qc,qu;
 wire quant_capture=PUBLISH_QUANT&&permission&&state==IDLE&&!q[100]&&q_valid&&(!q[101]||q_index!=q[99:92]);
 if(PUBLISH_QUANT)begin:g_quant
  ot_hbm_accel_gu_metadata #(.WIDTH(QB)) quant_packet(.clk(clk),.rst_n(por_n),.we(quant_capture),.next_data({q_bf16,q_exp,q_codes}),.data(quant_data),.good(qg),.ce(qc),.due(qu));
 end else begin:g_no_quant
  assign quant_data=0;assign qg=1;assign qc=0;assign qu=0;
 end
 wire [CR*1024-1:0] codes_padded={{(CR*1024-N*8){1'b0}},quant_data[0+:N*8]};
 wire [ER*1024-1:0] scale_padded={{(ER*1024-(N/32)*10){1'b0}},quant_data[N*8+:(N/32)*10]};
 wire [BR*1024-1:0] bf16_padded={{(BR*1024-N*16){1'b0}},quant_data[N*8+(N/32)*10+:N*16]};
 wire [15:0] quant_row=q[117:102];
 wire [1023:0] quant_out=quant_row<CR?codes_padded[quant_row*1024+:1024]:quant_row<CR+ER?scale_padded[(quant_row-CR)*1024+:1024]:bf16_padded[(quant_row-CR-ER)*1024+:1024];
 wire good=cg&&rg&&wg&&qg;
 wire owned=retained&&owner_valid;
 assign fault=cu||ru||wu||qu||q[52]||(state!=IDLE&&!owned);
 wire permission=good&&!fault&&owned;
 assign rd_q=data;
 assign drained=good&&!fault&&state==IDLE&&!(|rd_re)&&!(|wr_we)&&!quant_capture&&(!PUBLISH_QUANT||!q[100]);
 assign publication_checked=good&&!fault&&checked==D&&state==IDLE&&(!PUBLISH_QUANT||(q[91:60]==(D/N)*QR&&!q[100]&&!quant_capture));
 assign child_enable=!ENABLE||(!retained&&good&&!fault)||
   (permission&&((state==IDLE&&!(|rd_re)&&!(|wr_we)&&!quant_capture&&!q[100])||state==READ_EDGE||state==REPLY_EDGE||(state==WRITE_EDGE&&!q[100])||state==QEDGE));
 assign read_permit=state==READ_EDGE;
 wire [31:0] word_addr={{(32-AW){1'b0}},rd_addr[idx*AW+:AW]};
 assign read_addr={word_addr[31:5],5'b0};assign read_tag=idx[7:0];assign read_rank=q[59:53];
 assign read_v=!INPUT_CP&&permission&&state==REQ;
 assign cp_req_v=INPUT_CP&&permission&&state==REQ;
 assign cp_req={1'b0,word_addr[29:3],5'b0,256'd0,32'd0,idx};
 assign cp_rsp_r=INPUT_CP&&permission&&state==RSP;
 assign rsp_r=!INPUT_CP&&permission&&state==RSP;
 assign pub_addr=state==QREQ||state==QACK?q[159:128]+q[99:92]*QR*32+quant_row*32:{{(32-AW){1'b0}},wr_addr[idx*AW+:AW]};
 assign pub_data=state==QREQ||state==QACK?quant_out:write_data[idx*32+:1024];
 assign pub_v=permission&&(state==WREQ||state==QREQ);
 assign ACK_r=permission&&(state==WACK||state==QACK);
 wire reply_ok=INPUT_CP?(cp_rsp[272:257]==idx&&!cp_rsp[256]):(rsp_frame==frame&&rsp_tag==read_tag&&rsp_rank==read_rank);
 wire response_v=INPUT_CP?cp_rsp_v:rsp_v;
 wire response_r=INPUT_CP?cp_rsp_r:rsp_r;
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
  if(enroll&&state==IDLE)begin nq[51:20]=0;nq[19:4]=0;nq[117:60]=0;
   if(PUBLISH_QUANT)begin
    nq[159:128]=quant_base;
    if((|quant_base[4:0])||({1'b0,quant_base}+(D/N)*QR*32)>33'h100000000)nq[52]=1;
   end
  end
  if(PUBLISH_QUANT&&!q_valid)nq[101]=0;
  if(quant_capture)begin
   nq[100]=1;nq[101]=1;nq[99:92]=q_index;nq[117:102]=0;
   if(q_frame!=frame||q_index!=q[91:60]/QR)nq[52]=1;
  end
  if(permission)case(state)
   IDLE:begin
    if(|wr_we)begin
     if(!shape_ok||checked+N>D)nq[52]=1;
     else begin nq[19:4]=0;nq[3:0]=WREQ;end
    end else if(quant_capture||q[100])nq[3:0]=QREQ;
    else if(|rd_re)begin nq[19:4]=0;nq[3:0]=SCAN;end
   end
   SCAN:if(idx==4*N)nq[3:0]=READ_EDGE;
        else if(rd_re[idx])nq[3:0]=REQ;
        else nq[19:4]=idx+1;
   REQ:if(INPUT_CP?(cp_req_v&&cp_req_r):(read_v&&read_r))nq[3:0]=RSP;
   RSP:if(response_v&&response_r)begin
    if(!reply_ok)nq[52]=1;
    else begin nd[idx*32+:32]=INPUT_CP?cp_rsp[word_addr[2:0]*32+:32]:rsp_data[word_addr[4:0]*32+:32];nq[19:4]=idx+1;nq[3:0]=SCAN;end
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
   WRITE_EDGE:nq[3:0]=PUBLISH_QUANT&&q[100]?QREQ:IDLE;
   QREQ:if(pub_v&&pub_r)nq[3:0]=QACK;
   QACK:if(ACK_v&&ACK_r)begin
    if(!ack_ok)nq[52]=1;
    else begin nq[91:60]=q[91:60]+1;
     if(quant_row+1==QR)begin nq[100]=0;nq[3:0]=QEDGE;end
     else begin nq[117:102]=quant_row+1;nq[3:0]=QREQ;end
    end
   end
   QEDGE:nq[3:0]=IDLE;
   default:nq[52]=1;
  endcase
 end
 ot_hbm_accel_gu_metadata #(.WIDTH(CW)) control(.clk(clk),.rst_n(por_n),.we(cg&&nq!=q),.next_data(nq[0+:CW]),.data(q[0+:CW]),.good(cg),.ce(cc),.due(cu));
 ot_hbm_accel_gu_metadata #(.WIDTH(4*N*32)) read_packet(.clk(clk),.rst_n(por_n),.we(permission&&state==RSP&&response_v&&reply_ok),.next_data(nd),.data(data),.good(rg),.ce(rc),.due(ru));
 ot_hbm_accel_gu_metadata #(.WIDTH(N*32)) write_packet(.clk(clk),.rst_n(por_n),.we(permission&&state==IDLE&&(|wr_we)&&shape_ok),.next_data(wr_data),.data(write_data),.good(wg),.ce(wc),.due(wu));
 end endgenerate
endmodule
`default_nettype wire

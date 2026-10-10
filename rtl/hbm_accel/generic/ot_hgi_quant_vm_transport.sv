`timescale 1ns/1ps
`default_nettype none
// CP ABI is existing337/273 sector path; rsp[256] is WRITE_ECHO, NOT fault.
// Native bypass is separate, byte/cycle unchanged; ENABLE=0 has no requests.
// hgi-takeover 2026-10-09 (VM fast path): up to 4 requests in flight.  A request's address / lane bookkeeping advances
// when it is staged; a 4-deep descriptor FIFO {write, step, lane, part, last read, last write, final, tag} pairs the
// in-order responses with their requests.  Every response is accepted the cycle it arrives (rsp_r = 1).
// MUTANT 4 (ordering): responses are paired with the NEWEST descriptor instead of the oldest -> must FAIL.
module ot_hgi_quant_vm_transport #(parameter ENABLE=0, DEPTH=32, MUTANT=0)(
 input wire clk,rst_n,input wire [1408:0] cmd,
 output wire ready,output reg done,output reg fault,output wire drained,
 output wire req_v,input wire req_r,output wire [336:0] req,
 input wire rsp_v,output wire rsp_r,input wire [272:0] rsp,
 input wire provider_fault
);
 localparam PW=$clog2(DEPTH),CW=$clog2(DEPTH+1);
 wire [127:0] incoming_header=cmd[1+:128];
 wire [255:0] ca=cmd[385+:256],co=cmd[1153+:256];
 reg [255:0] a,o;reg validating;
 wire [127:0] ch=header;
 reg busy,bad;
 reg seat_v;reg [336:0] seat;
 reg response_v;reg [272:0] response;
 reg [127:0] header;
 reg [19:0] n,m,read_row,read_col,write_row,write_col;
 reg [39:0] launched,returned,finished;
 reg [31:0] read_addr,write_addr,read_rowbase,write_rowbase,rs,ws;
 reg [15:0] ri,wi;
 reg [3:0] seat_step,pending_step;reg [2:0] seat_lane,pending_lane;
 reg [31:0] abase,obase;
 reg [5:0] read_part,write_part;
 reg [15:0] next_tag,pending_tag;
 reg [1023:0] x;
 reg launch;
 reg [PW-1:0] head,tail;
 reg [CW-1:0] reserved,queued;
 reg [511:0] result[0:DEPTH-1];
 wire vo,qfault,decode_fault;wire [511:0] y;
 ot_hgi_quant_decode quant(.clk(clk),.rst_n(rst_n),.v(launch),
 .generic_enable(1'b1),.legacy_fp4(1'b0),.header(header),.x(x),
 .vo(vo),.y(y),.fault(qfault),.decode_fault(decode_fault));
 wire [15:0] air=a[5]?16'd0:(a[135:120]==0?16'd1:a[135:120]);
 wire [15:0] oir=o[135:120]==0?16'd1:o[135:120];
 wire [63:0] aspan=(a[87:68]-20'd1)*{32'd0,a[119:88]}+(a[67:48]-20'd1)*{48'd0,air};
 wire [63:0] ospan=(o[87:68]-20'd1)*{32'd0,o[119:88]}+(o[67:48]-20'd1)*{48'd0,oir};
 wire same_geometry=a[47:8]==o[47:8] && air==oir && a[119:88]==o[119:88];
 wire shape_ok=ch[127:124]==4 && ch[123:118]>=4 && ch[123:118]<=6 &&
 ch[99:93]==7'b0010001 && !ch[92] &&
 (ch[123:118]!=6 || ch[71:64]==16) && a[1:0]==1 && o[1:0]==1 &&
 a[4:2]==0 && (o[4:2]==0 || o[4:2]==1) && !o[5] &&
 a[87:68]!=0 && a[87:68]==o[87:68] && a[67:48]!=0 && a[67:48]==o[67:48] &&
 (ch[123:118]==6 ? a[51:48]==0 : a[52:48]==0) &&
 ({24'd0,a[47:8]}+aspan<64'd262144) && ({24'd0,o[47:8]}+ospan<64'd262144) &&
 // In-place identical geometry is safe only when rows do not alias each other.
 (!same_geometry || o[87:68]==1 || o[119:88]>(o[67:48]-20'd1)*{16'd0,oir}) &&
 (same_geometry || ({24'd0,a[47:8]}+aspan<o[47:8]) ||
 ({24'd0,o[47:8]}+ospan<a[47:8]));
 assign ready=ENABLE&&rst_n&&!busy;
 // ---------------------------------------------------------------- in-flight descriptors (in request order)
 localparam integer DW=1+4+3+6+1+1+1+16;
 reg [DW-1:0] pd [0:3]; reg [1:0] pd_h,pd_t; reg [2:0] pd_n; reg [DW-1:0] seat_d;
 wire pending=pd_n!=0;
 assign drained=!busy&&!pending&&reserved==0;
 wire reads_done=read_row==m;
 wire write_offer=queued!=0 && (reads_done || (reserved>=DEPTH && MUTANT!=3));
 wire read_offer=!reads_done && (read_part!=0 || (reserved<DEPTH || MUTANT==3));
 assign req_v=ENABLE&&rst_n&&seat_v&&!bad;
 wire [31:0] word_addr=write_offer?write_addr:read_addr;
 wire burst_write=wi==1 && write_addr[2:0]==0 && n-write_col>=8 && 32-write_part>=8;
 wire burst_read=ri==1 && read_addr[2:0]==0 && n-read_col>=8 && 32-read_part>=8;
 wire [3:0] offer_step=write_offer?(burst_write?4'd8:4'd1):(burst_read?4'd8:4'd1);
 reg [255:0] wd;
 always @* begin
  wd=0;
  if(burst_write)for(integer j=0;j<8;j=j+1)
    wd[j*32+:32]={result[head][(write_part+j)*16+:16],16'd0};
  else wd[write_addr[2:0]*32+:32]={result[head][write_part*16+:16],16'd0};
 end
 wire [31:0] write_mask=burst_write?32'hffffffff:(32'hf<<(write_addr[2:0]*4));
 assign req=seat;
 assign rsp_r=ENABLE&&rst_n;                     // never back-pressured: one response a cycle is processed
 wire take_req=req_v&&req_r,take_rsp=response_v;
 // the descriptor this response belongs to (MUTANT 4: the newest one)
 wire [DW-1:0] dsc=(MUTANT==4)?pd[pd_t-2'd1]:pd[pd_h];
 wire d_we=dsc[DW-1]; wire [3:0] d_step=dsc[DW-2-:4]; wire [2:0] d_lane=dsc[DW-6-:3]; wire [5:0] d_part=dsc[DW-9-:6];
 wire d_lastr=dsc[18]; wire d_lastw=dsc[17]; wire d_final=dsc[16]; wire [15:0] d_tag=dsc[15:0];
 wire reply_ok=response[272:257]==d_tag && response[256]==d_we;
 // staging the next request (the seat is free, or is being taken this cycle) while fewer than 4 are in flight
 // (req_r is NOT in this cone: the boundary stays registered -- a seat is restaged the cycle after it is taken)
 wire stage=busy&&!validating&&!bad&&!launch&&(write_offer||read_offer)&&!seat_v&&pd_n<3'd4;
 wire s_last_read=!write_offer&&(read_part+offer_step==32 || read_col+offer_step==n);
 wire s_last_write=write_offer&&(write_part+offer_step==32 || write_col+offer_step==n);
 wire s_final=s_last_write&&write_row+1==m&&write_col+offer_step==n;
 wire reserve_read=stage&&!write_offer&&read_part==0;
 wire retire_write=take_rsp&&reply_ok&&d_we&&d_lastw&&!bad;
 wire [PW-1:0] head_next=head==DEPTH-1?0:head+1;
 wire [PW-1:0] tail_next=tail==DEPTH-1?0:tail+1;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin
   a<=0;o<=0;validating<=0;busy<=0;bad<=0;seat_v<=0;seat<=0;response_v<=0;response<=0;header<=0;n<=0;m<=0;
   abase<=0;obase<=0;read_row<=0;read_col<=0;write_row<=0;write_col<=0;
   read_addr<=0;write_addr<=0;read_rowbase<=0;write_rowbase<=0;rs<=0;ws<=0;ri<=0;wi<=0;
   seat_step<=0;pending_step<=0;seat_lane<=0;pending_lane<=0;launched<=0;returned<=0;finished<=0;
   read_part<=0;write_part<=0;next_tag<=0;pending_tag<=0;
   launch<=0;head<=0;tail<=0;reserved<=0;queued<=0;done<=0;fault<=0;pd_h<=0;pd_t<=0;pd_n<=0;
  end else begin
   done<=0;launch<=0;
   response_v<=rsp_v; if(rsp_v) response<=rsp;
   if(ready&&cmd[0])begin
    a<=ca;o<=co;header<=incoming_header;validating<=1;busy<=1;bad<=0;fault<=0;
    n<=ca[67:48];m<=ca[87:68];abase<=ca[39:8];obase<=co[39:8];
    read_addr<=ca[39:8];write_addr<=co[39:8];read_rowbase<=ca[39:8];write_rowbase<=co[39:8];
    read_row<=0;read_col<=0;write_row<=0;write_col<=0;rs<=ca[119:88];ws<=co[119:88];
    ri<=ca[5]?16'd0:(ca[135:120]==0?16'd1:ca[135:120]);
    wi<=co[135:120]==0?16'd1:co[135:120];
    launched<=0;returned<=0;finished<=0;read_part<=0;write_part<=0;
    reserved<=0;queued<=0;head<=0;tail<=0;
   end
   if(busy&&validating)begin
    validating<=0;
    if(!shape_ok)begin bad<=1;fault<=1;busy<=0;done<=1;end
   end
   if(busy&&!validating)begin
    if(take_req&&!stage)seat_v<=0;
    if(bad)seat_v<=0;
    if(provider_fault||decode_fault)begin bad<=1;fault<=1;end
    // ---- stage the next request and advance its stream at once
    if(stage)begin
     seat_v<=1;seat<={write_offer,{word_addr[29:3],5'd0},write_offer?wd:256'd0,write_offer?write_mask:32'hffffffff,next_tag};
     next_tag<=next_tag+1;
     seat_d<={write_offer,offer_step,word_addr[2:0],write_offer?write_part:read_part,s_last_read,s_last_write,s_final,next_tag};
     if(write_offer)begin
      if(s_last_write)begin head<=head_next;write_part<=0;end
      else write_part<=write_part+offer_step;
      if(write_col+offer_step==n)begin
       write_row<=write_row+1;write_col<=0;write_rowbase<=write_rowbase+ws;write_addr<=write_rowbase+ws;
      end else begin write_col<=write_col+offer_step;write_addr<=write_addr+offer_step*wi;end
     end else begin
      if(read_col+offer_step==n)begin
       read_row<=read_row+1;read_col<=0;read_rowbase<=read_rowbase+rs;read_addr<=read_rowbase+rs;
      end else begin read_col<=read_col+offer_step;read_addr<=read_addr+offer_step*ri;end
      if(s_last_read)read_part<=0; else read_part<=read_part+offer_step;
     end
    end
    // ---- responses, in request order
    if(take_rsp)begin
     pd_h<=pd_h+2'd1;
     if(!reply_ok)begin bad<=1;fault<=1;end
     else if(!bad)begin
      if(d_we)begin
       if(d_lastw)finished<=finished+1;
      end else if(d_lastr)begin launch<=1;launched<=launched+1;end
     end
    end
    // a request enters the in-flight FIFO when the station takes it (a seat dropped by a fault never does)
    if(take_req)begin pd[pd_t]<=seat_d;pd_t<=pd_t+2'd1;end
    pd_n<=pd_n+{2'd0,take_req}-{2'd0,take_rsp};
    if(vo)begin
     returned<=returned+1;
     if(!bad && MUTANT!=1)begin
      result[tail]<=y;tail<=tail_next;
      if(qfault)begin bad<=1;fault<=1;end
     end
    end
    // A reservation includes unread assembly, nonelastic arithmetic and ACK debt.
    if(!bad)begin
     case({reserve_read,retire_write})
      2'b10:reserved<=reserved+1;2'b01:reserved<=reserved-1;
     endcase
     case({vo&&MUTANT!=1,stage&&s_last_write})
      2'b10:queued<=queued+1;2'b01:queued<=queued-1;
     endcase
    end
    if(bad&&!pending&&!seat_v&&!launch&&returned==launched)begin
     busy<=0;reserved<=0;queued<=0;done<=1;fault<=1;
    end else if(!bad && take_rsp&&reply_ok&&d_we&&d_lastw&&(d_final || MUTANT==2))begin busy<=0;done<=1;end
   end
  end
 end
 // Independent lane capture prevents Yosys variable-LHS priority mux chains
 // from carrying raw cmd.valid through all1024 input assembly bits.
 // A beat's first read response clears the lanes it does not write (the next beat's reads may be in flight while the
 // previous beat is being launched: the clear happens at the response, never at the request).
 for(genvar lane=0;lane<32;lane=lane+1)begin:g_input_lane
  always @(posedge clk or negedge rst_n)begin
   if(!rst_n)x[lane*32+:32]<=0;
   else if(ready&&cmd[0])x[lane*32+:32]<=0;
   else if(take_rsp&&reply_ok&&!d_we&&!bad)begin
    if(d_step==8 && lane>=d_part && lane<d_part+8)
      x[lane*32+:32]<=response[(lane-d_part)*32+:32];
    else if(d_step==1 && lane==d_part)
      x[lane*32+:32]<=response[d_lane*32+:32];
    else if(d_part==0)
      x[lane*32+:32]<=0;
   end
  end
 end
 initial if(DEPTH<24)$fatal(1,"QDQ result reservations require23 inflight+assembly");
endmodule
`default_nettype wire

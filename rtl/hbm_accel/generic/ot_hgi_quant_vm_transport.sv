`timescale 1ns/1ps
`default_nettype none
// CP ABI is existing337/273 sector path; rsp[256] is WRITE_ECHO, NOT fault.
// Native bypass is separate, byte/cycle unchanged; ENABLE=0 has no requests.
module ot_hgi_quant_vm_transport #(parameter ENABLE=0, DEPTH=32, MUTANT=0)(
 input wire clk,rst_n,input wire [1408:0] cmd,
 output wire ready,output reg done,output reg fault,output wire drained,
 output wire req_v,input wire req_r,output wire [336:0] req,
 input wire rsp_v,output wire rsp_r,input wire [272:0] rsp,
 input wire provider_fault
);
 localparam PW=$clog2(DEPTH),CW=$clog2(DEPTH+1);
 wire [127:0] ch=cmd[1+:128];
 wire [255:0] a=cmd[385+:256],o=cmd[1153+:256];
 reg busy,bad,pending,pending_write;
 reg seat_v;reg [336:0] seat;
 reg [127:0] header;
 reg [19:0] n,read_words,launched,returned,finished;
 reg [31:0] abase,obase;
 reg [1:0] read_part,write_part;
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
 wire shape_ok=ch[127:124]==4 && ch[123:118]>=4 && ch[123:118]<=6 &&
 ch[99:93]==7'b0010001 && !ch[92] &&
 (ch[123:118]!=6 || ch[71:64]==16) && a[1:0]==1 && o[1:0]==1 &&
 a[4:2]==0 && (o[4:2]==0 || o[4:2]==1) &&
 !a[5] && !o[5] && a[135:120]<=1 && o[135:120]<=1 &&
 a[87:68]==1 && o[87:68]==1 && a[67:48]!=0 && a[67:48]==o[67:48] &&
 (ch[123:118]==6 ? a[51:48]==0 : a[52:48]==0) &&
 a[47:26]==0 && o[47:26]==0 && a[10:8]==0 && o[10:8]==0 &&
 ({1'b0,a[47:8]}+a[67:48]<=41'd262144) &&
 ({1'b0,o[47:8]}+o[67:48]<=41'd262144) &&
 // Same-base same-geometry in-place is safe: the complete block is read before publication.
 ((a[47:8]==o[47:8]) || ({1'b0,a[47:8]}+a[67:48]<=o[47:8]) ||
 ({1'b0,o[47:8]}+o[67:48]<=a[47:8]));
 assign ready=ENABLE&&rst_n&&!busy;
 assign drained=!busy&&!pending&&reserved==0;
 wire write_offer=queued!=0 && (read_words>=n || (reserved>=DEPTH && MUTANT!=3));
 wire read_offer=read_words<n && (read_part!=0 || (reserved<DEPTH || MUTANT==3));
 assign req_v=ENABLE&&rst_n&&seat_v&&!bad;
 wire [31:0] word_addr=write_offer ? obase+finished*32+write_part*8 : abase+read_words;
 reg [255:0] wd;
 always @* begin
  wd=0;
  for(integer j=0;j<8;j=j+1)wd[j*32+:32]={result[head][(write_part*8+j)*16+:16],16'd0};
 end
 assign req=seat;
 assign rsp_r=ENABLE&&rst_n&&pending;
 wire take_req=req_v&&req_r,take_rsp=rsp_v&&rsp_r;
 wire reply_ok=rsp[272:257]==pending_tag && rsp[256]==pending_write;
 wire last_read=(read_part==3 || read_words+8==n);
 wire last_write=(write_part==3 || finished*32+write_part*8+8==n);
 wire reserve_read=take_req&&!req[336]&&read_part==0;
 wire retire_write=take_rsp&&reply_ok&&pending_write&&last_write&&!bad;
 wire [PW-1:0] head_next=head==DEPTH-1?0:head+1;
 wire [PW-1:0] tail_next=tail==DEPTH-1?0:tail+1;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin
   busy<=0;bad<=0;pending<=0;pending_write<=0;seat_v<=0;seat<=0;header<=0;n<=0;
   abase<=0;obase<=0;read_words<=0;launched<=0;returned<=0;finished<=0;
   read_part<=0;write_part<=0;next_tag<=0;pending_tag<=0;
   x<=0;launch<=0;head<=0;tail<=0;reserved<=0;queued<=0;done<=0;fault<=0;
  end else begin
   done<=0;launch<=0;
   if(ready&&cmd[0])begin
    fault<=0;bad<=!shape_ok;
    if(!shape_ok)begin done<=1;fault<=1;end
    else begin busy<=1;header<=ch;n<=a[67:48];abase<=a[39:8];obase<=o[39:8];
     read_words<=0;launched<=0;returned<=0;finished<=0;read_part<=0;write_part<=0;
     reserved<=0;queued<=0;head<=0;tail<=0;x<=0;end
   end
   if(busy)begin
    if(!bad&&!pending&&!seat_v&&!launch&&(write_offer||read_offer))begin
     seat_v<=1;seat<={write_offer,word_addr<<2,write_offer?wd:256'd0,32'hffffffff,next_tag};
    end
    if(bad)seat_v<=0;
    if(provider_fault||decode_fault)begin bad<=1;fault<=1;end
    if(take_req)begin
     if(!req[336]&&read_part==0)x<=0;
     seat_v<=0;
     pending<=1;pending_write<=req[336];pending_tag<=next_tag;next_tag<=next_tag+1;end
    if(take_rsp)begin
     pending<=0;
     if(!reply_ok)begin bad<=1;fault<=1;end
     else if(!bad)begin
      if(pending_write)begin
       if(last_write)begin finished<=finished+1;head<=head_next;write_part<=0;end
       else write_part<=write_part+1;
      end else begin
       x[read_part*256+:256]<=rsp[255:0];read_words<=read_words+8;
       if(last_read)begin launch<=1;launched<=launched+1;read_part<=0;end
       else read_part<=read_part+1;
      end
     end
    end
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
     case({vo&&MUTANT!=1,retire_write})
      2'b10:queued<=queued+1;2'b01:queued<=queued-1;
     endcase
    end
    if(bad&&!pending&&!launch&&returned==launched)begin
     busy<=0;reserved<=0;queued<=0;done<=1;fault<=1;
    end else if(!bad && take_rsp&&reply_ok&&pending_write&&last_write &&
      (finished+1==(n+31)/32 || MUTANT==2))begin busy<=0;done<=1;end
   end
  end
 end
 initial if(DEPTH<24)$fatal(1,"QDQ result reservations require23 inflight+assembly");
endmodule
`default_nettype wire

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
 (o[87:68]==1 || o[119:88]>(o[67:48]-20'd1)*{16'd0,oir}) &&
 (same_geometry || ({24'd0,a[47:8]}+aspan<o[47:8]) ||
 ({24'd0,o[47:8]}+ospan<a[47:8]));
 assign ready=ENABLE&&rst_n&&!busy;
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
 assign rsp_r=ENABLE&&rst_n&&pending;
 wire take_req=req_v&&req_r,take_rsp=rsp_v&&rsp_r;
 wire reply_ok=rsp[272:257]==pending_tag && rsp[256]==pending_write;
 wire last_read=(read_part+pending_step==32 || read_col+pending_step==n);
 wire last_write=(write_part+pending_step==32 || write_col+pending_step==n);
 wire reserve_read=take_req&&!req[336]&&read_part==0;
 wire retire_write=take_rsp&&reply_ok&&pending_write&&last_write&&!bad;
 wire [PW-1:0] head_next=head==DEPTH-1?0:head+1;
 wire [PW-1:0] tail_next=tail==DEPTH-1?0:tail+1;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin
   busy<=0;bad<=0;pending<=0;pending_write<=0;seat_v<=0;seat<=0;header<=0;n<=0;m<=0;
   abase<=0;obase<=0;read_row<=0;read_col<=0;write_row<=0;write_col<=0;
   read_addr<=0;write_addr<=0;read_rowbase<=0;write_rowbase<=0;rs<=0;ws<=0;ri<=0;wi<=0;
   seat_step<=0;pending_step<=0;seat_lane<=0;pending_lane<=0;launched<=0;returned<=0;finished<=0;
   read_part<=0;write_part<=0;next_tag<=0;pending_tag<=0;
   x<=0;launch<=0;head<=0;tail<=0;reserved<=0;queued<=0;done<=0;fault<=0;
  end else begin
   done<=0;launch<=0;
   if(ready&&cmd[0])begin
    fault<=0;bad<=!shape_ok;
    if(!shape_ok)begin done<=1;fault<=1;end
    else begin busy<=1;header<=ch;n<=a[67:48];m<=a[87:68];abase<=a[39:8];obase<=o[39:8];
     read_addr<=a[39:8];write_addr<=o[39:8];read_rowbase<=a[39:8];write_rowbase<=o[39:8];
     read_row<=0;read_col<=0;write_row<=0;write_col<=0;rs<=a[119:88];ws<=o[119:88];ri<=air;wi<=oir;
     launched<=0;returned<=0;finished<=0;read_part<=0;write_part<=0;
     reserved<=0;queued<=0;head<=0;tail<=0;x<=0;end
   end
   if(busy)begin
    if(!bad&&!pending&&!seat_v&&!launch&&(write_offer||read_offer))begin
     seat_v<=1;seat<={write_offer,{word_addr[29:3],5'd0},write_offer?wd:256'd0,write_offer?write_mask:32'hffffffff,next_tag};
     seat_step<=offer_step;seat_lane<=word_addr[2:0];
    end
    if(bad)seat_v<=0;
    if(provider_fault||decode_fault)begin bad<=1;fault<=1;end
    if(take_req)begin
     if(!req[336]&&read_part==0)x<=0;
     seat_v<=0;
     pending_step<=seat_step;pending_lane<=seat_lane;
     pending<=1;pending_write<=req[336];pending_tag<=next_tag;next_tag<=next_tag+1;end
    if(take_rsp)begin
     pending<=0;
     if(!reply_ok)begin bad<=1;fault<=1;end
     else if(!bad)begin
      if(pending_write)begin
       if(last_write)begin finished<=finished+1;head<=head_next;write_part<=0;end
       else write_part<=write_part+pending_step;
       if(write_col+pending_step==n)begin
        write_row<=write_row+1;write_col<=0;write_rowbase<=write_rowbase+ws;write_addr<=write_rowbase+ws;
       end else begin write_col<=write_col+pending_step;write_addr<=write_addr+pending_step*wi;end
      end else begin
       if(pending_step==8)x[read_part*32+:256]<=rsp[255:0];
       else x[read_part*32+:32]<=rsp[pending_lane*32+:32];
       if(read_col+pending_step==n)begin
        read_row<=read_row+1;read_col<=0;read_rowbase<=read_rowbase+rs;read_addr<=read_rowbase+rs;
       end else begin read_col<=read_col+pending_step;read_addr<=read_addr+pending_step*ri;end
       if(last_read)begin launch<=1;launched<=launched+1;read_part<=0;end
       else read_part<=read_part+pending_step;
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
      (write_row+1==m && write_col+pending_step==n || MUTANT==2))begin busy<=0;done<=1;end
   end
  end
 end
 initial if(DEPTH<24)$fatal(1,"QDQ result reservations require23 inflight+assembly");
endmodule
`default_nettype wire

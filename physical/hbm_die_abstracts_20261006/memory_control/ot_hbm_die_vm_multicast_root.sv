`timescale 1ns/1ps
`default_nettype none
// Actual two-bank128 activation staging + four held multicast outputs.
// Prebuild: vm_root_prebuild.json. Default off; whole VM parent/SSFF OPEN.
// All payload+192-bit source identities live in actual 128x256 SRAM with W6
// SECDED. Writes are ACKed only after SRAM readback. No zero-init dependency.
// por_n is COLD reset only. The caller must drain before resetting ownership.
module ot_hbm_die_vm_multicast_root #(parameter integer ENABLE=0)(
 input wire clk,por_n,
 input wire wr_v,output wire wr_ready,input wire wr_bank,input wire [6:0] wr_addr,
 input wire [2062:0] wr_data,input wire [191:0] wr_owner,
 output wire wr_ACK_v,input wire wr_ACK_ready,output wire [191:0] wr_ACK_owner,
 input wire rd_v,output wire rd_ready,input wire rd_bank,input wire [6:0] rd_addr,
 input wire [191:0] rd_owner,
 output wire [3:0] tap_v,input wire [3:0] tap_ready,output wire [4*2063-1:0] tap_data,
 output wire [4*192-1:0] tap_owner,
 input wire [3:0] tap_ACK_v,input wire [4*192-1:0] tap_ACK_owner,
 output wire native_release,drained,output wire fault
);
 import ot_gpu_w6_secded_pkg::*;
 generate if(!ENABLE)begin:off
  assign wr_ready=0;assign wr_ACK_v=0;assign wr_ACK_owner=0;assign rd_ready=0;
  assign tap_v=0;assign tap_data=0;assign tap_owner=0;assign native_release=0;
  assign drained=1;assign fault=0;
 end else begin:on
  localparam [3:0] IDLE=0,WRITE=1,VERIFY=2,CAPTURE=3,CHECK=4,WACK=5,READ=6,PUBLISH=7;
  reg [3:0] state,next_state;
  reg bank,next_bank,is_write,next_is_write,sticky,next_sticky;
  reg [6:0] addr,next_addr;
  reg [3:0] sent,next_sent,acked,next_acked;
  reg [71:0] control_code;
  reg [36*72-1:0] seat;
  reg [11*256-1:0] sampled;
  reg [4*72-1:0] validity; // authoritative coded256 valid bits, cold reset only
  wire [255:0] valid_bits;wire [3:0] valid_UE;
  for(genvar k=0;k<4;k=k+1)begin:validity_decode
   wire [65:0] d=decode64(validity[k*72+:72]);
   assign valid_bits[k*64+:64]=d[63:0];assign valid_UE[k]=d[65];
  end
  wire [63:0] control={42'b0,sticky,is_write,bank,addr,sent,acked,state};
  wire [63:0] next_control={42'b0,next_sticky,next_is_write,next_bank,next_addr,next_sent,next_acked,next_state};
  wire [65:0] control_d=decode64(control_code);
  wire control_bad=control_d[65] || control_d[63:0]!=control;
  wire [2303:0] seat_data,sample_data;
  wire [35:0] seat_UE,sample_UE;
  for(genvar k=0;k<36;k=k+1)begin:row_decode
   wire [65:0] a=decode64(seat[k*72+:72]),b=decode64(sampled[k*72+:72]);
   assign seat_data[k*64+:64]=a[63:0];assign seat_UE[k]=a[65];
   assign sample_data[k*64+:64]=b[63:0];assign sample_UE[k]=b[65];
  end
  wire seat_bad=|seat_UE;
  assign fault=sticky||control_bad||(|valid_UE)||(state!=IDLE&&seat_bad);
  assign wr_ready=state==IDLE&&!fault&&!rd_v;
  assign rd_ready=state==IDLE&&!fault&&!wr_v;
  wire wf=wr_v&&wr_ready,rf=rd_v&&rd_ready;
  assign wr_ACK_v=state==WACK&&!fault;
  assign wr_ACK_owner=seat_data[2063+:192];
  assign drained=state==IDLE&&!fault;
  assign native_release=state==PUBLISH&&(&acked)&&!fault;
  wire [2815:0] ram_q[0:1];
  for(genvar b=0;b<2;b=b+1)begin:banks
   for(genvar m=0;m<11;m=m+1)begin:macros
    wire [2815:0] write_word={224'b0,seat};
    ot_sram_1r1w_128x256_m1_r2c2 u_sram(
     .clk(clk),.r_ce_in((state==VERIFY||state==READ)&&bank==1'(b)&&!fault),.r_addr_in(addr),
     .rd_out(ram_q[b][m*256+:256]),.w_ce_in(state==WRITE&&bank==1'(b)&&!fault),
     .w_addr_in(addr),.wd_in(write_word[m*256+:256]),.w_mask_in({256{1'b1}}),
     .rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(16'b0));
   end
  end
  for(genvar t=0;t<4;t=t+1)begin:taps
   assign tap_v[t]=state==PUBLISH&&!sent[t]&&!fault;
   assign tap_data[t*2063+:2063]=seat_data[2062:0];
   assign tap_owner[t*192+:192]=seat_data[2063+:192];
  end
  always @*begin
   next_state=state;next_bank=bank;next_addr=addr;next_is_write=is_write;
   next_sent=sent;next_acked=acked;next_sticky=sticky||control_bad||(|valid_UE)||(state!=IDLE&&seat_bad);
   if((|tap_ACK_v)&&state!=PUBLISH)next_sticky=1;
   if(!fault)case(state)
    IDLE:begin
     next_sent=0;next_acked=0;
     if(wf)begin next_bank=wr_bank;next_addr=wr_addr;next_is_write=1;next_state=WRITE;end
     if(rf)begin
      if(!valid_bits[{rd_bank,rd_addr}])next_sticky=1;
      else begin next_bank=rd_bank;next_addr=rd_addr;next_is_write=0;next_state=READ;end
     end
    end
    WRITE:next_state=VERIFY;
    VERIFY,READ:next_state=CAPTURE;
    CAPTURE:next_state=CHECK;
    CHECK:begin
     if((|sample_UE)||(|sample_data[2303:2255]))next_sticky=1;
     else if(is_write)begin
      if(sample_data!=seat_data)next_sticky=1;else next_state=WACK;
     end else begin
      if(sample_data[2063+:192]!=seat_data[2063+:192])next_sticky=1;else next_state=PUBLISH;
     end
    end
    WACK:if(wr_ACK_ready)next_state=IDLE;
    PUBLISH:begin
     for(integer t=0;t<4;t=t+1)begin
      if(tap_v[t]&&tap_ready[t])next_sent[t]=1;
      if(tap_ACK_v[t])begin
       if(!sent[t]||acked[t]||tap_ACK_owner[t*192+:192]!=seat_data[2063+:192])next_sticky=1;
       else next_acked[t]=1;
      end
     end
     if(&acked)next_state=IDLE;
    end
    default:next_sticky=1;
   endcase
   if(next_sticky)begin next_state=state;next_sent=sent;next_acked=acked;end
  end
  always @(posedge clk or negedge por_n)begin
   if(!por_n)begin
    state<=IDLE;bank<=0;addr<=0;is_write<=0;sticky<=0;sent<=0;acked<=0;
    control_code<=0;seat<=0;sampled<=0;validity<=0;
   end else begin
    state<=next_state;bank<=next_bank;addr<=next_addr;is_write<=next_is_write;
    sticky<=next_sticky;sent<=next_sent;acked<=next_acked;control_code<=encode64(next_control);
    if(wf||rf)begin
     reg [2303:0] raw;
     raw=wf?{49'b0,wr_owner,wr_data}:{49'b0,rd_owner,2063'b0};
     for(integer k=0;k<36;k=k+1)seat[k*72+:72]<=encode64(raw[k*64+:64]);
    end
    if(state==CAPTURE&&!fault)sampled<=ram_q[bank];
    if(state==CHECK&&!fault&&!is_write&&!next_sticky)
     for(integer k=0;k<36;k=k+1)seat[k*72+:72]<=encode64(sample_data[k*64+:64]);
    if(state==CHECK&&!fault&&is_write&&!next_sticky)begin
     reg [255:0] next_valid;next_valid=valid_bits;next_valid[{bank,addr}]=1;
     for(integer k=0;k<4;k=k+1)validity[k*72+:72]<=encode64(next_valid[k*64+:64]);
    end
   end
  end
 end endgenerate
endmodule
`default_nettype wire

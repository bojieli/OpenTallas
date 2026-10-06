`timescale 1ps/1fs
`default_nettype none
// Actual index WORD-addressed32-FP32-word SRAM provider. Default off.
// Prebuild index_fp32_adapter_prebuild.json. No arithmetic/config modifications.
// Caller binds a real exclusive allocation and owner before writes. Writes
// publish only after actual SRAM readback. All interfaces held until accepted.
// por_n is COLD reset: caller must drain before any reset/window replacement.
module ot_hbm_index_fp32_sram_adapter #(parameter integer ENABLE=0)(
 input wire clk,por_n,
 input wire bind_v,output wire bind_ready,
 input wire [31:0] bind_base_word,bind_span_words,bind_job,
 input wire [3:0] bind_gen,input wire [19:0] bind_pos,input wire [6:0] bind_rank,
 output wire owner_held,
 input wire wr_v,output wire wr_ready,input wire [31:0] wr_addr,
 input wire [1023:0] wr_data,input wire [31:0] wr_job,
 input wire [3:0] wr_gen,input wire [19:0] wr_pos,input wire [6:0] wr_rank,
 output wire wr_ACK_v,input wire wr_ACK_ready,output wire [31:0] wr_ACK_addr,
 output wire [31:0] wr_ACK_job,output wire [3:0] wr_ACK_gen,
 output wire [19:0] wr_ACK_pos,output wire [6:0] wr_ACK_rank,
 output wire positive_publication_ACK,
 input wire read_v,output wire read_r,input wire [31:0] read_addr,
 input wire [5:0] read_words,input wire [7:0] read_tag,
 input wire [31:0] read_job,input wire [3:0] read_gen,
 input wire [19:0] read_pos,input wire [6:0] read_rank,
 output wire rsp_v,input wire rsp_r,output wire [1023:0] rsp_data,
 output wire [7:0] rsp_tag,output wire [31:0] rsp_job,
 output wire [3:0] rsp_gen,output wire [19:0] rsp_pos,output wire [6:0] rsp_rank,
 output wire drained,output wire fault
);
 import ot_gpu_w6_secded_pkg::*;
 generate if(!ENABLE)begin:off
  assign bind_ready=0;assign owner_held=0;assign wr_ready=0;assign wr_ACK_v=0;
  assign wr_ACK_addr=0;assign wr_ACK_job=0;assign wr_ACK_gen=0;assign wr_ACK_pos=0;assign wr_ACK_rank=0;
  assign positive_publication_ACK=0;assign read_r=0;assign rsp_v=0;assign rsp_data=0;
  assign rsp_tag=0;assign rsp_job=0;assign rsp_gen=0;assign rsp_pos=0;assign rsp_rank=0;
  assign drained=1;assign fault=0;
 end else begin:on
  localparam [3:0] IDLE=0,WRITE=1,VERIFY=2,CAPTURE=3,CHECK=4,WACK=5,READ=6,RESP=7;
  reg [3:0] state,next_state;
  reg [8:0] row,next_row;
  reg [7:0] tag,next_tag;
  reg is_write,next_is_write,sticky,next_sticky;
  reg [71:0] control_seal;
  reg [127:0] window;
  reg [143:0] window_seal;
  wire held=window[127];wire [31:0] base=window[126:95],span=window[94:63];
  wire [62:0] owner=window[62:0];
  wire [62:0] write_owner={wr_job,wr_gen,wr_pos,wr_rank};
  wire [62:0] read_owner={read_job,read_gen,read_pos,read_rank};
  wire [127:0] new_window={1'b1,bind_base_word,bind_span_words,bind_job,bind_gen,bind_pos,bind_rank};
  wire [32:0] bind_end={1'b0,bind_base_word}+{1'b0,bind_span_words};
  wire bind_bad=bind_span_words==0||bind_span_words>16384||(|bind_span_words[4:0])||
    (|bind_base_word[4:0])||bind_end[32]||bind_rank>=96;
  wire [31:0] woffset=wr_addr-base,roffset=read_addr-base;
  wire write_bad=!held||write_owner!=owner||wr_addr<base||woffset>=span||(|wr_addr[4:0]);
  wire read_bad=!held||read_owner!=owner||read_addr<base||roffset>=span||(|read_addr[4:0])||read_words!=32;
  wire [63:0] control={41'b0,sticky,is_write,row,tag,state};
  wire [63:0] next_control={41'b0,next_sticky,next_is_write,next_row,next_tag,next_state};
  wire [65:0] control_d=decode64(control_seal);
  wire [65:0] window_d0=decode64(window_seal[0+:72]),window_d1=decode64(window_seal[72+:72]);
  wire control_bad=control_d[65]||control_d[63:0]!=control;
  wire window_bad=window_d0[65]||window_d1[65]||{window_d1[63:0],window_d0[63:0]}!=window;
  reg [17*72-1:0] seat;
  reg [1279:0] sample;
  reg [8*72-1:0] valid_seal;
  wire [511:0] valid_bits;wire [7:0] valid_UE;
  for(genvar k=0;k<8;k=k+1)begin:valid_decode
   wire [65:0] d=decode64(valid_seal[k*72+:72]);
   assign valid_bits[k*64+:64]=d[63:0];assign valid_UE[k]=d[65];
  end
  wire [1087:0] seat_data,sample_data;wire [16:0] seat_UE,sample_UE;
  for(genvar k=0;k<17;k=k+1)begin:row_decode
   wire [65:0] a=decode64(seat[k*72+:72]),b=decode64(sample[k*72+:72]);
   assign seat_data[k*64+:64]=a[63:0];assign sample_data[k*64+:64]=b[63:0];
   assign seat_UE[k]=a[65];assign sample_UE[k]=b[65];
  end
  assign fault=sticky||control_bad||window_bad||(|valid_UE)||(state!=IDLE&&(|seat_UE));
  assign drained=state==IDLE&&!fault;
  assign owner_held=held&&!fault;
  assign bind_ready=drained&&!wr_v&&!read_v;
  assign wr_ready=drained&&held&&!bind_v&&!read_v&&!write_bad;
  assign read_r=drained&&held&&!bind_v&&!wr_v&&!read_bad;
  wire bf=bind_v&&bind_ready,wf=wr_v&&wr_ready,rf=read_v&&read_r;
  assign wr_ACK_v=state==WACK&&!fault;
  assign wr_ACK_addr=base+{18'b0,row,5'b0};
  assign {wr_ACK_job,wr_ACK_gen,wr_ACK_pos,wr_ACK_rank}=seat_data[1024+:63];
  assign positive_publication_ACK=wr_ACK_v&&wr_ACK_ready;
  assign rsp_v=state==RESP&&!fault;assign rsp_data=seat_data[1023:0];assign rsp_tag=tag;
  assign {rsp_job,rsp_gen,rsp_pos,rsp_rank}=seat_data[1024+:63];
  wire [1279:0] ram_q;
  wire [1279:0] write_word={56'b0,seat};
  for(genvar m=0;m<10;m=m+1)begin:macros
   ot_sram_1r1w_512x128_m4_r2c2 u_sram(
    .clk(clk),.r_ce_in((state==VERIFY||state==READ)&&!fault),.r_addr_in(row),.rd_out(ram_q[m*128+:128]),
    .w_ce_in(state==WRITE&&!fault),.w_addr_in(row),.wd_in(write_word[m*128+:128]),.w_mask_in({128{1'b1}}),
    .rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(14'b0));
  end
  always @*begin
   next_state=state;next_row=row;next_tag=tag;next_is_write=is_write;
   next_sticky=fault;
   if(!fault)case(state)
    IDLE:begin
     if(bind_v&&bind_ready&&bind_bad)next_sticky=1;
     if(wr_v&&!bind_v&&!read_v&&write_bad)next_sticky=1;
     if(read_v&&!bind_v&&!wr_v&&read_bad)next_sticky=1;
     if(wf)begin next_row=woffset[13:5];next_is_write=1;next_tag=0;next_state=WRITE;end
     if(rf)begin
      if(!valid_bits[roffset[13:5]])next_sticky=1;
      else begin next_row=roffset[13:5];next_is_write=0;next_tag=read_tag;next_state=READ;end
     end
    end
    WRITE:next_state=VERIFY;
    VERIFY,READ:next_state=CAPTURE;
    CAPTURE:next_state=CHECK;
    CHECK:begin
     if((|sample_UE)||sample_data[1087]||(|sample[1279:1224]))next_sticky=1;
     else if(is_write)begin
      if(sample_data!=seat_data)next_sticky=1;else next_state=WACK;
     end else if(sample_data[1024+:63]!=owner)next_sticky=1;
     else next_state=RESP;
    end
    WACK:if(wr_ACK_ready)next_state=IDLE;
    RESP:if(rsp_r)next_state=IDLE;
    default:next_sticky=1;
   endcase
  end
  always @(posedge clk or negedge por_n)begin
   if(!por_n)begin
    state<=IDLE;row<=0;tag<=0;is_write<=0;sticky<=0;control_seal<=0;
    window<=0;window_seal<=0;valid_seal<=0;seat<=0;sample<=0;
   end else begin
    state<=next_state;row<=next_row;tag<=next_tag;is_write<=next_is_write;
    sticky<=next_sticky;control_seal<=encode64(next_control);
    if(bf&&!bind_bad)begin
     window<=new_window;window_seal<={encode64(new_window[127:64]),encode64(new_window[63:0])};valid_seal<=0;
    end
    if(wf)for(integer k=0;k<17;k=k+1)seat[k*72+:72]<=encode64(64'(1088'({1'b0,write_owner,wr_data})>>(k*64)));
    if(rf)for(integer k=0;k<17;k=k+1)seat[k*72+:72]<=encode64(64'(1088'({1'b0,read_owner,1024'b0})>>(k*64)));
    if(state==CAPTURE&&!fault)sample<=ram_q;
    if(state==CHECK&&!fault&&next_state==RESP)seat<=sample[1223:0];
    if(state==WACK&&positive_publication_ACK)begin
     for(integer k=0;k<8;k=k+1)begin
      reg [63:0] v;v=valid_bits[k*64+:64];if(row/64==k)v[row%64]=1;
      valid_seal[k*72+:72]<=encode64(v);
     end
    end
   end
  end
 end endgenerate
endmodule
`default_nettype wire

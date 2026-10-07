`timescale 1ns/1ps
// Candidate full-shape storage, not physically admitted. Root POR only.
// Native outputs have no ready: reserve and source_permit MUST precede launch.
module ot_hbm_sm_result_provider #(parameter integer ENABLE=0)(
 input wire clk,por_n,installed,
 input wire reserve_v,output wire reserve_r,
 input wire [15:0] record_id,provider_tag,
 input wire [12:0] rows,
 input wire [36:0] base,limit,
 output wire source_permit,retained,fault,
 input wire result_v,input wire [11:0] result_row,input wire [255:0] result_data,
 input wire native_done,
 output wire publication_v,input wire publication_r,output wire [15:0] publication_record,
 output wire req_v,input wire req_r,output wire req_we,
 output wire [36:0] req_addr,output wire [255:0] req_data,output wire [15:0] req_tag,
 input wire rsp_v,output wire rsp_r,input wire rsp_we,input wire [15:0] rsp_tag,
 input wire [255:0] rsp_data,input wire rsp_error
);
import ot_gpu_w6_secded_pkg::*;
generate if(!ENABLE) begin:off
 assign reserve_r=0;assign source_permit=0;assign retained=0;assign fault=0;
 assign publication_v=0;assign publication_record=0;
 assign req_v=0;assign req_we=0;assign req_addr=0;assign req_data=0;assign req_tag=0;assign rsp_r=0;
end else begin:on
 localparam [3:0] IDLE=0,CLEAR=1,CAPTURE=2,FETCH=3,CHECK=4,WRITE=5,WAIT_W=6,READ=7,WAIT_R=8,DONE=9,FAIL=10;
 // Protected immutable reservation4, mutable control1, staged payload4.
 reg [71:0] code[0:8];reg [71:0] seen[0:63];
 wire [65:0] d[0:8];wire [8:0] ue;
 for(genvar k=0;k<9;k=k+1)begin:dec
  assign d[k]=decode64(code[k]);assign ue[k]=d[k][65];
 end
 wire [3:0] state=d[4][3:0];wire [12:0] count=d[4][16:4];
 wire [11:0] slot=d[4][28:17];wire [5:0] clear_slot=d[4][34:29];
 wire [12:0] held_rows=d[0][12:0];wire [15:0] held_record=d[0][28:13];
 wire [15:0] tag=d[0][44:29];wire [36:0] held_base=d[1][36:0];
 wire [36:0] held_limit=d[2][36:0];
 wire [65:0] seen_word=decode64(seen[result_row[11:6]]);
 wire legal_result=result_row<held_rows&&!seen_word[result_row[5:0]]&&!seen_word[65];
 wire shape=rows>=1&&rows<=4096&&base[4:0]==0&&limit>base&&({1'b0,base}+38'(rows)*38'd32<={1'b0,limit});
 assign fault=(|ue)||state==FAIL||(state!=IDLE&&!installed);
 assign reserve_r=state==IDLE&&installed&&shape&&!fault;
 assign source_permit=state==CAPTURE&&!fault;
 assign retained=state!=IDLE;
 assign publication_v=state==DONE&&!fault;
 assign publication_record=held_record;
 assign req_v=(state==WRITE||state==READ)&&!fault;
 assign req_we=state==WRITE;
 assign req_addr=held_base+{20'b0,slot,5'b0};
 assign req_data={d[8][63:0],d[7][63:0],d[6][63:0],d[5][63:0]};
 assign req_tag=tag;
 wire response_match=rsp_tag==tag&&rsp_we==(state==WAIT_W)&&!rsp_error;
 assign rsp_r=(state==WAIT_W||state==WAIT_R)&&response_match&&!fault;
 wire take_result=result_v&&source_permit&&legal_result;
 wire [319:0] encoded_row={32'b0,encode64(result_data[255:192]),encode64(result_data[191:128]),encode64(result_data[127:64]),encode64(result_data[63:0])};
 wire [2559:0] bank_q;
 for(genvar b=0;b<8;b=b+1)begin:bank
  localparam integer BANK_INDEX=b;
  for(genvar w=0;w<5;w=w+1)begin:word
   ot_sram_2rw_512x64_m4_r2c2 mem(.clk(clk),
    .a_ce_in(take_result&&result_row[11:9]==BANK_INDEX),.a_we_in(1'b1),.a_addr_in(result_row[8:0]),
    .a_wd_in(encoded_row[w*64+:64]),.a_w_mask_in(64'hffffffffffffffff),.a_rd_out(),
    .b_ce_in(state==FETCH&&!fault&&slot[11:9]==BANK_INDEX),.b_we_in(1'b0),.b_addr_in(slot[8:0]),
    .b_wd_in(64'b0),.b_w_mask_in(64'b0),.b_rd_out(bank_q[BANK_INDEX*320+w*64+:64]),
    .rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(12'b0));
  end
 end
 wire [319:0] captured=bank_q[slot[11:9]*320+:320];
 wire [65:0] cd[0:3];wire [3:0] capture_ue;
 for(genvar k=0;k<4;k=k+1)begin:cd_dec
  assign cd[k]=decode64(captured[k*72+:72]);assign capture_ue[k]=cd[k][65];
 end
 reg [63:0] ctl;
 always @*begin
  ctl=d[4][63:0];
  case(state)
   IDLE:if(reserve_v&&reserve_r)ctl=64'(CLEAR);
   CLEAR:if(clear_slot==63)ctl=64'(CAPTURE);else ctl[34:29]=clear_slot+1'b1;
   CAPTURE:begin
    if(take_result)ctl[16:4]=count+1'b1;
    if(native_done)begin
     if(count+13'(take_result)==held_rows)ctl[3:0]=FETCH;else ctl[3:0]=FAIL;
    end
   end
   FETCH:ctl[3:0]=CHECK;
   CHECK:ctl[3:0]=(|capture_ue)?FAIL:WRITE;
   WRITE:if(req_v&&req_r)ctl[3:0]=WAIT_W;
   WAIT_W:if(rsp_v&&rsp_r)ctl[3:0]=READ;
   READ:if(req_v&&req_r)ctl[3:0]=WAIT_R;
   WAIT_R:if(rsp_v&&rsp_r)begin
    if(rsp_data!=req_data)ctl[3:0]=FAIL;
    else if({1'b0,slot}+13'd1==held_rows)ctl[3:0]=DONE;
    else begin ctl[28:17]=slot+1'b1;ctl[3:0]=FETCH;end
   end
   DONE:if(publication_v&&publication_r)ctl=0;
   default:begin end
  endcase
  if(fault||(result_v&&(!source_permit||!legal_result))||
     (native_done&&state!=CAPTURE)||
     (rsp_v&&(!(state==WAIT_W||state==WAIT_R)||!response_match))||
     (reserve_v&&state==IDLE&&!reserve_r))ctl[3:0]=FAIL;
 end
 integer k;
 always @(posedge clk or negedge por_n)begin
  if(!por_n)begin
   for(k=0;k<9;k=k+1)code[k]<=encode64(0);
   // Bitmap is initialized by CLEAR before permission, no bulk reset network.
  end else begin
   code[4]<=encode64(ctl);
   if(reserve_v&&reserve_r)begin
    code[0]<=encode64({19'b0,provider_tag,record_id,rows});
    code[1]<=encode64({27'b0,base});code[2]<=encode64({27'b0,limit});code[3]<=encode64(0);
   end
   if(state==CLEAR&&!fault)seen[clear_slot]<=encode64(0);
   if(take_result)seen[result_row[11:6]]<=encode64(seen_word[63:0]|(64'b1<<result_row[5:0]));
   if(state==CHECK&&!fault&&!(|capture_ue))
    for(k=0;k<4;k=k+1)code[5+k]<=encode64(cd[k][63:0]);
  end
 end
end endgenerate
endmodule

`timescale 1ns/1ps
// Full physical data/check memory. Only owner-matched protected readback releases visibility.
// Warm reset retains accepted debt; recovery is NOT fabricated from an empty transport.
module ot_dsrom_vm_backend(
 input wire clk,cold_n,rst_n,
 input wire req_v,output wire req_ready,
 input wire [ot_dsrom_vm_pkg::REQ_CODE-1:0] req_code,
 output wire reply_v,input wire reply_ready,
 output wire [ot_dsrom_vm_pkg::REP_CODE-1:0] reply_code,
 input wire receipt_v,output wire receipt_ready,input wire [143:0] receipt_code,
 output wire initializing,output reg debt,output wire fault
);
 import ot_dsrom_vm_pkg::*;import ot_gpu_w6_secded_pkg::*;
 localparam INIT=0,IDLE=1,ISSUE=2,CAPTURE=3,DECODE=4,CHECK=5,MERGE=6,COMMIT=7,
            SEND=8,WAIT_RECEIPT=9,FINAL_SEND=10;
 reg [3:0] state,state_check;reg poison,poison_check,debt_check;
 reg [8:0] clear_row,clear_check;
 request_t packet,packet_check,incoming;
 reg [1:0] mode,mode_check;reg [2:0] writer,writer_check;
 reg [4:0] written,written_check;reg [1:0] read_done,read_done_check;
 reg [1023:0] result_data,result_check;
 reg [511:0] raw_data,decoded_data,decoded_check,expected,expected_check;
 reg [63:0] raw_checks;
 reg decoded_ue,decoded_ue_check,had_ce,had_ce_check;
 wire req_ce,req_ue;wire [REQ_CODE-1:0] unused_req_encoded;
 ot_dsrom_vm_codec #(.BITS(REQ_BITS)) u_req_decode(.raw_in(REQ_BITS'(0)),.encoded(unused_req_encoded),
  .coded_in(req_code),.decoded(incoming),.corrected(req_ce),.uncorrectable(req_ue));
 wire [79:0] receipt;wire ack_ce,ack_ue;wire [143:0] unused_ack_encoded;
 ot_dsrom_vm_codec #(.BITS(80)) u_receipt_decode(.raw_in(80'd0),.encoded(unused_ack_encoded),
  .coded_in(receipt_code),.decoded(receipt),.corrected(ack_ce),.uncorrectable(ack_ue));
 wire bad=state!=~state_check||poison!=~poison_check||debt!=~debt_check||clear_row!=~clear_check||
  (debt&&(packet!=~packet_check||mode!=~mode_check||writer!=~writer_check||writer>4||
   written!=~written_check||read_done!=~read_done_check||result_data!=~result_check||
   decoded_data!=~decoded_check||expected!=~expected_check||decoded_ue!=~decoded_ue_check||had_ce!=~had_ce_check));
 assign fault=poison||bad;wire safe=cold_n&&rst_n&&!fault;
 assign initializing=state==INIT;assign req_ready=safe&&state==IDLE&&!debt;
 assign receipt_ready=safe&&state==WAIT_RECEIPT&&debt;
 reply_t response;
 always @*begin
  response='0;response.ordinal=packet.ordinal;response.final_receipt=state==FINAL_SEND;response.owner=packet.owner;
  response.re=packet.re;response.data=result_data;response.visible=written;
  response.wa=packet.wa;response.wm=packet.wm;response.corrected=had_ce;
 end
 wire unused_rep_ce,unused_rep_ue;wire [REP_BITS-1:0] unused_rep_data;
 ot_dsrom_vm_codec #(.BITS(REP_BITS)) u_reply_encode(.raw_in(response),.encoded(reply_code),
  .coded_in(REP_CODE'(0)),.decoded(unused_rep_data),.corrected(unused_rep_ce),.uncorrectable(unused_rep_ue));
 assign reply_v=safe&&debt&&(state==SEND||state==FINAL_SEND)&&written==packet.we&&read_done==packet.re;
 wire [14:0] address=mode==0?packet.ra[14:0]:mode==1?packet.ra[29:15]:packet.wa[writer*15+:15];
 wire read_en=safe&&state==ISSUE;
 wire write_en=safe&&(state==INIT||state==COMMIT);
 wire [511:0] data_q[0:63];wire [127:0] check_q[0:31];
 function automatic [7:0] parity64(input [63:0] d);
  reg [71:0] code;integer k;
  begin code=encode64(d);for(k=0;k<7;k=k+1)parity64[k]=code[(1<<k)-1];parity64[7]=code[71];end
 endfunction
 function automatic [71:0] join_code(input [63:0] d,input [7:0] parity);
  reg [71:0] code;integer p,j,k;
  begin code=0;j=0;k=0;for(p=1;p<=71;p=p+1)begin
   if((p&(p-1))!=0)begin code[p-1]=d[j];j=j+1;end
   else begin code[p-1]=parity[k];k=k+1;end
  end code[71]=parity[7];join_code=code;end
 endfunction
 wire [63:0] encoded_checks;
 for(genvar chunk=0;chunk<8;chunk=chunk+1)assign encoded_checks[chunk*8+:8]=parity64(expected[chunk*64+:64]);
 for(genvar g=0;g<64;g=g+1)begin:g_data
  for(genvar c=0;c<4;c=c+1)begin:g_column
   (* keep=1,dont_touch=1 *) ot_sram_1r1w_512x128_m4_r2c2 u_data(
    .clk(clk),.r_ce_in(read_en&&address[14:9]==g),.r_addr_in(address[8:0]),.rd_out(data_q[g][c*128+:128]),
    .w_ce_in(write_en&&(state==INIT||address[14:9]==g)),.w_addr_in(state==INIT?clear_row:address[8:0]),
    .wd_in(state==INIT?128'd0:expected[c*128+:128]),.w_mask_in({128{1'b1}}),
    .rr_en(2'd0),.rr_addr(14'd0),.cr_en(2'd0),.cr_sel(14'd0));
  end
 end
 for(genvar g=0;g<32;g=g+1)begin:g_checks
  (* keep=1,dont_touch=1 *) ot_sram_1r1w_512x128_m4_r2c2 u_check(
   .clk(clk),.r_ce_in(read_en&&address[14:10]==g),.r_addr_in(address[8:0]),.rd_out(check_q[g]),
   .w_ce_in(write_en&&(state==INIT||address[14:10]==g)),.w_addr_in(state==INIT?clear_row:address[8:0]),
   .wd_in(state==INIT?128'd0:address[9]?{encoded_checks,64'd0}:{64'd0,encoded_checks}),
   .w_mask_in(state==INIT?{128{1'b1}}:address[9]?{64'hffffffffffffffff,64'd0}:{64'd0,64'hffffffffffffffff}),
   .rr_en(2'd0),.rr_addr(14'd0),.cr_en(2'd0),.cr_sel(14'd0));
 end
 wire [511:0] decoded_next;wire [7:0] ce,ue;
 for(genvar c=0;c<8;c=c+1)begin:g_decode
  wire [65:0] v=decode64(join_code(raw_data[c*64+:64],raw_checks[c*8+:8]));
  assign decoded_next[c*64+:64]=v[63:0];assign ce[c]=v[64];assign ue[c]=v[65];
 end
 function automatic integer next_writer(input [4:0] mask,input integer first);
  begin next_writer=-1;for(integer k=0;k<5;k=k+1)if(k>=first&&mask[k]&&next_writer<0)next_writer=k;end
 endfunction
 task automatic jump(input [3:0] s);begin state<=s;state_check<=~s;end endtask
 task automatic select_mode(input [1:0] m);begin mode<=m;mode_check<=~m;end endtask
 task automatic select_writer(input integer w);begin writer<=3'(w);writer_check<=~3'(w);end endtask
 task automatic fail;begin poison<=1;poison_check<=0;end endtask
 task automatic begin_writes(input [4:0] w,input integer first);
  integer n;begin n=next_writer(w,first);if(n<0)jump(SEND);else begin select_writer(n);select_mode(2);jump(ISSUE);end end
 endtask
 always @(posedge clk)begin:service
  reg [511:0] merged;integer n;
  if(!cold_n)begin
   state<=INIT;state_check<=~4'(INIT);poison<=0;poison_check<=1;debt<=0;debt_check<=1;
   clear_row<=0;clear_check<=9'h1ff;packet<=0;packet_check<={REQ_BITS{1'b1}};
   mode<=0;mode_check<=3;writer<=0;writer_check<=7;written<=0;written_check<=31;
   read_done<=0;read_done_check<=3;result_data<=0;result_check<={1024{1'b1}};
   raw_data<=0;raw_checks<=0;decoded_data<=0;decoded_check<={512{1'b1}};
   expected<=0;expected_check<={512{1'b1}};decoded_ue<=0;decoded_ue_check<=1;had_ce<=0;had_ce_check<=1;
  end else if(!rst_n)begin if(debt)fail();end
  else if(bad)fail();
  else if(!poison)begin
   case(state)
    INIT:if(clear_row==511)jump(IDLE);else begin clear_row<=clear_row+1;clear_check<=~(clear_row+9'd1);end
    IDLE:if(req_v&&req_ready)begin
     debt<=1;debt_check<=0;packet<=incoming;packet_check<=~incoming;
     written<=0;written_check<=31;read_done<=0;read_done_check<=3;
     result_data<=0;result_check<={1024{1'b1}};had_ce<=req_ce;had_ce_check<=~req_ce;
     if(req_ue||!(|incoming.we)&&!(|incoming.re))fail();
     else if(incoming.re[0])begin select_mode(0);jump(ISSUE);end
     else if(incoming.re[1])begin select_mode(1);jump(ISSUE);end
     else begin_writes(incoming.we,0);
    end
    ISSUE:jump(CAPTURE);
    CAPTURE:begin raw_data<=data_q[address[14:9]];raw_checks<=address[9]?check_q[address[14:10]][127:64]:check_q[address[14:10]][63:0];jump(DECODE);end
    DECODE:begin decoded_data<=decoded_next;decoded_check<=~decoded_next;decoded_ue<=|ue;decoded_ue_check<=~(|ue);
     had_ce<=had_ce||(|ce);had_ce_check<=~(had_ce||(|ce));jump(CHECK);end
    CHECK:if(decoded_ue)fail();else case(mode)
     0:begin result_data[511:0]<=decoded_data;result_check[511:0]<=~decoded_data;
      read_done[0]<=1;read_done_check[0]<=0;
      if(packet.re[1])begin select_mode(1);jump(ISSUE);end else begin_writes(packet.we,0);end
     1:begin result_data[1023:512]<=decoded_data;result_check[1023:512]<=~decoded_data;
      read_done[1]<=1;read_done_check[1]<=0;begin_writes(packet.we,0);end
     2:jump(MERGE);
     3:if(decoded_data!=expected)fail();else begin written[writer]<=1;written_check[writer]<=0;begin_writes(packet.we,integer'(writer)+1);end
    endcase
    MERGE:begin merged=decoded_data;for(integer k=0;k<16;k=k+1)if(packet.wm[writer*16+k])merged[k*32+:32]=packet.wd[writer*512+k*32+:32];
     if(packet.wm[writer*16+:16]==0)fail();else begin expected<=merged;expected_check<=~merged;jump(COMMIT);end end
    COMMIT:begin select_mode(3);jump(ISSUE);end
    SEND:if(reply_v&&reply_ready)jump(WAIT_RECEIPT);
    WAIT_RECEIPT:if(receipt_v&&receipt_ready)begin
     if(ack_ue||receipt[79:48]!=packet.ordinal||receipt[47:1]!=packet.owner||!receipt[0])fail();else jump(FINAL_SEND);
    end
    FINAL_SEND:if(reply_v&&reply_ready)begin debt<=0;debt_check<=1;jump(IDLE);end
    default:fail();
   endcase
  end
 end
endmodule

`timescale 1ps/1fs
// Additive output endpoint. Separate source/destination banks are deliberately
// charged by the model. No production numerical engine is instantiated.
module ot_dsrom_softmax_egress_payload(
 input wire clk_stream,clk_chain,cold_abort,
 input wire begin_valid,begin_short,input wire [31:0] begin_epoch,input wire [15:0] begin_tag,
 output wire begin_ready,
 input wire e_valid,input wire [8191:0] e_data,
 input wire b_valid,input wire [4095:0] b_data,
 input wire [31:0] producer_epoch,input wire [15:0] producer_tag,
 input wire destination_allow_commit,
 output wire e_visible,done_valid,input wire done_ready,
 output wire capture_commit,output wire [6:0] capture_addr,
 output wire destination_commit,output wire [55:0] destination_identity,
 output wire receipt_valid,output wire [55:0] receipt_identity,
 output wire fault
);
 import ot_gpu_w6_secded_pkg::*;
 wire srst,crst;
 ot_hbm_collective_reset_entry #(.ENABLE(1)) resets(.clk_stream(clk_stream),.clk_link(clk_chain),
  .por_stream(cold_abort),.por_link(cold_abort),.rst_n(srst),.prst_n(crst));
 localparam [2:0] IDLE=0,CAP_E=1,DRAIN_E=2,CAP_B=3,DRAIN_B=4,DONE=5;
 (* keep=1,dont_touch=1 *) reg [2:0] state,state_n;
 (* keep=1,dont_touch=1 *) reg [48:0] context_q,context_n;
 (* keep=1,dont_touch=1 *) reg [5:0] captured,captured_n,sent,sent_n,received,received_n;
 (* keep=1,dont_touch=1 *) reg pending,pending_n,failed,failed_n;
 (* keep=1,dont_touch=1 *) reg [6:0] pending_addr,pending_addr_n;
 (* keep=1,dont_touch=1 *) reg return_v,return_v_n;
 (* keep=1,dont_touch=1 *) reg [15:0] return_tag,return_tag_n;
 reg [9215:0] pending_code;
 reg [4607:0] half_code;
 wire [9215:0] incoming_code;
 genvar enc_lane;generate for(enc_lane=0;enc_lane<128;enc_lane=enc_lane+1)begin:g_encode
  assign incoming_code[enc_lane*72+:72]=encode64(e_valid?e_data[enc_lane*64+:64]:b_data[(enc_lane%64)*64+:64]);
 end endgenerate
 wire [31:0] epoch=context_q[48:17];wire [15:0] tag=context_q[16:1];wire short_row=context_q[0];
 wire [5:0] e_limit=short_row?6'd8:6'd40;
 wire b_phase=(state==CAP_B||state==DRAIN_B||state==DONE);
 wire [5:0] drain_limit=b_phase?6'd16:e_limit;
 wire integrity=(state_n==~state)&&(context_n==~context_q)&&(captured_n==~captured)&&
  (sent_n==~sent)&&(received_n==~received)&&(pending_n==~pending)&&(pending_addr_n==~pending_addr)&&
  (failed_n==~failed)&&(return_v_n==~return_v)&&(return_tag_n==~return_tag)&&
  state<=DONE&&captured<=(b_phase?6'd32:e_limit)&&sent<=drain_limit&&received<=sent;
 wire sfault,dfault,qfault,afault,d_failed;
 assign fault=failed||!integrity||sfault||dfault||qfault||afault||d_failed;
 assign begin_ready=srst&&state==IDLE&&!fault;
 assign e_visible=srst&&(state==CAP_B||state==DRAIN_B||state==DONE)&&!fault;
 assign done_valid=srst&&state==DONE&&!fault;
 wire bad_producer=(e_valid||b_valid)&&((producer_epoch!=epoch)||(producer_tag!=tag));
 wire bad_capture=(e_valid&&(state!=CAP_E||captured>=e_limit))||
  (b_valid&&(state!=CAP_B||captured>=32))||(e_valid&&b_valid)||bad_producer;
 assign capture_commit=srst&&pending&&!fault;
 assign capture_addr=pending_addr;
 wire [9215:0] source_q;
 wire rd_valid,rd_ready,mem_r_en;wire [6:0] mem_r_addr;wire [15:0] mem_r_tag;
 wire sv,sready;wire [1023:0] sd;wire [2:0] sb;wire [15:0] st;
 assign rd_valid=srst&&!fault&&(state==DRAIN_E||state==DRAIN_B)&&sent<drain_limit;
 wire [6:0] drain_addr=(b_phase?7'd112:7'd72)+{1'b0,sent};
 ot_dsrom_softmax_serial_row source_reader(.clk(clk_stream),.rst_n(srst),
  .wr_valid(1'b0),.wr_ready(),.wr_data(1024'd0),.wr_beat(3'd0),.wr_addr(7'd0),.wr_tag(16'd0),
  .mem_w_valid(),.mem_w_ready(1'b0),.mem_w_addr(),.mem_w_code(),
  .rd_valid(rd_valid),.rd_ready(rd_ready),.rd_addr(drain_addr),.rd_tag(tag),
  .mem_r_en(mem_r_en),.mem_r_addr(mem_r_addr),.mem_r_tag(mem_r_tag),
  .mem_return_valid(return_v),.mem_return_tag(return_tag),.mem_return_code(source_q),
  .out_valid(sv),.out_ready(sready),.out_data(sd),.out_beat(sb),.out_tag(st),.out_corrected(),.fault(sfault));
 ot_dsrom_softmax_egress_macro_bank source_bank(.clk(clk_stream),
  .w_en(capture_commit),.w_addr(pending_addr),.w_code(pending_code),
  .r_en(mem_r_en&&!fault),.r_addr(mem_r_addr),.r_code(source_q));
 wire qv,qr;wire [1082:0] q;
 wire [1082:0] send_packet={b_phase,epoch,tag,drain_addr,sb,sd};
 wire fifo_ready;
 assign sready=srst&&!fault&&fifo_ready;
 ot_hbm_collective_protected_cdc #(.ENABLE(1),.W(1083),.AW(6)) payload_cdc(
  .wclk(clk_stream),.wrst_n(srst),.in_v(sv&&!fault&&srst),.in_r(fifo_ready),.in_d(send_packet),
  .rclk(clk_chain),.rrst_n(crst),.out_v(qv),.out_r(qr),.out_d(q),.wempty(),.rempty(),.fault(qfault));
 wire [55:0] q_identity=q[1082:1027];wire [6:0] q_addr=q[1033:1027];
 wire [15:0] q_tag=q[1049:1034];wire [2:0] q_beat=q[1026:1024];
 (* keep=1,dont_touch=1 *) reg [55:0] dest_id,dest_id_n;
 (* keep=1,dont_touch=1 *) reg dest_open,dest_open_n,dest_failed,dest_failed_n;
 wire dest_integrity=(dest_id_n==~dest_id)&&(dest_open_n==~dest_open)&&(dest_failed_n==~dest_failed);
 assign d_failed=dest_failed||!dest_integrity;
 wire dest_wr_ready,mwv;wire [6:0] mwa;wire [9215:0] mwc;
 wire ack_ready,ack_v;wire [55:0] ack;
 wire bad_dest=qv&&dest_wr_ready&&((dest_open&&q_identity!=dest_id)||(!dest_open&&q_beat!=0)||
  (q_identity[55]?(q_addr<112):(q_addr<72||q_addr>111)));
 assign qr=crst&&!fault&&dest_wr_ready&&!bad_dest;
 wire qfire=qv&&qr;
 wire macro_commit=crst&&!fault&&mwv&&destination_allow_commit&&ack_ready;
 assign destination_commit=macro_commit;
 assign destination_identity=dest_id;
 ot_dsrom_softmax_serial_row destination_writer(.clk(clk_chain),.rst_n(crst),
  .wr_valid(qfire),.wr_ready(dest_wr_ready),.wr_data(q[1023:0]),.wr_beat(q_beat),.wr_addr(q_addr),.wr_tag(q_tag),
  .mem_w_valid(mwv),.mem_w_ready(destination_allow_commit&&ack_ready&&!fault&&crst),.mem_w_addr(mwa),.mem_w_code(mwc),
  .rd_valid(1'b0),.rd_ready(),.rd_addr(7'd0),.rd_tag(16'd0),.mem_r_en(),.mem_r_addr(),.mem_r_tag(),
  .mem_return_valid(1'b0),.mem_return_tag(16'd0),.mem_return_code(9216'd0),
  .out_valid(),.out_ready(1'b0),.out_data(),.out_beat(),.out_tag(),.out_corrected(),.fault(dfault));
 wire [9215:0] unused_dest_q;
 ot_dsrom_softmax_egress_macro_bank destination_bank(.clk(clk_chain),
  .w_en(macro_commit),.w_addr(mwa),.w_code(mwc),.r_en(1'b0),.r_addr(7'd0),.r_code(unused_dest_q));
`ifdef SOFTMAX_EGRESS_EARLY_RECEIPT
 wire ack_send=qfire&&q_beat==7;
 wire [55:0] ack_packet=q_identity;
`else
 wire ack_send=macro_commit;
 wire [55:0] ack_packet=dest_id;
`endif
 ot_hbm_collective_protected_cdc #(.ENABLE(1),.W(56),.AW(6)) visibility_cdc(
  .wclk(clk_chain),.wrst_n(crst),.in_v(ack_send),.in_r(ack_ready),.in_d(ack_packet),
  .rclk(clk_stream),.rrst_n(srst),.out_v(ack_v),.out_r(srst&&!fault),.out_d(ack),.wempty(),.rempty(),.fault(afault));
 wire ack_bad=ack_v&&(ack!={b_phase,epoch,tag,((b_phase?7'd112:7'd72)+{1'b0,received})}||
  !(state==DRAIN_E||state==DRAIN_B)||received>=sent);
 assign receipt_valid=srst&&ack_v&&!fault&&!ack_bad;
 assign receipt_identity=ack;
 always @(posedge clk_stream)begin
  if(!srst)begin
   state<=IDLE;state_n<=~IDLE;context_q<=0;context_n<=~49'd0;
   captured<=0;captured_n<=~6'd0;sent<=0;sent_n<=~6'd0;received<=0;received_n<=~6'd0;
   pending<=0;pending_n<=1;pending_addr<=0;pending_addr_n<=~7'd0;
   failed<=0;failed_n<=1;return_v<=0;return_v_n<=1;return_tag<=0;return_tag_n<=~16'd0;
  end else if(fault||bad_capture||ack_bad)begin failed<=1;failed_n<=0;end
  else begin
   return_v<=mem_r_en;return_v_n<=~mem_r_en;
   if(mem_r_en)begin return_tag<=mem_r_tag;return_tag_n<=~mem_r_tag;end
   pending<=0;pending_n<=1;
   if(begin_valid&&begin_ready)begin
    state<=CAP_E;state_n<=~CAP_E;context_q<={begin_epoch,begin_tag,begin_short};context_n<=~{begin_epoch,begin_tag,begin_short};
    captured<=0;captured_n<=~6'd0;sent<=0;sent_n<=~6'd0;received<=0;received_n<=~6'd0;
   end
   if(e_valid)begin
    pending_code<=incoming_code;
    pending<=1;pending_n<=0;pending_addr<=7'd72+{1'b0,captured};pending_addr_n<=~(7'd72+{1'b0,captured});
    captured<=captured+1'b1;captured_n<=~(captured+6'd1);
   end
   if(b_valid)begin
    if(!captured[0])begin
     half_code<=incoming_code[4607:0];
    end else begin
`ifdef SOFTMAX_EGRESS_SWAP_HALVES
     pending_code[9215:4608]<=half_code;
     pending_code[4607:0]<=incoming_code[4607:0];
`else
     pending_code[4607:0]<=half_code;
     pending_code[9215:4608]<=incoming_code[9215:4608];
`endif
     pending<=1;pending_n<=0;pending_addr<=7'd112+{2'd0,captured[5:1]};pending_addr_n<=~(7'd112+{2'd0,captured[5:1]});
    end
    captured<=captured+1'b1;captured_n<=~(captured+6'd1);
   end
   if(capture_commit&&state==CAP_E&&captured==e_limit)begin state<=DRAIN_E;state_n<=~DRAIN_E;end
   if(capture_commit&&state==CAP_B&&captured==32)begin state<=DRAIN_B;state_n<=~DRAIN_B;end
   if(sv&&sready&&sb==7)begin sent<=sent+1'b1;sent_n<=~(sent+6'd1);end
   if(receipt_valid)begin
    received<=received+1'b1;received_n<=~(received+6'd1);
    if(received+6'd1==drain_limit)begin
     if(state==DRAIN_E)begin
      state<=CAP_B;state_n<=~CAP_B;captured<=0;captured_n<=~6'd0;sent<=0;sent_n<=~6'd0;received<=0;received_n<=~6'd0;
     end else begin state<=DONE;state_n<=~DONE;end
    end
   end
   if(done_valid&&done_ready)begin state<=IDLE;state_n<=~IDLE;captured<=0;captured_n<=~6'd0;sent<=0;sent_n<=~6'd0;received<=0;received_n<=~6'd0;end
  end
 end
 always @(posedge clk_chain)begin
  if(!crst)begin dest_id<=0;dest_id_n<=~56'd0;dest_open<=0;dest_open_n<=1;dest_failed<=0;dest_failed_n<=1;end
  else if(fault||bad_dest)begin dest_failed<=1;dest_failed_n<=0;end
  else begin
   if(qfire&&!dest_open)begin dest_id<=q_identity;dest_id_n<=~q_identity;dest_open<=1;dest_open_n<=0;end
   if(macro_commit)begin dest_open<=0;dest_open_n<=1;end
  end
 end
endmodule

module ot_dsrom_softmax_egress_macro_bank(
 input wire clk,w_en,input wire [6:0] w_addr,input wire [9215:0] w_code,
 input wire r_en,input wire [6:0] r_addr,output wire [9215:0] r_code
);
 wire [9215:0] raw;
 genvar b;generate for(b=0;b<36;b=b+1)begin:g_bank
  ot_sram_1r1w_128x256_m1_r2c2 mem(.clk(clk),.r_ce_in(r_en),.r_addr_in(r_addr),.rd_out(raw[b*256+:256]),
   .w_ce_in(w_en),.w_addr_in(w_addr),.wd_in(w_code[b*256+:256]),.w_mask_in({256{1'b1}}),
   .rr_en(2'd0),.rr_addr(14'd0),.cr_en(2'd0),.cr_sel(16'd0));
 end endgenerate
`ifdef SYNTHESIS
 assign r_code=raw;
`else
 assign #(455.3205489475797) r_code=raw;
`endif
endmodule

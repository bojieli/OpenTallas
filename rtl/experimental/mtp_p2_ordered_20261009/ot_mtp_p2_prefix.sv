`timescale 1ns/1ps
`default_nettype none
// Exact +0,E0,E1,E2 prefix; systematic Hsiao code matches ordered transport.
// mtp-lead 2026-10-09: BREG=1 gates healthy with a registered duplicate-state compare (bad_q; fault still sees bad
// directly). Default 0: the original logic.
module ot_mtp_p2_prefix #(parameter integer ENABLE=0, MUT_COPY_FIRST=0, BREG=0)(
 input wire clk,rst_n,start_v, output wire start_r,
 input wire [73:0] start_identity,input wire [26:0] start_ids,
 input wire in_v,output wire in_r,input wire [73:0] in_identity,
 input wire [8:0] in_expert,input wire in_shared,in_row_last,in_transaction_last,
 input wire [6:0] in_word,input wire [575:0] in_secded,
 output wire out_v,input wire out_r,output wire [73:0] out_identity,
 output wire [6:0] out_word,output wire out_last,output wire [575:0] out_secded,
 input wire abort,output wire done,fault,corrected
);
 generate if(!ENABLE) begin: disabled
 assign start_r=0;assign in_r=0;assign out_v=0;assign out_identity=0;
 assign out_word=0;assign out_last=0;assign out_secded=0;
 assign done=0;assign fault=0;assign corrected=0;
 end else begin: enabled
 localparam [3:0] IDLE=0,RECEIVE=1,IDEC=2,AREQ=3,AWAIT=4,ADEC=5,
 ARESULT=6,ISSUE=7,ADDS=8,ENC1=9,ENC2=10,WRITE=11,ADVANCE=12,HOLD=13;
 reg [3:0] state,state_copy;reg [1:0] expert_index,expert_copy;
 reg [6:0] word_index,word_copy;reg [73:0] identity,identity_copy;
 reg [26:0] ids,ids_copy;reg draining,draining_copy,fault_q,done_q,corrected_q;
 reg [511:0] contribution,accum,sum_q;
 wire bad=(state!=state_copy)||(expert_index!=expert_copy)||(word_index!=word_copy)||
 (identity!=identity_copy)||(ids!=ids_copy)||(draining!=draining_copy);
 reg bad_q;
 wire healthy=!fault_q&&!(BREG?bad_q:bad)&&!abort;
 assign start_r=healthy&&state==IDLE;assign in_r=healthy&&state==RECEIVE;
 assign out_v=healthy&&state==HOLD;assign out_identity=identity;
 assign out_word=word_index;assign out_last=word_index==79;
 assign done=done_q;assign fault=fault_q||bad;assign corrected=corrected_q;
 wire [511:0] input_data,acc_data,add_data;
 wire [7:0] iov,ice,iue,aov,ace,aue;
 wire [15:0] add_v;wire [31:0] add_err;wire [767:0] mem_q;
 wire [575:0] encoded;assign out_secded=encoded;
 for(genvar slice=0;slice<8;slice=slice+1)begin: codecs
 ot_secded_dec #(.K(64),.R(8)) id(.clk(clk),.rst_n(rst_n),.v(in_v&&in_r),
 .w(in_secded[72*slice+:72]),.ov(iov[slice]),.d(input_data[64*slice+:64]),
 .ce(ice[slice]),.ue(iue[slice]),.n_ce(),.n_ue());
 ot_secded_dec #(.K(64),.R(8)) ad(.clk(clk),.rst_n(rst_n),.v(healthy&&state==ADEC),
 .w(mem_q[72*slice+:72]),.ov(aov[slice]),.d(acc_data[64*slice+:64]),
 .ce(ace[slice]),.ue(aue[slice]),.n_ce(),.n_ue());
 ot_secded_enc #(.K(64),.R(8)) enc(.clk(clk),.d(sum_q[64*slice+:64]),.q(encoded[72*slice+:72]));
 end
 for(genvar lane=0;lane<16;lane=lane+1)begin: adds
 ot_v41_fadd #(.CUT(9'b1_0111_1011),.SPLIT9(0)) a(.clk(clk),.rst_n(rst_n),
 .valid_in(healthy&&state==ISSUE),.a(accum[32*lane+:32]),.b(contribution[32*lane+:32]),
 .y(add_data[32*lane+:32]),.err(add_err[2*lane+:2]),.valid_out(add_v[lane]));
 end
 for(genvar mi=0;mi<3;mi=mi+1)begin: memories
 wire [767:0] mw={192'd0,encoded};
 ot_sram_1r1w_128x256_m1_r2c2 m(.clk(clk),.r_ce_in(healthy&&state==AREQ),
 .r_addr_in(word_index),.rd_out(mem_q[256*mi+:256]),.w_ce_in(healthy&&state==WRITE),
 .w_addr_in(word_index),.wd_in(mw[256*mi+:256]),.w_mask_in({256{1'b1}}),
 .rr_en(2'd0),.rr_addr(12'd0),.cr_en(2'd0),.cr_sel(16'd0));
 end
 reg input_native_bad;integer lane;
 always @*begin input_native_bad=0;
 for(lane=0;lane<16;lane=lane+1)if(input_data[32*lane+:16]!=0)input_native_bad=1;
 end
 task automatic ns(input [3:0] n);begin state<=n;state_copy<=n;end endtask
 task automatic sw(input [6:0] n);begin word_index<=n;word_copy<=n;end endtask
 always @(posedge clk or negedge rst_n)begin
 if(!rst_n)begin state<=IDLE;state_copy<=IDLE;expert_index<=0;expert_copy<=0;
 word_index<=0;word_copy<=0;identity<=0;identity_copy<=0;ids<=0;ids_copy<=0;
 draining<=0;draining_copy<=0;fault_q<=0;done_q<=0;corrected_q<=0;
 contribution<=0;accum<=0;sum_q<=0;bad_q<=0;end
 else begin done_q<=0;bad_q<=bad;if(bad||abort)fault_q<=1;
 if(healthy)case(state)
 IDLE:if(start_v&&start_r)begin
 if(!(start_ids[8:0]<start_ids[17:9]&&start_ids[17:9]<start_ids[26:18]&&start_ids[26:18]<384))fault_q<=1;
 else begin identity<=start_identity;identity_copy<=start_identity;ids<=start_ids;ids_copy<=start_ids;
 expert_index<=0;expert_copy<=0;sw(0);draining<=0;draining_copy<=0;corrected_q<=0;ns(RECEIVE);end end
 RECEIVE:if(in_v&&in_r)begin
 if(in_identity!=identity||in_expert!=ids[9*expert_index+:9]||in_shared||in_word!=word_index||
 in_row_last!=(word_index==79)||in_transaction_last!=((expert_index==2)&&(word_index==79)))fault_q<=1;
 ns(IDEC);end
 IDEC:if(&iov)begin if((|iue)||input_native_bad)fault_q<=1;
 else begin contribution<=input_data;if(|ice)corrected_q<=1;
 if(expert_index==0)begin accum<=0;if(MUT_COPY_FIRST)begin sum_q<=input_data;ns(ENC1);end else ns(ISSUE);end
 else ns(AREQ);end end
 AREQ:ns(AWAIT);AWAIT:ns(ADEC);ADEC:ns(ARESULT);
 ARESULT:if(&aov)begin if(|aue)fault_q<=1;
 else begin if(|ace)corrected_q<=1;if(draining)begin sum_q<=acc_data;ns(ENC1);end
 else begin accum<=acc_data;ns(ISSUE);end end end
 ISSUE:ns(ADDS);
 ADDS:if(&add_v)begin if(|add_err)fault_q<=1;else begin sum_q<=add_data;ns(ENC1);end end
 ENC1:ns(ENC2);ENC2:if(draining)ns(HOLD);else ns(WRITE);
 WRITE:ns(ADVANCE);
 ADVANCE:if(word_index==79)begin sw(0);
 if(expert_index==2)begin draining<=1;draining_copy<=1;ns(AREQ);end
 else begin expert_index<=expert_index+1;expert_copy<=expert_copy+1;ns(RECEIVE);end end
 else begin sw(word_index+1);ns(RECEIVE);end
 HOLD:if(out_r&&out_v)begin if(word_index==79)begin done_q<=1;ns(IDLE);end
 else begin sw(word_index+1);ns(AREQ);end end
 default:fault_q<=1;
 endcase end end
 end endgenerate
endmodule
`default_nettype wire

`timescale 1ns/1ps
`default_nettype none
// Default-off full TP4-rank transport candidate. No FP32 arithmetic occurs here.
// Three complete expert rows drain in ascending selected-ID order, then shared.
// Each SRAM flit is eight SECDED72 words. The consumer MUST correct/decode and
// reject UE before arithmetic; sink_abort poisons this transaction on that path.
module ot_mtp_p2_ordered_rows #(parameter integer ENABLE=0, parameter integer MUT_ORDER=0) (
  input wire clk, rst_n,
  input wire start_v, output wire start_r,
  input wire [73:0] start_identity, // {user6,pos32,epoch32,stage2,rank2}
  input wire [26:0] start_ids,      // three ascending distinct 9-bit IDs, low ID first
  input wire [1:0] in_v, output reg [1:0] in_r,
  input wire [147:0] in_identity,
  input wire [17:0] in_expert,
  input wire [1:0] in_shared, in_last,
  input wire [13:0] in_word,
  input wire [1023:0] in_data,
  output wire out_v, input wire out_r,
  output wire [73:0] out_identity,
  output wire [8:0] out_expert,
  output wire out_shared, out_row_last, out_transaction_last,
  output wire [6:0] out_word,
  output wire [575:0] out_secded,
  input wire sink_abort,
  output reg done, fault
);
  generate if (!ENABLE) begin: disabled
    assign start_r=0; assign out_v=0; assign out_identity=0; assign out_expert=0;
    assign out_shared=0; assign out_row_last=0; assign out_transaction_last=0;
    assign out_word=0; assign out_secded=0;
    always @* begin in_r=0; done=0; fault=0; end
  end else begin: enabled
    reg busy, busy_copy;
    reg [73:0] identity, identity_copy;
    reg [26:0] ids, ids_copy;
    reg [6:0] count[0:3], count_copy[0:3];
    reg [3:0] complete, complete_copy;
    reg [1:0] read_bank, read_bank_copy;
    reg [6:0] read_word, read_word_copy;
    reg all_issued, all_issued_copy;
    reg [3:0] wp,rp,wp_copy,rp_copy;
    reg [575:0] queue[0:7];
    reg [8:0] queue_meta[0:7], queue_meta_copy[0:7]; // bank2 + word7
    reg pending, pending_copy;
    reg [8:0] pending_meta, pending_meta_copy;
    reg [3:0] wr_commit, wr_commit_last;
    reg [27:0] wr_address;
    wire [575:0] encoded[0:3];
    wire [767:0] bank_q[0:3];
    reg [3:0] accept_bank, accept_last;
    reg [511:0] accepted_data[0:3];
    reg [6:0] accepted_word[0:3];
    reg [1:0] target[0:1];
    reg valid_identity[0:1];
    reg valid_expert[0:1];
    reg [6:0] lane_word[0:1];
    integer l,b;
    integer si,sb;
    wire state_bad=(busy!=busy_copy)||(identity!=identity_copy)||(ids!=ids_copy)||
      (complete!=complete_copy)||(read_bank!=read_bank_copy)||
      (read_word!=read_word_copy)||(all_issued!=all_issued_copy)||
      (wp!=wp_copy)||(rp!=rp_copy)||(pending!=pending_copy)||(pending_meta!=pending_meta_copy)||
      (count[0]!=count_copy[0])||(count[1]!=count_copy[1])||
      (count[2]!=count_copy[2])||(count[3]!=count_copy[3]);
    wire queue_bad=(queue_meta[rp[2:0]]!=queue_meta_copy[rp[2:0]]);
    wire [3:0] occupancy=wp-rp;
    wire issue=busy&&!fault&&!state_bad&&!all_issued&&
      complete[read_bank]&&(occupancy+pending<8);
    wire pop=out_v&&out_r;
    assign start_r=!busy&&!fault&&!state_bad;
    assign out_v=busy&&!fault&&!state_bad&&(wp!=rp)&&!queue_bad;
    assign out_secded=queue[rp[2:0]];
    assign out_word=queue_meta[rp[2:0]][6:0];
    assign out_shared=queue_meta[rp[2:0]][8:7]==3;
    assign out_expert=out_shared?9'd0:ids[9*queue_meta[rp[2:0]][8:7]+:9];
    assign out_identity=identity;
    assign out_row_last=out_word==79;
    assign out_transaction_last=out_shared&&out_row_last;

    always @* begin
      accept_bank=0; accept_last=0; in_r=0;
      for(b=0;b<4;b=b+1) begin accepted_data[b]=0;accepted_word[b]=0;end
      for(l=0;l<2;l=l+1) begin
        target[l]=0;valid_expert[l]=in_shared[l];
        lane_word[l]=in_word[7*l+:7];
        if(in_shared[l]) target[l]=3;
        else for(b=0;b<3;b=b+1)
          if(in_expert[9*l+:9]==ids[9*b+:9]) begin target[l]=b;valid_expert[l]=1;end
        valid_identity[l]=(in_identity[74*l+:74]==identity);
        // Two input lanes may write different row banks simultaneously. Lane0
        // wins a bank conflict; the other producer holds its full beat.
        in_r[l]=busy&&!fault&&!state_bad&&
          !(l==1&&in_v[0]&&in_r[0]&&target[0]==target[1]);
        if(in_v[l]&&in_r[l]&&valid_identity[l]&&valid_expert[l]&&
           count[target[l]]<80&&lane_word[l]==count[target[l]]&&in_last[l]==(lane_word[l]==79)) begin
          accept_bank[target[l]]=1;accept_last[target[l]]=in_last[l];
          accepted_data[target[l]]=in_data[512*l+:512];
          accepted_word[target[l]]=lane_word[l];
        end
      end
    end
    for(genvar bank=0;bank<4;bank=bank+1) begin: banks
      for(genvar slice=0;slice<8;slice=slice+1) begin: codes
        ot_secded_enc #(.K(64),.R(8)) enc(.clk(clk),
          .d(accepted_data[bank][64*slice+:64]),.q(encoded[bank][72*slice+:72]));
      end
      wire [767:0] macro_word={192'd0,encoded[bank]};
      for(genvar macro_index=0;macro_index<3;macro_index=macro_index+1) begin: macros
        ot_sram_1r1w_128x256_m1_r2c2 mem(.clk(clk),
          .r_ce_in(issue&&read_bank==bank),.r_addr_in(read_word),
          .rd_out(bank_q[bank][256*macro_index+:256]),
          .w_ce_in(wr_commit[bank]),.w_addr_in(wr_address[7*bank+:7]),
          .wd_in(macro_word[256*macro_index+:256]),.w_mask_in(256'hffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff),
          .rr_en(2'd0),.rr_addr(12'd0),.cr_en(2'd0),.cr_sel(16'd0));
      end
    end
    always @(posedge clk or negedge rst_n) begin
      if(!rst_n) begin
        busy<=0;busy_copy<=0;identity<=0;identity_copy<=0;ids<=0;ids_copy<=0;
        complete<=0;complete_copy<=0;read_bank<=0;read_bank_copy<=0;
        read_word<=0;read_word_copy<=0;all_issued<=0;all_issued_copy<=0;
        wp<=0;rp<=0;wp_copy<=0;rp_copy<=0;pending<=0;pending_copy<=0;
        pending_meta<=0;pending_meta_copy<=0;wr_commit<=0;wr_commit_last<=0;
        wr_address<=0;done<=0;fault<=0;
        for(sb=0;sb<4;sb=sb+1) begin count[sb]<=0;count_copy[sb]<=0;end
      end else begin
        done<=0;wr_commit<=accept_bank;wr_commit_last<=accept_last;
        for(sb=0;sb<4;sb=sb+1) wr_address[7*sb+:7]<=accepted_word[sb];
        if(state_bad||sink_abort||(busy&&wp!=rp&&queue_bad)) fault<=1;
        for(si=0;si<2;si=si+1) if(in_v[si]&&in_r[si]&&
          (!valid_identity[si]||!valid_expert[si]||count[target[si]]>=80||lane_word[si]!=count[target[si]]||
           in_last[si]!=(lane_word[si]==79))) fault<=1;
        for(sb=0;sb<4;sb=sb+1) begin
          if(accept_bank[sb]) begin count[sb]<=count[sb]+1;count_copy[sb]<=count_copy[sb]+1;end
          if(wr_commit[sb]&&wr_commit_last[sb]) begin complete[sb]<=1;complete_copy[sb]<=1;end
        end
        pending<=issue;pending_copy<=issue;
        if(issue) begin
          pending_meta<={read_bank,read_word};pending_meta_copy<={read_bank,read_word};
          if(read_word==79) begin
            read_word<=0;read_word_copy<=0;
            if(read_bank==3) begin all_issued<=1;all_issued_copy<=1;end
            else begin read_bank<=read_bank+1;read_bank_copy<=read_bank_copy+1;end
          end else begin read_word<=read_word+1;read_word_copy<=read_word_copy+1;end
        end
        if(pending&&!fault&&!state_bad) begin
          queue[wp[2:0]]<=bank_q[pending_meta[8:7]][575:0];
          queue_meta[wp[2:0]]<=pending_meta;queue_meta_copy[wp[2:0]]<=pending_meta_copy;
          wp<=wp+1;wp_copy<=wp_copy+1;
        end
        if(pop) begin
          rp<=rp+1;rp_copy<=rp_copy+1;
          if(out_transaction_last) begin busy<=0;busy_copy<=0;done<=1;end
        end
        if(start_v&&start_r) begin
          if(!(start_ids[8:0]<start_ids[17:9]&&start_ids[17:9]<start_ids[26:18]&&start_ids[26:18]<384)) fault<=1;
          else begin
            busy<=1;busy_copy<=1;identity<=start_identity;identity_copy<=start_identity;
            ids<=start_ids;ids_copy<=start_ids;complete<=0;complete_copy<=0;
            read_bank<=MUT_ORDER?1:0;read_bank_copy<=MUT_ORDER?1:0;read_word<=0;read_word_copy<=0;
            all_issued<=0;all_issued_copy<=0;wp<=0;rp<=0;wp_copy<=0;rp_copy<=0;
            pending<=0;pending_copy<=0;wr_commit<=0;wr_commit_last<=0;
            for(sb=0;sb<4;sb=sb+1) begin count[sb]<=0;count_copy[sb]<=0;end
          end
        end
      end
    end
  end endgenerate
endmodule
`default_nettype wire

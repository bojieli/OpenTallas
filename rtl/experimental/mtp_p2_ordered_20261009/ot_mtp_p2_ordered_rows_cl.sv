`timescale 1ns/1ps
`default_nettype none
// drive-0158 dual-track "-cl" of ot_mtp_p2_ordered_rows (REVIEW_20261009 R7 + addendum 02:35; templates D + A).
// Failure fixed: mtp-p2-transport-8ed8e9762 EARLY_FAIL_SETUP TT -939 at place: input->reg in_expert[7] -> banks[0]
// .codes[0].enc.q, 908 ps of logic (identity/expert/count compares + lane select + SECDED parity tree in one cycle
// straight from the pins).  Structure, function unchanged (same ascending-ID drain, same SECDED72 words, same checks):
//  A  PIN STATION: every in_* bit is captured by a pin flop (2-entry registered-ready skid per lane; in_r is a flop).
//  B  ACCEPT: identity / expert / word / last checks + bank select from the station (registered accept + data).
//  C  ENCODE: SECDED(72,64) of the registered accepted data (ot_secded_enc, unchanged) -> SRAM write next edge.
//  Cost: +2 edges on the producer -> SRAM write path (station + accept register); drain order, read path, queue and
//  output unchanged.  ~+2 cycles per P2 transaction (inside the approved +0.2 us per step).
// REVIEW S4 / R7: the duplicated "_copy" state mirrors (state_bad / queue_bad) are NOT carried (control mirrors are
// rejected; SECDED stays on the 12 SRAM payloads only).
module ot_mtp_p2_ordered_rows_cl #(parameter integer ENABLE=0, parameter integer MUT_ORDER=0) (
  input wire clk, rst_n,
  input wire start_v, output wire start_r,
  input wire [73:0] start_identity,
  input wire [26:0] start_ids,
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
  localparam integer BW = 74 + 9 + 1 + 1 + 7 + 512;   // one lane beat: identity, expert, shared, last, word, data
  generate if (!ENABLE) begin: disabled
    always @* in_r = 0;
    always @(posedge clk) begin done <= 0; fault <= 0; end
    assign start_r=0; assign out_v=0; assign out_identity=0; assign out_expert=0;
    assign out_shared=0; assign out_row_last=0; assign out_transaction_last=0;
    assign out_word=0; assign out_secded=0;
  end else begin: enabled
    reg busy;
    reg [73:0] identity;
    reg [26:0] ids;
    reg [6:0] count[0:3];
    reg [3:0] complete;
    reg [1:0] read_bank;
    reg [6:0] read_word;
    reg all_issued;
    reg [3:0] wp,rp;
    reg [575:0] queue[0:7];
    reg [8:0] queue_meta[0:7];
    reg pending;
    reg [8:0] pending_meta;
    // ---- A: pin station, 2-entry skid per lane, registered ready ----
    reg [BW-1:0] st_m[0:1], st_s[0:1];       // main / skid entry
    reg [1:0] st_mv, st_sv;
    wire [1:0] take;                          // B consumes the main entry of lane l this cycle
    // ---- B: accept register ----
    reg [3:0] acc_bank, acc_last;
    reg [511:0] acc_data[0:3];
    reg [6:0] acc_word[0:3];
    // ---- C: encode + write ----
    reg [3:0] wr_commit, wr_commit_last;
    reg [27:0] wr_address;
    wire [575:0] encoded[0:3];
    wire [767:0] bank_q[0:3];
    // decode of the station main entries
    reg [3:0] accept_bank, accept_last;
    reg [511:0] accepted_data[0:3];
    reg [6:0] accepted_word[0:3];
    reg [1:0] target[0:1];
    reg valid_identity[0:1], valid_expert[0:1], bad[0:1], go[0:1];
    reg [6:0] lane_word[0:1];
    reg [1:0] take_r;
    integer l,b,si,sb;
    wire [3:0] occupancy=wp-rp;
    wire issue=busy&&!fault&&!all_issued&&complete[read_bank]&&(occupancy+pending<8);
    wire pop=out_v&&out_r;
    // ready (registered): accepting while the transaction is open and not faulted
    wire busy_next_ready = (busy || (start_v&&start_r)) && !fault && !sink_abort;
    assign start_r=!busy&&!fault;
    assign out_v=busy&&!fault&&(wp!=rp);
    assign out_secded=queue[rp[2:0]];
    assign out_word=queue_meta[rp[2:0]][6:0];
    assign out_shared=queue_meta[rp[2:0]][8:7]==3;
    assign out_expert=out_shared?9'd0:ids[9*queue_meta[rp[2:0]][8:7]+:9];
    assign out_identity=identity;
    assign out_row_last=out_word==79;
    assign out_transaction_last=out_shared&&out_row_last;
    assign take = take_r;
    // B: the same per-beat checks as the reference, on the station's main entries.  Lane 0 wins a bank conflict;
    // lane 1 keeps its beat in the station (it is consumed next cycle).
    always @* begin
      accept_bank=0; accept_last=0; take_r=0;
      for(b=0;b<4;b=b+1) begin accepted_data[b]=0;accepted_word[b]=0;end
      for(l=0;l<2;l=l+1) begin
        target[l]=0; valid_expert[l]=st_m[l][BW-74-9-1];
        lane_word[l]=st_m[l][512 +: 7];
        if(st_m[l][BW-74-9-1]) target[l]=3;
        else for(b=0;b<3;b=b+1)
          if(st_m[l][BW-74-1 -: 9]==ids[9*b+:9]) begin target[l]=b;valid_expert[l]=1;end
        valid_identity[l]=(st_m[l][BW-1 -: 74]==identity);
        go[l]=st_mv[l]&&busy&&!fault&&!(l==1&&st_mv[0]&&target[0]==target[1]);
        bad[l]=!valid_identity[l]||!valid_expert[l]||count[target[l]]>=80||lane_word[l]!=count[target[l]]||
               st_m[l][512+7]!=(lane_word[l]==79);
        if(go[l]) begin
          take_r[l]=1;
          if(!bad[l]) begin
            accept_bank[target[l]]=1;accept_last[target[l]]=st_m[l][512+7];
            accepted_data[target[l]]=st_m[l][511:0];
            accepted_word[target[l]]=lane_word[l];
          end
        end
      end
    end
    for(genvar bank=0;bank<4;bank=bank+1) begin: banks
      for(genvar slice=0;slice<8;slice=slice+1) begin: codes
        ot_secded_enc #(.K(64),.R(8)) enc(.clk(clk),
          .d(acc_data[bank][64*slice+:64]),.q(encoded[bank][72*slice+:72]));
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
    // A: station data path (no reset on data)
    always @(posedge clk) begin
      for(si=0;si<2;si=si+1) begin
        // main <- skid when the main is consumed and the skid holds a beat; main <- pins when it is (or becomes) free
        if(take[si]||!st_mv[si]) begin
          if(st_sv[si]) st_m[si]<=st_s[si];
          else st_m[si]<={in_identity[74*si+:74],in_expert[9*si+:9],in_shared[si],in_last[si],in_word[7*si+:7],in_data[512*si+:512]};
        end
        if(in_v[si]&&in_r[si]&&st_mv[si]&&!take[si]) st_s[si]<={in_identity[74*si+:74],in_expert[9*si+:9],in_shared[si],in_last[si],in_word[7*si+:7],in_data[512*si+:512]};
        else if(in_v[si]&&in_r[si]&&st_sv[si]) st_s[si]<={in_identity[74*si+:74],in_expert[9*si+:9],in_shared[si],in_last[si],in_word[7*si+:7],in_data[512*si+:512]};
      end
      for(sb=0;sb<4;sb=sb+1) begin acc_data[sb]<=accepted_data[sb]; acc_word[sb]<=accepted_word[sb]; wr_address[7*sb+:7]<=acc_word[sb]; end
    end
    always @(posedge clk or negedge rst_n) begin
      if(!rst_n) begin
        busy<=0;identity<=0;ids<=0;complete<=0;read_bank<=0;read_word<=0;all_issued<=0;
        wp<=0;rp<=0;pending<=0;pending_meta<=0;wr_commit<=0;wr_commit_last<=0;acc_bank<=0;acc_last<=0;
        done<=0;fault<=0;st_mv<=0;st_sv<=0;in_r<=0;
        for(sb=0;sb<4;sb=sb+1) count[sb]<=0;
      end else begin
        done<=0;
        // A: occupancy; ready is a flop: 1 while the skid is empty (a beat accepted with in_r=1 always has a slot)
        for(si=0;si<2;si=si+1) begin
          case({in_v[si]&&in_r[si], take[si]})
            2'b10: if(!st_mv[si]) st_mv[si]<=1; else st_sv[si]<=1;
            2'b01: if(st_sv[si]) st_sv[si]<=0; else st_mv[si]<=0;
            default: ;   // 2'b11: one in, one out -> occupancy unchanged; 2'b00 unchanged
          endcase
        end
        for(si=0;si<2;si=si+1) begin
          // next occupancy >= 2 -> not ready
          if((st_mv[si]+st_sv[si]+(in_v[si]&&in_r[si])-take[si])>=2) in_r[si]<=0;
          else in_r[si]<=busy_next_ready;
        end
        // B -> C
        acc_bank<=accept_bank; acc_last<=accept_last;
        wr_commit<=acc_bank; wr_commit_last<=acc_last;
        if(sink_abort) fault<=1;
        for(si=0;si<2;si=si+1) if(go[si]&&bad[si]) fault<=1;
        for(sb=0;sb<4;sb=sb+1) begin
          if(accept_bank[sb]) count[sb]<=count[sb]+1;
          if(wr_commit[sb]&&wr_commit_last[sb]) complete[sb]<=1;
        end
        pending<=issue;
        if(issue) begin
          pending_meta<={read_bank,read_word};
          if(read_word==79) begin
            read_word<=0;
            if(read_bank==3) all_issued<=1; else read_bank<=read_bank+1;
          end else read_word<=read_word+1;
        end
        if(pending&&!fault) begin
          queue[wp[2:0]]<=bank_q[pending_meta[8:7]][575:0];
          queue_meta[wp[2:0]]<=pending_meta;
          wp<=wp+1;
        end
        if(pop) begin
          rp<=rp+1;
          if(out_transaction_last) begin busy<=0;done<=1;end
        end
        if(start_v&&start_r) begin
          if(!(start_ids[8:0]<start_ids[17:9]&&start_ids[17:9]<start_ids[26:18]&&start_ids[26:18]<384)) fault<=1;
          else begin
            busy<=1;identity<=start_identity;ids<=start_ids;complete<=0;
            read_bank<=MUT_ORDER?1:0;read_word<=0;all_issued<=0;wp<=0;rp<=0;
            pending<=0;wr_commit<=0;wr_commit_last<=0;acc_bank<=0;acc_last<=0;st_mv<=0;st_sv<=0;
            for(sb=0;sb<4;sb=sb+1) count[sb]<=0;
          end
        end
      end
    end
  end endgenerate
endmodule
`default_nettype wire

module kvattn_rel_pv_bound #(parameter integer PAIR=0,FIRST_INPUT_AGE=20,MUT=0) (
        input logic clk
        , input logic rst_n
        , input logic start
        , input logic [32:0]  col_clk
        , input logic [13:0]  context_len
        , input logic [15:0]  epoch
        , input logic [7:0]  in_valid
        , input logic [8191:0]  in_v
        , input logic [511:0]  in_e
        , input logic [111:0]  in_t
        , input logic [127:0]  in_epoch
        , output logic [7:0]  req_valid
        , output logic [111:0]  req_t
        , output logic out_valid
        , output logic [16383:0]  out_leaf
        , output logic [15:0]  out_epoch
        , output logic fault
        , output logic busy
        , output logic [15:0]  out_age
    );
 generate
 if (FIRST_INPUT_AGE!=20 || MUT!=0) begin:bad_profile
 UNSUPPORTED_PV_ARCHIVE_PROFILE bad();
 end else if(PAIR==0) begin:p0
 ot_qwen_tp8_pv_wide_pair_d u_native (.clk(clk), .rst_n(rst_n), .start(start), .col_clk(col_clk), .context_len(context_len), .epoch(epoch), .in_valid(in_valid), .in_v(in_v), .in_e(in_e), .in_t(in_t), .in_epoch(in_epoch), .req_valid(req_valid), .req_t(req_t), .out_valid(out_valid), .out_leaf(out_leaf), .out_epoch(out_epoch), .fault(fault), .busy(busy), .out_age(out_age));
 end else if(PAIR==1)begin:p1
 ot_qwen_tp8_pv_wide_pair_5 u_native (.clk(clk), .rst_n(rst_n), .start(start), .col_clk(col_clk), .context_len(context_len), .epoch(epoch), .in_valid(in_valid), .in_v(in_v), .in_e(in_e), .in_t(in_t), .in_epoch(in_epoch), .req_valid(req_valid), .req_t(req_t), .out_valid(out_valid), .out_leaf(out_leaf), .out_epoch(out_epoch), .fault(fault), .busy(busy), .out_age(out_age));
 end else begin:bad_pair
 UNSUPPORTED_PV_ARCHIVE_PAIR bad();
 end
 endgenerate
 endmodule

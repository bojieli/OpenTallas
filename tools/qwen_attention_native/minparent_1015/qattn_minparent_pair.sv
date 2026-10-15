module qattn_minparent_pair #(parameter integer PAIR=0) (
        input logic clk
        , input logic rst_n
        , input logic start
        , input logic [31:0]  slice_clk
        , input logic [13:0]  context_len
        , input logic [15:0]  epoch
        , input logic in_valid
        , output logic in_ready
        , input logic [1023:0]  in_v
        , input logic [63:0]  in_e
        , input logic [6:0]  in_c
        , input logic [13:0]  in_t
        , input logic [15:0]  in_epoch
        , input logic in_first
        , input logic in_last
        , output logic out_valid
        , input logic out_ready
        , output logic [16383:0]  out_leaf
        , output logic [6:0]  out_c
        , output logic [15:0]  out_epoch
        , output logic fault
        , output logic busy
        , output logic [31:0]  accepted
        , output logic [31:0]  committed
        , output logic [7:0]  peak_inflight
    );
    
initial if(PAIR!=0 && PAIR!=1)$fatal(1,"Unsupported PAIR");
generate if(PAIR==0)begin:lo
 ot_qwen_tp8_pv256_pair_c u(.*);
end else begin:hi
 ot_qwen_tp8_pv256_pair_b u(.*);
end endgenerate
endmodule

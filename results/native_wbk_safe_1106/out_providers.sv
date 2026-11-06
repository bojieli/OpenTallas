`timescale 1ns/1ps
`default_nettype none
module ot_wbq_sw_split_out__fcore #(parameter integer MUT=0)(
 input wire hbm_clk,hbm_rst_n,
 input wire [15:0] in_v,output wire [15:0] in_ready,
 input wire [479:0] in_addr,input wire [4095:0] in_data,
 output wire [15:0] w_k_v,input wire [15:0] w_k_rdy,
 output wire [479:0] w_k_addr,output wire [4095:0] w_k_wdata
);
 genvar p;
 generate for(p=0;p<16;p=p+1)begin:pc_pin
  wire krst;
  ot_reset_sync u_krst(.clk(hbm_clk),.async_rst_n(hbm_rst_n),.sync_rst_n(krst));
  ot_hbm_svc_pin_skid2 #(.WIDTH(286),.MUT(MUT)) u_k(.clk(hbm_clk),.rst_n(krst),.in_v(in_v[p]),.in_r(in_ready[p]),
   .in_data({in_addr[30*p+:30],in_data[256*p+:256]}),.out_v(w_k_v[p]),.out_r(w_k_rdy[p]),
   .out_data({w_k_addr[30*p+:30],w_k_wdata[256*p+:256]}));
 end endgenerate
endmodule
module ot_wbq_sw_split_out (
    input wire hbm_clk,
    input wire hbm_rst_n,
    input wire [15:0] in_v,
    output wire [15:0] in_ready,
    input wire [479:0] in_addr,
    input wire [4095:0] in_data,
    output wire [15:0] w_k_v,
    input wire [15:0] w_k_rdy,
    output wire [479:0] w_k_addr,
    output wire [4095:0] w_k_wdata
);
    wire [0:0] hbm_rst_n__rr;
    (* keep *) ot_hbm_face_rst_relay #(.W(1), .N(2)) u_brst_hbm_rst_n (.clk(hbm_clk), .rst_ni(hbm_rst_n), .rst_no(hbm_rst_n__rr));
    wire [15:0] w_k_v__fc;
    (* keep *) ot_hbm_face_reg #(.W(16)) u_bout_w_k_v (.clk(hbm_clk), .d(w_k_v__fc), .q(w_k_v));
    wire [15:0] w_k_rdy__fq;
    (* keep *) ot_hbm_face_reg #(.W(16)) u_bin_w_k_rdy (.clk(hbm_clk), .d(w_k_rdy), .q(w_k_rdy__fq));
    wire [479:0] w_k_addr__fc;
    (* keep *) ot_hbm_face_reg #(.W(480)) u_bout_w_k_addr (.clk(hbm_clk), .d(w_k_addr__fc), .q(w_k_addr));
    wire [4095:0] w_k_wdata__fc;
    (* keep *) ot_hbm_face_reg #(.W(4096)) u_bout_w_k_wdata (.clk(hbm_clk), .d(w_k_wdata__fc), .q(w_k_wdata));
    ot_wbq_sw_split_out__fcore u_fcore (
        .hbm_clk(hbm_clk),
        .hbm_rst_n(hbm_rst_n__rr),
        .in_v(in_v),
        .in_ready(in_ready),
        .in_addr(in_addr),
        .in_data(in_data),
        .w_k_v(w_k_v__fc),
        .w_k_rdy(w_k_rdy__fq),
        .w_k_addr(w_k_addr__fc),
        .w_k_wdata(w_k_wdata__fc)
    );
endmodule
module ot_hbm_svc_pin_skid2 #(parameter integer WIDTH=1,MUT=0)(
    input wire clk,rst_n,input wire in_v,output wire in_r,
    input wire [WIDTH-1:0]in_data,output wire out_v,input wire out_r,
    output wire [WIDTH-1:0]out_data
);
    reg head_valid,tail_valid;
    reg [WIDTH-1:0]head_data,tail_data;
    wire push=in_v&&in_r,pop=out_v&&out_r;
    assign in_r=!tail_valid;assign out_v=head_valid;assign out_data=head_data;
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n)begin head_valid<=0;tail_valid<=0;end
        else begin
            case({push,pop})
                2'b10:begin
                    if(!head_valid)begin head_data<=in_data;head_valid<=1;end
                    else begin tail_data<=in_data;tail_valid<=1;end
                end
                2'b01:begin
                    if(tail_valid)head_data<=tail_data;
                    head_valid<=tail_valid;tail_valid<=0;
                end
                2'b11:begin head_data<=in_data;head_valid<=1;tail_valid<=0;end
                default:;
            endcase
            // Checked negative control: illegally overwrite a stalled head.
            if(MUT!=0 && push && head_valid && !out_r)head_data<=in_data;
        end
    end
endmodule
`timescale 1ns/1ps
// Asynchronous-assert, synchronous-deassert reset conditioner.  ASYNC_STAGES
// includes the output stage and must be at least two for a CDC/RDC boundary.
module ot_reset_sync #(
    parameter integer ASYNC_STAGES = 2,
    parameter integer OUTPUT_COPIES = 1,
    // TREE 1 (S81-SHLK12 2026-10-20, default 0 = unchanged): with OUTPUT_COPIES > 1 the first stage is itself
    // ceil(OUTPUT_COPIES / 16) kept copies (D = 1), so after the synthesis copy pass no flop of the synchroniser drives
    // more than 16 loads.  Same release edge (still ASYNC_STAGES = 2 edges).
    parameter integer TREE = 0
) (
    input  wire clk,
    input  wire async_rst_n,
    output wire sync_rst_n
);
    (* async_reg = "true" *) reg [ASYNC_STAGES-1:0] reset_pipe;

    always @(posedge clk or negedge async_rst_n) begin
        if (!async_rst_n)
            reset_pipe <= {ASYNC_STAGES{1'b0}};
        else
            reset_pipe <= {reset_pipe[ASYNC_STAGES-2:0],1'b1};
    end

    generate if (OUTPUT_COPIES > 1 && TREE != 0 && ASYNC_STAGES == 2) begin : g_tree
        localparam integer L1 = (OUTPUT_COPIES + 15) / 16;
        (* keep = "true", async_reg = "true" *) reg [L1-1:0] reset_l1__ot_rlv;
        (* keep = "true" *) reg [OUTPUT_COPIES-1:0] reset_regions__ot_rlv;
        always @(posedge clk or negedge async_rst_n)
            if (!async_rst_n) reset_l1__ot_rlv <= '0;
            else reset_l1__ot_rlv <= {L1{1'b1}};
        // every output copy takes the first-stage copy 0 in RTL: both families are identical registers, and the
        // synthesis copy pass (physical/common_flow/ot_rst_copies.tcl) spreads the output copies over the first-stage
        // copies and the reset loads over the output copies (<= OT_RST_COPIES_MAX each)
        always @(posedge clk or negedge async_rst_n)
            if (!async_rst_n) reset_regions__ot_rlv <= '0;
            else reset_regions__ot_rlv <= {OUTPUT_COPIES{reset_l1__ot_rlv[0]}};
        assign sync_rst_n = reset_regions__ot_rlv[0];
    end else if (OUTPUT_COPIES > 1) begin : g_regions
        // Same release edge as reset_pipe's last stage. The canonicalizer
        // proves identical D/clock/reset and partitions reset loads <=256.
        (* keep = "true" *) reg [OUTPUT_COPIES-1:0] reset_regions__ot_rlv;
        always @(posedge clk or negedge async_rst_n)
            if (!async_rst_n) reset_regions__ot_rlv <= '0;
            else reset_regions__ot_rlv <= {OUTPUT_COPIES{reset_pipe[ASYNC_STAGES-2]}};
        assign sync_rst_n = reset_regions__ot_rlv[0];
    end else begin : g_original
        assign sync_rst_n = reset_pipe[ASYNC_STAGES-1];
    end endgenerate

`ifndef SYNTHESIS
    initial begin
        if (ASYNC_STAGES < 2)
            $error("ot_reset_sync requires at least two stages");
    end
`endif
endmodule

// GENERATED by face_shell.py (HBM-FACE): one face register stage, W bits, no reset (owner dec. 13d: datapath flops
// carry no reset; flushed by the reset-held producer).  keep_hierarchy + keep: every face bit keeps its OWN flop through
// Yosys (opt_merge / opt_clean / opt_dff never fold or drop a face register: face_guard R2).
(* keep_hierarchy, keep *)
module ot_hbm_face_reg #(parameter integer W = 1) (
    input  wire         clk,
    input  wire [W-1:0] d,
    output reg  [W-1:0] q
);
    always @(posedge clk) q <= d;
endmodule

// GENERATED by face_shell.py (DIE-HBM-61/RTL): face reset relay, W active-low reset bits, async assert,
// synchronous release after N clock edges (N >= 2).  keep_hierarchy + keep (the relay flops stay at the face).
(* keep_hierarchy, keep *)
module ot_hbm_face_rst_relay #(parameter integer W = 1, parameter integer N = 2) (
    input  wire         clk,
    input  wire [W-1:0] rst_ni,
    output wire [W-1:0] rst_no
);
    genvar g;
    generate for (g = 0; g < W; g = g + 1) begin : g_b
        reg [N-1:0] s;
        always @(posedge clk or negedge rst_ni[g])
            if (!rst_ni[g]) s <= {N{1'b0}};
            else            s <= {s[N-2:0], 1'b1};
        assign rst_no[g] = s[N-1];
    end endgenerate
endmodule


`timescale 1ns/1ps
// Does the pipelined TENSOR lane compute what the legacy lane computes?
//
// Both lanes carry the same memory-mapped contract, so the check is the one that
// matters for a drop-in: run BOTH on the same operand memories with the same
// descriptor and require the same output write stream, the same error code, and the
// same output count. Cycle counts must differ -- that is the point of the change --
// so they are reported rather than compared.
//
// ot_mac_bf16_fp32_pipe is already proven bit-identical to the scalar authority over
// 901,440 operand triples, so what is under test here is the LANE: address
// generation, the interleave that breaks the loop-carried dependence, the slot
// bookkeeping that returns each result to its own accumulator, and the drain order.
module tb_mac_lane_pipe_equiv;
    localparam integer AW = 16, MEM = 1 << 14;
    reg clk = 0, rst_n = 0;
    always #0.5 clk = ~clk;

    reg [31:0] mem_a [0:MEM-1];
    reg [31:0] mem_b [0:MEM-1];

    reg         start = 0;
    reg [15:0]  cfg_rows = 0, cfg_cols = 0, cfg_depth = 0;
    reg [31:0]  cfg_a_base = 0, cfg_b_base = 0, cfg_out_base = 0;

    // ---- legacy lane ----
    wire        L_ae, L_be, L_se, L_te, L_we, L_busy, L_done;
    wire [31:0] L_aa, L_ba, L_sa, L_ta, L_oa, L_od, L_oc, L_sat, L_mc;
    wire [7:0]  L_err;
    reg  [31:0] L_ad, L_bd;

    ot_a3_mac_lane legacy (
        .clk(clk), .rst_n(rst_n), .start(start),
        .cfg_rows(cfg_rows), .cfg_cols(cfg_cols), .cfg_depth(cfg_depth),
        .cfg_dtype_a(8'h10), .cfg_dtype_b(8'h10),
        .cfg_a_base(cfg_a_base), .cfg_b_base(cfg_b_base),
        .cfg_scale_a(1'b0), .cfg_scale_b(1'b0),
        .cfg_block_a(16'd0), .cfg_block_b(16'd0),
        .cfg_block_rows_a(16'd0), .cfg_block_rows_b(16'd0),
        .cfg_scale_a_base(32'd0), .cfg_scale_b_base(32'd0),
        .cfg_out_base(cfg_out_base),
        .a_rd_en(L_ae), .a_rd_addr(L_aa), .a_rd_data(L_ad),
        .b_rd_en(L_be), .b_rd_addr(L_ba), .b_rd_data(L_bd),
        .s_rd_en(L_se), .s_rd_addr(L_sa), .s_rd_data(32'd0),
        .t_rd_en(L_te), .t_rd_addr(L_ta), .t_rd_data(32'd0),
        .out_we(L_we), .out_addr(L_oa), .out_data(L_od),
        .busy(L_busy), .done(L_done), .error_code(L_err),
        .out_count(L_oc), .saturation_count(L_sat), .mac_count(L_mc));

    always @(posedge clk) begin
        if (L_ae) L_ad <= mem_a[L_aa[13:0]];
        if (L_be) L_bd <= mem_b[L_ba[13:0]];
    end

    // ---- pipelined lane ----
    wire        P_ae, P_be, P_we, P_busy, P_done;
    wire [31:0] P_aa, P_ba, P_oa, P_od, P_oc, P_sat, P_mc;
    wire [7:0]  P_err;
    reg  [31:0] P_ad, P_bd;

    ot_a3_mac_lane_pipe #(.LANES_IF(8)) fast (
        .clk(clk), .rst_n(rst_n), .start(start),
        .cfg_rows(cfg_rows), .cfg_cols(cfg_cols), .cfg_depth(cfg_depth),
        .cfg_dtype_a(8'h10), .cfg_dtype_b(8'h10),
        .cfg_a_base(cfg_a_base), .cfg_b_base(cfg_b_base),
        .cfg_out_base(cfg_out_base),
        .a_rd_en(P_ae), .a_rd_addr(P_aa), .a_rd_data(P_ad),
        .b_rd_en(P_be), .b_rd_addr(P_ba), .b_rd_data(P_bd),
        .out_we(P_we), .out_addr(P_oa), .out_data(P_od),
        .busy(P_busy), .done(P_done), .error_code(P_err),
        .out_count(P_oc), .saturation_count(P_sat), .mac_count(P_mc));

    always @(posedge clk) begin
        if (P_ae) P_ad <= mem_a[P_aa[13:0]];
        if (P_be) P_bd <= mem_b[P_ba[13:0]];
    end

    // ---- capture both write streams -----------------------------------------
    localparam integer WMAX = 8192;
    reg [31:0] La [0:WMAX-1], Ld [0:WMAX-1];
    reg [31:0] Pa [0:WMAX-1], Pd [0:WMAX-1];
    integer Ln = 0, Pn = 0, Lcyc = 0, Pcyc = 0;

    always @(posedge clk) if (rst_n) begin
        if (L_we && Ln < WMAX) begin La[Ln] = L_oa; Ld[Ln] = L_od; Ln = Ln + 1; end
        if (P_we && Pn < WMAX) begin Pa[Pn] = P_oa; Pd[Pn] = P_od; Pn = Pn + 1; end
        if (L_busy) Lcyc = Lcyc + 1;
        if (P_busy) Pcyc = Pcyc + 1;
    end

    integer i, j, bad = 0, cases = 0;
    reg [31:0] rnd = 32'h13572468;
    function [31:0] nxt; input [31:0] s; nxt = s*32'd1664525 + 32'd1013904223; endfunction
    reg [7:0] ex;

    task run_case(input [15:0] M, input [15:0] N, input [15:0] K);
        begin
            //: BF16 operands in a range that keeps every product and partial sum
            //: inside binary32, so both lanes take the no-error path and the
            //: comparison is about arithmetic rather than about fault handling.
            for (i = 0; i < MEM; i = i + 1) begin
                rnd = nxt(rnd); ex = 8'd118 + {5'b0, rnd[18:16]};
                mem_a[i] = {16'b0, rnd[31], ex, rnd[14:8]};
                rnd = nxt(rnd); ex = 8'd118 + {5'b0, rnd[18:16]};
                mem_b[i] = {16'b0, rnd[31], ex, rnd[14:8]};
            end
            Ln = 0; Pn = 0; Lcyc = 0; Pcyc = 0;
            rst_n = 0; start = 0;
            repeat (3) @(negedge clk);
            rst_n = 1;
            cfg_rows = M; cfg_cols = N; cfg_depth = K;
            cfg_a_base = 0; cfg_b_base = 32'd4096; cfg_out_base = 32'd0;
            @(negedge clk);
            start = 1; @(negedge clk); start = 0;
            //: wait for BOTH to retire
            i = 0;
            while (!((Ln >= M*N) && (Pn >= M*N)) && i < 4000000) begin
                @(negedge clk); i = i + 1;
            end
            repeat (20) @(negedge clk);

            cases = cases + 1;
            if (Ln != Pn) begin
                bad = bad + 1;
                $display("FAIL M=%0d N=%0d K=%0d: legacy wrote %0d, pipelined wrote %0d",
                         M, N, K, Ln, Pn);
            end else begin
                for (j = 0; j < Ln; j = j + 1)
                    if (La[j] !== Pa[j] || Ld[j] !== Pd[j]) begin
                        bad = bad + 1;
                        if (bad < 8)
                            $display("FAIL M=%0d N=%0d K=%0d write %0d: legacy %h@%h  pipelined %h@%h",
                                     M, N, K, j, Ld[j], La[j], Pd[j], Pa[j]);
                        j = Ln;
                    end
            end
            if (L_err !== P_err) begin
                bad = bad + 1;
                $display("FAIL M=%0d N=%0d K=%0d: error_code legacy %0d pipelined %0d",
                         M, N, K, L_err, P_err);
            end
            $display("  M=%0d N=%0d K=%0d : %0d writes, legacy %0d cycles, pipelined %0d cycles (%0.2fx)",
                     M, N, K, Ln, Lcyc, Pcyc, (Pcyc > 0) ? (1.0*Lcyc/Pcyc) : 0.0);
        end
    endtask

    initial begin
        $display("legacy ot_a3_mac_lane vs pipelined ot_a3_mac_lane_pipe, same memories");
        run_case(1, 8, 16);
        run_case(1, 16, 32);
        run_case(1, 12, 7);      // cols not a multiple of the interleave
        run_case(2, 8, 8);
        run_case(3, 5, 9);       // both awkward
        run_case(1, 64, 64);
        run_case(4, 16, 16);
        if (bad == 0)
            $display("PASS mac_lane_pipe: %0d descriptors, write streams and error codes identical to ot_a3_mac_lane", cases);
        else
            $display("FAIL mac_lane_pipe: %0d mismatches over %0d descriptors", bad, cases);
        $finish;
    end
endmodule

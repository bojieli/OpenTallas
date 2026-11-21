`timescale 1ns/1ps
// DIE-S81-85 form A (3) (11-09): a small behavioral array as generated 1R1W SRAM macros, cycle-exact.
//   SYNC = 0: equal to a COMBINATIONAL read of a flop array, rd = mem[ra_q], where ra_q is the read pointer register and
//             ra_n its D input (the address of the NEXT cycle).  The macro reads ra_n at every edge; a write at the same
//             edge to ra_n is bypassed (the macro model is read-first), so rd also shows a write of the cycle before.
//             Zero added cycles.  Needs >= 1 clock edge with the pointer in reset (S81 holds rst_n >= 64 clk).
//   SYNC = 1: equal to `q <= mem[ra]` (read-first, old data on a same-edge write): rd = macro rd_out, ra = this edge.
//   Out-of-range (>= DEPTH) writes are dropped and reads return 0, as the flop array in Verilator.
//   MACRO 0: ot_sram_1r1w_32x128_m1_r0c0 (DEPTH <= 32), 1: ot_sram_1r1w_160x256_m1_r0c0 (DEPTH <= 160); W split into
//   ceil(W / macro width) macros side by side, full-word writes.
//   MUT (bench negative controls): 1 = no write bypass, 2 = macro read at the current pointer (one cycle late).
module dsdv_svc_mem_ar #(
    parameter integer W = 512,
    parameter integer DEPTH = 32,
    parameter integer AW = 5,
    parameter integer MACRO = 0,
    parameter integer SYNC = 0,
    parameter integer MUT = 0,
    // A writer can address fewer rows while preserving invalid-read encoding.
    parameter integer WAW = AW
)(
    input  wire          clk,
    input  wire [AW-1:0] ra_n,
    input  wire          we,
    input  wire [WAW-1:0] wa,
    input  wire [W-1:0]  wd,
    output wire [W-1:0]  rd
);
    localparam integer MW = (MACRO == 1) ? 256 : 128;
    localparam integer MAW = (MACRO == 1) ? 8 : 5;
    localparam integer MD = (MACRO == 1) ? 160 : 32;
    localparam integer N = (W + MW - 1) / MW;
    reg [AW-1:0] ra_q;
    reg byp_v;
    reg [W-1:0] byp_d;
    wire w_ok = we && (32'(wa) < DEPTH);
    wire [AW-1:0] ra_m = (MUT == 2) ? ra_q : ra_n;
    wire [N*MW-1:0] wdp = (N*MW)'(wd);
    wire [N*MW-1:0] rdp;
    genvar g;
    generate
        if (DEPTH > MD || AW > MAW || WAW < 1 || WAW > MAW) begin : g_bad
            $error("dsdv_svc_mem_ar: invalid depth or address width for the macro");
        end
        for (g = 0; g < N; g = g + 1) begin : g_m
            if (MACRO == 1) begin : g_160
                ot_sram_1r1w_160x256_m1_r0c0 u_mem (
                    .clk(clk), .r_ce_in(1'b1), .r_addr_in(MAW'(ra_m)), .rd_out(rdp[g*MW +: MW]),
                    .w_ce_in(w_ok), .w_addr_in(MAW'(wa)), .wd_in(wdp[g*MW +: MW]), .w_mask_in({MW{1'b1}}));
            end else begin : g_32
                ot_sram_1r1w_32x128_m1_r0c0 u_mem (
                    .clk(clk), .r_ce_in(1'b1), .r_addr_in(MAW'(ra_m)), .rd_out(rdp[g*MW +: MW]),
                    .w_ce_in(w_ok), .w_addr_in(MAW'(wa)), .wd_in(wdp[g*MW +: MW]), .w_mask_in({MW{1'b1}}));
            end
        end
        if (SYNC != 0) begin : g_sync
            always @(posedge clk) ra_q <= ra_n;
            assign rd = (32'(ra_q) >= DEPTH) ? {W{1'b0}} : rdp[W-1:0];
        end else begin : g_ar
            always @(posedge clk) begin
                ra_q <= ra_n;
                byp_v <= (MUT != 1) && w_ok && wa == ra_n;
                byp_d <= wd;
            end
            assign rd = (32'(ra_q) >= DEPTH) ? {W{1'b0}} : byp_v ? byp_d : rdp[W-1:0];
        end
    endgenerate
`ifdef OT_SVC_MEM_COV
    // bench coverage (sim only): writes, pointer moves, reads that return a written entry
    integer cov_w = 0, cov_mv = 0, cov_rd = 0, cov_byp = 0;
    always @(posedge clk) begin
        if (w_ok) cov_w <= cov_w + 1;
        if (ra_n != ra_q) cov_mv <= cov_mv + 1;
        if (cov_w > 0 && rd != 0) cov_rd <= cov_rd + 1;
        if (byp_v) cov_byp <= cov_byp + 1;
    end
    final $display("MEM_COV %m writes=%0d ptr_moves=%0d nonzero_reads=%0d bypass=%0d", cov_w, cov_mv, cov_rd, cov_byp);
`endif
endmodule

// Move write-head selection behind the existing request register edge.
module dsdv_svc_wq_capture (
    input wire clk,
    input wire [340:0] head_0, head_1, head_2,
    input wire valid,
    input wire [2:0] source,
    input wire [340:0] read_req,
    output reg [340:0] request
);
    reg [340:0] head_0_q, head_1_q, head_2_q, read_req_q;
    reg [2:0] source_q;
    reg valid_q;
    always @(posedge clk) begin
        head_0_q <= head_0;
        head_1_q <= head_1;
        head_2_q <= head_2;
        read_req_q <= read_req;
        source_q <= source;
        valid_q <= valid;
    end
    always_comb begin
        request = '0;
        if (valid_q) begin
            case (source_q)
                3'd0: request = head_0_q;
                3'd1: request = head_1_q;
                3'd2: request = head_2_q;
                default: request = read_req_q;
            endcase
        end
    end
endmodule

// Read-first S81 landing store. Each writer has private SRAMs; a narrow
// live-value table selects the most recent writer. Replicate read columns
// so ROWX can retrieve two distinct addresses in the same bank on one edge.
module dsdv_svc_land_mem #(
    parameter bit ROWX = 1,
    parameter bit MUT = 0
)(
    input  wire                clk,
    input  wire [2:0]          we,
    input  wire [29:0]         wa,
    input  wire [767:0]        wd,
    input  wire [47:0]         ra,
    output wire [1023:0]       rd
);
    localparam integer ROWS_PER_BANK = 160;
    localparam integer WORDS = 4 * ROWS_PER_BANK;

    wire [255:0] bank_rd [0:3][0:3];
    for (genvar b = 0; b < 4; b = b + 1) begin : g_bank
        reg [1:0] writer [0:ROWS_PER_BANK-1];
        wire [2:0] bank_we;
        for (genvar w = 0; w < 3; w = w + 1) begin : g_wsel
            assign bank_we[w] = we[w] && 32'(wa[10*w +: 10]) < WORDS && wa[10*w +: 2] == 2'(b);
        end
        always @(posedge clk) begin
            // Match nonblocking write order in the flop reference: ROWS,
            // then PC1, then PC0 in descending priority on the same row.
            for (integer i = 0; i < 3; i = i + 1) begin
                integer w;
                w = MUT ? (2 - i) : i;
                if (bank_we[w])
                    writer[wa[10*w + 2 +: 8]] <= 2'(w);
            end
        end
        for (genvar r = 0; r < 4; r = r + 1) begin : g_read
            if ((ROWX && r < 2) || r == b) begin : g_replica
                wire bank_re = 32'(ra[12*r +: 12]) < WORDS && ra[12*r +: 2] == 2'(b);
                wire [7:0] ra_row = ra[12*r + 2 +: 8];
                reg [1:0] rd_writer;
                reg rd_valid;
                wire [255:0] src_rd [0:2];
                always @(posedge clk) begin
                    rd_valid <= bank_re;
                    if (bank_re)
                        rd_writer <= writer[ra_row];
                end
                for (genvar w = 0; w < 3; w = w + 1) begin : g_writer
                    ot_sram_1r1w_160x256_m1_r0c0 u_mem (
                        .clk(clk), .r_ce_in(bank_re), .r_addr_in(ra_row), .rd_out(src_rd[w]),
                        .w_ce_in(bank_we[w]), .w_addr_in(wa[10*w + 2 +: 8]), .wd_in(wd[256*w +: 256]),
                        .w_mask_in({256{1'b1}}));
                end
                assign bank_rd[r][b] = rd_valid ? src_rd[rd_writer] : 256'd0;
            end else begin : g_absent
                assign bank_rd[r][b] = 256'd0;
            end
        end
    end
    // Each selected bank drives one captured word. The remaining banks
    // supply zero; no extra capture or hold edge is introduced.
    for (genvar r = 0; r < 4; r = r + 1) begin : g_res
        assign rd[256*r +: 256] = bank_rd[r][0] | bank_rd[r][1] | bank_rd[r][2] | bank_rd[r][3];
    end
endmodule

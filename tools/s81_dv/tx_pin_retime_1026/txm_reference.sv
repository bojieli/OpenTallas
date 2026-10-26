module dsdv_idx_txm__reference #(
    parameter integer D = 8192,
    parameter bit SRAM_MACRO = 0
) (
    input  wire                 ck,
    input  wire                 re,
    input  wire [$clog2(D)-1:0] ra,
    output reg  [255:0]         rd,
    input  wire                 we,
    input  wire [$clog2(D)-1:0] wa,
    input  wire [255:0]         wd,
    input  wire [255:0]         wm
);
    localparam integer AW = $clog2(D);
    generate if (SRAM_MACRO) begin : g_m
        localparam integer NB = D / 1024;
        initial if (D % 1024 != 0 || D < 1024) $fatal(1, "dsdv_idx_txm: D must be a multiple of 1024");
        wire [255:0] q [0:NB-1];
        reg  [(AW > 10 ? AW-11 : 0):0] bs;
        genvar b;
        for (b = 0; b < NB; b = b + 1) begin : g_b
            ot_sram_1r1w_1024x256_m2_r2c2 u_mem (
                .clk(ck), .r_ce_in(re && (NB == 1 || ra[AW-1:10] == b)), .r_addr_in(ra[9:0]), .rd_out(q[b]), // selrange-ok: ra[AW-1:10] is unnecessary at NB=1/D=1024 because constant true NB==1 masks the comparison; RTL-SELRANGE triage ~/coord/lanes/RTL-SELRANGE.md section3
                .w_ce_in(we && (NB == 1 || wa[AW-1:10] == b)), .w_addr_in(wa[9:0]), .wd_in(wd), .w_mask_in(wm), // selrange-ok: wa[AW-1:10] is unnecessary at NB=1/D=1024 because constant true NB==1 masks the comparison; RTL-SELRANGE triage ~/coord/lanes/RTL-SELRANGE.md section3
                .rr_en(2'b0), .rr_addr(18'b0), .cr_en(2'b0), .cr_sel(16'b0));
        end
        // bank select: one-hot AND-OR (no runtime-indexed part-select)
        reg [255:0] mx;
        integer k;
        always @* begin
            mx = 256'd0;
            for (k = 0; k < NB; k = k + 1) if (bs == k) mx = mx | q[k];
        end
        always @(posedge ck) begin
            if (re) bs <= (NB == 1) ? '0 : ra[AW-1:10]; // selrange-ok: ra[AW-1:10] dead at NB=1/D=1024 because constant ternary chooses zero; RTL-SELRANGE triage ~/coord/lanes/RTL-SELRANGE.md section3
            rd <= mx;
        end
    end else begin : g_b
        reg [255:0] mem [0:D-1];
        reg [255:0] q;
        always @(posedge ck) begin
            if (we) mem[wa] <= (mem[wa] & ~wm) | (wd & wm);
            if (re) q <= mem[ra];
            rd <= q;
        end
    end endgenerate
endmodule

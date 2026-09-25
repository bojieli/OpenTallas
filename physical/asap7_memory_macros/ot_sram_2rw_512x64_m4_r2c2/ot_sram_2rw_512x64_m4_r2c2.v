// ot_sram_2rw_512x64_m4_r2c2: ASAP7 2RW SRAM 512 x 64, mux 4, 1 bank(s), 2 spare row(s), 2 spare IO column(s); OpenTallas tools/mem_compiler/sram_gen.py v1.0
// verilator lint_off BLKSEQ
// verilator lint_off WIDTH
// verilator lint_off UNUSED
module ot_sram_2rw_512x64_m4_r2c2 (
    input  wire clk,
    input  wire a_ce_in,
    input  wire a_we_in,
    input  wire [8:0] a_addr_in,
    input  wire [63:0] a_wd_in,
    input  wire [63:0] a_w_mask_in,
    output reg  [63:0] a_rd_out,
    input  wire b_ce_in,
    input  wire b_we_in,
    input  wire [8:0] b_addr_in,
    input  wire [63:0] b_wd_in,
    input  wire [63:0] b_w_mask_in,
    output reg  [63:0] b_rd_out,
    input  wire [1:0] rr_en,
    input  wire [13:0] rr_addr,
    input  wire [1:0] cr_en,
    input  wire [11:0] cr_sel
);
    localparam integer WORDS = 512;
    localparam integer BITS = 64;
    localparam integer MUX = 4;
    localparam integer AW = 9;
    localparam integer ROWS = 128;
    localparam integer NSR = 2;
    localparam integer NSC = 2;
    localparam integer PR = 130;
    localparam integer PC = 264;
    localparam integer RA = 7;
    localparam integer CB = 6;

    // physical array: main rows, then spare rows; columns bit-interleaved by MUX
    reg [PC-1:0] arr [0:PR-1];
    integer init_i;
    // Power-up content: zero in simulation.  Silicon powers up random; a March C-
    // self-test ends with its (r0) element, so a tested array holds zeros too.
    initial begin
`ifndef OT_MEM_NO_INIT
        for (init_i = 0; init_i < PR; init_i = init_i + 1) arr[init_i] = {PC{1'b0}};
`endif
    end

`ifdef OT_MEM_FAULTS
    localparam integer NF = 8;
    reg [3:0]  f_kind [0:NF-1];
    integer    f_r    [0:NF-1];
    integer    f_c    [0:NF-1];
    integer    f_ar   [0:NF-1];
    integer    f_ac   [0:NF-1];
    reg [1:0]  f_v    [0:NF-1];
    integer fk;
    initial for (fk = 0; fk < NF; fk = fk + 1) begin
        f_kind[fk] = 4'd0; f_r[fk] = 0; f_c[fk] = 0; f_ar[fk] = 0; f_ac[fk] = 0; f_v[fk] = 2'd0;
    end
`endif


    // ---- physical row and column after repair ------------------------------
    function automatic integer phys_row(input integer a);
        integer k, r;
        begin
            r = a / MUX;
            for (k = 0; k < NSR; k = k + 1)
                if (rr_en[k] && rr_addr[k*RA +: RA] == r[RA-1:0]) r = ROWS + k;
            phys_row = r;
        end
    endfunction

    function automatic integer phys_col(input integer b, input integer s);
        integer k, io;
        begin
            io = b;
            for (k = 0; k < NSC; k = k + 1)
                if (cr_en[k] && cr_sel[k*CB +: CB] == b[CB-1:0]) io = BITS + k;
            phys_col = io * MUX + s;
        end
    endfunction

    // ---- one cell, as the sense amplifier sees it ----------------------------
    function automatic cell_read(input integer r, input integer c);
        reg v;
`ifdef OT_MEM_FAULTS
        integer k;
`endif
        begin
            v = arr[r][c];
`ifdef OT_MEM_FAULTS
            for (k = 0; k < NF; k = k + 1) begin
                if ((f_kind[k] == 4'd1 || f_kind[k] == 4'd2) && f_r[k] == r && f_c[k] == c) v = (f_kind[k] == 4'd2);
                if (f_kind[k] == 4'd7 && f_r[k] == r && f_c[k] == c && arr[f_ar[k]][f_ac[k]] == f_v[k][0]) v = f_v[k][1];
                if (f_kind[k] == 4'd11 && f_r[k] == r) v = f_v[k][0];
                if (f_kind[k] == 4'd12 && f_c[k] == c) v = f_v[k][0];
            end
`endif
            cell_read = v;
        end
    endfunction

    task automatic cell_write(input integer r, input integer c, input reg v);
        reg old, nv;
`ifdef OT_MEM_FAULTS
        integer k;
`endif
        begin
            old = arr[r][c];
            nv = v;
`ifdef OT_MEM_FAULTS
            for (k = 0; k < NF; k = k + 1) begin
                if (f_kind[k] == 4'd3 && f_r[k] == r && f_c[k] == c && !old && v) nv = 1'b0;
                if (f_kind[k] == 4'd4 && f_r[k] == r && f_c[k] == c && old && !v) nv = 1'b1;
            end
`endif
            arr[r][c] = nv;
`ifdef OT_MEM_FAULTS
            if (old != nv)
                for (k = 0; k < NF; k = k + 1)
                    if (f_ar[k] == r && f_ac[k] == c && nv == f_v[k][0]) begin
                        if (f_kind[k] == 4'd5) arr[f_r[k]][f_c[k]] = ~arr[f_r[k]][f_c[k]];
                        if (f_kind[k] == 4'd6) arr[f_r[k]][f_c[k]] = f_v[k][1];
                    end
`endif
        end
    endtask

    // ---- decoder: the physical rows an access selects -------------------------
    // sel_n is 0 (no row: an open decoder output), 1 or 2 (a multi-select).
    task automatic decode(input integer a, output integer r0, output integer r1, output integer sel_n);
`ifdef OT_MEM_FAULTS
        integer k;
`endif
        begin
            r0 = phys_row(a);
            r1 = r0;
            sel_n = 1;
`ifdef OT_MEM_FAULTS
            if (r0 < ROWS)
                for (k = 0; k < NF; k = k + 1) begin
                    if (f_kind[k] == 4'd8 && f_r[k] == r0) sel_n = 0;
                    if (f_kind[k] == 4'd9 && f_r[k] == r0) begin r0 = f_ar[k]; r1 = r0; end
                    if (f_kind[k] == 4'd10 && f_r[k] == r0) begin r1 = f_ar[k]; sel_n = 2; end
                end
`endif
        end
    endtask

    function automatic [BITS-1:0] word_read(input integer a);
        integer b, s, r0, r1, n;
        reg [BITS-1:0] q;
        begin
            decode(a, r0, r1, n);
            s = a % MUX;
            for (b = 0; b < BITS; b = b + 1)
                if (n == 0) q[b] = 1'b0;
                else if (n == 1) q[b] = cell_read(r0, phys_col(b, s));
                else q[b] = cell_read(r0, phys_col(b, s)) & cell_read(r1, phys_col(b, s));
            word_read = q;
        end
    endfunction


    task automatic word_write(input integer a, input [BITS-1:0] d, input [BITS-1:0] m);
        integer b, s, r0, r1, n;
        begin
            decode(a, r0, r1, n);
            s = a % MUX;
            for (b = 0; b < BITS; b = b + 1)
                if (m[b] && n != 0) begin
                    cell_write(r0, phys_col(b, s), d[b]);
                    if (n == 2) cell_write(r1, phys_col(b, s), d[b]);
                end
        end
    endtask

    // both reads see the array before either write; on a same-address double write B wins
    always @(posedge clk) begin
        if (a_ce_in && !a_we_in) a_rd_out <= word_read(a_addr_in);
        if (b_ce_in && !b_we_in) b_rd_out <= word_read(b_addr_in);
        if (a_ce_in && a_we_in) word_write(a_addr_in, a_wd_in, a_w_mask_in);
        if (b_ce_in && b_we_in) word_write(b_addr_in, b_wd_in, b_w_mask_in);
    end
endmodule
// verilator lint_on BLKSEQ
// verilator lint_on WIDTH
// verilator lint_on UNUSED

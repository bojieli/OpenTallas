`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Shared memory BIST controller: one programmable March engine and one BIRA
// for N_SRAM SRAM macros, and a signature sweep for N_ROM ROM macros.
//
// Sequence on `start`:
//   for each SRAM m (one at a time, t_sel[m] held for the whole sequence):
//     clear its repair register and the BIRA; run the March program (pass 1)
//     recording every failing read in the BIRA; if nothing failed -> PASS.
//     Otherwise analyse; if repairable, load the allocation into the collar's
//     repair register (rep_load[m]) and run the March program again (pass 2,
//     verification); clean -> REPAIRED, else UNREPAIRABLE.  An unrepairable
//     analysis skips the verification and clears the repair register.
//   for each ROM r: clear its signature, read every address once
//     (ROM_WORDS[r] cycles), compare with the collar's expected signature.
//   done, pass = every SRAM PASS or REPAIRED and every ROM matching.
//
// March program register (cfg_addr 0..7, one 16-bit word per element):
//   [15] enable  [14] descending  [13:12] operations - 1
//   [5:4] op0  [7:6] op1  [9:8] op2  [11:10] op3,  op = 0 r0, 1 r1, 2 w0, 3 w1
//   (the data value is relative to the data background)
// cfg_addr 8: [3:0] background enables {column stripe, row stripe,
//   checkerboard, solid}; the program runs once per enabled background.
// Reset default: March C- = {(w0); up(r0,w1); up(r1,w0); down(r0,w1);
//   down(r1,w0); (r0)}, solid background only: 10N operations per macro.
//
// Status: sram_status[2m+1:2m] and rom_status[2r+1:2r]:
//   00 not run, 01 pass, 10 repaired (SRAM only), 11 fail / unrepairable.
//
// Stall: `hold` (and the BIRA while it analyses) freezes operation issue.
//
// Integration example (two SRAM collars and one ROM collar):
//
//   ot_mbist_ctrl #(.N_SRAM(2), .N_ROM(1), .AMAX(10), .DMAX(128), .RMAX(8), .CMAX(7),
//                   .NSR(2), .NSC(2), .E(6),
//                   .SRAM_WORDS({32'd512, 32'd256}), .ROM_WORDS(32'd1024)) u_ctrl (
//       .clk(clk), .rst_n(rst_n), .start(bist_start), .hold(1'b0),
//       .busy(bist_busy), .done(bist_done), .pass(bist_pass),
//       .cfg_we(1'b0), .cfg_addr(4'd0), .cfg_wdata(16'd0), .cfg_rdata(),
//       .sram_status(sram_st), .rom_status(rom_st),
//       .t_sel(t_sel), .t_req(t_req), .t_we(t_we), .t_addr(t_addr), .t_pol(t_pol), .t_bg(t_bg),
//       .c_fail({c1_fail, c0_fail}), .c_failvec({c1_vec, c0_vec}), .c_row({c1_row, c0_row}),
//       .rep_clear(rep_clear), .rep_load(rep_load), .rep_rr_en(rr_en), .rep_rr_addr(rr_addr),
//       .rep_cr_en(cr_en), .rep_cr_sel(cr_sel),
//       .rom_sel(rom_sel), .rom_clear(rom_clear), .rom_req(rom_req), .rom_addr(rom_addr),
//       .rom_match(rom_match));
//   ot_mbist_sram_collar #(.PORTS(0), .WORDS(256), .DW(64), .MUX(4), .NSR(2), .NSC(2),
//       .AMAX(10), .DMAX(128), .RMAX(8), .CMAX(7), .NSRB(2), .NSCB(2)) u_c0 (
//       ... .t_en(t_sel[0]), .t_req(t_req), .t_we(t_we), .t_addr(t_addr), .t_pol(t_pol),
//       .t_bg(t_bg), .c_fail(c0_fail), .c_failvec(c0_vec), .c_row(c0_row),
//       .rep_clear(rep_clear[0]), .rep_load(rep_load[0]), .rep_rr_en(rr_en), ...);
//   ot_mbist_rom_collar #(.WORDS(1024), .DW(72), .AMAX(10)) u_r0 (
//       ... .t_en(rom_sel[0]), .t_clear(rom_clear), .t_req(rom_req), .t_addr(rom_addr),
//       .exp_sig(expected_signature), .sig(), .sig_match(rom_match[0]), .sig_busy());
//
// The functional path through every collar is combinational pass-through while
// its t_sel / rom_sel is low (see rtl/test/tb_mbist.sv for a complete top).
// ---------------------------------------------------------------------------
// Lint waiver: the macro select `msel` indexes packed per-macro vectors whose width
// is a parameter; the dynamic index is range-checked by the sequence (msel < N).
// verilator lint_off WIDTH
module ot_mbist_ctrl #(
    parameter integer N_SRAM = 2,
    parameter integer N_ROM  = 1,
    parameter integer AMAX   = 16,
    parameter integer DMAX   = 128,
    parameter integer RMAX   = 16,
    parameter integer CMAX   = 8,
    parameter integer NSR    = 2,
    parameter integer NSC    = 2,
    parameter integer E      = 6,
    parameter [((N_SRAM > 0) ? N_SRAM : 1)*32-1:0] SRAM_WORDS = {32'd512, 32'd256},
    parameter [((N_ROM > 0) ? N_ROM : 1)*32-1:0]   ROM_WORDS  = 32'd1024,
    parameter integer NS1    = (N_SRAM > 0) ? N_SRAM : 1,
    parameter integer NR1    = (N_ROM > 0) ? N_ROM : 1,
    parameter integer NSR1   = (NSR > 0) ? NSR : 1,
    parameter integer NSC1   = (NSC > 0) ? NSC : 1
) (
    input  wire                  clk,
    input  wire                  rst_n,
    input  wire                  start,
    input  wire                  hold,
    output reg                   busy,
    output reg                   done,
    output reg                   pass,
    // configuration
    input  wire                  cfg_we,
    input  wire [3:0]            cfg_addr,
    input  wire [15:0]           cfg_wdata,
    output reg  [15:0]           cfg_rdata,
    // status
    output reg  [NS1*2-1:0]      sram_status,
    output reg  [NR1*2-1:0]      rom_status,
    // SRAM test bus (broadcast) and responses
    output reg  [NS1-1:0]        t_sel,
    output reg                   t_req,
    output reg                   t_we,
    output reg  [AMAX-1:0]       t_addr,
    output reg                   t_pol,
    output reg  [1:0]            t_bg,
    input  wire [NS1-1:0]        c_fail,
    input  wire [NS1*DMAX-1:0]   c_failvec,
    input  wire [NS1*RMAX-1:0]   c_row,
    // repair broadcast
    output reg  [NS1-1:0]        rep_clear,
    output reg  [NS1-1:0]        rep_load,
    output wire [NSR1-1:0]       rep_rr_en,
    output wire [NSR1*RMAX-1:0]  rep_rr_addr,
    output wire [NSC1-1:0]       rep_cr_en,
    output wire [NSC1*CMAX-1:0]  rep_cr_sel,
    // ROM test bus
    output reg  [NR1-1:0]        rom_sel,
    output reg                   rom_clear,
    output reg                   rom_req,
    output reg  [AMAX-1:0]       rom_addr,
    input  wire [NR1-1:0]        rom_match,
    // BIRA observation (current / last analysed SRAM)
    output wire [7:0]            dbg_bira_events,
    output wire [7:0]            dbg_bira_must_cols,
    output wire                  dbg_bira_overflow
);
    localparam [3:0] S_IDLE = 4'd0, S_MSTART = 4'd1, S_MINIT = 4'd2, S_MARCH = 4'd3, S_DRAIN = 4'd4,
                     S_EVAL = 4'd5, S_ANA = 4'd6, S_LOAD = 4'd7, S_RSTART = 4'd8, S_RSWEEP = 4'd9,
                     S_RDRAIN = 4'd10, S_REVAL = 4'd11, S_DONE = 4'd12;

    // ---- program ------------------------------------------------------------
    reg [15:0] alg [0:7];
    reg [3:0]  bgmask;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            alg[0] <= 16'h8020;   // (w0)
            alg[1] <= 16'h90C0;   // up(r0,w1)
            alg[2] <= 16'h9090;   // up(r1,w0)
            alg[3] <= 16'hD0C0;   // down(r0,w1)
            alg[4] <= 16'hD090;   // down(r1,w0)
            alg[5] <= 16'h8000;   // (r0)
            alg[6] <= 16'h0000;
            alg[7] <= 16'h0000;
            bgmask <= 4'b0001;
        end else if (cfg_we && !busy) begin
            if (cfg_addr[3]) bgmask <= cfg_wdata[3:0];
            else alg[cfg_addr[2:0]] <= cfg_wdata;
        end
    end
    always @* cfg_rdata = cfg_addr[3] ? {12'd0, bgmask} : alg[cfg_addr[2:0]];

    // ---- BIRA -----------------------------------------------------------------
    reg              bira_clear, bira_rec, bira_analyze;
    reg  [15:0]      msel;                 // current macro index
    wire             bira_busy, bira_done, bira_ok, bira_unrep;
    wire [7:0]       bira_nmust, bira_nev;
    wire [DMAX-1:0]  ev_vec = c_failvec[msel*DMAX +: DMAX];
    wire [RMAX-1:0]  ev_row = c_row[msel*RMAX +: RMAX];
    wire             ev_fail = c_fail[msel];
    ot_mbist_bira #(.R(NSR), .C(NSC), .E(E), .RMAX(RMAX), .DMAX(DMAX), .CMAX(CMAX)) u_bira (
        .clk(clk), .rst_n(rst_n), .clear(bira_clear), .rec_en(bira_rec), .ev_valid(ev_fail),
        .ev_row(ev_row), .ev_vec(ev_vec), .analyze(bira_analyze), .busy(bira_busy), .done(bira_done),
        .repairable(bira_ok), .unrep(bira_unrep), .rr_en(rep_rr_en), .rr_addr(rep_rr_addr),
        .cr_en(rep_cr_en), .cr_sel(rep_cr_sel), .n_must_cols(bira_nmust), .n_events(bira_nev));

    // ---- March engine ---------------------------------------------------------
    reg [3:0]      st;
    reg [1:0]      bg;
    reg [2:0]      el;
    reg [1:0]      opi;
    reg [AMAX-1:0] addr;
    reg [1:0]      mpass;                  // 1: test, 2: verify after repair
    reg            fail_seen;
    reg [2:0]      drain;
    reg [AMAX-1:0] last;                   // words - 1 of the current macro

    function automatic [AMAX-1:0] sram_last(input [15:0] m);
        sram_last = SRAM_WORDS[m*32 +: AMAX] - 1'b1;
    endfunction
    function automatic [AMAX-1:0] rom_last(input [15:0] m);
        rom_last = ROM_WORDS[m*32 +: AMAX] - 1'b1;
    endfunction

    assign dbg_bira_events = bira_nev;
    assign dbg_bira_must_cols = bira_nmust;
    assign dbg_bira_overflow = bira_unrep;
    /* verilator lint_off UNUSED */
    wire [15:0] cur    = alg[el];            // [15] and [3:0] are not used by the engine
    /* verilator lint_on UNUSED */
    wire        down   = cur[14];
    wire [1:0]  nops_m = cur[13:12];
    wire [1:0]  op     = (opi == 2'd0) ? cur[5:4] : (opi == 2'd1) ? cur[7:6] :
                         (opi == 2'd2) ? cur[9:8] : cur[11:10];

    // next enabled element after `e` (8 = none), first enabled background from `b` (4 = none)
    function automatic [3:0] next_el(input [3:0] e, input [7:0] en);
        integer i;
        begin
            next_el = 4'd8;
            for (i = 7; i >= 0; i = i - 1)
                if (i >= e && en[i]) next_el = i[3:0];
        end
    endfunction
    function automatic [2:0] next_bg(input [2:0] b, input [3:0] en);
        integer i;
        begin
            next_bg = 3'd4;
            for (i = 3; i >= 0; i = i - 1)
                if (i >= b && en[i]) next_bg = i[2:0];
        end
    endfunction

    wire [7:0] el_en = {alg[7][15], alg[6][15], alg[5][15], alg[4][15],
                        alg[3][15], alg[2][15], alg[1][15], alg[0][15]};
    wire [3:0] el_first = next_el(4'd0, el_en);
    wire [3:0] el_after = next_el({1'b0, el} + 4'd1, el_en);
    wire [2:0] bg_first = next_bg(3'd0, bgmask);
    wire [2:0] bg_after = next_bg({1'b0, bg} + 3'd1, bgmask);
    wire       at_end   = down ? (addr == {AMAX{1'b0}}) : (addr == last);
    wire       stall    = hold | bira_busy;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            st <= S_IDLE; busy <= 1'b0; done <= 1'b0; pass <= 1'b0;
            sram_status <= {(NS1*2){1'b0}}; rom_status <= {(NR1*2){1'b0}};
            t_sel <= {NS1{1'b0}}; t_req <= 1'b0; t_we <= 1'b0; t_addr <= {AMAX{1'b0}}; t_pol <= 1'b0;
            t_bg <= 2'd0; rep_clear <= {NS1{1'b0}}; rep_load <= {NS1{1'b0}};
            rom_sel <= {NR1{1'b0}}; rom_clear <= 1'b0; rom_req <= 1'b0; rom_addr <= {AMAX{1'b0}};
            bira_clear <= 1'b0; bira_rec <= 1'b0; bira_analyze <= 1'b0;
            msel <= 16'd0; bg <= 2'd0; el <= 3'd0; opi <= 2'd0; addr <= {AMAX{1'b0}}; mpass <= 2'd0;
            fail_seen <= 1'b0; drain <= 3'd0; last <= {AMAX{1'b0}};
        end else begin
            t_req <= 1'b0; rep_clear <= {NS1{1'b0}}; rep_load <= {NS1{1'b0}};
            bira_clear <= 1'b0; bira_analyze <= 1'b0; rom_clear <= 1'b0; rom_req <= 1'b0;
            if ((st == S_MARCH || st == S_DRAIN) && ev_fail) fail_seen <= 1'b1;
            case (st)
                S_IDLE: if (start) begin
                    busy <= 1'b1; done <= 1'b0; pass <= 1'b0; msel <= 16'd0;
                    sram_status <= {(NS1*2){1'b0}}; rom_status <= {(NR1*2){1'b0}};
                    st <= (N_SRAM > 0) ? S_MSTART : S_RSTART;
                end
                S_MSTART: begin                              // select macro, clear repair and BIRA
                    t_sel <= {NS1{1'b0}};
                    t_sel[msel] <= 1'b1;
                    rep_clear[msel] <= 1'b1;
                    bira_clear <= 1'b1;
                    last <= sram_last(msel);
                    mpass <= 2'd1;
                    st <= S_MINIT;
                end
                S_MINIT: begin                               // (re)start the March program
                    fail_seen <= 1'b0;
                    bira_rec <= (mpass == 2'd1);
                    opi <= 2'd0;
                    if (el_first == 4'd8 || bg_first == 3'd4) st <= S_DRAIN;
                    else begin
                        el <= el_first[2:0];
                        bg <= bg_first[1:0];
                        addr <= alg[el_first[2:0]][14] ? last : {AMAX{1'b0}};
                        st <= S_MARCH;
                    end
                    drain <= 3'd0;
                end
                S_MARCH: if (!stall) begin
                    t_req <= 1'b1; t_we <= op[1]; t_pol <= op[0]; t_addr <= addr; t_bg <= bg;
                    if (opi == nops_m) begin
                        opi <= 2'd0;
                        if (!at_end) addr <= down ? addr - 1'b1 : addr + 1'b1;
                        else if (el_after != 4'd8) begin
                            el <= el_after[2:0];
                            addr <= alg[el_after[2:0]][14] ? last : {AMAX{1'b0}};
                        end else if (bg_after != 3'd4) begin
                            bg <= bg_after[1:0];
                            el <= el_first[2:0];
                            addr <= alg[el_first[2:0]][14] ? last : {AMAX{1'b0}};
                        end else begin
                            st <= S_DRAIN;
                            drain <= 3'd0;
                        end
                    end else opi <= opi + 2'd1;
                end
                S_DRAIN: begin                               // collar compare pipeline is 2 deep
                    drain <= drain + 3'd1;
                    if (drain == 3'd3) begin
                        bira_rec <= 1'b0;
                        st <= S_EVAL;
                    end
                end
                S_EVAL: begin
                    if (!fail_seen) begin
                        sram_status[msel*2 +: 2] <= (mpass == 2'd1) ? 2'b01 : 2'b10;
                        st <= S_LOAD;                        // next macro
                        mpass <= 2'd0;
                    end else if (mpass == 2'd1) begin
                        bira_analyze <= 1'b1;
                        st <= S_ANA;
                    end else begin
                        sram_status[msel*2 +: 2] <= 2'b11;
                        rep_clear[msel] <= 1'b1;
                        st <= S_LOAD;
                        mpass <= 2'd0;
                    end
                end
                S_ANA: if (bira_done) begin
                    if (bira_ok) begin
                        rep_load[msel] <= 1'b1;
                        mpass <= 2'd2;
                        st <= S_MINIT;
                    end else begin
                        sram_status[msel*2 +: 2] <= 2'b11;
                        rep_clear[msel] <= 1'b1;
                        mpass <= 2'd0;
                        st <= S_LOAD;
                    end
                end
                S_LOAD: begin                                // advance to the next SRAM, then the ROMs
                    t_sel <= {NS1{1'b0}};
                    if (msel + 16'd1 < N_SRAM) begin
                        msel <= msel + 16'd1;
                        st <= S_MSTART;
                    end else begin
                        msel <= 16'd0;
                        st <= (N_ROM > 0) ? S_RSTART : S_DONE;
                    end
                end
                S_RSTART: begin
                    rom_sel <= {NR1{1'b0}};
                    rom_sel[msel] <= 1'b1;
                    rom_clear <= 1'b1;
                    last <= rom_last(msel);
                    addr <= {AMAX{1'b0}};
                    st <= S_RSWEEP;
                end
                S_RSWEEP: if (!hold) begin
                    rom_req <= 1'b1;
                    rom_addr <= addr;
                    if (addr == last) begin
                        st <= S_RDRAIN;
                        drain <= 3'd0;
                    end else addr <= addr + 1'b1;
                end
                S_RDRAIN: begin
                    drain <= drain + 3'd1;
                    if (drain == 3'd3) st <= S_REVAL;       // ROM collar: macro read + registered word + fold
                end
                S_REVAL: begin
                    rom_status[msel*2 +: 2] <= rom_match[msel] ? 2'b01 : 2'b11;
                    rom_sel <= {NR1{1'b0}};
                    if (msel + 16'd1 < N_ROM) begin
                        msel <= msel + 16'd1;
                        st <= S_RSTART;
                    end else st <= S_DONE;
                end
                S_DONE: begin
                    busy <= 1'b0;
                    done <= 1'b1;
                    pass <= all_good(sram_status, rom_status);
                    st <= S_IDLE;
                end
                default: st <= S_IDLE;
            endcase
        end
    end

    function automatic all_good(input [NS1*2-1:0] ss, input [NR1*2-1:0] rs);
        integer i;
        begin
            all_good = 1'b1;
            for (i = 0; i < N_SRAM; i = i + 1)
                if (ss[i*2 +: 2] != 2'b01 && ss[i*2 +: 2] != 2'b10) all_good = 1'b0;
            for (i = 0; i < N_ROM; i = i + 1)
                if (rs[i*2 +: 2] != 2'b01) all_good = 1'b0;
        end
    endfunction
endmodule
// verilator lint_on WIDTH

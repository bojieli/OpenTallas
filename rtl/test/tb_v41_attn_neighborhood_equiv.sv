`timescale 1ns/1ps
// Cycle equivalence of the group-column cut (ot_v41_attn_neighborhood =
// ot_v41_attn_stage_ctl + 16 ot_v41_attn_col_slice) against the adopted
// modules: ot_chip_v41x_window_stage4, the merge beat register update rules of
// ot_chip_v41x_attn_row_merge (clear, full 4-bank load, one-lane load from
// bank lane 0 or a CKV row), and ot_hdc_v41x_attn_staging (behavioural).
// Random fills (all 17 sectors, some aborted), invalidations, requests (prefix
// and non-prefix masks, hits, misses, hazards), beat and staging traffic.
// Every cycle compares response metadata, the 16,896-bit rotation register,
// the 16,960-bit beat and the 16,960-bit staging read data.
module tb_v41_attn_neighborhood_equiv;
    parameter integer SRAM_MACRO = 1;
    parameter integer CYCLES = 20000;
    parameter integer SEED = 1;
    localparam integer POS_W = 21, USER_W = 10;
    reg clk = 0, rst_n = 0;
    always #1 clk = ~clk;

    reg inv_v, fill_v, fill_last, req_v;
    reg [POS_W-1:0] inv_row, fill_row, req_first_row;
    reg [USER_W-1:0] fill_user, req_user;
    reg [4:0] fill_sector;
    reg [255:0] fill_data;
    reg [3:0] req_mask;
    reg beat_clr, beat_full, beat_ckv;
    reg [3:0] beat_lane, stg_we;
    reg [2303:0] ckv_row;
    reg [7:0] stg_waddr, stg_raddr;

    // ---------------- reference
    wire r_ready, r_v, r_fault;
    wire [USER_W-1:0] r_user;
    wire [POS_W-1:0] r_first;
    wire [3:0] r_mask, r_vmask;
    wire [4*4224-1:0] r_rows;
    ot_chip_v41x_window_stage4 #(.POS_W(POS_W), .USER_W(USER_W)) u_ref (
        .clk(clk), .rst_n(rst_n), .inv_v(inv_v), .inv_row(inv_row),
        .fill_v(fill_v), .fill_user(fill_user), .fill_row(fill_row),
        .fill_sector(fill_sector), .fill_data(fill_data), .fill_last(fill_last),
        .req_v(req_v), .req_ready(r_ready), .req_user(req_user),
        .req_first_row(req_first_row), .req_mask(req_mask),
        .rsp_v(r_v), .rsp_user(r_user), .rsp_first_row(r_first), .rsp_mask(r_mask),
        .rsp_valid_mask(r_vmask), .rsp_rows(r_rows), .rsp_fault(r_fault));
    wire [4*16*265-1:0] wb_fmt;
    wire [16*265-1:0] cfmt;
    genvar gg, ll;
    generate for (ll = 0; ll < 4; ll = ll + 1) begin : g_rl
        for (gg = 0; gg < 16; gg = gg + 1) begin : g_rg
            assign wb_fmt[(ll*16+gg)*265 +: 265] =
                {1'b0, r_rows[ll*4224+4096+8*gg +: 8], r_rows[ll*4224+256*gg +: 256]};
        end
    end
    for (gg = 0; gg < 16; gg = gg + 1) begin : g_cf
        assign cfmt[gg*265 +: 265] = {1'b1, 120'b0, ckv_row[2048+16*gg +: 16], ckv_row[128*gg +: 128]};
    end endgenerate
    reg [4*16*265-1:0] r_beat;
    integer li;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) r_beat <= 0;
        else if (beat_clr) r_beat <= 0;
        else if (beat_full) r_beat <= wb_fmt;
        else for (li = 0; li < 4; li = li + 1)
            if (beat_lane[li]) r_beat[li*16*265 +: 16*265] <= beat_ckv ? cfmt : wb_fmt[0 +: 16*265];
    wire [4*16*265-1:0] r_stg;
    ot_hdc_v41x_attn_staging #(.D(512), .NL(4), .TROWS(640), .SRAM_MACRO(0)) u_ref_stg (
        .clk(clk), .wr_en(stg_we), .wr_addr(stg_waddr), .wr_data(r_beat),
        .rd_addr(stg_raddr), .rd_data(r_stg));

    // ---------------- cut
    wire d_ready, d_v, d_fault;
    wire [USER_W-1:0] d_user;
    wire [POS_W-1:0] d_first;
    wire [3:0] d_mask, d_vmask;
    wire [4*16*265-1:0] d_stg;
    ot_v41_attn_neighborhood #(.SRAM_MACRO(SRAM_MACRO), .POS_W(POS_W), .USER_W(USER_W)) u_dut (
        .clk(clk), .rst_n(rst_n), .inv_v(inv_v), .inv_row(inv_row),
        .fill_v(fill_v), .fill_user(fill_user), .fill_row(fill_row),
        .fill_sector(fill_sector), .fill_data(fill_data), .fill_last(fill_last),
        .req_v(req_v), .req_ready(d_ready), .req_user(req_user),
        .req_first_row(req_first_row), .req_mask(req_mask),
        .rsp_v(d_v), .rsp_user(d_user), .rsp_first_row(d_first), .rsp_mask(d_mask),
        .rsp_valid_mask(d_vmask), .rsp_fault(d_fault),
        .beat_clr(beat_clr), .beat_full(beat_full), .beat_lane(beat_lane), .beat_ckv(beat_ckv),
        .ckv_row(ckv_row), .stg_we(stg_we), .stg_waddr(stg_waddr), .stg_raddr(stg_raddr),
        .stg_q(d_stg));
    // cut rotation and beat registers, gathered to reference layout
    wire [4*4224-1:0] d_rows;
    wire [4*16*265-1:0] d_beat;
    generate for (gg = 0; gg < 16; gg = gg + 1) begin : g_dg
        for (ll = 0; ll < 4; ll = ll + 1) begin : g_dl
            assign d_rows[ll*4224+256*gg +: 256] = u_dut.g_col[gg].u_col.rot[ll][255:0];
            assign d_rows[ll*4224+4096+8*gg +: 8] = u_dut.g_col[gg].u_col.rot[ll][263:256];
            assign d_beat[(ll*16+gg)*265 +: 265] = u_dut.g_col[gg].u_col.beat[ll];
        end
    end endgenerate

    // ---------------- stimulus
    integer cyc = 0, errors = 0, hits = 0, fills_done = 0, rsp_n = 0, stg_reads = 0;
    integer seed;
    reg [POS_W-1:0] frow; reg [USER_W-1:0] fuser; integer fsec; reg filling;
    function automatic [255:0] rnd256(input integer dummy);
        integer k; begin for (k = 0; k < 8; k = k + 1) rnd256[32*k +: 32] = $random(seed); end
    endfunction
    task automatic drive;
        integer k, r;
        begin
            // fill: a row is 17 consecutive sectors; sometimes aborted or gapped
            fill_v = 0; fill_last = 0;
            if (!filling && ($random(seed) & 3) == 0) begin
                filling = 1; fsec = 0;
                frow = 21'(($random(seed) & 255) + 1000);
                if (($random(seed) & 15) == 0) frow = 21'd1048575 - 21'($random(seed) & 3);
                fuser = 10'($random(seed) & 1);
            end
            if (filling && ($random(seed) & 7) != 0) begin
                fill_v = 1; fill_row = frow; fill_user = fuser; fill_sector = 5'(fsec);
                fill_data = rnd256(0);
                fill_last = (fsec == 16) && (($random(seed) & 15) != 0);
                fsec = fsec + 1;
                if (fsec == 17 || ($random(seed) & 63) == 0) begin filling = 0; fills_done = fills_done + 1; end
            end
            if (!fill_v) begin fill_row = 21'($random(seed)); fill_sector = 5'($random(seed)); fill_data = rnd256(0); fill_user = 10'($random(seed)); end
            inv_v = (($random(seed) & 31) == 0);
            inv_row = 21'(($random(seed) & 255) + 1000);
            req_v = ($random(seed) & 1);
            req_first_row = 21'(($random(seed) & 255) + 998);
            if (($random(seed) & 31) == 0) req_first_row = 21'd1048575 - 21'($random(seed) & 7);
            req_user = 10'($random(seed) & 1);
            r = $random(seed) & 7;
            req_mask = r < 4 ? 4'hf : r == 4 ? 4'h1 : r == 5 ? 4'h3 : r == 6 ? 4'h7 : 4'($random(seed));
            r = $random(seed) & 15;
            beat_clr = (r == 0); beat_full = (r >= 1 && r <= 5);
            beat_lane = (r >= 6 && r <= 11) ? (4'b1 << ($random(seed) & 3)) : 4'b0;
            beat_ckv = $random(seed) & 1;
            for (k = 0; k < 72; k = k + 1) ckv_row[32*k +: 32] = $random(seed);
            stg_we = ($random(seed) & 1) ? 4'($random(seed)) : 4'b0;
            stg_waddr = 8'(($random(seed) & 255) % 160);
            stg_raddr = 8'(($random(seed) & 255) % 160);
        end
    endtask
    initial begin
        seed = SEED; filling = 0;
        inv_v = 0; fill_v = 0; fill_last = 0; req_v = 0; inv_row = 0; fill_row = 0; req_first_row = 0;
        fill_user = 0; req_user = 0; fill_sector = 0; fill_data = 0; req_mask = 0;
        beat_clr = 0; beat_full = 0; beat_lane = 0; beat_ckv = 0; ckv_row = 0; stg_we = 0;
        stg_waddr = 0; stg_raddr = 0;
        repeat (3) @(posedge clk);
        #0.5 rst_n = 1;
        // staging memories start undefined in the reference: write every address first
        begin : init_stg
            integer a;
            for (a = 0; a < 160; a = a + 1) begin
                @(negedge clk); stg_we = 4'hf; stg_waddr = 8'(a); beat_clr = 0; beat_full = 0; beat_lane = 0;
            end
            @(negedge clk); stg_we = 0;
        end
        repeat (CYCLES) begin
            @(negedge clk); drive; cyc = cyc + 1;
        end
        @(negedge clk);
        $display("V41_ATTN_NEIGHBORHOOD_EQUIV %s sram_macro=%0d cycles=%0d rsp=%0d lane_hits=%0d fills=%0d stg_reads=%0d errors=%0d",
                 errors == 0 ? "PASS" : "FAIL", SRAM_MACRO, cyc, rsp_n, hits, fills_done, stg_reads, errors);
        if (errors != 0) $fatal(1, "EQUIVALENCE_TERMINAL_FAIL");
        $finish;
    end
    always @(posedge clk) if (rst_n) begin
        #0.1;
        if ({r_v, r_user, r_first, r_mask, r_vmask, r_fault} !== {d_v, d_user, d_first, d_mask, d_vmask, d_fault} ||
            r_ready !== d_ready) begin
            errors = errors + 1;
            if (errors < 5) $display("META MISMATCH cyc=%0d ref=%b %h %h %h %h %b cut=%b %h %h %h %h %b", cyc,
                r_v, r_user, r_first, r_mask, r_vmask, r_fault, d_v, d_user, d_first, d_mask, d_vmask, d_fault);
        end
        if (r_rows !== d_rows) begin errors = errors + 1; if (errors < 5) $display("ROWS MISMATCH cyc=%0d", cyc); end
        if (r_beat !== d_beat) begin errors = errors + 1; if (errors < 5) $display("BEAT MISMATCH cyc=%0d", cyc); end
        if (cyc > 1 && r_stg !== d_stg) begin errors = errors + 1; if (errors < 5) $display("STG MISMATCH cyc=%0d", cyc); end
        if (r_v) rsp_n = rsp_n + 1;
        hits = hits + r_vmask[0] + r_vmask[1] + r_vmask[2] + r_vmask[3];
        if (cyc > 1) stg_reads = stg_reads + 1;
    end
endmodule

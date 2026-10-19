`timescale 1ns/1ps
// =====================================================================================================================
// qfd_dv_cmd_cal -- the static slice-command calendar of the DV Qwen compute die (Q-CTLM, 2026-10-17).  Lives inside
// qfd_tt_ctlm_dv.  It replaces the issue side of qfd_seq_su_static: on the DV die the SU, VM, stations and collective
// commands are slice commands (rtl/qwen_dv/qfd_dv_slice2.sv cmd word, W5 cmd_wi), and this calendar plays them at
// compiler-assigned edges.  Static cycle schedule (owner 10-14 18:59): no ready, no credit, no readiness input at all;
// a late entry or an out-of-order image FAULTS, it never stretches a cycle.
//
// IMAGE (program-loaded over the existing program-write face, the second program copy = the old SU copy):
//   PW0..PW1023  the full dense program image, ascending, one word an edge (PW0 opens a load).  Every word is written
//                into this block's own copy (two ot_sram_1r1w_64x512_m1_r2c2, the ME program store's organisation:
//                row = a[9:4], macro = a[3], 64-b slice = a[2:0]); the consumed macro writes are observed by
//                qkd_program_pw_observer -> program_obs (sink 1 of qfd_program_record_port).
//   DW0..DW7     the calendar descriptor (after PW1023, in order; observed -> descriptor_obs):
//                  DW0 = {32'h43414c44 "CALD", 6'd0, base[25:16], 7'd0, nent[8:0]}
//                  DW1..DW4 = segment s = DW(1+s): {32'd0, first[31:16], count[15:0]}
//                         s0 = stage 0 (token start / embedding), s1 = stages 1..LAST_STAGE-1 (decode layer),
//                         s2 = stage LAST_STAGE (LM head), s3 = BOOT (played once when the image seals: SETID ...)
//                  DW5..DW7 = 0.  DW7 seals.
//   ENTRIES      entry e = PW words base + 2e (low) and base + 2e + 1 (high), 128 b = {delta 12 [127:116], cmd 116}.
//                Entry k of a segment issues at edge S + T_k, T_k = delta_0 + ... + delta_k (delta >= 1), S = the
//                edge that samples `start` (or the seal edge + 1 for BOOT).  The FIRST entry needs T_0 >= 4 (the
//                store read pipeline); a gap above 4095 edges is spanned with NOP entries (cmd[0] = 0).
//   Seal checks: magic, base % 8 == 0, base >= 16 x (ME program rows, PW1017 [27:18]), base + 2 nent <= 976 (the ME
//   control rows 976..1023 stay out), nent >= 1, every non-empty segment 4-aligned (first % 4 == 0) and inside nent,
//   DW5..7 zero, PW strictly ascending 0..1023 then DW 0..7.
// ENTRY KINDS (cmd = the slice command word; [0] go, [3:1] kind, [115:112] dst):
//   go = 0           NOP: nothing leaves (spacer)
//   dst = 4'hE       LOCAL (no slice answers dst 14; the word does not leave this block):
//                      kind 1 EMB  -> emb_start pulse (embedding row consumed for the current token)
//                      kind 2 SEG  -> ME program segment start, program base [15:4]
//                      other kinds FAULT
//   otherwise        forwarded on `cmd` (W5 cmd_wi) on its issue edge: SU / STN / ROOT / PORTS / STREAM / AMAX /
//                    SETID and every collective (XC, kind 0).  su_issue / xc_issue mark SU and XC issues.
// OUTPUT TIMING: `cmd` and the local pulses are registers loaded on the issue edge (S + T_k).
// MUT (bench only): 1 = every entry fires one edge late; 2 = entry word halves swapped; 3 = BOOT segment never starts.
// =====================================================================================================================
module qfd_dv_cmd_cal #(
    parameter integer MUT = 0,
    parameter integer LAST_STAGE = 37,
    parameter integer TW = 20                       // issue-time width (edges from the segment start)
) (
    input  wire          ck,
    input  wire          rst_n,
    input  wire          pw_v,
    input  wire [9:0]    pw_addr,
    input  wire [63:0]   pw_data,
    input  wire          dw_v,
    input  wire [2:0]    dw_addr,
    input  wire [63:0]   dw_data,
    input  wire          start,
    input  wire [5:0]    stage,
    output reg  [115:0]  cmd,
    output reg           loc_emb,
    output reg           loc_seg,
    output reg  [11:0]   loc_base,
    output reg           su_issue,
    output reg  [8:0]    su_pidx,
    output reg           xc_issue,
    output reg  [75:0]   program_obs,
    output reg  [68:0]   descriptor_obs,
    output wire          image_ready,
    output reg           running,
    output reg           done,
    output reg           fault
);
    // ================================================================ image load
    reg         loading, sealed, sealed_d;
    reg  [10:0] pw_cnt;
    reg  [3:0]  dw_cnt;
    reg  [9:0]  meta_rows;
    reg  [63:0] dwr [0:6];
    wire [63:0] d0 = dwr[0];
    wire [9:0]  base = d0[25:16];
    wire [8:0]  nent = d0[8:0];
    reg         seal_bad;
    integer     s;
    always @* begin
        seal_bad = d0[63:32] != 32'h43414c44 || d0[31:26] != 6'd0 || d0[15:9] != 7'd0 || base[2:0] != 3'd0 ||
                   nent == 9'd0 || {1'b0, base} + {1'b0, nent, 1'b0} > 11'd976 || {4'd0, base} < {meta_rows, 4'd0} ||
                   dwr[5] != 64'd0 || dwr[6] != 64'd0 || dw_data != 64'd0;
        for (s = 1; s <= 4; s = s + 1)
            if (dwr[s][63:32] != 32'd0 ||
                (dwr[s][15:0] != 16'd0 && (dwr[s][17:16] != 2'd0 || {1'b0, dwr[s][31:16]} + {1'b0, dwr[s][15:0]} > {8'd0, nent})))
                seal_bad = 1'b1;
    end
    // program copy: every macro write pin from a register (as the ME store), observed at the macro pins
    reg         pw_v2, pw_b2; reg [5:0] pw_row2; reg [7:0] pw_sl2; reg [63:0] pw_d2;
    reg         dw_v2; reg [2:0] dw_a2; reg [63:0] dw_d2;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin pw_v2 <= 1'b0; dw_v2 <= 1'b0; end
        else begin pw_v2 <= pw_v; dw_v2 <= dw_v; end
    always @(posedge ck) begin
        pw_b2 <= pw_addr[3]; pw_row2 <= pw_addr[9:4]; pw_sl2 <= 8'd1 << pw_addr[2:0]; pw_d2 <= pw_data;
        dw_a2 <= dw_addr; dw_d2 <= dw_data;
    end
    wire [511:0] w_mask;
    genvar g;
    generate for (g = 0; g < 8; g = g + 1) begin : g_mask
        assign w_mask[64*g +: 64] = {64{pw_sl2[g]}};
    end endgenerate
    wire [1:0]    m_ce = {pw_v2 && pw_b2, pw_v2 && !pw_b2};
    wire [1023:0] m_data = {2{{8{pw_d2}}}}, m_mask = {2{w_mask}};
    wire          ob_v, ob_full; wire [9:0] ob_addr; wire [63:0] ob_data;
    qkd_program_pw_observer u_obs (.macro_ce(m_ce), .macro_row({pw_row2, pw_row2}), .macro_data(m_data),
        .macro_mask(m_mask), .consumed_v(ob_v), .consumed_addr(ob_addr), .consumed_data(ob_data), .full_word(ob_full));
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin program_obs <= 76'd0; descriptor_obs <= 69'd0; end
        else begin
            program_obs <= {ob_v, ob_full, ob_addr, ob_data};
            descriptor_obs <= {dw_v2, 1'b1, dw_a2, dw_d2};
        end
    // store read port (issue side)
    reg          rce_q, rbank_q; reg [5:0] rrow_q;
    wire [511:0] rd [0:1];
    generate for (g = 0; g < 2; g = g + 1) begin : g_m
        ot_sram_1r1w_64x512_m1_r2c2 u_pm (.clk(ck), .r_ce_in(rce_q && (rbank_q == g[0])), .r_addr_in(rrow_q), .rd_out(rd[g]),
            .w_ce_in(m_ce[g]), .w_addr_in(pw_row2), .wd_in(m_data[512*g +: 512]), .w_mask_in(m_mask[512*g +: 512]),
            .rr_en(2'b00), .rr_addr(12'd0), .cr_en(2'b00), .cr_sel(18'd0));
    end endgenerate

    // ================================================================ segment start
    wire       boot_go = sealed && !sealed_d && (MUT != 3);
    wire [1:0] sseg = (stage == 6'd0) ? 2'd0 : (stage == LAST_STAGE[5:0]) ? 2'd2 : 2'd1;
    wire       go = start || boot_go;
    wire [1:0] gseg = boot_go ? 2'd3 : sseg;
    wire [63:0] gd = dwr[{1'b0, gseg} + 3'd1];
    wire [15:0] g_first = gd[31:16], g_cnt = gd[15:0];

    // ================================================================ fetch (4 entries per macro word) + FIFO (8)
    reg  [9:0]  f_idx, f_rem, i_rem;
    reg  [3:0]  fifo_n, infl;
    reg  [2:0]  wp, rp;
    reg  [115:0] q_cmd [0:7];
    reg  [TW-1:0] q_t [0:7];
    reg  [TW-1:0] t_acc, tcount;
    reg         rd_v, rd_bank; reg [2:0] rd_n, r_n_q;
    wire [9:0]  waddr = base + {f_idx[8:0], 1'b0};
    wire [2:0]  f_n = (f_rem >= 10'd4) ? 3'd4 : f_rem[2:0];
    wire        can_read = running && f_rem != 10'd0 && ({1'b0, fifo_n} + {1'b0, infl} + 5'd4 <= 5'd8);
    // the up-to-4 entries of the word that answers this edge
    wire [511:0] rw = rd[rd_bank];
    reg  [127:0] ent [0:3];
    reg  [TW-1:0] et [0:3];
    reg  [3:0]  zdelta;
    integer j;
    always @* begin
        for (j = 0; j < 4; j = j + 1) begin
            ent[j] = (MUT == 2) ? {rw[128*j +: 64], rw[128*j + 64 +: 64]} : rw[128*j +: 128];
            zdelta[j] = (j < rd_n) && ent[j][127:116] == 12'd0;
        end
        et[0] = t_acc + {{(TW-12){1'b0}}, ent[0][127:116]};
        for (j = 1; j < 4; j = j + 1) et[j] = et[j-1] + {{(TW-12){1'b0}}, ent[j][127:116]};
    end
    // ================================================================ issue
    wire [115:0] hc = q_cmd[rp];
    wire [TW-1:0] ht = q_t[rp] + ((MUT == 1) ? {{(TW-1){1'b0}}, 1'b1} : {TW{1'b0}});
    wire        hv = fifo_n != 4'd0;
    wire        fire = running && hv && tcount == ht;
    wire        late = running && hv && tcount > ht;
    wire        h_go = hc[0], h_loc = hc[115:112] == 4'hE;
    wire [2:0]  h_kind = hc[3:1];
    wire        pop = fire;
    wire [2:0]  push_n = rd_v ? rd_n : 3'd0;

    always @(posedge ck or negedge rst_n) begin
        if (!rst_n) begin
            loading <= 1'b0; sealed <= 1'b0; sealed_d <= 1'b0; pw_cnt <= 11'd0; dw_cnt <= 4'd0; meta_rows <= 10'd0;
            for (s = 0; s < 7; s = s + 1) dwr[s] <= 64'd0;
            running <= 1'b0; done <= 1'b0; fault <= 1'b0;
            f_idx <= 10'd0; f_rem <= 10'd0; i_rem <= 10'd0; fifo_n <= 4'd0; infl <= 4'd0; wp <= 3'd0; rp <= 3'd0;
            t_acc <= {TW{1'b0}}; tcount <= {TW{1'b0}};
            rce_q <= 1'b0; rbank_q <= 1'b0; rrow_q <= 6'd0; r_n_q <= 3'd0; rd_v <= 1'b0; rd_bank <= 1'b0; rd_n <= 3'd0;
            cmd <= 116'd0; loc_emb <= 1'b0; loc_seg <= 1'b0; loc_base <= 12'd0;
            su_issue <= 1'b0; su_pidx <= 9'd0; xc_issue <= 1'b0;
        end else begin
            sealed_d <= sealed;
            done <= 1'b0;
            // ---------------- image load (never while a segment runs)
            if (pw_v) begin
                if (pw_addr == 10'd0) begin                     // a new image: the load fault state restarts (as ME)
                    fault <= running;
                    loading <= 1'b1; sealed <= 1'b0; pw_cnt <= 11'd1; dw_cnt <= 4'd0; meta_rows <= 10'd0;
                end else begin
                    if (running || !loading || {1'b0, pw_addr} != pw_cnt) fault <= 1'b1;
                    pw_cnt <= pw_cnt + 11'd1;
                    if (pw_addr == 10'd1017) meta_rows <= pw_data[27:18];
                end
            end
            if (dw_v) begin
                if (running || !loading || pw_cnt != 11'd1024 || {1'b0, dw_addr} != dw_cnt || pw_v) fault <= 1'b1;
                dw_cnt <= dw_cnt + 4'd1;
                if (dw_addr != 3'd7) dwr[dw_addr] <= dw_data;
                else begin
                    loading <= 1'b0;
                    if (seal_bad) fault <= 1'b1; else sealed <= 1'b1;
                end
            end
            // ---------------- segment start
            if (go) begin
                if (!sealed || running || (start && boot_go) || (start && stage > LAST_STAGE[5:0])) fault <= 1'b1;
                else if (g_cnt != 16'd0) begin
                    running <= 1'b1; f_idx <= g_first[9:0]; f_rem <= g_cnt[9:0]; i_rem <= g_cnt[9:0];
                    t_acc <= {TW{1'b0}}; tcount <= {{(TW-1){1'b0}}, 1'b1};
                    fifo_n <= 4'd0; infl <= 4'd0; wp <= 3'd0; rp <= 3'd0; rce_q <= 1'b0; rd_v <= 1'b0;
                end else done <= 1'b1;
            end else begin
                if (running) begin
                    tcount <= tcount + {{(TW-1){1'b0}}, 1'b1};
                    if (&tcount) fault <= 1'b1;
                end
                // fetch: read decision (flop-driven macro pins), answer one edge later, push the edge after
                rce_q <= can_read; rbank_q <= waddr[3]; rrow_q <= waddr[9:4]; r_n_q <= f_n;
                if (can_read) begin f_idx <= f_idx + 10'd4; f_rem <= f_rem - {7'd0, f_n}; end
                rd_v <= rce_q; rd_bank <= rbank_q; rd_n <= r_n_q;
                infl <= infl + (can_read ? {1'b0, f_n} : 4'd0) - (rd_v ? {1'b0, rd_n} : 4'd0);
                if (rd_v) begin
                    for (j = 0; j < 4; j = j + 1)
                        if (j < rd_n) begin q_cmd[wp + j[2:0]] <= ent[j][115:0]; q_t[wp + j[2:0]] <= et[j]; end
                    wp <= wp + rd_n;
                    t_acc <= et[rd_n[1:0] - 2'd1];
                    if (|zdelta) fault <= 1'b1;
                end
                fifo_n <= fifo_n + {1'b0, push_n} - (pop ? 4'd1 : 4'd0);
                if (late) fault <= 1'b1;
                if (pop) begin
                    rp <= rp + 3'd1; i_rem <= i_rem - 10'd1;
                    if (i_rem == 10'd1) begin running <= 1'b0; done <= 1'b1; end
                end
            end
            // ---------------- issue register (one word an edge)
            cmd <= 116'd0; loc_emb <= 1'b0; loc_seg <= 1'b0; su_issue <= 1'b0; xc_issue <= 1'b0;
            if (fire && !go && h_go) begin
                if (h_loc) begin
                    if (h_kind == 3'd1) loc_emb <= 1'b1;
                    else if (h_kind == 3'd2) begin loc_seg <= 1'b1; loc_base <= hc[15:4]; end
                    else fault <= 1'b1;
                end else begin
                    cmd <= hc;
                    su_issue <= h_kind == 3'd1; su_pidx <= hc[12:4]; xc_issue <= h_kind == 3'd0;
                end
            end
        end
    end
    assign image_ready = sealed && !fault;
endmodule

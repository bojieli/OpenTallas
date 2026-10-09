`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_dsrom_window_stage_pipeline: the packed WINDOW staging buffer of ot_dsrom_window_attn_source_la
// (claude/dsrom-s81-window-bind-20261004).  Successor of ot_chip_v41x_window_stage4 for the wide load:
// the same four-bank row organisation (absolute row 4q + b in bank b, slot q mod 32) and a pipelined,
// one-four-row-request-a-cycle read path into the attention row merge; filled by up to NPC sectors a cycle
// (one response port per HBM pseudo-channel) instead of one.
//
// Landing.  Each bank is split into 17 sector columns (16 code sectors of 256 b, the scale sector's low
// 128 b), every column a 32-entry single-write-port array: 68 columns, each written at most once a cycle.
// A response beat (granule tag t, beat j -> window sector s = 4 t + j, slot = s / 17, column = s mod 17)
// passes through five elastic per-pseudo-channel decode registers. From the final registers, the lowest
// pseudo-channel targeting a column wins; a losing beat holds and back-pressures its pipeline. Column
// payload and row enables are registered before the actual FF write. The accepted beats are
// also forwarded (acc_*) to ot_dsrom_window_stream_la, whose issue / completion accounting therefore sees
// exactly the beats that landed. Acceptance coincides with the actual payload write, preserving original
// tags and beat numbers. Read capture uses four eight-entry groups and a final registered group mux,
// adding one edge to the original two-edge four-row response protocol.
// A sector landed twice in one job, or a beat outside the 2,176-sector window, is a fault.
//
// Job.  `job_v` (one cycle, while not busy) opens a job: rows [first, first + count) of user `user`,
// count <= 128; all sector-landed bits clear.  Row R is readable when first <= R < first + count, its 17
// sectors have landed in this job, and the request names the job's user (the row-tag / user checks of the
// as-built prefetch are made once, at job start, by the source's tag mirror).  `all_rows` = every job row
// readable.  Bytes are moved, never transformed.
// ---------------------------------------------------------------------------
module ot_dsrom_window_stage_pipeline #(
    parameter integer POS_W = 21,
    parameter integer USER_W = 10,
    parameter integer NPC = 32,
    parameter integer WTAGW = 13,
    parameter integer BEATW = 4,
    parameter integer MAX_CONTEXT = 1048576,
    // 0: flat, 1: 68 mixed-width macros, 2: 132 full-depth 128-bit macros.
    parameter integer SPLIT_COLUMNS = 0,
    // MARGIN = 1 (default off): register-to-register boundary and wire staging for the 1.9 mm parent
    // (OWNER_RULE_MARGIN_FIRST 2026-10-06).  Request: pin register -> per-bank kept copy -> per-column kept
    // address/valid register (+3 cycles).  Response: per-bank column-output register before the lane mux
    // (+1 cycle).  Write: two-entry input FIFO with a registered in_rdy (+1 cycle) and per-bank kept copies
    // of the accepted beats before the column OR trees (+1 cycle; acc_* still coincides with the FF write).
    // all_rows is registered (+1 cycle, cleared by job_v).  Bytes, order and checks are unchanged.
    parameter integer MARGIN = 0
) (
    input  wire                   clk,
    input  wire                   rst_n,
    input  wire                   job_v,
    input  wire [USER_W-1:0]      job_user,
    input  wire [POS_W-1:0]       job_first,
    input  wire [7:0]             job_count,
    output wire                   all_rows,
    output reg  [11:0]            sectors_landed,
    output reg                    fault,
    // HBM responses (client port of ot_dsrom_hbm_wmux)
    input  wire [NPC-1:0]         in_v,
    output wire [NPC-1:0]         in_rdy,
    input  wire [NPC*WTAGW-1:0]   in_tag,
    input  wire [NPC*BEATW-1:0]   in_beat,
    input  wire [NPC*256-1:0]     in_data,
    // accepted beats (to the stream engine's accounting)
    output wire [NPC-1:0]         acc_v,
    output wire [NPC*WTAGW-1:0]   acc_tag,
    output wire [NPC*BEATW-1:0]   acc_beat,
    output wire [NPC*256-1:0]     acc_data,
    // four-row read port (ot_chip_v41x_window_stage4 protocol)
    input  wire                   req_v,
    output wire                   req_ready,
    input  wire [USER_W-1:0]      req_user,
    input  wire [POS_W-1:0]       req_first_row,
    input  wire [3:0]             req_mask,
    output reg                    rsp_v,
    output reg  [USER_W-1:0]      rsp_user,
    output reg  [POS_W-1:0]       rsp_first_row,
    output reg  [3:0]             rsp_mask,
    output reg  [3:0]             rsp_valid_mask,
    output reg  [4*4224-1:0]      rsp_rows,
    output reg                    rsp_fault
);
    localparam integer ROWB = 4224, PITCH = 17, NSECT = 128 * PITCH;
    assign req_ready = 1'b1;
    // ---------------- job ----------------
    reg [USER_W-1:0] j_user;
    reg [POS_W-1:0]  j_first;
    reg [7:0]        j_count;
    reg [127:0]      in_job;                 // slot belongs to a job row
    reg [NSECT-1:0]  landed;                 // sector landed in this job
    wire [127:0]     slot_done;
    genvar s;
    generate for (s = 0; s < 128; s = s + 1) begin : g_slot
        assign slot_done[s] = &landed[s*PITCH +: PITCH];
    end endgenerate
    wire all_rows_c = &(slot_done | ~in_job);
    generate if (MARGIN) begin : g_all_rows_q
        reg all_rows_q;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) all_rows_q <= 1'b0;
            else all_rows_q <= job_v ? 1'b0 : all_rows_c;
        assign all_rows = all_rows_q;
    end else begin : g_all_rows_c
        assign all_rows = all_rows_c;
    end endgenerate
    // Five elastic decode stages; every stage holds data and original identity.
    // Readiness is derived from current occupancy and an actual downstream take.
    reg [NPC-1:0] dv [0:4];
    wire [NPC-1:0] dr [0:4];
    reg [WTAGW-1:0] dt [0:4][0:NPC-1];
    reg [BEATW-1:0] db [0:4][0:NPC-1];
    reg [255:0] dd [0:4][0:NPC-1];
    reg [11:0] ds [0:4][0:NPC-1];
    reg [23:0] dx [0:4][0:NPC-1];
    reg [6:0] dslot [0:4][0:NPC-1];
    reg [11:0] dtmp [0:4][0:NPC-1];
    reg [4:0] dc [0:4][0:NPC-1];
    reg [NPC-1:0] bad [0:4];
    wire [NPC-1:0] take;
    wire [NPC-1:0] bf = dv[4];
    wire [NPC-1:0] b_bad = bad[4];
    wire [WTAGW-1:0] b_tag [0:NPC-1];
    wire [BEATW-1:0] b_beat [0:NPC-1];
    wire [255:0] b_data [0:NPC-1];
    wire [11:0] b_sec [0:NPC-1];
    wire [6:0] b_slot [0:NPC-1];
    wire [4:0] b_col [0:NPC-1];
    reg [NPC-1:0] acc;
    reg [NPC-1:0] av;
    reg [WTAGW-1:0] at [0:NPC-1];
    reg [BEATW-1:0] ab [0:NPC-1];
    reg [255:0] ad [0:NPC-1];
    // Write-side source of decode stage 0: the input pins (MARGIN = 0) or a two-entry FIFO whose
    // in_rdy is a flop (MARGIN = 1).
    wire [NPC-1:0] h_v;
    wire [WTAGW-1:0] h_tag [0:NPC-1];
    wire [BEATW-1:0] h_beat [0:NPC-1];
    wire [255:0] h_data [0:NPC-1];
    // Accepted-beat report: av coincides with the column registers' physical FF write.
    reg [NPC-1:0] av2;
    reg [WTAGW-1:0] at2 [0:NPC-1];
    reg [BEATW-1:0] ab2 [0:NPC-1];
    reg [255:0] ad2 [0:NPC-1];
    wire [NPC-1:0] avw = MARGIN ? av2 : av;
    assign acc_v = avw;
    generate for (genvar p=0; p<NPC; p=p+1) begin : g_decode
        assign b_tag[p]=dt[4][p]; assign b_beat[p]=db[4][p];
        assign b_data[p]=dd[4][p]; assign b_sec[p]=ds[4][p];
        assign b_slot[p]=dslot[4][p]; assign b_col[p]=dc[4][p];
        assign take[p] = acc[p] || (bf[p] && b_bad[p]);
        assign dr[4][p] = !dv[4][p] || take[p];
        for (genvar z=0; z<4; z=z+1) begin : g_rdy
            assign dr[z][p] = !dv[z][p] || dr[z+1][p];
        end
        assign acc_tag[p*WTAGW +: WTAGW]=MARGIN ? at2[p] : at[p];
        assign acc_beat[p*BEATW +: BEATW]=MARGIN ? ab2[p] : ab[p];
        assign acc_data[p*256 +: 256]=MARGIN ? ad2[p] : ad[p];
        if (MARGIN) begin : g_in_fifo
            reg [WTAGW-1:0] ft [0:1];
            reg [BEATW-1:0] fb [0:1];
            reg [255:0] fd [0:1];
            reg wp, rp, rdy_q;
            reg [1:0] occ;
            wire push = in_v[p] && rdy_q;
            wire pop = (occ != 2'd0) && dr[0][p];
            wire [1:0] occ_n = occ + {1'b0,push} - {1'b0,pop};
            always @(posedge clk) if (push) begin
                ft[wp] <= in_tag[p*WTAGW +: WTAGW]; fb[wp] <= in_beat[p*BEATW +: BEATW];
                fd[wp] <= in_data[p*256 +: 256];
            end
            always @(posedge clk or negedge rst_n)
                if (!rst_n) begin wp <= 1'b0; rp <= 1'b0; occ <= 2'd0; rdy_q <= 1'b1; end
                else begin
                    if (push) wp <= ~wp;
                    if (pop) rp <= ~rp;
                    occ <= occ_n; rdy_q <= occ_n < 2'd2;
                end
            assign in_rdy[p] = rdy_q;
            assign h_v[p] = occ != 2'd0;
            assign h_tag[p] = ft[rp]; assign h_beat[p] = fb[rp]; assign h_data[p] = fd[rp];
            always @(posedge clk or negedge rst_n)
                if (!rst_n) av2[p] <= 1'b0;
                else begin
                    av2[p] <= av[p];
                    if (av[p]) begin at2[p] <= at[p]; ab2[p] <= ab[p]; ad2[p] <= ad[p]; end
                end
        end else begin : g_in_pins
            assign in_rdy[p] = dr[0][p];
            assign h_v[p] = in_v[p];
            assign h_tag[p] = in_tag[p*WTAGW +: WTAGW]; assign h_beat[p] = in_beat[p*BEATW +: BEATW];
            assign h_data[p] = in_data[p*256 +: 256];
        end
        wire [WTAGW+2:0] sec_raw = {1'b0,h_tag[p],2'b00} + (WTAGW+3)'(h_beat[p]);
        wire [23:0] mult = dx[1][p] + ({12'd0,ds[1][p]} << 4);
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) begin
                for (integer z=0; z<5; z=z+1) begin dv[z][p]<=0; bad[z][p]<=0; end
                av[p]<=0;
            end else begin
                if (dr[0][p]) begin
                    dv[0][p]<=h_v[p];
                    if (h_v[p]) begin
                        dt[0][p]<=h_tag[p]; db[0][p]<=h_beat[p];
                        dd[0][p]<=h_data[p]; ds[0][p]<=sec_raw[11:0];
                        bad[0][p]<=sec_raw>=NSECT;
                    end
                end
                for (integer z=1; z<5; z=z+1) if (dr[z][p]) begin
                    dv[z][p]<=dv[z-1][p];
                    if (dv[z-1][p]) begin
                        dt[z][p]<=dt[z-1][p]; db[z][p]<=db[z-1][p]; dd[z][p]<=dd[z-1][p];
                        ds[z][p]<=ds[z-1][p]; bad[z][p]<=bad[z-1][p];
                    end
                end
                if (dr[1][p]) dx[1][p]<=({12'd0,ds[0][p]}<<12)-({12'd0,ds[0][p]}<<8);
                if (dr[2][p]) dslot[2][p]<=mult[22:16];
                if (dr[3][p]) begin
                    dslot[3][p]<=dslot[2][p]; dtmp[3][p]<=ds[2][p]-{dslot[2][p],4'b0000};
                end
                if (dr[4][p]) begin
                    dslot[4][p]<=dslot[3][p]; dc[4][p]<=5'(dtmp[3][p]-dslot[3][p]);
                end
                // av coincides with the column registers' physical FF write.
                av[p]<=acc[p];
                if (acc[p]) begin at[p]<=b_tag[p]; ab[p]<=b_beat[p]; ad[p]<=b_data[p]; end
            end
        end
    end endgenerate
    // Parallel conflict comparisons, then balanced OR data muxes; no serial
    // priority payload mux or arithmetic in any memory-row enable cone.
    generate for (genvar p=0; p<NPC; p=p+1) begin : g_winner
        wire [NPC-1:0] conflicts;
        for (genvar q=0; q<NPC; q=q+1) begin : g_conflict
            assign conflicts[q] = q<p && bf[q] && !b_bad[q] &&
                b_slot[q][1:0]==b_slot[p][1:0] && b_col[q]==b_col[p];
        end
        always @* acc[p] = bf[p] && !b_bad[p] && !(|conflicts);
    end endgenerate
    wire [NSECT-1:0] write_sector;
    wire [NSECT-1:0] duplicates = write_sector & landed;
    // Balanced population count; 32 serial additions are never inferred.
    wire [1:0] pc2 [0:15]; wire [2:0] pc4 [0:7];
    wire [3:0] pc8 [0:3]; wire [4:0] pc16 [0:1]; wire [5:0] nwrite;
    generate
        for(genvar x=0;x<16;x=x+1) assign pc2[x]={1'b0,avw[2*x]}+{1'b0,avw[2*x+1]};
        for(genvar x=0;x<8;x=x+1) assign pc4[x]={1'b0,pc2[2*x]}+{1'b0,pc2[2*x+1]};
        for(genvar x=0;x<4;x=x+1) assign pc8[x]={1'b0,pc4[2*x]}+{1'b0,pc4[2*x+1]};
        for(genvar x=0;x<2;x=x+1) assign pc16[x]={1'b0,pc8[2*x]}+{1'b0,pc8[2*x+1]};
    endgenerate
    assign nwrite={1'b0,pc16[0]}+{1'b0,pc16[1]};
    // ---------------- banks: 4 x 17 columns x 32 entries ----------------
    wire [ROWB-1:0] bank_q [0:3];
    reg  [3:0] bank_qv;
    reg  v1, bad1, v0, bad0;
    reg [USER_W-1:0] user0; reg [POS_W-1:0] first0; reg [3:0] mask0;
    reg [POS_W-1:0] owner_first0;
    reg [POS_W:0] owner_end0;
    reg [USER_W-1:0] owner_user0;
    // Effective request (r_*): the pins (MARGIN = 0) or a three-register global chain whose edge matches
    // the per-column address registers (MARGIN = 1).  a_* are the pin registers.
    wire r_v; wire [USER_W-1:0] r_user; wire [POS_W-1:0] r_first; wire [3:0] r_mask;
    reg a_v; reg [USER_W-1:0] a_user; reg [POS_W-1:0] a_first; reg [3:0] a_mask;
    generate if (MARGIN) begin : g_req_chain
        reg g_v, q_v;
        reg [USER_W-1:0] g_user, q_user; reg [POS_W-1:0] g_first, q_first; reg [3:0] g_mask, q_mask;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin a_v <= 1'b0; g_v <= 1'b0; q_v <= 1'b0; end
            else begin a_v <= req_v; g_v <= a_v; q_v <= g_v; end
        always @(posedge clk) begin
            a_user <= req_user; a_first <= req_first_row; a_mask <= req_mask;
            g_user <= a_user; g_first <= a_first; g_mask <= a_mask;
            q_user <= g_user; q_first <= g_first; q_mask <= g_mask;
        end
        assign r_v = q_v; assign r_user = q_user; assign r_first = q_first; assign r_mask = q_mask;
    end else begin : g_req_pins
        assign r_v = req_v; assign r_user = req_user; assign r_first = req_first_row; assign r_mask = req_mask;
    end endgenerate
    // Accepted-request witnesses share the payload's two read edges. Capture
    // the preedge owner/completion state; a later job or landing cannot change
    // this request's validity. No permission is reused for another request.
    always @(posedge clk) if (r_v) begin
        owner_first0 <= j_first;
        owner_end0 <= {1'b0, j_first} + (POS_W+1)'(j_count);
        owner_user0 <= j_user;
    end
    reg  [USER_W-1:0] user1;
    reg  [POS_W-1:0] first1;
    reg  [3:0] mask1;
    wire prefix_mask = r_mask == 4'b0001 || r_mask == 4'b0011 ||
                       r_mask == 4'b0111 || r_mask == 4'b1111;
    // MARGIN response stage: per-bank column-output registers and the matching control edge.
    reg [ROWB-1:0] bq1 [0:3];
    reg [3:0] bqv1;
    reg v2, bad2; reg [USER_W-1:0] user2; reg [POS_W-1:0] first2; reg [3:0] mask2;
    generate for (genvar b = 0; b < 4; b = b + 1) begin : g_bank
        wire [1:0] lane = 2'(b) - r_first[1:0];
        wire [POS_W:0] wanted = {1'b0, r_first} + (POS_W+1)'(lane);
        wire [4:0] raddr = wanted[6:2];
        reg [POS_W:0] wanted0;
        reg [3:0] complete_group0;
        always @(posedge clk) if (r_v) wanted0 <= wanted;
        for (genvar group=0; group<4; group=group+1) begin : g_read_complete
            wire [4:0] slot_row = 5'(8*group) + 5'(raddr[2:0]);
            always @(posedge clk) if (r_v)
                complete_group0[group] <= slot_done[{slot_row, 2'(b)}];
        end
        wire ok0 = wanted0 < (POS_W+1)'(MAX_CONTEXT) &&
                   wanted0 >= {1'b0, owner_first0} && wanted0 < owner_end0 &&
                   user0 == owner_user0 && complete_group0[wanted0[6:5]];
        // Per-bank kept copy of the pin-registered request (MARGIN), placed toward the bank.
        wire m_v; wire [POS_W-1:0] m_first;
        // Per-bank write staging (MARGIN): kept copies of the final decode registers' payload and slot.
        wire [255:0] w_data [0:NPC-1];
        wire [4:0] w_row [0:NPC-1];
        if (MARGIN) begin : g_m
            ot_dsrom_window_keep_reg #(.W(1), .RESET(1)) u_mv (.clk(clk), .rst_n(rst_n), .d(a_v), .q(m_v));
            ot_dsrom_window_keep_reg #(.W(POS_W), .RESET(0)) u_mf (.clk(clk), .rst_n(rst_n), .d(a_first), .q(m_first));
            for (genvar p=0;p<NPC;p=p+1) begin : g_wcopy
                ot_dsrom_window_keep_reg #(.W(256+5), .RESET(0)) u_w (.clk(clk), .rst_n(rst_n),
                    .d({b_slot[p][6:2], b_data[p]}), .q({w_row[p], w_data[p]}));
            end
        end else begin : g_nm
            assign m_v = 1'b0; assign m_first = '0;
            for (genvar p=0;p<NPC;p=p+1) begin : g_wdirect
                assign w_data[p] = b_data[p]; assign w_row[p] = b_slot[p][6:2];
            end
        end
        wire [1:0] m_lane = 2'(b) - m_first[1:0];
        wire [POS_W:0] m_wanted = {1'b0, m_first} + (POS_W+1)'(m_lane);
        for (genvar k = 0; k < PITCH; k = k + 1) begin : g_col
            localparam integer CWID = (k < 16) ? 256 : 128;
            wire [CWID-1:0] q;
            wire [NPC-1:0] chosen_c;
            wire [NPC-1:0] chosen;
            wire [CWID-1:0] data_tree [0:2*NPC-2];
            reg [CWID-1:0] wd;
            reg [31:0] row_we;
            for (genvar p=0;p<NPC;p=p+1) begin : g_choose
                assign chosen_c[p]=acc[p] && b_slot[p][1:0]==2'(b) && b_col[p]==5'(k);
                assign data_tree[NPC-1+p]=w_data[p][CWID-1:0] & {CWID{chosen[p]}};
            end
            // Column read address/valid: the pins (MARGIN = 0) or a per-column kept register (MARGIN = 1).
            wire col_v; wire [4:0] col_addr;
            if (MARGIN) begin : g_cm
                reg [NPC-1:0] chosen_q;
                always @(posedge clk or negedge rst_n)
                    if (!rst_n) chosen_q <= '0; else chosen_q <= chosen_c;
                assign chosen = chosen_q;
                ot_dsrom_window_keep_reg #(.W(1), .RESET(1)) u_cv (.clk(clk), .rst_n(rst_n), .d(m_v), .q(col_v));
                ot_dsrom_window_keep_reg #(.W(5), .RESET(0)) u_ca (.clk(clk), .rst_n(rst_n), .d(m_wanted[6:2]), .q(col_addr));
            end else begin : g_cp
                assign chosen = chosen_c;
                assign col_v = r_v; assign col_addr = raddr;
            end
            for (genvar p=0;p<NPC-1;p=p+1) begin : g_or
                assign data_tree[p]=data_tree[2*p+1] | data_tree[2*p+2];
            end
            always @(posedge clk) wd<=data_tree[0];
            for (genvar r=0;r<32;r=r+1) begin : g_row
                wire [NPC-1:0] matching;
                for (genvar p=0;p<NPC;p=p+1) begin : g_match
                    assign matching[p]=chosen[p] && w_row[p]==5'(r);
                end
                always @(posedge clk or negedge rst_n)
                    if (!rst_n) row_we[r]<=0; else row_we[r]<=|matching;
                assign write_sector[(4*r+b)*PITCH+k]=row_we[r];
            end
            if (SPLIT_COLUMNS) begin : g_split
                if(CWID==256 && SPLIT_COLUMNS==2) begin : g_payload_split128
                    ot_dsrom_window_column_256_split u_column (
                        .clk(clk), .rst_n(rst_n), .row_we(row_we), .write_data(wd),
                        .read_v(col_v), .read_addr(col_addr), .read_data(q));
                end else if(CWID==256) begin : g_payload
                    (* keep_hierarchy = "yes" *) ot_dsrom_window_column_256 u_column (
                        .clk(clk), .rst_n(rst_n), .row_we(row_we), .write_data(wd),
                        .read_v(col_v), .read_addr(col_addr), .read_data(q));
                end else begin : g_scale
                    (* keep_hierarchy = "yes" *) ot_dsrom_window_column_128 u_column (
                        .clk(clk), .rst_n(rst_n), .row_we(row_we), .write_data(wd),
                        .read_v(col_v), .read_addr(col_addr), .read_data(q));
                end
            end else begin : g_flat
                reg [CWID-1:0] mem [0:31];
                for (genvar r=0;r<32;r=r+1) begin : g_write
                    always @(posedge clk) if (row_we[r]) mem[r]<=wd;
                end
                reg [CWID-1:0] rq [0:3];
                reg [CWID-1:0] q_flat;
                reg [1:0] rh;
                reg read_v;
                for (genvar group=0;group<4;group=group+1) begin : g_read
                    always @(posedge clk) if (col_v) rq[group]<=mem[8*group+col_addr[2:0]];
                end
                always @(posedge clk or negedge rst_n)
                    if (!rst_n) read_v<=0;
                    else begin
                        read_v<=col_v;
                        if(col_v) rh<=col_addr[4:3];
                        if(read_v) q_flat<=rq[rh];
                    end
                assign q=q_flat;
            end
            if (k < 16) begin : g_c
                assign bank_q[b][256*k +: 256] = q;
            end else begin : g_s
                assign bank_q[b][4096 +: 128] = q;
            end
        end
        always @(posedge clk or negedge rst_n)
            if (!rst_n) bank_qv[b]<=0;
            else if(v0) bank_qv[b]<=ok0;
        if (MARGIN) begin : g_bq1
            always @(posedge clk) bq1[b] <= bank_q[b];
            always @(posedge clk or negedge rst_n)
                if (!rst_n) bqv1[b] <= 1'b0; else bqv1[b] <= bank_qv[b];
        end
    end endgenerate
    // lanes (stage4's second register: bank order -> chronological lanes)
    wire [POS_W-1:0] first_l = MARGIN ? first2 : first1;
    wire [3:0] mask_l = MARGIN ? mask2 : mask1;
    wire [3:0] qv_l = MARGIN ? bqv1 : bank_qv;
    wire [3:0] lane_ok;
    generate for (genvar l = 0; l < 4; l = l + 1) begin : g_lane
        wire [1:0] bank = first_l[1:0] + 2'(l);
        wire [ROWB-1:0] row_l = MARGIN ? bq1[bank] : bank_q[bank];
        assign lane_ok[l] = mask_l[l] && qv_l[bank];
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin rsp_rows[l*ROWB +: ROWB] <= '0; rsp_valid_mask[l] <= 1'b0; end
            else begin
                rsp_rows[l*ROWB +: ROWB] <= lane_ok[l] ? row_l : '0;
                rsp_valid_mask[l] <= lane_ok[l];
            end
    end endgenerate
    generate for (genvar slot=0;slot<128;slot=slot+1) begin : g_membership
        wire [6:0] offset=7'(slot)-job_first[6:0];
        always @(posedge clk or negedge rst_n)
            if(!rst_n) in_job[slot]<=0; else if(job_v) in_job[slot]<={1'b0,offset}<job_count;
    end endgenerate
    // ---------------- control ----------------
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            j_user<=0; j_first<=0; j_count<=0; landed<=0; sectors_landed<=0; fault<=0;
            v0<=0; bad0<=0; user0<=0; first0<=0; mask0<=0;
            v1<=0; bad1<=0; user1<=0; first1<=0; mask1<=0;
            v2<=0; bad2<=0; user2<=0; first2<=0; mask2<=0;
            rsp_v<=0; rsp_user<=0; rsp_first_row<=0; rsp_mask<=0; rsp_fault<=0;
        end else begin
            if(job_v) begin
                j_user<=job_user; j_first<=job_first; j_count<=job_count; landed<=0; sectors_landed<=0;
            end else begin
                landed<=landed | write_sector;
                sectors_landed<=sectors_landed+12'(nwrite);
            end
            if ((|duplicates) || (|(bf & b_bad))) fault<=1'b1;
            // read path (stage4)
            v0<=r_v; v1<=v0; v2<=v1;
            if(v0) begin user1<=user0; first1<=first0; mask1<=mask0; bad1<=bad0; end
            if(v1) begin user2<=user1; first2<=first1; mask2<=mask1; bad2<=bad1; end
            if (r_v) begin
                user0 <= r_user; first0 <= r_first; mask0 <= r_mask;
                bad0 <= !prefix_mask ||
                    ({1'b0, r_first} + (POS_W+1)'(r_mask[3] ? 3 : r_mask[2] ? 2 : r_mask[1] ? 1 : 0)) >=
                    (POS_W+1)'(MAX_CONTEXT);
            end
            if (MARGIN) begin
                rsp_v <= v2; rsp_user <= user2; rsp_first_row <= first2; rsp_mask <= mask2;
                rsp_fault <= v2 && (bad2 || ((mask2 & ~lane_ok) != 0));
            end else begin
                rsp_v <= v1; rsp_user <= user1; rsp_first_row <= first1; rsp_mask <= mask1;
                rsp_fault <= v1 && (bad1 || ((mask1 & ~lane_ok) != 0));
            end
        end
    end
`ifndef SYNTHESIS
    initial if (MARGIN != 0 && MARGIN != 1) $fatal(1, "ot_dsrom_window_stage_pipeline MARGIN must be 0 or 1");
    initial if (POS_W < 21 || USER_W < 10 || MAX_CONTEXT != 1048576 || WTAGW < 10)
        $fatal(1, "ot_dsrom_window_stage_pipeline parameter contract failed");
`endif
endmodule

// One complete full-depth sector column. This hierarchy cut preserves both
// existing read edges and read-before-write behavior, including payload state
// across reset. The parent owns the write-data/enable registers and validity.
module ot_dsrom_window_column #(
    parameter integer WIDTH=256,
    // REDESIGN-S81 2026-10-08 (wcol256 TT+link budget -110.4 / wcol128 -84.6: row_we pin -> enable mux -> mem,
    // 2 logic + buffers on a fanout-WIDTH enable).  PINREG 1: row_we / write_data captured at the pins, the write
    // commits one cycle later, and the read captures the row's NEXT value (the mem D input: the committing write
    // bypassed), so every port is cycle-identical to PINREG 0 -- zero protocol cycles.  WE_REP: kept copies of each
    // captured row enable, one per WIDTH/WE_REP slice (fanout WIDTH/WE_REP, reg -> reg).
    parameter integer PINREG=0,
    parameter integer WE_REP=1
) (
    input wire clk, rst_n,
    input wire [31:0] row_we,
    input wire [WIDTH-1:0] write_data,
    input wire read_v,
    input wire [4:0] read_addr,
    output reg [WIDTH-1:0] read_data
);
    reg [WIDTH-1:0] mem [0:31];
    reg [WIDTH-1:0] rq [0:3];
    reg [1:0] rh;
    reg pending;
    generate
        if (PINREG) begin : g_pin
            localparam integer SW = WIDTH / WE_REP;
            reg [WIDTH-1:0] wd_q;
            always @(posedge clk) wd_q <= write_data;
            wire [WIDTH-1:0] nxt [0:31];
            for(genvar row=0;row<32;row=row+1) begin : g_write
                wire [WE_REP-1:0] we_q;
                for (genvar c=0;c<WE_REP;c=c+1) begin : g_rep
                    ot_dsrom_window_keep_reg #(.W(1), .RESET(0)) u_we (.clk(clk), .rst_n(rst_n), .d(row_we[row]), .q(we_q[c]));
                    assign nxt[row][SW*c +: SW] = we_q[c] ? wd_q[SW*c +: SW] : mem[row][SW*c +: SW];
                end
                always @(posedge clk) mem[row] <= nxt[row];
            end
            for(genvar group=0;group<4;group=group+1) begin : g_read
`ifdef OT_WCOL_MUT_NOBYPASS
                always @(posedge clk) if(read_v) rq[group]<=mem[8*group+read_addr[2:0]];   // negative control
`else
                always @(posedge clk) if(read_v) rq[group]<=nxt[8*group+read_addr[2:0]];
`endif
            end
        end else begin : g_base
            for(genvar row=0;row<32;row=row+1) begin : g_write
                always @(posedge clk) if(row_we[row]) mem[row]<=write_data;
            end
            for(genvar group=0;group<4;group=group+1) begin : g_read
                always @(posedge clk) if(read_v) rq[group]<=mem[8*group+read_addr[2:0]];
            end
        end
    endgenerate
    always @(posedge clk or negedge rst_n)
        if(!rst_n) pending<=0;
        else begin
            pending<=read_v;
            if(read_v) rh<=read_addr[4:3];
            if(pending) read_data<=rq[rh];
        end
endmodule

// Fixed-width names permit simultaneous LEF/LIB binding of both physical kinds.
// REDESIGN-S81 2026-10-08: the hardened columns default to PINREG 1 (cycle-identical ports, pins registered).
module ot_dsrom_window_column_128 #(parameter integer PINREG=1, parameter integer WE_REP=2) (
    input wire clk, rst_n,
    input wire [31:0] row_we,
    input wire [127:0] write_data,
    input wire read_v,
    input wire [4:0] read_addr,
    output wire [127:0] read_data
);
    ot_dsrom_window_column #(.WIDTH(128), .PINREG(PINREG), .WE_REP(WE_REP)) u_logic (.*);
endmodule

// Fixed-width names permit simultaneous LEF/LIB binding of both physical kinds.
module ot_dsrom_window_column_256 #(parameter integer PINREG=1, parameter integer WE_REP=4) (
    input wire clk, rst_n,
    input wire [31:0] row_we,
    input wire [255:0] write_data,
    input wire read_v,
    input wire [4:0] read_addr,
    output wire [255:0] read_data
);
    ot_dsrom_window_column #(.WIDTH(256), .PINREG(PINREG), .WE_REP(WE_REP)) u_logic (.*);
endmodule

// Kept register: one instance per physical copy.  The hierarchy boundary stops synthesis from merging
// identical copies (a plain (* keep *) reg does not stop opt_merge), so each copy can sit at its load.
(* keep_hierarchy = "yes" *)
module ot_dsrom_window_keep_reg #(
    parameter integer W = 1,
    parameter integer RESET = 0
) (
    input wire clk, rst_n,
    input wire [W-1:0] d,
    output reg [W-1:0] q
);
    generate if (RESET) begin : g_r
        always @(posedge clk or negedge rst_n) if (!rst_n) q <= '0; else q <= d;
    end else begin : g_n
        always @(posedge clk) q <= d;
    end endgenerate
endmodule

// Structural split only: identical read/write edges, full 32-row depth in each half.
module ot_dsrom_window_column_256_split (
    input wire clk, rst_n,
    input wire [31:0] row_we,
    input wire [255:0] write_data,
    input wire read_v,
    input wire [4:0] read_addr,
    output wire [255:0] read_data
);
    for (genvar half=0; half<2; half=half+1) begin : g_half
        (* keep_hierarchy = "yes" *) ot_dsrom_window_column_128 u_column (
            .clk(clk), .rst_n(rst_n), .row_we(row_we),
            .write_data(write_data[128*half+:128]), .read_v(read_v),
            .read_addr(read_addr), .read_data(read_data[128*half+:128]));
    end
endmodule

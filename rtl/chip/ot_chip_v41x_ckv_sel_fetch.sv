`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Owned selected-CKV row fetch of one die (DeepSeek-V4.1, tensor group 4).
//
// The die walks a stream of selected entries (index idx = 0, 1, ...) and
// fetches the rows it owns (id[5:4] == DIE_ID); the other three dies fetch
// theirs, and every die's owned rows are all-gathered so that each die stages
// all n_sel rows (owned share + all-gather, the model's attn.gather_rows
// share="tp" followed by attn.rows_allgather).  The stream is either
//   * the die's OWNED-RANK LIST of ot_chip_v41x_ckv_sel_ids (OWN bit set):
//     every entry is owned, one dispatch per cycle (the adopted wiring), or
//   * the whole rank table (id_rank_in = id_idx): non-owned entries are
//     skipped at one entry per cycle (functional, slower: the last owned rank
//     is reached only after n_sel cycles).
//
// Each owned row is handed to one of NSLOT row slots; a slot is an unchanged
// ot_chip_v41x_ckv_selected_dma (PIPE = 1: nine back-to-back sector reads,
// responses in any order) and holds the finished 288-B row until it is sent.
// Slots are allocated round robin in rank order.  Per HBM stack, the slots'
// requests are arbitrated oldest-slot-first starting at the oldest busy slot
// (the allocation order); the stack sees tag = {slot, sector}.  The response
// is routed to its slot by the tag's slot field.  Finished rows leave on the
// output as soon as they are complete, oldest-first among the complete slots
// (the collector places them by rank, so order is not required here).
//
// Interfaces
//   job     job_v/job_ready: window_count (the row index of rank 0),
//           published_source_count and the four per-stack regions of the
//           current user/source layer (as the DMA).  One job per layer.
//   ids     id_count (entries available, final when id_done), id_done;
//           id_idx (this module's registered cursor) -> id_rank_in (the
//           entry's selection rank), id_gid, id_die (combinational reads of
//           the table / owned list).
//   rows    o_v/o_ready, o_rank (selection rank), o_gid, o_row (the DMA's
//           2,304-bit packed row: 512 E2M1 nibbles low first, then 32 E4M3
//           scales).  One row per cycle at most.
//   hbm     four stack ports, reads only, one-sector requests, tags
//           {slot, sector}; responses may be reordered only across stacks
//           (per-stack order is irrelevant: the DMA accepts any order).
//   status  done (every owned row of the job sent), fault/fault_code (OR of
//           slot faults; {cursor, slot-remote, dma}), st_* counters.
// ---------------------------------------------------------------------------
module ot_chip_v41x_ckv_sel_fetch #(
    parameter integer DIE_ID = 0,
    parameter integer NSLOT = 16,
    parameter integer POS_W = 21,
    parameter integer SEC_W = 30,
    parameter integer HAW = 30,
    parameter integer K = 512,
    parameter integer MAX_CONTEXT = 1048576,
    parameter integer SW = (NSLOT > 1) ? $clog2(NSLOT) : 1,
    parameter integer TAGW = SW + 4,
    parameter integer KW = $clog2(K + 1)
) (
    input  wire                  clk,
    input  wire                  rst_n,
    input  wire                  job_v,
    output wire                  job_ready,
    input  wire [7:0]            window_count,
    input  wire [POS_W-1:0]      published_source_count,
    input  wire [4*SEC_W-1:0]    region_base_sector,
    input  wire [4*SEC_W-1:0]    region_sector_count,
    input  wire [KW-1:0]         id_count,
    input  wire                  id_done,
    output wire [KW-1:0]         id_idx,
    input  wire [KW-1:0]         id_rank_in,
    input  wire [POS_W-1:0]      id_gid,
    input  wire [1:0]            id_die,
    output wire                  o_v,
    input  wire                  o_ready,
    output wire [KW-1:0]         o_rank,
    output wire [POS_W-1:0]      o_gid,
    output wire [2303:0]         o_row,
    output reg                   done,
    output reg                   fault,
    output reg  [1:0]            fault_code,   // {slot remote, slot DMA}
    output reg  [31:0]           st_owned_rows,
    output wire [3:0]            m_v,
    input  wire [3:0]            m_rdy,
    output wire [4*HAW-1:0]      m_addr,
    output wire [4*TAGW-1:0]     m_tag,
    input  wire [3:0]            s_v,
    input  wire [4*TAGW-1:0]     s_tag,
    input  wire [4*4-1:0]        s_beat,
    input  wire [4*256-1:0]      s_data
);
    // ---- job state ----
    reg run;
    reg [KW-1:0] cur;                 // scan cursor (rank)
    reg [7:0] wcount;
    reg [SW-1:0] alloc;               // next slot to allocate (round robin)
    reg [NSLOT-1:0] busy;             // slot holds a row not yet sent
    reg [KW-1:0] srank [0:NSLOT-1];
    assign job_ready = !run;
    assign id_idx = cur;

    // ---- slots ----
    wire [NSLOT-1:0] sl_ready, sl_ok, sl_fault, sl_remote;
    wire [NSLOT*2304-1:0] sl_row;
    wire [NSLOT*POS_W-1:0] sl_src;
    wire [NSLOT*4-1:0] sl_mv;
    wire [NSLOT*4*HAW-1:0] sl_maddr;
    wire [NSLOT*4*4-1:0] sl_mtag;
    reg  [NSLOT*4-1:0] sl_mrdy;
    reg  [NSLOT*4-1:0] sl_sv;

    wire scan = run && cur < id_count;
    wire owned = id_die == 2'(DIE_ID);
    wire slot_free = !busy[alloc] && sl_ready[alloc];
    wire dispatch = scan && owned && slot_free;
    wire skip = scan && !owned;

    genvar s;
    generate for (s = 0; s < NSLOT; s = s + 1) begin : g_slot
        wire [9:0] lrow;
        wire [3:0] fc;
        wire [31:0] nrows, nsec;
        wire q_unused_v;
        wire [31:0] q_unused;
        wire [7:0] q8_unused;
        wire [9:0] plr;
        wire [4*16-1:0] mlen_unused;
        wire [3:0] mwe_unused;
        wire [4*256-1:0] mwd_unused;
        wire [4*32-1:0] mws_unused;
        wire [3:0] srdy_unused;
        wire [1:0] rdie_unused;
        wire [4*4-1:0] len4;
        wire [4*4-1:0] tag4;
        wire [4*4-1:0] s_tag_slot;     // the DMA sees only the sector field of the stack tag
        assign lrow = 10'(wcount) + 10'(id_rank_in);
        ot_chip_v41x_ckv_selected_dma #(.POS_W(POS_W), .SEC_W(SEC_W), .HAW(HAW), .TAGW(4),
                                        .DIE_ID(DIE_ID), .MAX_CONTEXT(MAX_CONTEXT), .PIPE(1)) u_dma (
            .clk(clk), .rst_n(rst_n),
            .region_base_sector(region_base_sector), .region_sector_count(region_sector_count),
            .published_source_count(published_source_count),
            .fetch_v(dispatch && alloc == SW'(s)), .fetch_ready(sl_ready[s]),
            .local_row(lrow), .window_count(wcount), .source_id(id_gid),
            .remote_needed(sl_remote[s]), .remote_die(rdie_unused), .kv_ok(sl_ok[s]),
            .re(1'b0), .rrow(10'd0), .relem(9'd0), .q(q_unused), .q_fp8(q8_unused),
            .packed_row(sl_row[s*2304 +: 2304]), .packed_valid(), .packed_local_row(plr),
            .packed_source_id(sl_src[s*POS_W +: POS_W]),
            .fault(sl_fault[s]), .fault_code(fc), .st_rows_fetched(nrows), .st_sectors_read(nsec),
            .m_v(sl_mv[s*4 +: 4]), .m_rdy(sl_mrdy[s*4 +: 4]), .m_addr(sl_maddr[s*4*HAW +: 4*HAW]),
            .m_len(len4), .m_tag(tag4), .m_we(mwe_unused), .m_wdata(mwd_unused), .m_wstrb(mws_unused),
            .m_wr_done(4'd0), .s_v(sl_sv[s*4 +: 4]), .s_rdy(srdy_unused),
            .s_tag(s_tag_slot), .s_beat(s_beat), .s_data(s_data));
        genvar k;
        for (k = 0; k < 4; k = k + 1) begin : g_t
            assign s_tag_slot[k*4 +: 4] = s_tag[k*TAGW +: 4];
            assign sl_mtag[(s*4 + k)*4 +: 4] = tag4[k*4 +: 4];
        end
    end endgenerate

    // ---- per-stack arbitration: first requesting slot at or after the oldest busy slot ----
    reg [SW-1:0] oldest;              // oldest busy slot (allocation order)
    reg [3:0] mv_r;
    reg [4*HAW-1:0] maddr_r;
    reg [4*TAGW-1:0] mtag_r;
    integer st, j, idx;
    reg found;
    always @(*) begin
        sl_mrdy = '0; mv_r = 0; maddr_r = 0; mtag_r = 0;
        for (st = 0; st < 4; st = st + 1) begin
            found = 1'b0;
            for (j = 0; j < NSLOT; j = j + 1) begin
                idx = (32'(oldest) + j) % NSLOT;
                if (!found && sl_mv[idx*4 + st]) begin
                    found = 1'b1;
                    mv_r[st] = 1'b1;
                    maddr_r[st*HAW +: HAW] = sl_maddr[(idx*4 + st)*HAW +: HAW];
                    mtag_r[st*TAGW +: TAGW] = {SW'(idx), sl_mtag[(idx*4 + st)*4 +: 4]};
                    sl_mrdy[idx*4 + st] = m_rdy[st];
                end
            end
        end
    end
    assign m_v = mv_r;
    assign m_addr = maddr_r;
    assign m_tag = mtag_r;

    // ---- response routing by the tag's slot field ----
    always @(*) begin
        sl_sv = '0;
        for (st = 0; st < 4; st = st + 1)
            if (s_v[st]) sl_sv[32'(s_tag[st*TAGW + 4 +: SW])*4 + st] = 1'b1;
    end

    // ---- output: oldest complete slot ----
    reg [SW-1:0] osel;
    reg ofound;
    always @(*) begin
        osel = 0; ofound = 1'b0;
        for (j = 0; j < NSLOT; j = j + 1) begin
            idx = (32'(oldest) + j) % NSLOT;
            if (!ofound && busy[idx] && sl_ok[idx]) begin ofound = 1'b1; osel = SW'(idx); end
        end
    end
    assign o_v = run && ofound;
    assign o_rank = srank[osel];
    assign o_gid = sl_src[osel*POS_W +: POS_W];
    assign o_row = sl_row[osel*2304 +: 2304];
    wire osend = o_v && o_ready;

    // oldest busy slot, after this cycle's retire / allocation
    reg [NSLOT-1:0] busy_n;
    reg [SW-1:0] oldest_n;
    reg ofd;
    always @(*) begin
        busy_n = busy;
        if (osend) busy_n[osel] = 1'b0;
        if (dispatch) busy_n[alloc] = 1'b1;
        oldest_n = alloc; ofd = 1'b0;
        // the oldest busy slot is the first busy one after the allocation pointer
        for (j = 0; j < NSLOT; j = j + 1) begin
            idx = (32'(dispatch ? SW'((32'(alloc) + 1) % NSLOT) : alloc) + j) % NSLOT;
            if (!ofd && busy_n[idx]) begin ofd = 1'b1; oldest_n = SW'(idx); end
        end
    end

`ifndef SYNTHESIS
    initial if (NSLOT < 1 || TAGW < SW + 4)
        $fatal(1, "selected CKV fetch parameter contract failed");
`endif
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            run <= 0; cur <= 0; wcount <= 0; alloc <= 0; busy <= 0; oldest <= 0;
            done <= 0; fault <= 0; fault_code <= 0; st_owned_rows <= 0;
        end else begin
            if (|sl_fault) begin fault <= 1; fault_code[0] <= 1; end
            if (|sl_remote) begin fault <= 1; fault_code[1] <= 1; end
            if (job_v && !run) begin
                run <= 1; cur <= 0; wcount <= window_count; done <= 0;
                st_owned_rows <= 0;
            end else if (run) begin
                if (dispatch) begin
                    srank[alloc] <= id_rank_in;
                    alloc <= SW'((32'(alloc) + 1) % NSLOT);
                    st_owned_rows <= st_owned_rows + 1;
                end
                if (dispatch || skip) cur <= cur + 1'b1;
                busy <= busy_n;
                oldest <= oldest_n;
                if (cur == id_count && id_done && busy_n == 0 && !dispatch) begin
                    run <= 0; done <= 1;
                end
            end
        end
    end
endmodule

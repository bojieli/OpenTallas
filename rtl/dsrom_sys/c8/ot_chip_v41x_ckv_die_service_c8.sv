`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Selected compressed-KV row service of one DeepSeek-V4.1 die (tensor group 4),
// the CKV_SELECTED path of ot_chip_v41x_die (rtl/chip/ckvsel/).
//
// Replaces the program's selected-row gather (SU a_ind = IND_O into KV/KVT,
// a_base 0, a_so 512: "read global compressed rows by id", W17 contract) with:
//   ids     on sel_v (the gather's issue), read the n_sel = K global ids (u32,
//           ascending, 16 a 512-bit word) from the vector memory at word
//           sel_vmword through the VM read port (vm_re/vm_raddr -> vm_rq one
//           cycle later; the die lends it the collective DMA's idle xb port)
//           into ot_chip_v41x_ckv_sel_ids (owned-rank list of DIE_ID);
//   own row the position's new compressed row (global id = its QDQ4E element
//           address / 512) is captured from the core's QE QDQ4E writes
//           (nw_we/nw_addr/nw_data, 32 BF16-in-FP32 elements a beat) and
//           re-encoded exactly to E2M1 codes + E4M3 scales
//           (ot_chip_v41x_ckv_row_encoder).  If it is selected (it is the
//           largest id, so rank K-1) every die takes it locally; it is never
//           fetched.  The owner die (id[5:4] == DIE_ID) also WRITES it to its
//           HBM home (stack id[7:6], sectors CKV_BASE + 9 * local + k) so a later
//           position can select it (the K client's write port);
//   fetch   ot_chip_v41x_ckv_sel_fetch on the die's spare K client (four stack
//           ports, tags in the low 14 bits), the owned rows only, rows in any
//           order, once the id table is complete;
//   gather  each fetched row is broadcast to the other three dies (ag_tx_*)
//           and written locally; rows from the other dies arrive on ag_rx_*
//           (always accepted);
//   collect a rank-addressed row buffer (the selected part of the attention
//           staging), every write checked against the id table;
//   stream  per attention descriptor (job_v), ranks 0 .. K-1 leave in order
//           through ot_chip_v41x_ckv_stream_merge as the engine's four-row FP4
//           beats (kv_v/kv_ready/kv_m/kv_w).  The die streams the 128 window
//           rows first; the QK and the PV descriptor each replay the buffer
//           (no second HBM fetch).
// A step's buffer is valid from its sel_v until the next sel_v.
// Faults (sticky): {encoder, id table, fetch, collect order/id, merger, VM ids}.
// ---------------------------------------------------------------------------
module ot_chip_v41x_ckv_die_service_c8 #(
    parameter integer C8_PUBLICATION=0,
    parameter integer DIE_ID = 0,
    parameter integer K = 512,
    parameter integer POS_W = 21,
    parameter integer AW = 30,              // core element address width
    parameter integer VWA = 15,             // VM word address width
    parameter integer HAW = 30,             // HBM sector address
    parameter integer TAGW = 16,
    parameter integer CKV_BASE = 1 << 22,
    parameter integer CKV_SECTORS = 1 << 21,
    parameter integer NSLOT = 64,
    parameter integer KW = $clog2(K + 1)
) (
    input  wire               clk,
    input  wire               rst_n,
    // core
    input  wire               sel_v,
    input  wire [VWA-1:0]     sel_vmword,
    input  wire               nw_we,
    input  wire [AW-1:0]      nw_addr,
    input  wire [1023:0]      nw_data,
    // VM read (one-cycle latency)
    output wire               vm_re,
    output wire [VWA-1:0]     vm_raddr,
    input  wire [511:0]       vm_rq,
    output wire               vm_busy,
    // K client (ot_chip_v41x_kv_rope_reqmux c_*)
    output wire [3:0]         c_v,
    input  wire [3:0]         c_rdy,
    output wire [4*HAW-1:0]   c_addr,
    output wire [15:0]        c_len,
    output wire [4*TAGW-1:0]  c_tag,
    output wire [3:0]         c_we,
    output wire [1023:0]      c_wdata,
    output wire [127:0]       c_wstrb,
    input  wire [3:0]         c_wr_done,
    input  wire [3:0]         c_sv,
    output wire [3:0]         c_srdy,
    input  wire [4*TAGW-1:0]  c_stag,
    input  wire [15:0]        c_sbeat,
    input  wire [1023:0]      c_sdata,
    // all-gather
    output wire               ag_tx_valid,
    input  wire               ag_tx_ready,
    output wire [KW-1:0]      ag_tx_rank,
    output wire [POS_W-1:0]   ag_tx_gid,
    output wire [2303:0]      ag_tx_row,
    input  wire [2:0]         ag_rx_valid,
    input  wire [3*KW-1:0]    ag_rx_rank,
    input  wire [3*POS_W-1:0] ag_rx_gid,
    input  wire [3*2304-1:0]  ag_rx_row,
    // attention
    input  wire               job_v,
    output wire               job_ready,
    output wire               kv_v,
    input  wire               kv_ready,
    output wire [3:0]         kv_m,
    output wire [4*16*265-1:0] kv_w,
    output wire               job_done,
    // status
    output reg                fault,
    output reg  [5:0]         fault_code,
    output wire               rows_ready,     // all K ranks present
    output reg  [31:0]        st_rows_local,
    output reg  [31:0]        st_rows_remote,
    output reg  [31:0]        st_cycles_to_ready,
    input wire [46:0] position_identity,
    output reg own_visible_v,
    output reg [46:0] own_visible_identity,
    output reg [POS_W-1:0] own_visible_gid,
    output wire own_pending,
    output wire reuse_ready
);
    localparam integer NWORD = K / 16;
    // ---------------- ids: VM read -> table ----------------
    reg rd_act;
    reg [VWA-1:0] rd_ptr;
    reg [$clog2(NWORD+1)-1:0] rd_cnt;
    reg rq_v, rq_last;
    reg [1:0] tail;                      // empty beats for quarters 1..3
    reg id_clr;
    assign vm_re = rd_act;
    assign vm_raddr = rd_ptr;
    assign vm_busy = rd_act || rq_v;
    reg [3:0] s_valid, s_last;
    reg [4*16-1:0] s_lv;
    reg [4*16*20-1:0] s_idx;
    integer l;
    always @(*) begin
        s_valid = 0; s_last = 0; s_lv = 0; s_idx = 0;
        if (rq_v) begin
            s_valid[0] = 1'b1; s_last[0] = rq_last; s_lv[15:0] = 16'hffff;
            for (l = 0; l < 16; l = l + 1) s_idx[l*20 +: 20] = vm_rq[32*l +: 20];
        end else if (tail != 0) begin
            s_valid[tail] = 1'b1; s_last[tail] = 1'b1;
        end
    end
    reg [3:0] id_hi_bad;
    always @(*) begin
        id_hi_bad = 0;
        for (l = 0; l < 16; l = l + 1) if (vm_rq[32*l + 20 +: 12] != 0) id_hi_bad[0] = 1'b1;
    end
    wire [KW-1:0] id_count; wire id_done; wire [31:0] id_dc;
    wire [5*KW-1:0] rd_rank;
    wire [5*POS_W-1:0] rd_gid;
    wire [9:0] rd_die_u, rd_stack_u; wire [5*POS_W-1:0] rd_local_u;
    wire [4*KW-1:0] own_count, own_rank; wire [4*POS_W-1:0] own_gid; wire [KW-1:0] own_idx;
    wire id_fault; wire [3:0] id_fc; wire [3:0] s_ready;
    ot_chip_v41x_ckv_sel_ids #(.K(K), .POS_W(POS_W), .NRD(5), .OWN(4'b1 << DIE_ID)) u_ids (
        .clk(clk), .rst_n(rst_n), .clr(id_clr), .exp_n(KW'(K)),
        .s_valid(s_valid), .s_ready(s_ready), .s_last(s_last), .s_lv(s_lv), .s_idx(s_idx),
        .count(id_count), .done(id_done), .done_cycle_count(id_dc),
        .rd_rank(rd_rank), .rd_gid(rd_gid), .rd_die(rd_die_u), .rd_stack(rd_stack_u), .rd_local(rd_local_u),
        .own_count(own_count), .own_idx({4{own_idx}}), .own_rank(own_rank), .own_gid(own_gid),
        .fault(id_fault), .fault_code(id_fc));

    // ---------------- own row: QDQ4E capture -> encoder ----------------
    reg [8191:0] nw_vals;
    reg [15:0] nw_got;
    reg [POS_W-1:0] nw_gid;
    reg nw_have, nw_bad;
    wire [AW-1:0] nw_off = nw_addr - (AW'(nw_gid) << 9);
    wire enc_busy, enc_ov, enc_fault;
    wire [2303:0] enc_row;
    reg enc_go, enc_done;
    reg [2303:0] new_row;
    ot_chip_v41x_ckv_row_encoder u_enc (.clk(clk), .rst_n(rst_n), .ld_v(enc_go), .vals(nw_vals),
        .busy(enc_busy), .o_v(enc_ov), .o_row(enc_row), .o_fault(enc_fault));

    // ---------------- step state ----------------
    reg step;                           // a selection is loaded / loading
    reg go;                             // table complete and own row encoded: fetch, gather
    wire [POS_W-1:0] last_gid = rd_gid[4*POS_W +: POS_W];    // rank K-1 (port 4 address below)
    wire new_sel = go && last_gid == nw_gid;                 // the own row is selected (rank K-1)
    wire new_owned = nw_gid[5:4] == 2'(DIE_ID);
    wire [KW-1:0] fetch_count = own_count[DIE_ID*KW +: KW] - KW'(new_sel && new_owned);

    // ---------------- fetch (owned rows) ----------------
    wire f_ready, f_ov, f_done, f_fault; wire [1:0] f_fc;
    wire [KW-1:0] f_rank, f_idx; wire [POS_W-1:0] f_gid; wire [2303:0] f_row;
    wire [31:0] f_owned;
    wire [3:0] f_mv; wire [3:0] f_mrdy; wire [4*HAW-1:0] f_maddr;
    localparam integer FSW = (NSLOT > 1) ? $clog2(NSLOT) : 1;
    localparam integer FTW = FSW + 4;
    wire [4*FTW-1:0] f_mtag;
    wire [4*FTW-1:0] f_stag;
    reg f_job;
    assign own_idx = f_idx;
    ot_chip_v41x_ckv_sel_fetch #(.DIE_ID(DIE_ID), .NSLOT(NSLOT), .POS_W(POS_W), .SEC_W(HAW), .HAW(HAW), .K(K)) u_fetch (
        .clk(clk), .rst_n(rst_n), .job_v(f_job), .job_ready(f_ready),
        .window_count(8'd128), .published_source_count(POS_W'((1 << POS_W) - 1)),
        .region_base_sector({4{HAW'(CKV_BASE)}}), .region_sector_count({4{HAW'(CKV_SECTORS)}}),
        .id_count(go ? fetch_count : KW'(0)), .id_done(go), .id_idx(f_idx),
        .id_rank_in(own_rank[DIE_ID*KW +: KW]), .id_gid(own_gid[DIE_ID*POS_W +: POS_W]),
        .id_die(own_gid[DIE_ID*POS_W + 4 +: 2]),
        .o_v(f_ov), .o_ready(ag_tx_ready), .o_rank(f_rank), .o_gid(f_gid), .o_row(f_row),
        .done(f_done), .fault(f_fault), .fault_code(f_fc), .st_owned_rows(f_owned),
        .m_v(f_mv), .m_rdy(f_mrdy), .m_addr(f_maddr), .m_tag(f_mtag),
        .s_v(c_sv), .s_tag(f_stag), .s_beat(c_sbeat), .s_data(c_sdata));
    assign ag_tx_valid = f_ov;
    assign ag_tx_rank = f_rank;
    assign ag_tx_gid = f_gid;
    assign ag_tx_row = f_row;

    // ---------------- owner write of the own row (9 sectors), then the fetch's reads ----------------
    reg wr_act;
    reg wr_pending;reg [46:0] own_identity;
    assign own_pending=wr_act || wr_pending;
    assign reuse_ready=rst_n && !fault && f_ready && !f_ov && !f_job && !rel_on && !rd_act && !rq_v && tail==0 && !own_pending && !enc_busy && !enc_go && !nw_have && nw_got==0 && !new_sel_pulse && !sel_v && !nw_we;
    reg [3:0] wr_k;
    wire [1:0] wr_stack = nw_gid[7:6];
    wire [POS_W-1:0] nw_local = ((nw_gid >> 8) << 4) | POS_W'(nw_gid[3:0]);
    genvar st;
    generate for (st = 0; st < 4; st = st + 1) begin : g_c
        wire w_this = wr_act && wr_stack == 2'(st) && (!C8_PUBLICATION || !wr_pending);
        assign c_v[st] = w_this ? 1'b1 : f_mv[st];
        assign f_mrdy[st] = w_this ? 1'b0 : c_rdy[st];
        assign c_addr[st*HAW +: HAW] = w_this ? HAW'(CKV_BASE + 9 * nw_local + wr_k) : f_maddr[st*HAW +: HAW];
        assign c_len[st*4 +: 4] = 4'd1;
        assign c_tag[st*TAGW +: TAGW] = w_this ? TAGW'(0) : TAGW'(f_mtag[st*FTW +: FTW]);
        assign c_we[st] = w_this;
        assign c_wdata[st*256 +: 256] = new_row[256*wr_k +: 256];
        assign c_wstrb[st*32 +: 32] = {32{1'b1}};
        assign f_stag[st*FTW +: FTW] = c_stag[st*TAGW +: FTW];
        assign c_srdy[st] = 1'b1;
    end endgenerate

    // ---------------- collector: rank-addressed buffer with replay ----------------
    reg [2303:0] buf_row [0:K-1];
    reg [K-1:0] present;
    reg [KW:0] npresent;
    // sources: 0 local fetch, 1..3 remote, 4 own row
    wire [4:0] wv = {new_sel_pulse, ag_rx_valid, f_ov && ag_tx_ready};
    reg new_sel_pulse;
    wire [5*KW-1:0] wrank = {KW'(K - 1), ag_rx_rank, f_rank};
    wire [5*POS_W-1:0] wgid = {nw_gid, ag_rx_gid, f_gid};
    wire [5*2304-1:0] wrow = {new_row, ag_rx_row, f_row};
    assign rd_rank = wrank;
    integer i, j;
    reg dup, oor, gidbad;
    reg [2:0] nwr;
    always @(*) begin
        dup = 0; oor = 0; gidbad = 0; nwr = 0;
        for (i = 0; i < 5; i = i + 1) if (wv[i]) begin
            nwr = nwr + 1'b1;
            if (wrank[i*KW +: KW] >= KW'(K)) oor = 1'b1;
            else if (present[wrank[i*KW +: KW]]) dup = 1'b1;
            if (wgid[i*POS_W +: POS_W] != rd_gid[i*POS_W +: POS_W]) gidbad = 1'b1;
            for (j = 0; j < i; j = j + 1)
                if (wv[j] && wrank[j*KW +: KW] == wrank[i*KW +: KW]) dup = 1'b1;
        end
    end
    assign rows_ready = npresent == (KW+1)'(K);
    // release to the merger: up to four consecutive present ranks a cycle
    reg [KW-1:0] rel;
    reg rel_on;
    wire [2:0] c_take;
    reg [2:0] c_n;
    always @(*) begin
        c_n = 0;
        if (rel_on) begin
            for (i = 0; i < 4; i = i + 1)
                if (c_n == 3'(i) && 32'(rel) + i < K && present[32'(rel) + i]) c_n = c_n + 1'b1;
        end
    end
    wire [4*2304-1:0] c_rows;
    genvar gr;
    generate for (gr = 0; gr < 4; gr = gr + 1) begin : g_rel
        assign c_rows[gr*2304 +: 2304] = buf_row[KW'(32'(rel) + gr)];
    end endgenerate
    wire m_jready, m_done, m_fault; wire [1:0] m_fc;
    ot_chip_v41x_ckv_stream_merge #(.K(K)) u_merge (
        .clk(clk), .rst_n(rst_n), .job_v(job_v && rel_ok), .job_ready(m_jready),
        .window_count(8'd0), .n_sel(KW'(K)),
        .w_v(1'b0), .w_ready(), .w_m(4'd0), .w_rows('0),
        .c_n(c_n), .c_take(c_take), .c_rank(rel), .c_rows(c_rows),
        .kv_v(kv_v), .kv_ready(kv_ready), .kv_m(kv_m), .kv_w(kv_w),
        .done(m_done), .fault(m_fault), .fault_code(m_fc));
    wire rel_ok = step && m_jready && !rel_on && (!C8_PUBLICATION || (rows_ready && !own_pending));
    assign job_ready = rel_ok;
    assign job_done = m_done;

    reg [31:0] cyc;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            rd_act <= 0; rd_ptr <= 0; rd_cnt <= 0; rq_v <= 0; rq_last <= 0; tail <= 0; id_clr <= 0;
            nw_got <= 0; nw_gid <= 0; nw_have <= 0; nw_bad <= 0; enc_go <= 0; enc_done <= 0;
            wr_pending<=0;own_visible_v<=0;own_visible_identity<=0;own_visible_gid<=0;own_identity<=0;
            step <= 0; go <= 0; f_job <= 0; wr_act <= 0; wr_k <= 0;
            present <= 0; npresent <= 0; new_sel_pulse <= 0; rel <= 0; rel_on <= 0;
            fault <= 0; fault_code <= 0; st_rows_local <= 0; st_rows_remote <= 0; st_cycles_to_ready <= 0; cyc <= 0;
        end else begin
            id_clr <= 1'b0; f_job <= 1'b0; enc_go <= 1'b0; new_sel_pulse <= 1'b0;
            cyc <= cyc + 1;own_visible_v<=0;
            // own-row capture: the step's first QDQ4E row (16 beats of 32 elements)
            if (nw_we) begin
                if (!nw_have && nw_got == 0) begin
                    nw_gid <= POS_W'(nw_addr >> 9);own_identity<=position_identity;
                    if (nw_addr[8:5] != 0 || nw_addr[4:0] != 0) nw_bad <= 1'b1;
                    nw_vals[0 +: 512] <= {nw_data[1023:1008], nw_data[991:976], nw_data[959:944], nw_data[927:912],
                                          nw_data[895:880], nw_data[863:848], nw_data[831:816], nw_data[799:784],
                                          nw_data[767:752], nw_data[735:720], nw_data[703:688], nw_data[671:656],
                                          nw_data[639:624], nw_data[607:592], nw_data[575:560], nw_data[543:528],
                                          nw_data[511:496], nw_data[479:464], nw_data[447:432], nw_data[415:400],
                                          nw_data[383:368], nw_data[351:336], nw_data[319:304], nw_data[287:272],
                                          nw_data[255:240], nw_data[223:208], nw_data[191:176], nw_data[159:144],
                                          nw_data[127:112], nw_data[95:80], nw_data[63:48], nw_data[31:16]};
                    nw_got <= 16'd1;
                end else if (!nw_have) begin
                    if (nw_off >= AW'(512) || nw_off[4:0] != 0 || nw_got[nw_off[8:5]]) nw_bad <= 1'b1;
                    else begin
                        for (i = 0; i < 32; i = i + 1)
                            nw_vals[512*nw_off[8:5] + 16*i +: 16] <= nw_data[32*i + 16 +: 16];
                        nw_got <= nw_got | (16'd1 << nw_off[8:5]);
                        if ((nw_got | (16'd1 << nw_off[8:5])) == 16'hffff) begin nw_have <= 1'b1; enc_go <= 1'b1; end
                    end
                end
            end
            if (enc_ov) begin enc_done <= 1'b1; new_row <= enc_row; if (enc_fault) begin fault <= 1; fault_code[5] <= 1; end end
            // a new selection: clear the step, read the ids
            if (sel_v && !rd_act) begin
                step <= 1; go <= 0; id_clr <= 1; rd_act <= 1; rd_ptr <= sel_vmword; rd_cnt <= 0;
                present <= 0; npresent <= 0; rel_on <= 0; tail <= 0;
                st_rows_local <= 0; st_rows_remote <= 0; cyc <= 0;
            end else if (rd_act) begin
                rd_ptr <= rd_ptr + 1'b1; rd_cnt <= rd_cnt + 1'b1;
                if (32'(rd_cnt) == NWORD - 1) rd_act <= 0;
            end
            rq_v <= rd_act; rq_last <= rd_act && 32'(rd_cnt) == NWORD - 1;
            if (rq_v && id_hi_bad[0]) begin fault <= 1; fault_code[0] <= 1; end
            if (rq_v && rq_last) tail <= 2'd1;
            else if (tail != 0 && !rq_v && s_ready[tail]) tail <= (tail == 2'd3) ? 2'd0 : tail + 1'b1;
            if (id_fault) begin fault <= 1; fault_code[4] <= 1; end
            // start: table complete and own row encoded
            if (step && !go && id_done && enc_done) begin
                go <= 1; f_job <= 1; nw_got <= 0; nw_have <= 0; enc_done <= 0;
                if (new_owned) begin wr_act <= 1; wr_k <= 0; end
            end
            if (go && !new_sel_pulse && !present[K-1] && last_gid == nw_gid && !new_sel_done) new_sel_pulse <= 1'b1;
            // owner write (granted one sector a cycle)
            if (!C8_PUBLICATION) begin
                if (wr_act && c_rdy[wr_stack]) begin
                    if (wr_k == 4'd8) wr_act<=0; else wr_k<=wr_k+1'b1;
                end
            end else begin
                if (wr_act && !wr_pending && c_rdy[wr_stack]) wr_pending<=1;
                if (wr_act && wr_pending && c_wr_done[wr_stack]) begin
                    wr_pending<=0;
                    if (wr_k==4'd8) begin
                        wr_act<=0;own_visible_v<=1;own_visible_identity<=own_identity;own_visible_gid<=nw_gid;
                    end else wr_k<=wr_k+1'b1;
                end
            end
            if (f_fault) begin fault <= 1; fault_code[3] <= 1; end
            // collector writes
            if (dup || oor || gidbad) begin fault <= 1; fault_code[2] <= 1; end
            for (i = 0; i < 5; i = i + 1)
                if (wv[i] && wrank[i*KW +: KW] < KW'(K)) begin
                    buf_row[wrank[i*KW +: KW]] <= wrow[i*2304 +: 2304];
                    present[wrank[i*KW +: KW]] <= 1'b1;
                end
            if (C8_PUBLICATION && sel_v && !rd_act) npresent <= 0;
            else npresent <= npresent + (KW+1)'(nwr);
            if (wv[0]) st_rows_local <= st_rows_local + 1;
            st_rows_remote <= st_rows_remote + 32'(ag_rx_valid[0]) + 32'(ag_rx_valid[1]) + 32'(ag_rx_valid[2]);
            if (!rows_ready && npresent + (KW+1)'(nwr) == (KW+1)'(K)) st_cycles_to_ready <= cyc;
            // release per attention job: rewind for every descriptor (QK, then PV)
            if (job_v && rel_ok) begin rel_on <= 1; rel <= 0; end
            else if (rel_on) begin
                rel <= rel + KW'(c_take);
                if (m_done) rel_on <= 0;
            end
            if (m_fault) begin fault <= 1; fault_code[1] <= 1; end
            if (nw_bad) begin fault <= 1; fault_code[5] <= 1; end
        end
    end
    reg new_sel_done;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) new_sel_done <= 0;
        else if (sel_v) new_sel_done <= 0;
        else if (new_sel_pulse) new_sel_done <= 1;
endmodule

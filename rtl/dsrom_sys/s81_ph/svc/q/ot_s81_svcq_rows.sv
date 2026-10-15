`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// CLAUDE s81-svcq-1011: selected-CKV row assembler of an S81 scan-service slab (successor in function of
// ot_chip_v41x_ckv_sel_collect, rtl/chip/, unchanged; same in-order output port so ot_chip_v41x_ckv_stream_merge
// consumes it unchanged).
//
// Exactness rule (ot_s81ph_col.sv DECISION): no arithmetic crosses slabs.  Slab ST of die DIE_ID
//   HOLDS   selected rows whose owner stack id[7:6] == ST (any die): q.k over the full 512 dims runs here, and only
//           here, for those rows (their score words leave this slab);
//   OWNS    p.v dims 128 ST .. 128 ST + 127 = chunk pairs 2 ST, 2 ST + 1 of every row: p.v over ALL T rows in the
//           golden's row order runs here for those dims.
// So a staged row is COMPLETE when it is held and all eight chunk pairs are present, or not held and its two owned
// pairs are present; the other pairs of a non-held row are zero (the engine computes on them; nothing derived from
// them leaves the slab).  Row sources:
//   table   SEL_IDS words: the job's selection ids in rank order (16 a word); each entry owned by (DIE_ID, ST) is
//           appended to the OWN list read by ot_s81_svcq_selfetch (local HBM rows);
//   local   whole 2,304-bit rows from the fetch (rank, id);
//   remote  ROWS words: one chunk pair (288 b: 256 b of E2M1 nibbles + 32 b of E4M3 scales) of rank r with its id.
// Every write is checked against the table: rank < n_sel, table entry written, id equal, the pair (row) not already
// present; a remote word for a row this slab fetches itself, or for a pair the slab does not need, is a contract
// violation.  Violations latch fault (sticky) and the word is dropped (fail closed).
// Row format (2,304-bit DMA row): 512 E2M1 nibbles (element e at 4e), 32 E4M3 scales at 2048 + 8k (one per 16).
// Pair j: nibbles [256 j +: 256], scales [2048 + 32 j +: 32].
// ---------------------------------------------------------------------------
module ot_s81_svcq_rows #(
    parameter integer DIE_ID = 0,
    parameter integer ST = 0,
    parameter integer K = 512,
    parameter integer POS_W = 21,
    parameter integer NOUT = 4,
    parameter integer KW = $clog2(K + 1)
) (
    input  wire                   clk,
    input  wire                   rst_n,
    input  wire                   clr,
    input  wire [KW-1:0]          exp_n,
    // table
    input  wire                   t_v,
    input  wire [KW-1:0]          t_rank,
    input  wire [4:0]             t_n,           // 1..16 entries
    input  wire [16*32-1:0]       t_ids,
    // own list (registered read)
    output reg  [KW-1:0]          own_count,
    output wire                   own_done,
    input  wire [KW-1:0]          own_idx,
    output reg  [KW-1:0]          own_rank,
    output reg  [POS_W-1:0]       own_gid,
    // local whole rows
    input  wire                   l_v,
    input  wire [KW-1:0]          l_rank,
    input  wire [POS_W-1:0]       l_gid,
    input  wire [2303:0]          l_row,
    // remote pairs
    input  wire                   r_v,
    input  wire [KW-1:0]          r_rank,
    input  wire [POS_W-1:0]       r_gid,
    input  wire [2:0]             r_pair,
    input  wire [287:0]           r_data,
    // held map (score emission)
    output wire [K-1:0]           held,
    // in-order output (ot_chip_v41x_ckv_sel_collect port)
    output reg  [2:0]             o_n,
    input  wire [2:0]             o_take,
    output wire [KW-1:0]          o_rank,
    output wire [NOUT*2304-1:0]   o_row,
    output reg                    done,
    output reg                    fault,
    output reg  [5:0]             fault_code     // {take, unneeded/own remote, dup, id, range, table}
);
    reg [POS_W-1:0] tab [0:K-1];
    reg [K-1:0] tw, hld;
    reg [7:0] pv [0:K-1];
    reg [2303:0] buf_row [0:K-1];
    reg [KW-1:0] nexp, rd, nt;
    reg [KW-1:0] own_r [0:K-1];
    reg [POS_W-1:0] own_g [0:K-1];
    assign held = hld;
    assign o_rank = rd;
    assign own_done = (nt == nexp);

    function automatic bit complete(input integer r);
        complete = tw[r] && (hld[r] ? (pv[r] == 8'hff) : (pv[r][2*ST] && pv[r][2*ST+1]));
    endfunction
    integer oj;
    reg ostop;
    always @(*) begin
        o_n = 0; ostop = 1'b0;
        for (oj = 0; oj < NOUT; oj = oj + 1)
            if (!ostop && !done && 32'(rd) + oj < 32'(nexp) && complete(32'(rd) + oj)) o_n = o_n + 1'b1;
            else ostop = 1'b1;
    end
    genvar go;
    generate for (go = 0; go < NOUT; go = go + 1) begin : g_o
        wire [KW-1:0] ra = rd + KW'(go);
        wire [2303:0] rw = buf_row[ra];
        wire [7:0] rp = pv[ra];
        genvar gp;
        for (gp = 0; gp < 8; gp = gp + 1) begin : g_p    // absent pairs leave as zero (never stale data)
            assign o_row[go*2304 + 256*gp +: 256] = rp[gp] ? rw[256*gp +: 256] : 256'b0;
            assign o_row[go*2304 + 2048 + 32*gp +: 32] = rp[gp] ? rw[2048 + 32*gp +: 32] : 32'b0;
        end
    end endgenerate

    wire [POS_W-1:0] own_mask = POS_W'(8'hf0);
    integer i, j;
    reg [KW:0] na;
    reg [31:0] id;
    reg lbad, rbad;
    always @(posedge clk) begin
        own_rank <= own_r[own_idx];
        own_gid <= own_g[own_idx];
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            tw <= 0; hld <= 0; nexp <= 0; rd <= 0; nt <= 0; own_count <= 0; done <= 0; fault <= 0; fault_code <= 0;
            for (i = 0; i < K; i = i + 1) pv[i] <= 0;
        end else if (clr) begin
            tw <= 0; hld <= 0; nexp <= exp_n; rd <= 0; nt <= 0; own_count <= 0; done <= (exp_n == 0);
            for (i = 0; i < K; i = i + 1) pv[i] <= 0;
        end else begin
            // table words (in rank order, contiguous)
            if (t_v) begin
                if (t_rank != nt || t_n == 0 || t_n > 5'd16 || 32'(t_rank) + 32'(t_n) > 32'(nexp)) begin
                    fault <= 1; fault_code[0] <= 1;
                end else begin
                    na = (KW+1)'(own_count);
                    for (j = 0; j < 16; j = j + 1) if (j < t_n) begin
                        id = t_ids[32*j +: 32];
                        if (id >= (32'd1 << POS_W)) begin fault <= 1; fault_code[0] <= 1; end
                        tab[32'(t_rank) + j] <= POS_W'(id);
                        tw[32'(t_rank) + j] <= 1'b1;
                        hld[32'(t_rank) + j] <= id[7:6] == 2'(ST);
                        if (id[5:4] == 2'(DIE_ID) && id[7:6] == 2'(ST)) begin
                            own_r[na[KW-1:0]] <= KW'(32'(t_rank) + j);
                            own_g[na[KW-1:0]] <= POS_W'(id);
                            na = na + 1'b1;
                        end
                    end
                    own_count <= na[KW-1:0];
                    nt <= KW'(32'(t_rank) + 32'(t_n));
                end
            end
            // local whole row
            if (l_v) begin
                lbad = 1'b0;
                if (l_rank >= nexp || !tw[l_rank]) begin lbad = 1'b1; fault <= 1; fault_code[1] <= 1; end
                else if (l_gid != tab[l_rank] || l_gid[5:4] != 2'(DIE_ID) || l_gid[7:6] != 2'(ST)) begin
                    lbad = 1'b1; fault <= 1; fault_code[2] <= 1;
                end else if (pv[l_rank] != 0) begin lbad = 1'b1; fault <= 1; fault_code[3] <= 1; end
                if (!lbad) begin buf_row[l_rank] <= l_row; pv[l_rank] <= 8'hff; end
            end
            // remote pair
            if (r_v) begin
                rbad = 1'b0;
                if (r_rank >= nexp || !tw[r_rank]) begin rbad = 1'b1; fault <= 1; fault_code[1] <= 1; end
                else if (r_gid != tab[r_rank]) begin rbad = 1'b1; fault <= 1; fault_code[2] <= 1; end
                else if ((r_gid[5:4] == 2'(DIE_ID) && r_gid[7:6] == 2'(ST)) ||
                         (!hld[r_rank] && r_pair[2:1] != 2'(ST))) begin rbad = 1'b1; fault <= 1; fault_code[4] <= 1; end
                else if (pv[r_rank][r_pair] || (l_v && !lbad && l_rank == r_rank)) begin
                    rbad = 1'b1; fault <= 1; fault_code[3] <= 1;
                end
                if (!rbad) begin
                    buf_row[r_rank][256*r_pair +: 256] <= r_data[255:0];
                    buf_row[r_rank][2048 + 32*r_pair +: 32] <= r_data[287:256];
                    pv[r_rank][r_pair] <= 1'b1;
                end
            end
            if (o_take > o_n) begin fault <= 1; fault_code[5] <= 1; end
            else if (o_take != 0) begin
                rd <= rd + KW'(o_take);
                if (rd + KW'(o_take) == nexp) done <= 1;
            end
        end
    end
endmodule

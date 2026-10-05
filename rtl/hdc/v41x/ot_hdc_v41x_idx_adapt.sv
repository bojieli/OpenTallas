`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// INDEXER ADAPTER of the re-specified V4.1 decode core (ot_hdc_core_v41x, ME
// slot engine 3), and the index-key WRITER that keeps the key image in HBM.
//
// THE OP.  The FUSED indexer op (tools/hdc_program_v41.py Builder(idx_fused),
// ISA field me_fuse; tools/hdc_isa_v41.py): a KV-sourced ME op on the index
// keys that computes, per key row r < n (n = me_nout + DYN, me_mmode = 1),
//     IS[r] = to_bf16(csum_hh to_bf16(relu(to_bf16(dot(q[hh], key[r]))) * wts[hh]))
// over the 2^me_hg * IL index heads hh = h*IL + j, q[hh] at vector-memory
// elements xbase + h*xcs + j*xjs + k*xks (BF16), wts[hh] at me_wts + hh,
// written as element obase*16 + r.  This is exactly the golden's indexer
// score (hdc_golden_v41.Model.indexer under R-ARITH class "idx": the block
// dot, 7 sequential adds over each 8-head chunk, the 2-level chunk tree) and
// the unit that computes it is the indexer engine ot_hdc_v41x_idx_engine
// (NK keys a cycle, the head sum fused).
//
// KEY SOURCE: HBM.  The keys are not read from the KV SRAM: they stream from
// the die's HBM through ot_hdc_v41x_idx_kstream (one stack, 32 pseudo-
// channels, the refresh-aware controller of the HBM model outside) in the
// lossless 68-B format (128 E2M1 codes + 4 UE8M0 scales per key, 1,024-key
// super-blocks of 17 4-KB blocks).  The reduced vehicle's keys are 32-dim:
// codes 0..31 and scale byte 0 of each 68-B record; the rest is zero and the
// engine is built with NB = 1 (one 32-block per head).
// The key array of the index-key KV region at word base wb sits at HBM block
// (wb - cfg_ik_base) / 128 * 17 (every IK region is a multiple of 128 KV words
// from cfg_ik_base, so the arrays never overlap; tools/hdc_images_v41x.py
// builds the same map and asserts it).
//
// KEY WRITER (ot_hdc_v41x_idx_kwr, below).  The program writes each new index
// key into the KV SRAM with a transposed-KV stream op (dst = KVT, o_base the
// region, o_row the key row).  The writer latches that op at issue, collects
// its 32 BF16 elements from the KV write lanes, re-encodes them exactly
// (FP4 E2M1 + UE8M0, below) and emits the record's two HBM sector writes
// (codes; the scale byte in the super-block's scale block).  The HBM model of
// the bench is read-only, so the bench applies them through its backdoor
// (rtl/test/tb_hdc_core_v41x.sv); write timing is not modelled.
//
// RE-ENCODING (q, keys).  A QDQ4 block's BF16 values encode exactly: scale
// byte u = Emax - 2 (Emax the largest biased exponent of a nonzero element),
// code from (E - Emax + 2, top mantissa bit).  An element that does not
// encode faults (the op or the key write).
//
// DATAFLOW.  QLOAD: the q elements and the head weights through the G vector-
// memory x ports.  QL: one head a cycle into the engine's q registers, while
// the key stream is commanded.  RUN: key beats (16 keys) from the stream into
// the engine, score beats (NK = 16 keys, one vector-memory word) out.
// ---------------------------------------------------------------------------
module ot_hdc_v41x_idx_adapt #(
    parameter integer W    = 16,
    parameter integer G    = 4,
    parameter integer IL   = 8,
    parameter integer AW   = 24,
    parameter integer NW   = 16,
    parameter integer MP   = 1,
    parameter integer IH   = 32,           // index heads (the engine's)
    parameter integer NPC  = 32,           // HBM pseudo-channels
    parameter integer HAW  = 28,           // HBM sector address
    parameter integer HLENW = 4,
    parameter integer HTAGW = 16,
    parameter integer HBEATW = 4
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              go,
    output wire              ready,
    output reg               idle,
    input  wire [AW-1:0]     cfg_ik_base,
    input  wire [NW-1:0]     i_nout,
    input  wire [NW-1:0]     i_k,
    input  wire [AW-1:0]     i_wbase,
    input  wire [AW-1:0]     i_xbase,
    input  wire [AW-1:0]     i_xks,
    input  wire [AW-1:0]     i_xjs,
    input  wire [AW-1:0]     i_xcs,
    input  wire [1:0]        i_hg,
    input  wire              i_round,
    input  wire [AW-1:0]     i_obase,
    input  wire              i_mmode,
    input  wire              i_oen,
    input  wire              i_fuse,
    input  wire [AW-1:0]     i_wts,
    // vector memory x reads (copy 0's G ports)
    output reg  [MP*G-1:0]   x_re,
    output reg  [MP*G*AW-1:0] x_addr,
    input  wire [MP*G*32-1:0] x_q,
    // result words
    output reg               ov,
    output reg  [MP*G-1:0]   o_we,
    output reg  [MP*G*AW-1:0] o_addr,
    output reg  [MP*G*W-1:0] o_mask,
    output reg  [MP*G*W*32-1:0] o_data,
    // HBM (one stack): per pseudo-channel request / response ports
    output wire [NPC-1:0]       h_req_v,
    input  wire [NPC-1:0]       h_req_rdy,
    output wire [NPC*HAW-1:0]   h_req_addr,
    output wire [NPC*HLENW-1:0] h_req_len,
    output wire [NPC*HTAGW-1:0] h_req_tag,
    input  wire [NPC-1:0]       h_rsp_v,
    output wire [NPC-1:0]       h_rsp_rdy,
    input  wire [NPC*HTAGW-1:0] h_rsp_tag,
    input  wire [NPC*HBEATW-1:0] h_rsp_beat,
    input  wire [NPC*256-1:0]   h_rsp_data,
    output reg               fault,
    // activation counters (bench)
    output reg  [31:0]       dbg_ops,             // fused ops run
    output reg  [31:0]       dbg_elems,           // index scores written
    output wire [47:0]       dbg_keys_streamed,   // keys delivered by the HBM key stream
    output wire [47:0]       dbg_hbm_beats,       // HBM beats received
    output wire [47:0]       dbg_keys_scored,     // keys scored by the engine
    output wire [47:0]       dbg_headsums_fused   // head terms summed inside the engine
);
    localparam integer NK  = 16;                        // engine keys a cycle = the stream's beat
    localparam integer QE  = IH * 32;
    localparam integer QEW = $clog2(QE + IH);
    localparam integer HW  = 20;                        // stream block counter
    localparam [2:0] A_IDLE = 0, A_QLD = 1, A_QL = 2, A_RUN = 3, A_END = 4;

    reg  [2:0]    st;
    reg  [NW-1:0] n;
    reg  [AW-1:0] xbase, xks, xjs, xcs, obase, wts, wbase;
    reg           rnd, oen, cfg_bad;
    reg  [QEW:0]  qe;                                   // element being read: q (< QE), then wts
    reg  [5:0]    qh;                                   // head being loaded into the engine
    reg  [NW-1:0] nout_w;                               // score words written
    assign ready = (st == A_IDLE);

    function automatic [15:0] bf16(input [31:0] x);
        bf16 = x[31:16] + ((x[15] && (x[14:0] != 0 || x[16])) ? 16'd1 : 16'd0);
    endfunction

    // ---- QLOAD
    reg           q1_v, q2_v;
    reg  [QEW:0]  q1_e, q2_e;
    reg  [15:0]   qv [0:QE+IH-1];                       // q (head hh, dim k at hh*32 + k), then wts[hh] at QE + hh
    reg           rd_bad;
    wire [NW-1:0] qe_hh = qe >> 5;
    integer g;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            st <= A_IDLE; x_re <= 0; q1_v <= 1'b0; q2_v <= 1'b0;
        end else begin
            x_re <= 0; q1_v <= 1'b0; q2_v <= q1_v;
            case (st)
                A_IDLE: if (go) begin st <= A_QLD; qe <= 0; end
                A_QLD: begin
                    x_re[G-1:0] <= {G{1'b1}};
                    q1_v <= 1'b1;
                    qe <= qe + G;
                    if (qe + G >= QE + IH) st <= A_QL;
                end
                A_QL: if (!q1_v && !q2_v) begin
                    if (qh == IH - 1) st <= A_RUN;
                end
                A_RUN: if (nout_w * NK >= n && !ks_busy && !e_ov) st <= A_END;
                A_END: st <= A_IDLE;
                default: st <= A_IDLE;
            endcase
        end
    end
    always @(posedge clk) begin
        if (st == A_IDLE && go) begin
            n <= i_nout; xbase <= i_xbase; xks <= i_xks; xjs <= i_xjs; xcs <= i_xcs; obase <= i_obase;
            wts <= i_wts; rnd <= i_round; oen <= i_oen; wbase <= i_wbase;
            //: this adapter runs the fused op only, over exactly the engine's heads, one 32-block per head
            cfg_bad <= !i_fuse || (i_k != 32) || !i_mmode || ((IL << i_hg) != IH);
        end
        for (g = 0; g < G; g = g + 1)
            x_addr[g*AW +: AW] <= (qe + g < QE) ?
                xbase + ((qe + g) >> 5) / IL * xcs + ((qe + g) >> 5) % IL * xjs + ((qe + g) & 31) * xks :
                wts + (qe + g - QE);
        q1_e <= qe; q2_e <= q1_e;
        if (q2_v)
            for (g = 0; g < G; g = g + 1)
                if (q2_e + g < QE + IH)
                    qv[q2_e + g] <= (rnd && q2_e + g < QE) ? bf16(x_q[32*g +: 32]) : x_q[32*g + 16 +: 16];
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) rd_bad <= 1'b0;
        else if (st == A_IDLE && go) rd_bad <= 1'b0;
        else if (q2_v)
            for (g = 0; g < G; g = g + 1)
                if (q2_e + g < QE + IH && !(rnd && q2_e + g < QE) && x_q[32*g +: 16] != 16'd0) rd_bad <= 1'b1;
    end

    // ---- QL: one head a cycle into the engine
    reg  [32*16-1:0] qrow;
    reg  [136:0]     qenc;
    reg              ql_v, qbad;
    reg  [7:0]       ql_head;
    reg  [15:0]      ql_w;
    integer kx;
    always @(*) begin
        for (kx = 0; kx < 32; kx = kx + 1) qrow[16*kx +: 16] = qv[qh * 32 + kx];
        qenc = ot_hdc_v41x_idx_enc32(qrow);
    end
    reg  [127:0] ql_codes;
    reg  [7:0]   ql_sc;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin ql_v <= 1'b0; qh <= 0; qbad <= 1'b0; end
        else begin
            ql_v <= 1'b0;
            if (st == A_IDLE && go) begin qh <= 0; qbad <= 1'b0; end
            if (st == A_QL && !q1_v && !q2_v) begin
                ql_v <= 1'b1;
                qh <= qh + 1'b1;
                if (qenc[136]) qbad <= 1'b1;
            end
        end
    end
    always @(posedge clk) begin
        ql_head <= qh; ql_codes <= qenc[127:0]; ql_sc <= qenc[135:128]; ql_w <= qv[QE + qh];
    end

    // ---- the key stream (commanded at the start of QL)
    wire             ks_busy, ks_v, e_k_ready;
    wire [15:0]      ks_kv;
    wire [16*544-1:0] ks_key;
    reg              ks_cmd;
    wire [AW-1:0]    ik_off = wbase - cfg_ik_base;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) ks_cmd <= 1'b0; else ks_cmd <= (st == A_QL && !q1_v && !q2_v && qh == 0);
    ot_hdc_v41x_idx_kstream #(.NPC(NPC), .WB(32), .GA(24), .AW(HAW), .HW(HW), .TAGW(HTAGW), .LENW(HLENW),
                              .BEATW(HBEATW), .DW(256)) u_ks (
        .clk(clk), .rst_n(rst_n), .cmd_v(ks_cmd), .cmd_base(((ik_off >> 7) * 17)), .cmd_nkeys(n),
        .busy(ks_busy), .req_v(h_req_v), .req_rdy(h_req_rdy), .req_addr(h_req_addr), .req_len(h_req_len),
        .req_tag(h_req_tag), .rsp_v(h_rsp_v), .rsp_rdy(h_rsp_rdy), .rsp_tag(h_rsp_tag), .rsp_beat(h_rsp_beat),
        .rsp_data(h_rsp_data), .o_valid(ks_v), .o_ready(e_k_ready), .o_kv(ks_kv), .o_key(ks_key),
        .cnt_keys_streamed(dbg_keys_streamed), .cnt_hbm_beats(dbg_hbm_beats));
    // a 68-B key {scales[31:0], codes[511:0]} -> the NB = 1 engine key {scale byte 0, codes of dims 0..31}
    reg [NK*136-1:0] e_key;
    integer kk;
    always @(*)
        for (kk = 0; kk < NK; kk = kk + 1)
            e_key[136*kk +: 136] = {ks_key[544*kk + 512 +: 8], ks_key[544*kk +: 128]};

    // ---- the engine
    wire          e_ov;
    wire [NK-1:0] e_okv, e_of;
    wire [NK*16-1:0] e_os;
    wire [47:0]   e_cf;
    ot_hdc_v41x_idx_engine #(.NK(NK), .IH(IH), .NB(1), .FD(64)) u_eng (
        .clk(clk), .rst_n(rst_n), .ql_v(ql_v), .ql_head(ql_head), .ql_codes(ql_codes), .ql_sc(ql_sc),
        .ql_w(ql_w), .k_valid(ks_v), .k_ready(e_k_ready), .k_kv(ks_kv), .k_keep(ks_kv), .k_key(e_key),
        .o_valid(e_ov), .o_ready(1'b1), .o_kv(e_okv), .o_score(e_os), .o_fault(e_of),
        .cnt_keys_scored(dbg_keys_scored), .cnt_headsums_fused(dbg_headsums_fused), .cnt_faults(e_cf));

    // ---- scores: beat j (keys 16j ..) is vector-memory word obase + j
    integer l;
    reg sfault;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin o_we <= 0; ov <= 1'b0; sfault <= 1'b0; nout_w <= 0; end
        else begin
            o_we <= 0; ov <= 1'b0; sfault <= 1'b0;
            if (st == A_IDLE && go) nout_w <= 0;
            if (e_ov) begin
                o_we[0] <= oen; ov <= 1'b1; nout_w <= nout_w + 1'b1;
                if (|(e_okv & e_of)) sfault <= 1'b1;
            end
        end
    end
    always @(posedge clk) begin
        o_addr <= 0; o_mask <= 0; o_data <= 0;
        o_addr[AW-1:0] <= obase + nout_w;
        for (l = 0; l < W; l = l + 1) begin
            o_mask[l] <= e_okv[l];
            o_data[32*l +: 32] <= {e_os[16*l +: 16], 16'd0};
        end
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin idle <= 1'b1; fault <= 1'b0; dbg_ops <= 0; dbg_elems <= 0; end
        else begin
            idle <= (st == A_IDLE) && !go && !(|o_we) && !ks_busy;
            fault <= sfault || (st != A_IDLE && (rd_bad || cfg_bad || qbad));
            if (st == A_IDLE && go) dbg_ops <= dbg_ops + 1;
            if (e_ov) dbg_elems <= dbg_elems + $countones(e_okv);
        end
    end

    // the block encoder: 32 BF16 values -> {bad, u[7:0], codes[127:0]}
    function automatic [136:0] ot_hdc_v41x_idx_enc32(input [32*16-1:0] v);
        reg [7:0] emax, e, u;
        reg [6:0] m;
        reg bad, any;
        reg [127:0] c;
        integer i, d;
        begin
            emax = 8'd0; bad = 1'b0; any = 1'b0; c = 128'd0;
            for (i = 0; i < 32; i = i + 1)
                if (v[16*i +: 15] != 15'd0) begin
                    any = 1'b1;
                    if (v[16*i + 7 +: 8] > emax) emax = v[16*i + 7 +: 8];
                end
            u = any ? emax - 8'd2 : 8'd0;
            if (any && (emax < 8'd2 || emax > 8'd254 || u > 8'd252)) bad = 1'b1;
            for (i = 0; i < 32; i = i + 1) begin
                e = v[16*i + 7 +: 8];
                m = v[16*i +: 7];
                if (v[16*i +: 15] != 15'd0) begin
                    d = e - emax + 2;
                    if (e == 8'd0 || e == 8'd255 || m[5:0] != 6'd0) bad = 1'b1;
                    case (d)
                        2:  c[4*i +: 3] = m[6] ? 3'd7 : 3'd6;
                        1:  c[4*i +: 3] = m[6] ? 3'd5 : 3'd4;
                        0:  c[4*i +: 3] = m[6] ? 3'd3 : 3'd2;
                        -1: begin c[4*i +: 3] = 3'd1; if (m[6]) bad = 1'b1; end
                        default: bad = 1'b1;
                    endcase
                    c[4*i + 3] = v[16*i + 15];
                end
            end
            ot_hdc_v41x_idx_enc32 = {bad, u, c};
        end
    endfunction
endmodule

// ---------------------------------------------------------------------------
// Index-key writer: the transposed-KV stream op that writes an index key row
// (dst = KVT, o_base >= the index keys' KV base) is latched at issue; its 32
// elements are collected from the KV write lanes (element o_base + (row>>4)*
// 32*16 + d*16 + (row & 15)), re-encoded, and emitted as the key's HBM record:
//   code sector  (B0 + 1 + row/64)*128 + 2*(row%64)   <- {128'b0, codes of dims 0..31}
//   scale sector B0*128 + row/8, 32-bit field row%8    <- {24'b0, u}
// with B0 = (o_base/16 - cfg_ik_base)/128 * 17 (the stream's map).  One key
// write in flight (a second one issuing before the first completes faults).
// ---------------------------------------------------------------------------
module ot_hdc_v41x_idx_kwr #(
    parameter integer AW  = 24,
    parameter integer NW  = 16,
    parameter integer NL  = 8,             // KV write lanes
    parameter integer HAW = 28
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire [AW-1:0]     cfg_ik_base,          // KV words
    input  wire              su_go,
    input  wire [1:0]        i_dst,
    input  wire [AW-1:0]     i_obase,              // elements (the KVT region base)
    input  wire [AW-1:0]     i_orow,
    input  wire [NW-1:0]     i_nout,
    input  wire [NL-1:0]     kv_we,
    input  wire [NL*AW-1:0]  kv_waddr,
    input  wire [NL*32-1:0]  kv_wdata,
    output reg               w_v,
    output reg  [HAW-1:0]    w_csec,
    output reg  [127:0]      w_codes,
    output reg  [HAW-1:0]    w_ssec,
    output reg  [2:0]        w_sslot,
    output reg  [7:0]        w_scale,
    output reg               fault,
    output reg  [31:0]       dbg_keys              // keys written
);
    reg          busy;
    reg [AW-1:0] rbase, row;
    reg [15:0]   el [0:31];
    reg [31:0]   got;
    reg          wbad;
    wire [AW-1:0] rb_e = rbase + (row >> 4) * 512 + row[3:0];
    wire         hit = su_go && i_dst == 2'd3 && (i_obase >> 4) >= cfg_ik_base;
    integer q;
    reg [AW-1:0] off;
    reg [32*16-1:0] rowv;
    reg [136:0]  enc;
    reg [AW-1:0] b0;
    integer kx;
    always @(*) begin
        for (kx = 0; kx < 32; kx = kx + 1) rowv[16*kx +: 16] = el[kx];
        enc = enc32(rowv);
        b0 = ((rbase >> 4) - cfg_ik_base) / 128 * 17;
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin busy <= 1'b0; w_v <= 1'b0; fault <= 1'b0; got <= 0; wbad <= 1'b0; dbg_keys <= 0; end
        else begin
            w_v <= 1'b0;
            fault <= 1'b0;
            if (hit) begin
                if (busy || i_nout != 1) fault <= 1'b1;
                busy <= 1'b1; rbase <= i_obase; row <= i_orow; got <= 0; wbad <= 1'b0;
            end else if (busy) begin
                for (q = 0; q < NL; q = q + 1)
                    if (kv_we[q]) begin
                        off = kv_waddr[q*AW +: AW] - rb_e;
                        if (kv_waddr[q*AW +: AW] >= rb_e && off < 512 && off[3:0] == 0) begin
                            el[off >> 4] <= kv_wdata[32*q + 16 +: 16];
                            got[off >> 4] <= 1'b1;
                            if (kv_wdata[32*q +: 16] != 16'd0) wbad <= 1'b1;
                        end
                    end
                if (&got) begin
                    busy <= 1'b0; got <= 0;
                    w_v <= 1'b1; dbg_keys <= dbg_keys + 1;
                    if (enc[136] || wbad) fault <= 1'b1;
                end
            end
        end
    end
    always @(posedge clk) begin
        w_csec <= (b0 + 1 + (row >> 6)) * 128 + 2 * (row & 63);
        w_codes <= enc[127:0];
        w_ssec <= b0 * 128 + (row >> 3);
        w_sslot <= row[2:0];
        w_scale <= enc[135:128];
    end

    function automatic [136:0] enc32(input [32*16-1:0] v);
        reg [7:0] emax, e, u;
        reg [6:0] m;
        reg bad, any;
        reg [127:0] c;
        integer i, d;
        begin
            emax = 8'd0; bad = 1'b0; any = 1'b0; c = 128'd0;
            for (i = 0; i < 32; i = i + 1)
                if (v[16*i +: 15] != 15'd0) begin
                    any = 1'b1;
                    if (v[16*i + 7 +: 8] > emax) emax = v[16*i + 7 +: 8];
                end
            u = any ? emax - 8'd2 : 8'd0;
            if (any && (emax < 8'd2 || emax > 8'd254 || u > 8'd252)) bad = 1'b1;
            for (i = 0; i < 32; i = i + 1) begin
                e = v[16*i + 7 +: 8];
                m = v[16*i +: 7];
                if (v[16*i +: 15] != 15'd0) begin
                    d = e - emax + 2;
                    if (e == 8'd0 || e == 8'd255 || m[5:0] != 6'd0) bad = 1'b1;
                    case (d)
                        2:  c[4*i +: 3] = m[6] ? 3'd7 : 3'd6;
                        1:  c[4*i +: 3] = m[6] ? 3'd5 : 3'd4;
                        0:  c[4*i +: 3] = m[6] ? 3'd3 : 3'd2;
                        -1: begin c[4*i +: 3] = 3'd1; if (m[6]) bad = 1'b1; end
                        default: bad = 1'b1;
                    endcase
                    c[4*i + 3] = v[16*i + 15];
                end
            end
            enc32 = {bad, u, c};
        end
    endfunction
endmodule

`timescale 1ns/1ps
`default_nettype none
// Static ARGMAX.LOCAL (H-IDX 2026-10-15, MTP). Successor of ot_hgi_argmax_record (historical: one VM packet request
// outstanding, am_rdy handshake to the SU stream). The CLOSED engine ot_hgi_argmax18_m (GENERIC18 = 1, LP = 8: numpy
// argmax, lowest index on ties, first NaN wins and is flagged, global id = local + RANK * imm_a) is used unchanged;
// it is a fixed-latency pipeline. Around it everything is on compiler edges; nothing waits for data, credits or ready.
//
// A = VM (mode 0): one FP32 row read through the SW IDX read group (shared with INDEX/TOPK by
//     ot_hbm_idx_vm_share_static, owner booked by the compiler), ONE SECTOR PER EDGE (consecutive sectors sit in
//     consecutive banks): rq registered S+j, bank samples S+j+1, capture S+j+8, engine beat register S+j+9, engine samples S+j+10.
// A = STREAM (mode 1): the SU reduce logit stream {v, last, mask8, vals256, bias256, bias_en} is sampled into pin
//     registers on the producer's compiler edges (pin X), engine beat register X+1, engine samples X+2. No am_rdy: the compiler
//     opens the record (go) before the first beat and the producer never waits.
// O = VM: two words {value (FP32 bits), id (U32)} at o_base and o_base + o_is, two word-masked sector writes on the
//     SW 'argmax' record client (cq338): W0 = L + ELAT + 1, W1 = W0 + 1, where L = the edge the engine samples the
//     last beat and ELAT the engine's fixed latency (the engine's out_v is checked to rise exactly at L + ELAT).
//     client_seq = 0 / 1; cr sampled at W_i + ACK (12, measured on the slice), compared one edge later.
//     done / fault after W1 + ACK + 1. Range fault (id >= 2^18) or engine fault: zero-mask writes on the same slots, fault.
// Timeline (mode 0), G = edge sampling go: S = G+3, ns = ((a_base+n-1)>>3) - (a_base>>3) + 1, L = S + ns + 9.
// Timeline (mode 1): L = (edge the stream pin samples the last beat) + 2; go must be sampled before the first beat.
// MUT (bench): 1 id not corrected for the A word offset; 2 capture one edge early; 3 second O word not written.
module ot_hbm_argmax_static #(
    parameter integer MUT = 0,
    parameter integer ACK = 12,
    parameter integer ELAT = 14      // measured: closed engine samples the last beat at L, out_v sampled at L+14
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [1:0]    sid,
    input  wire [7:0]    die_id,          // static rank strap
    input  wire          go,
    input  wire          mode,            // 0 VM, 1 STREAM
    input  wire [17:0]   imm_a,
    input  wire          a_mirror,
    input  wire [17:0]   a_base,
    input  wire [17:0]   n,
    input  wire [17:0]   o_base,
    input  wire [15:0]   o_is,
    output reg  [135:0]  vm_rq,
    input  wire [2055:0] vm_rr,
    input  wire [522:0]  am_stream,       // {bias_en, bias256, vals256, mask8, last, v}
    output reg  [337:0]  cq,
    output reg  [1:0]    cq_seq,
    input  wire [273:0]  cr,
    output reg           busy, done, fault, nan_flag
);
    localparam [3:0] E_IDLE=0, E_CHK=1, E_ROW=2, E_RD=3, E_WAIT=4, E_W0=5, E_W1=6, E_END=7;
    reg [3:0] st; reg [5:0] cnt; reg flt;
    reg mode_q, am_q; reg [17:0] imm_q, ab_q, n_q, ob_q; reg [15:0] ois_q; reg legal_q;
    wire legal = n != 18'd0 && imm_a < 18'd262143 &&
                 (mode || (a_mirror ? a_base[17:16] == 2'd0 : a_base[17:16] == sid)) &&
                 o_base[17:16] == sid && ((o_base + {2'd0, o_is}) >> 16) == {16'd0, sid};
    always @(posedge clk) if (go && !busy) begin
        mode_q <= mode; am_q <= a_mirror; imm_q <= imm_a; ab_q <= a_base; n_q <= n; ob_q <= o_base;
        ois_q <= o_is; legal_q <= legal;
    end
    // ---------------------------------------------------------------- VM reader (one sector per edge)
    reg [14:0] i_sec, i_left; reg i_first; reg [17:0] le;
    wire rd_now = st == E_RD;
    wire rd_last = rd_now && i_left == 15'd0;
    reg [11:0] dp [0:8];                  // {v, bank3, first, last, off3, lastw3}
    wire [11:0] di = dp[(MUT == 2) ? 6 : 7];
    reg cap_v, cap_first, cap_last; reg [2:0] cap_off, cap_lastw; reg [255:0] cap_d;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin vm_rq <= 136'd0; cap_v <= 1'b0; for (integer d = 0; d < 9; d = d + 1) dp[d] <= 12'd0; end
        else begin
            vm_rq <= 136'd0; dp[0] <= 12'd0;
            for (integer d = 1; d < 9; d = d + 1) dp[d] <= dp[d-1];
            if (rd_now) begin
                vm_rq[17*i_sec[2:0] +: 17] <= {1'b1, am_q, i_sec};
                dp[0] <= {1'b1, i_sec[2:0], i_first, rd_last, i_first ? ab_q[2:0] : 3'd0, le[2:0]};
            end
            cap_v <= di[11];
        end
    always @(posedge clk) begin cap_d <= vm_rr[257*di[10:8] +: 256]; {cap_first, cap_last, cap_off, cap_lastw} <= di[7:0]; end
    reg rd_bad;
    always @* begin
        rd_bad = 1'b0;
        for (integer l = 0; l < 8; l = l + 1) if (vm_rr[257*l+256] != (di[11] && di[10:8] == 3'(l))) rd_bad = 1'b1;
    end
    // ---------------------------------------------------------------- stream pins
    reg [522:0] as_q;
    always @(posedge clk or negedge rst_n) if (!rst_n) as_q <= 523'd0; else as_q <= am_stream;
    // ---------------------------------------------------------------- engine (closed, unchanged)
    reg e_v, e_last, e_be; reg [7:0] e_m; reg [255:0] e_vals, e_bias;
    wire s_beat = busy && mode_q && as_q[0];
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin e_v <= 1'b0; e_last <= 1'b0; end
        else begin
            e_v <= mode_q ? s_beat : cap_v; e_last <= mode_q ? (s_beat && as_q[1]) : (cap_v && cap_last);
        end
    always @(posedge clk) begin
        if (mode_q) begin e_m <= as_q[9:2]; e_vals <= as_q[265:10]; e_bias <= as_q[521:266]; e_be <= as_q[522]; end
        else begin
            for (integer l = 0; l < 8; l = l + 1)
                e_m[l] <= (!cap_first || l[2:0] >= cap_off) && (!cap_last || l[2:0] <= cap_lastw);
            e_vals <= cap_d; e_bias <= 256'd0; e_be <= 1'b0;
        end
    end
    wire o_v, o_nan, o_f, o_rf; wire [17:0] o_idx; wire [31:0] o_val;
    ot_hgi_argmax18_m #(.LP(8), .GENERIC18(1)) u_e (.clk(clk), .rst_n(rst_n), .in_v(e_v), .in_last(e_last),
        .in_bias_en(e_be), .in_mask(e_m), .in_vals(e_vals), .in_bias(e_bias), .cfg_rank(die_id[6:0]), .cfg_imm_a(imm_q),
        .out_v(o_v), .out_idx(o_idx), .out_nan(o_nan), .fault(o_f), .out_range_fault(o_rf), .out_value(o_val));
    // ---------------------------------------------------------------- result and writes
    reg [31:0] res_val, res_id; reg res_bad;
    wire [17:0] wa = (st == E_W1) ? ob_q + {2'd0, ois_q} : ob_q;
    wire [31:0] wdat = (st == E_W1) ? res_id : res_val;
    reg [2:0] ap [0:ACK]; reg cr_v; reg [15:0] cr_tag; reg cr_we; reg wr_now;
    wire [2:0] ax = ap[ACK-1];
    wire ack_bad = cr_v != ax[2] || (ax[2] && (cr_tag != {14'h1E80, ax[1:0]} || !cr_we));
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin cr_v <= 1'b0; for (integer d = 0; d <= ACK; d = d + 1) ap[d] <= 3'd0; end
        else begin
            cr_v <= cr[273]; ap[0] <= {wr_now, cq_seq};
            for (integer d = 1; d <= ACK; d = d + 1) ap[d] <= ap[d-1];
        end
    always @(posedge clk) begin cr_tag <= cr[272:257]; cr_we <= cr[256]; end
    wire kill = flt || res_bad || (MUT == 3 && st == E_W1);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            st <= E_IDLE; busy <= 1'b0; done <= 1'b0; fault <= 1'b0; nan_flag <= 1'b0; flt <= 1'b0; cq <= 338'd0;
            cq_seq <= 2'd0; wr_now <= 1'b0; cnt <= 6'd0; res_bad <= 1'b0;
        end else begin
            done <= 1'b0; fault <= 1'b0; cq[337] <= 1'b0; wr_now <= 1'b0;
            if (busy && st != E_CHK && (ack_bad || (!mode_q && rd_bad))) flt <= 1'b1;
            if (o_v && !(st == E_WAIT && cnt == 6'd0)) flt <= 1'b1;      // engine out must be exactly on L+ELAT
            case (st)
                E_IDLE: if (go) begin busy <= 1'b1; st <= E_CHK; end
                E_CHK: begin
                    flt <= 1'b0; res_bad <= 1'b0; le <= ab_q + n_q - 18'd1;
                    if (!legal_q) begin fault <= 1'b1; busy <= 1'b0; st <= E_IDLE; end
                    else st <= mode_q ? E_WAIT : E_ROW;
                    cnt <= 6'd63;                          // STREAM: armed by the last beat
                end
                E_ROW: begin i_sec <= ab_q[17:3]; i_left <= le[17:3] - ab_q[17:3]; i_first <= 1'b1; st <= E_RD; end
                E_RD: begin
                    i_sec <= i_sec + 15'd1; i_left <= i_left - 15'd1; i_first <= 1'b0;
                    if (rd_last) st <= E_WAIT;
                end
                E_WAIT: begin
                    if (e_v && e_last) cnt <= 6'(ELAT - 1);   // the engine samples the last beat at this edge: L
                    else if (cnt != 6'd63 && cnt != 6'd0) cnt <= cnt - 6'd1;
                    if (cnt == 6'd0) begin                     // L + ELAT: engine out_v
                        if (!o_v) flt <= 1'b1;
                        res_val <= o_val;
                        res_id <= {14'd0, o_idx} - ((MUT == 1 || mode_q) ? 32'd0 : {29'd0, ab_q[2:0]});
                        res_bad <= o_f || o_rf;
                        if (o_nan) nan_flag <= 1'b1;
                        st <= E_W0;
                    end
                end
                E_W0, E_W1: begin                               // W0 = L+ELAT+1, W1 = W0+1
                    wr_now <= 1'b1; cq_seq <= (st == E_W1) ? 2'd1 : 2'd0;
                    cq <= {1'b1, 1'b1, 11'd0, 1'b0, wa[17:3], 5'd0, {8{wdat}},
                           kill ? 32'd0 : (32'hF << (4 * wa[2:0])), {14'h1E80, (st == E_W1) ? 2'd1 : 2'd0}};
                    if (st == E_W1) begin cnt <= 6'(ACK); st <= E_END; end else st <= E_W1;
                end
                E_END: if (cnt == 6'd0) begin                  // W1 + ACK + 1
                    done <= !(flt || res_bad || ack_bad); fault <= flt || res_bad || ack_bad; busy <= 1'b0; st <= E_IDLE;
                end else cnt <= cnt - 6'd1;
                default: st <= E_IDLE;
            endcase
        end
    end
endmodule
`default_nettype wire

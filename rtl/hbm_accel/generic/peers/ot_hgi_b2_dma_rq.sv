`timescale 1ns/1ps
`default_nettype none
// B2 request leaf: record adapter + registered I-list reader and row sequencer.
// Current contract VM format; BACK remains a separate per-cluster hard leaf.
module ot_hgi_b2_dma_rq #(parameter integer SBIT=35, parameter integer MUT_B2=0, parameter integer MUT_IL=0, parameter integer MUT_SEAM=0)(
 input wire clk, rst_n, input wire [1:0] qid, input wire [703:0] dma_rec, output wire [3:0] dma_ret,
 output wire mover_v, output wire [226:0] mover_cmd, input wire pin_m_rdy, pin_m_done, pin_m_fault, pin_m_src,
 output wire mover_fv, input wire pin_m_fence_rdy, input wire pin_m_fence_done,
 output wire [337:0] il_vmq, output wire il_active, input wire [273:0] vmr
);
 reg m_done, m_fault, m_src, m_fence_rdy, m_fence_done;
 reg [273:0] vmr_q;
 wire [2:0] reset_region;
 ot_rst_relay #(.REGIONS(3)) u_rst(.clk(clk), .rst_n_in(rst_n), .rst_n(reset_region));
 wire rn = reset_region[0];
 always @(posedge clk or negedge rn) begin
    if (!rn) begin m_done<=0; m_fault<=0; m_src<=0; m_fence_rdy<=0; m_fence_done<=0; vmr_q<=0; end
    else begin m_done<=pin_m_done; m_fault<=pin_m_fault; m_src<=pin_m_src; m_fence_rdy<=pin_m_fence_rdy; m_fence_done<=pin_m_fence_done; vmr_q<=vmr; end
 end
 localparam integer FRONT=0, BACK=0, B2=1, QID=0;
 reg [1:0] qid_q; always @(posedge clk) qid_q <= qid;
    wire d_mv_src, d_mv_pdone, d_mv_fdone, d_wq, d_is_v, d_is_rdy; wire [207:0] d_is_cmd;
    wire d_mv_v, d_mv_rdy, d_mv_done, d_mv_fault, d_fv, d_frdy, d_fdone, d_rdy, d_done, d_fault;
    wire [226:0] d_mv;
    // the core is cluster 0: HBM descriptors rotated by -qid on the way in, request addresses +qid on the way out
    wire [255:0] ra_r, ro_r;
    ot_hgi_b2_qrot_d #(.SBIT(SBIT)) u_rqa (.qid(qid_q), .d(dma_rec[384:129]), .r(ra_r));
    ot_hgi_b2_qrot_d #(.SBIT(SBIT)) u_rqo (.qid(qid_q), .d(dma_rec[640:385]), .r(ro_r));
    ot_hgi_dma_record #(.LEGACY(0), .B2(1), .QID(0), .SBIT(SBIT)) u_dma (.clk(clk), .rst_n(reset_region[1]), .hgi_en(1'b1),
        .rec_v(dma_rec[0]), .rec_rdy(d_rdy), .rec_hdr(dma_rec[128:1]), .rec_a(ra_r), .rec_o(ro_r),
        .rec_n_a(dma_rec[661:641]), .rec_n_o(dma_rec[682:662]), .rec_pos1(dma_rec[703:683]),
        .rec_ilist({14'd0, dma_rec[129 + 255 -: 17], dma_rec[129 + 7]}), .rec_done(d_done), .rec_fault(d_fault), .halted(),
        .wr_quiet(d_wq), .lg_mv_v(1'b0), .lg_mv_rdy(), .lg_mv(227'd0), .lg_fence_v(1'b0), .lg_fence_rdy(),
        .mv_v(d_mv_v), .mv_rdy(d_mv_rdy), .mv(d_mv), .mv_done(d_mv_done), .mv_fault(d_mv_fault),
        .mv_src(d_mv_src), .mv_pdone(d_mv_pdone), .mv_fdone(d_mv_fdone),
        .is_v(d_is_v), .is_rdy(d_is_rdy), .is_cmd(d_is_cmd), .fence_v(d_fv), .fence_rdy(d_frdy), .fence_done(d_fdone));

    wire [2:0] sf = d_mv[4:2];
    wire elig = d_mv[1:0] == 2'd0 && d_mv[94:93] == 2'd1 && d_mv[92:77] == 16'd1 && d_mv[185:170] == 16'd1 &&
                (sf == 3'd0 || sf == 3'd1 || sf == 3'd2 || sf == 3'd4 || sf == 3'd5) &&
                d_mv[9:5] == 5'd0 && d_mv[49:45] == 5'd0 && d_mv[100:98] == 3'd0 && d_mv[140:138] == 3'd0 &&
                ((sf == 3'd0 || sf == 3'd5) ? d_mv[208:206] == 3'd0 : (sf == 3'd1) ? d_mv[209:206] == 4'd0 : d_mv[210:206] == 5'd0) &&
                d_mv[205:186] != 20'd0 && d_mv[226:206] != 21'd0;
    wire to_f = (FRONT != 0) && elig && d_mv[44:43] == 2'd0;      // source code 0 / 1 (STRIPE4); others: the mover faults
    // BACK: a raw FP32 / U32 VM -> HBM STORE of whole sectors, VM rows 64-word aligned, HBM rows 32 B aligned, code 0 / 1
    wire [2:0] df = d_mv[97:95];
    wire to_b = (BACK != 0) && d_mv[1:0] == 2'd1 && d_mv[94:93] == 2'd0 && d_mv[92:77] == 16'd1 && d_mv[185:170] == 16'd1 &&
                (sf == 3'd0 || sf == 3'd5) && (df == 3'd0 || df == 3'd5) && d_mv[10:5] == 6'd0 && d_mv[50:45] == 6'd0 &&
                d_mv[208:206] == 3'd0 && d_mv[102:98] == 5'd0 && d_mv[142:138] == 5'd0 && d_mv[137:136] == 2'd0 &&
                d_mv[205:186] != 20'd0 && d_mv[226:206] != 21'd0;
    wire b_rdy, b_src, b_done, b_fault, b_quiet; wire [512:0] b_vr2q, m_vr2q;
    reg  m_pend;                                // a move sent to the mover / front not yet done (BACK waits for it)
    reg  b_own;                                 // the back engine owns the VM read group (registered: !b_quiet)
    // ---------------------------------------------------------------- I-list reader state
    reg rd_act; reg [31:0] rd_w; reg [19:0] rd_left;           // next id word to request, ids not yet requested
    reg [2:0] rd_out; reg [5:0] rd_fl;                         // sector reads in flight, ids in flight + buffered
    reg [2:0] ro_off [0:3]; reg [3:0] ro_k [0:3]; reg [1:0] ro_h, ro_t;    // per read: first word, ids in it
    reg [255:0] rb_d [0:3]; reg [1:0] rb_h, rb_t; reg [2:0] rb_n;          // response FIFO
    reg [2:0] u_off; reg [3:0] u_k; reg [19:0] u_e;            // unpack position in the head response, list position
    reg [31:0] idf [0:31]; reg [4:0] idf_h, idf_t; reg [5:0] idf_n;
    reg [337:0] r_vmq;

    wire ix_rdy_f, id_rdy_f; reg ixf_v; reg [175:0] ixf_cmd;
    wire s_id_v = idf_n != 6'd0;
    wire s_id_take;
    reg [3:0] iss_k; reg iss_go;
    always @* begin
        iss_k = 4'd8 - {1'b0, rd_w[2:0]};
        if ({16'd0, iss_k} > rd_left) iss_k = rd_left[3:0];
        iss_go = rd_act && rd_left != 20'd0 && rd_out < 3'd4 && ({2'd0, iss_k} <= 6'd32 - rd_fl);
    end
    // row sequencer (FRONT 0)
    reg [175:0] sc; reg sq_act, sq_last, sq_mv_v, sq_wait; reg [226:0] sq_mv; reg [19:0] sq_e;
    reg sq_p0v; reg [59:0] sq_p0; reg [2:0] sq_ph; reg [59:0] sq_p; reg [42:0] sq_lo, sq_hi; reg [31:0] sq_id;
    reg [34:0] sq_pp [0:3];
    reg [30:0] sq_nlo [0:3], sq_nhi [0:3];
    reg [28:0] sq_qp [0:15];
    reg [31:0] sq_dw; // modulo32 destination: base + row_index * stride
    reg sq_skd;                                                 // B2: the stream's last row was another stack's (done pulse)
    localparam integer QS = (MUT_B2 == 1) ? (QID + 1) % 4 : QID;
    assign il_vmq = r_vmq; assign il_active = rd_act;
    wire f_rdy, f_done, f_fault;
    assign d_frdy = m_fence_rdy && b_quiet;
    assign d_mv_rdy = !m_pend && !rd_act && !sq_act && (to_b ? (b_rdy && !m_pend) : (b_quiet && (to_f ? f_rdy : m_rdy)));
    assign d_mv_done = f_done | (m_done && (!sq_act || sq_last)) | b_done | sq_skd;
    assign d_mv_fault = f_fault | m_fault | b_fault;
    assign d_mv_src = (m_src && !sq_act) | b_src; assign d_mv_pdone = (m_done && (!sq_act || sq_last)) | b_done | sq_skd; assign d_mv_fdone = f_done;
    always @(posedge clk or negedge rn)
        if (!rn) begin m_pend <= 1'b0; b_own <= 1'b0; end
        else begin
            b_own <= (BACK != 0) && !b_quiet;
            if (f_done || m_done) m_pend <= 1'b0;
            if ((d_mv_v && d_mv_rdy && !to_b) || (d_is_v && d_is_rdy)) m_pend <= 1'b1;
        end

    assign b_rdy = 1'b0; assign b_src = 1'b0; assign b_done = 1'b0; assign b_fault = 1'b0; assign b_quiet = 1'b1;
    assign f_rdy = 1'b0; assign f_done = 1'b0; assign f_fault = 1'b0;
    assign ix_rdy_f = 1'b0; assign id_rdy_f = 1'b0;
    // hbm-fq/dma 10-11: with the KV engine the sector engine reads VM sources through the packet client (SVR2 0)
    // ---------------------------------------------------------------- stream command, I-list reader, row sequencer
    assign d_is_rdy = !m_pend && !rd_act && !sq_act && m_rdy && b_quiet && ((FRONT != 0) ? (ix_rdy_f && f_rdy) : 1'b1) && !ixf_v;
    assign s_id_take = (FRONT != 0) ? (s_id_v && id_rdy_f) : (sq_act && !sq_wait && sq_ph == 3'd0 && s_id_v);
    always @(posedge clk or negedge rn) begin
        if (!rn) begin
            rd_act <= 1'b0; rd_out <= 3'd0; rd_fl <= 6'd0; ro_h <= 2'd0; ro_t <= 2'd0; idf_h <= 5'd0; idf_t <= 5'd0;
            idf_n <= 6'd0; r_vmq <= 338'd0; rb_h <= 2'd0; rb_t <= 2'd0; rb_n <= 3'd0; u_k <= 4'd0; u_e <= 20'd0; ixf_v <= 1'b0;
            sq_act <= 1'b0; sq_mv_v <= 1'b0; sq_wait <= 1'b0; sq_last <= 1'b0; sq_ph <= 3'd0; sq_skd <= 1'b0;
        end else begin : rdr
            reg push, rsp_in, upop;
            ixf_v <= 1'b0; r_vmq[337] <= 1'b0; push = 1'b0; sq_skd <= 1'b0;
            if (d_is_v && d_is_rdy) begin
                sc <= d_is_cmd[175:0]; rd_act <= d_is_cmd[174:155] != 20'd0; rd_w <= d_is_cmd[207:176]; rd_left <= d_is_cmd[174:155]; u_e <= 20'd0;
                if (FRONT != 0) begin ixf_v <= 1'b1; ixf_cmd <= d_is_cmd[175:0]; end
                else begin
                    sq_act <= d_is_cmd[174:155] != 20'd0; sq_e <= 20'd0; sq_dw <= d_is_cmd[122:91]; sq_p0v <= 1'b0; sq_wait <= 1'b0; sq_ph <= 3'd0; sq_last <= 1'b0;
                end
            end
            if (iss_go) begin
                r_vmq <= {1'b1, 1'b0, rd_w[29:3], 5'd0, 256'd0, 32'd0, 16'h4944};   // byte address = sector x 32
                ro_off[ro_t] <= rd_w[2:0]; ro_k[ro_t] <= iss_k; ro_t <= ro_t + 2'd1;
                rd_w <= rd_w + {28'd0, iss_k}; rd_left <= rd_left - {16'd0, iss_k};
            end
            rsp_in = rd_act && vmr_q[273];
            if (rsp_in) begin rb_d[rb_t] <= vmr_q[255:0]; rb_t <= rb_t + 2'd1; end
            upop = 1'b0;
            if (rb_n != 3'd0) begin : unp
                reg [2:0] o; reg [3:0] kk;
                o = (u_k == 4'd0) ? ro_off[ro_h] : u_off; kk = (u_k == 4'd0) ? ro_k[ro_h] : u_k;
                idf[idf_t] <= rb_d[rb_h][{((MUT_IL != 0 && u_e == 20'd1) ? o + 3'd1 : o), 5'd0} +: 32];
                idf_t <= idf_t + 5'd1; push = 1'b1; u_e <= u_e + 20'd1;
                u_off <= o + 3'd1; u_k <= kk - 4'd1;
                if (kk == 4'd1) begin upop = 1'b1; rb_h <= rb_h + 2'd1; ro_h <= ro_h + 2'd1; u_k <= 4'd0; end
            end
            rb_n <= rb_n + {2'd0, rsp_in} - {2'd0, upop};
            rd_out <= rd_out + {2'd0, iss_go} - {2'd0, rsp_in};
            if (s_id_take) idf_h <= idf_h + 5'd1;
            idf_n <= idf_n + {5'd0, push} - {5'd0, s_id_take};
            rd_fl <= rd_fl + (iss_go ? {2'd0, iss_k} : 6'd0) - {5'd0, s_id_take};
            if (rd_act && rd_left == 20'd0 && rd_out == 3'd0 && !iss_go && !rsp_in && rb_n == 3'd0) rd_act <= 1'b0;
            // row sequencer (FRONT 0): id -> partial products -> address -> one mover LOAD, wait for its done
            sq_mv_v <= sq_mv_v && !m_rdy;
            if (sq_act) begin
                if (sq_ph == 3'd0 && !sq_wait && s_id_v) begin sq_id <= idf[idf_h]; sq_ph <= 3'd1; end
                if (sq_ph == 3'd1) begin
                    // Each two-bit product contains only one 29-bit add.
                    // Two registered combine edges preserve the unsigned8x27 result.
                    for (integer pp=0;pp<16;pp=pp+1)
                        sq_qp[pp] <= {27'd0,sq_id[pp*2 +: 2]} * {2'd0,sc[69:43]};
                    sq_ph <= 3'd6;
                end
                if (sq_ph == 3'd6) begin
                    for (integer pp=0;pp<4;pp=pp+1) begin
                        sq_nlo[pp] <= {2'd0,sq_qp[pp*4]} + {sq_qp[pp*4+1],2'd0};
                        sq_nhi[pp] <= {2'd0,sq_qp[pp*4+2]} + {sq_qp[pp*4+3],2'd0};
                    end
                    sq_ph <= 3'd5;
                end
                if (sq_ph == 3'd5) begin
                    for (integer pp=0;pp<4;pp=pp+1)
                        sq_pp[pp] <= {4'd0,sq_nlo[pp]} + {sq_nhi[pp],4'd0};
                    sq_ph <= 3'd2;
                end
                if (sq_ph == 3'd2) begin
                    sq_lo <= {8'd0,sq_pp[0]} + ({8'd0,sq_pp[1]} << 8);
                    sq_hi <= {8'd0,sq_pp[2]} + ({8'd0,sq_pp[3]} << 8);
                    sq_ph <= 3'd3;
                end
                if (sq_ph == 3'd3) begin : ps
                    reg [59:0] p;
                    p = {17'd0, sq_lo} + ({17'd0, sq_hi} << 16);
                    if (!sq_p0v) begin sq_p0 <= p; sq_p0v <= 1'b1; end
                    sq_p <= p - (sc[175] ? (sq_p0v ? sq_p0 : p) : 60'd0);
                    sq_ph <= 3'd4;
                end
                if (sq_ph == 3'd4) begin : mvw
                    reg [59:0] a; reg [31:0] dw;
                    a = {20'd0, sc[42:3]} + sq_p; dw = sq_dw;
                    // move word {n 21, m 20, dst istride 16, dst stride 32, dst base 40, dst fmt 3, dst space 2,
                    //            src istride 16, src stride 32, src base 40, src fmt 3, src space 2}
                    sq_mv <= {sc[90:70], 20'd1, 16'd1, 32'd0, {8'd0, dw}, (sc[2:0] == 3'd5) ? 3'd5 : 3'd0, 2'd1,
                              16'd1, 32'd0, a[39:0], sc[2:0], 2'd0};
                    sq_ph <= 3'd0; sq_e <= sq_e + 20'd1; sq_dw <= sq_dw + sc[154:123];
                    if (B2 != 0 && a[SBIT +: 2] != 2'(QS)) begin          // B2: another stack's row: skipped
                        if (sq_e + 20'd1 == sc[174:155]) begin sq_act <= 1'b0; sq_skd <= 1'b1; end
                    end else begin
                        sq_mv_v <= 1'b1; sq_wait <= 1'b1;
                        sq_last <= sq_e + 20'd1 == sc[174:155];
                    end
                end
                if (sq_wait && m_done) begin
                    sq_wait <= 1'b0;
                    if (sq_last) sq_act <= 1'b0;
                end
                if (m_fault) begin sq_act <= 1'b0; sq_wait <= 1'b0; end
            end
        end
    end
`ifndef SYNTHESIS
    reg trc; initial trc = $test$plusargs("DMA_TRACE");
    always @(posedge clk) if (trc && rst_n && d_mv_v && d_mv_rdy)
        $display("ENGINES move -> %s ssp %0d sf %0d src %h sst %0d sis %0d dsp %0d df %0d dst %h dstr %0d dis %0d m %0d n %0d",
                 to_b ? "back" : to_f ? "front" : "mover", d_mv[1:0], d_mv[4:2], d_mv[44:5], d_mv[76:45], d_mv[92:77], d_mv[94:93], d_mv[97:95], d_mv[137:98],
                 d_mv[169:138], d_mv[185:170], d_mv[205:186], d_mv[226:206]);
`endif

    assign d_fdone = m_fence_done;
    // The record adapter has one posted-background reservation. Keep that actual
    // reservation charged until completion before accepting another standalone
    // or I-list record; current SQ row progression retains its existing handshake.
    // Two-entry skid: both payload slots are flops; head is the output pin register.
    // Source acceptance is local space, independent of the downstream ready pin.
    reg [1:0] move_n; reg [226:0] move_head, move_tail;
    wire m_rdy = move_n < 2;
    wire move_push = (sq_act ? sq_mv_v : (d_mv_v && !m_pend && !to_f && !to_b && !rd_act && b_quiet)) && m_rdy;
    wire move_pop = move_n != 0 && pin_m_rdy;
    wire [226:0] move_in = (sq_act ? sq_mv : d_mv) ^ ((MUT_SEAM == 1) ? (227'd1 << 206) : 227'd0);
    reg move_valid;
    assign mover_v = move_valid;
    assign mover_cmd = move_head;
    always @(posedge clk or negedge rn) begin
       if (!rn) begin move_n <= 0; move_valid <= 0; end
       else begin
          move_valid <= (move_n + {1'b0,move_push} - {1'b0,move_pop}) != 0;
          case ({move_push,move_pop})
             2'b10: begin
                if (move_n == 0) move_head <= move_in; else move_tail <= move_in;
                move_n <= move_n + 1'b1;
             end
             2'b01: begin move_head <= move_tail; move_n <= move_n - 1'b1; end
             2'b11: begin
                if (move_n == 1) move_head <= move_in;
                else begin move_head <= move_tail; move_tail <= move_in; end
             end
             default: begin end
          endcase
       end
    end
    assign mover_fv = d_fv && b_quiet;

    assign dma_ret = {d_wq, d_fault, d_done, d_rdy};
endmodule
`default_nettype wire

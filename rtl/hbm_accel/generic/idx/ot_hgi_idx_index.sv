`timescale 1ns/1ps
`default_nettype none
// HGI-1 IDX.INDEX frame adapter (hgi-takeover 2026-10-09, spec G18 / review 10:45 decision 2): one IDX.INDEX record
// (op 0) = one frame of the DS native selector hfd_idx_sel_native_qend (physical/hbm_accel_die_views/index).
//
//   param [11:0] k (1 .. 512), [12] cand_en, [13] keep_en; imm_a = n (keys this die, <= 4 x 2,736); imm_b = layer
//   A  VM FP32 [4,096] the post-RoPE index query, head-major (head h = words 128h .. 128h+127), base 8-word aligned
//   B  VM FP32 [32]    the scaled head weights as BF16 values in FP32 words (low 16 bits must be 0)
//   C  VM U32  [44]    keep bitmap (keep_en): quarter q bit j = word 11q + j/32, bit j%32 (j < 342)
//   O  VM U32  [k]     local top-k ids in the selector's order (quarter order = ascending id)
//   R  VM FP32 [k]     their values: BF16 score << 16, or -inf (0xFF800000) for a masked (ninf) lane
//   D  VM, cand_en: block candidates: ids (U32) at D.base + j, values (BF16 << 16) at D.base + D.stride + j
// Frame: keep beats (kin, 4 quarters, keep_en) -> frame start fs {keep_en, cand_en, k10, n_die14, rank7, pos20,
// gen 0, job 0} -> 128 query blocks qb {w16 = B[h][31:16], data = 32 words of A, blk, head} on 4 credits (qbr) ->
// the top-k beats (to, 16 lanes) and candidate beats (co, 2 lanes) are compacted lane by lane into O / R / D through
// sector packers (masked 8-word VM writes); toc / coc return one credit per beat consumed; done when the selector's
// done (ev[0]) is seen, both streams have delivered their last beat and every packer is flushed; ev[1] (selector
// fault: refused key, overflow, replay) or an illegal operand -> fault.  One VM request outstanding (the VM packet ABI).
module ot_hgi_idx_index #(
    parameter integer MUT = 0     // bench mutants: 1 head weight of the next head, 2 R written from the wrong lane
) (
    input  wire          clk,
    input  wire          rst_n,
    // frame command (from ot_hgi_idx_unit's record station)
    input  wire          go,
    input  wire [11:0]   k,
    input  wire          cand_en, keep_en,
    input  wire [31:0]   n,
    input  wire [6:0]    rank,
    input  wire [19:0]   pos,
    input  wire [17:0]   a_base, b_base, c_base, o_base, r_base, d_base,
    input  wire [17:0]   d_stride,
    input  wire          has_r,
    output reg           done,
    output reg           fault,
    // VM packet client (one outstanding)
    output reg  [337:0]  vmq,
    input  wire [273:0]  vmr,
    // native selector
    output reg  [89:0]   fs,
    output reg  [1047:0] qb,
    input  wire          qbr,
    output reg  [344:0]  kin,
    input  wire [611:0]  to,
    output reg           toc,
    input  wire [71:0]   co,
    output reg           coc,
    input  wire [1:0]    ev
);
    // ---------------------------------------------------------------- VM reader: word w -> one-sector cache
    reg vm_pend, vm_rd; reg [14:0] c_sec; reg c_ok; reg [255:0] c_dat; reg [14:0] rd_sec;
    // ---------------------------------------------------------------- packers: 0 O, 1 R, 2 D ids, 3 D values
    reg [17:0] pk_a [0:3];                 // next word address
    reg [255:0] pk_d [0:3]; reg [7:0] pk_m [0:3]; reg [3:0] pk_full;   // pending sector content / word mask
    reg [14:0] pk_s [0:3];                 // sector of the pending content
    // ---------------------------------------------------------------- frame state
    localparam S_IDLE = 4'd0, S_BW = 4'd1, S_KEEP = 4'd2, S_KSEND = 4'd3, S_FS = 4'd4, S_RUN = 4'd5, S_FLUSH = 4'd6,
               S_DONE = 4'd7;
    reg [3:0] st;
    reg [15:0] wts [0:31];                 // head weights
    reg [5:0] wi;                          // weight / keep word index
    reg [351:0] keep [0:3];
    reg [1:0] kq; reg [2:0] kgap;
    reg [7:0] qblk; reg [4:0] qw;          // query block being assembled, word within it (32 words)
    reg [1023:0] qdat; reg qfull;          // assembled block awaiting a credit
    reg [2:0] qcred;
    reg sel_done, to_last, co_last, bad;
    // output beat FIFOs (credit-sized: the selector holds at most OCRED = 8 beats in flight)
    reg [611:0] tf [0:7]; reg [2:0] tfh, tft; reg [3:0] tfn;
    reg [71:0]  cf [0:7]; reg [2:0] cfh, cft; reg [3:0] cfn;
    reg [4:0] tl; reg [1:0] cl;            // lane cursor within the head beat
    reg [31:0] nout, ncand;
    wire [17:0] a_word = a_base + {qblk, qw};
    // which packer has a complete (or final) sector to write
    reg wp_v; reg [1:0] wp;
    integer i;
    always @* begin
        wp_v = 1'b0; wp = 2'd0;
        for (i = 3; i >= 0; i = i - 1) if (pk_full[i]) begin wp_v = 1'b1; wp = i[1:0]; end
    end
    // a packer accepts a word when its pending sector is not full and the word lands in that sector (else full first)
    function automatic pk_ok(input integer p);
        pk_ok = !pk_full[p];
    endfunction
    // lane values of the head beats
    wire [611:0] th = tf[tfh]; wire [71:0] ch = cf[cfh];
    wire t_lv = th[4 + tl]; wire [19:0] t_idx = th[292 + 20*tl +: 20]; wire [15:0] t_val = th[36 + 16*tl +: 16];
    wire t_ninf = th[20 + tl];
    wire [4:0] tl_r = (MUT == 2) ? ((tl + 5'd1) & 5'd15) : tl;
    wire [15:0] t_valr = th[36 + 16*tl_r +: 16]; wire t_ninfr = th[20 + tl_r];
    wire c_lv = ch[4 + cl]; wire [16:0] c_blk = ch[38 + 17*cl +: 17]; wire [15:0] c_val = ch[6 + 16*cl +: 16];
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            st <= S_IDLE; done <= 1'b0; fault <= 1'b0; vmq <= 338'd0; vm_pend <= 1'b0; c_ok <= 1'b0;
            fs <= 90'd0; qb <= 1048'd0; kin <= 345'd0; toc <= 1'b0; coc <= 1'b0; pk_full <= 4'd0;
            tfh <= 3'd0; tft <= 3'd0; tfn <= 4'd0; cfh <= 3'd0; cft <= 3'd0; cfn <= 4'd0;
            for (i = 0; i < 4; i = i + 1) begin pk_m[i] <= 8'd0; pk_d[i] <= 256'd0; end
        end else begin
            done <= 1'b0; fault <= 1'b0; vmq[337] <= 1'b0; fs[0] <= 1'b0; qb[0] <= 1'b0; kin[0] <= 1'b0;
            toc <= 1'b0; coc <= 1'b0;
            // ---- capture output beats (always: the selector sends only against credits)
            if (to[0]) begin tf[tft] <= to; tft <= tft + 3'd1; end
            if (co[0]) begin cf[cft] <= co; cft <= cft + 3'd1; end
            if (qbr) qcred <= qcred + 3'd1;
            if (ev[0]) sel_done <= 1'b1;
            if (ev[1] && st != S_IDLE) bad <= 1'b1;
            // ---- VM responses
            if (vmr[273]) begin
                vm_pend <= 1'b0;
                if (vm_rd) begin c_ok <= 1'b1; c_sec <= rd_sec; c_dat <= vmr[255:0]; end
            end
            case (st)
                S_IDLE: if (go) begin
                    if (k == 12'd0 || k > 12'd512 || n > 32'd10944 || rank >= 7'd96 || a_base[2:0] != 3'd0)
                        fault <= 1'b1;
                    else begin
                        st <= S_BW; wi <= 6'd0; c_ok <= 1'b0; sel_done <= 1'b0; to_last <= 1'b0; co_last <= !cand_en;
                        bad <= 1'b0; qblk <= 8'd0; qw <= 5'd0; qfull <= 1'b0; qcred <= 3'd4; tl <= 5'd0; cl <= 2'd0;
                        nout <= 32'd0; ncand <= 32'd0; kgap <= 3'd0; tfn <= 4'd0; cfn <= 4'd0; tfh <= 3'd0; tft <= 3'd0; cfh <= 3'd0; cft <= 3'd0;
                        pk_a[0] <= o_base; pk_a[1] <= r_base; pk_a[2] <= d_base; pk_a[3] <= d_base + d_stride;
                        for (i = 0; i < 4; i = i + 1) begin pk_m[i] <= 8'd0; pk_s[i] <= 15'd0; end
                    end
                end
                // ---- head weights B[0..31]
                S_BW: if (!vm_pend) begin
                    if (c_ok && c_sec == (b_base + wi) >> 3) begin
                        if (c_dat[((b_base + wi) & 18'd7) * 32 +: 16] != 16'd0) bad <= 1'b1;
                        wts[wi[4:0]] <= c_dat[((b_base + wi) & 18'd7) * 32 + 16 +: 16];
                        if (wi == 6'd31) begin wi <= 6'd0; st <= keep_en ? S_KEEP : S_FS; end
                        else wi <= wi + 6'd1;
                    end else begin
                        vm_pend <= 1'b1; vm_rd <= 1'b1; rd_sec <= (b_base + wi) >> 3;
                        vmq <= {1'b1, 1'b0, {12'd0, 15'((b_base + wi) >> 3), 5'd0}, 256'd0, 32'd0, 16'h0910};
                    end
                end
                // ---- keep bitmap C[0..43]
                S_KEEP: if (!vm_pend) begin
                    if (c_ok && c_sec == (c_base + wi) >> 3) begin
                        keep[wi / 11][(wi % 11) * 32 +: 32] <= c_dat[((c_base + wi) & 18'd7) * 32 +: 32];
                        if (wi == 6'd43) begin st <= S_KSEND; kq <= 2'd0; kgap <= 3'd0; end
                        else wi <= wi + 6'd1;
                    end else begin
                        vm_pend <= 1'b1; vm_rd <= 1'b1; rd_sec <= (c_base + wi) >> 3;
                        vmq <= {1'b1, 1'b0, {12'd0, 15'((c_base + wi) >> 3), 5'd0}, 256'd0, 32'd0, 16'h0911};
                    end
                end
                S_KSEND: begin
                    if (kgap != 3'd0) kgap <= kgap - 3'd1;
                    else begin
                        kin <= {keep[kq][341:0], kq, 1'b1}; kgap <= 3'd3;
                        if (kq == 2'd3) st <= S_FS; else kq <= kq + 2'd1;
                    end
                end
                S_FS: if (kgap == 3'd0) begin
                    fs <= {keep_en, cand_en, k[9:0], n[13:0], rank, pos, 4'd0, 32'd0, 1'b1}; st <= S_RUN;
                end else kgap <= kgap - 3'd1;
                S_RUN: begin
                    // ---- query blocks: assemble 32 words of A, send against a credit
                    if (qfull && qcred != 3'd0) begin
                        qb <= {wts[(MUT == 1) ? 5'((qblk - 8'd1) / 4 + 1) : 5'((qblk - 8'd1) / 4)], qdat,
                               2'((qblk - 8'd1) % 4), 5'((qblk - 8'd1) / 4), 1'b1};
                        qcred <= qcred - 3'd1 + {2'd0, qbr}; qfull <= 1'b0;
                    end
                    if (!qfull && qblk != 8'd128 && !vm_pend && !wp_v) begin
                        if (c_ok && c_sec == a_word[17:3]) begin
                            qdat[qw * 32 +: 32] <= c_dat[a_word[2:0] * 32 +: 32];
                            qw <= qw + 5'd1;
                            if (qw == 5'd31) begin qfull <= 1'b1; qblk <= qblk + 8'd1; end
                        end else begin
                            vm_pend <= 1'b1; vm_rd <= 1'b1; rd_sec <= a_word[17:3];
                            vmq <= {1'b1, 1'b0, {12'd0, a_word[17:3], 5'd0}, 256'd0, 32'd0, 16'h0912};
                        end
                    end
                    // ---- top-k lanes -> O, R
                    if (tft != tfh && pk_ok(0) && (!has_r || pk_ok(1))) begin
                        if (t_lv) begin
                            pk_d[0][pk_a[0][2:0] * 32 +: 32] <= {12'd0, t_idx}; pk_m[0][pk_a[0][2:0]] <= 1'b1;
                            pk_s[0] <= pk_a[0][17:3]; pk_a[0] <= pk_a[0] + 18'd1;
                            if (pk_a[0][2:0] == 3'd7) pk_full[0] <= 1'b1;
                            if (has_r) begin
                                pk_d[1][pk_a[1][2:0] * 32 +: 32] <= t_ninfr ? 32'hFF80_0000 : {t_valr, 16'd0};
                                pk_m[1][pk_a[1][2:0]] <= 1'b1; pk_s[1] <= pk_a[1][17:3]; pk_a[1] <= pk_a[1] + 18'd1;
                                if (pk_a[1][2:0] == 3'd7) pk_full[1] <= 1'b1;
                            end
                            nout <= nout + 32'd1;
                        end
                        if (tl == 5'd15) begin
                            tl <= 5'd0; tfh <= tfh + 3'd1; toc <= 1'b1;
                            if (th[1]) to_last <= 1'b1;
                        end else tl <= tl + 5'd1;
                    end
                    // ---- candidate lanes -> D
                    if (cft != cfh && pk_ok(2) && pk_ok(3)) begin
                        if (c_lv) begin
                            pk_d[2][pk_a[2][2:0] * 32 +: 32] <= {15'd0, c_blk}; pk_m[2][pk_a[2][2:0]] <= 1'b1;
                            pk_s[2] <= pk_a[2][17:3]; pk_a[2] <= pk_a[2] + 18'd1;
                            if (pk_a[2][2:0] == 3'd7) pk_full[2] <= 1'b1;
                            pk_d[3][pk_a[3][2:0] * 32 +: 32] <= {c_val, 16'd0}; pk_m[3][pk_a[3][2:0]] <= 1'b1;
                            pk_s[3] <= pk_a[3][17:3]; pk_a[3] <= pk_a[3] + 18'd1;
                            if (pk_a[3][2:0] == 3'd7) pk_full[3] <= 1'b1;
                            ncand <= ncand + 32'd1;
                        end
                        if (cl == 2'd1) begin
                            cl <= 2'd0; cfh <= cfh + 3'd1; coc <= 1'b1;
                            if (ch[1]) co_last <= 1'b1;
                        end else cl <= cl + 2'd1;
                    end
                    if (bad) begin st <= S_IDLE; fault <= 1'b1; end
                    else if (sel_done && to_last && co_last && tft == tfh && cft == cfh && qblk == 8'd128 && !qfull) begin
                        st <= S_FLUSH;
                        for (i = 0; i < 4; i = i + 1) if (pk_m[i] != 8'd0) pk_full[i] <= 1'b1;
                    end
                end
                S_FLUSH: if (!wp_v && !vm_pend) begin st <= S_IDLE; done <= 1'b1; end
                default: st <= S_IDLE;
            endcase
            // ---- packer writes (masked sector writes), one outstanding request
            if (wp_v && !vm_pend && !(st == S_BW || st == S_KEEP) && !(vmq[337])) begin
                vm_pend <= 1'b1; vm_rd <= 1'b0;
                vmq <= {1'b1, 1'b1, {12'd0, pk_s[wp], 5'd0}, pk_d[wp],
                        {{4{pk_m[wp][7]}}, {4{pk_m[wp][6]}}, {4{pk_m[wp][5]}}, {4{pk_m[wp][4]}},
                         {4{pk_m[wp][3]}}, {4{pk_m[wp][2]}}, {4{pk_m[wp][1]}}, {4{pk_m[wp][0]}}}, 16'h0913};
                pk_full[wp] <= 1'b0; pk_m[wp] <= 8'd0;
            end
        end
    end
endmodule
`default_nettype wire

`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// x store of the Qwen SM macro (GPU-organised HBM comparator): NM hard SRAM
// macros (ot_sram_1r1w_1024x256) holding the op's activation fragments, and
// a double-buffered fragment register in front of the tensor core.
//
// A fragment is every lane's x for every column at one (group, k-step); the
// row-slot issue uses one per slot revolution (IL = 8 cycles).  It is
// SUBS = FRAGW / (NM * 256) macro words deep: fragment a is word a * SUBS + k
// of every macro, and macro m's word k is fragment bits [(k*NM + m)*256, +256).
// The prefetcher walks the op's fragment order (0 .. nfrag-1 once per row
// block) into the free buffer, one word of every macro a cycle, so a
// fragment loads in SUBS cycles plus the read latency.  `pop` (the issue
// leaving the head fragment) frees it; the issue reads the buffer it named
// (`rsel`) one cycle later, so the freed buffer is overwritten only after
// that.  `ready` says the head fragment is complete by the next cycle.
// ---------------------------------------------------------------------------
module ot_gpu_xstore #(
    parameter integer NM    = 16,
    parameter integer FRAGW = 32768,
    parameter integer AW    = 10,
    parameter integer XWM   = 8         // macros written per x-broadcast beat (256 B = the model's X_BCAST_BPC)
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              start,
    input  wire [15:0]       op_nfrag,      // fragments per row block (G * c)
    input  wire [15:0]       op_blocks,     // row blocks
    input  wire              pop,
    output wire              ready,
    output wire              head_sel,
    input  wire              rsel,
    output wire [FRAGW-1:0]  frag,
    input  wire              w_en,
    input  wire [AW-1:0]     w_addr,
    input  wire [((NM + XWM - 1) / XWM > 1 ? $clog2((NM + XWM - 1) / XWM) : 1)-1:0] w_grp,
    input  wire [XWM*256-1:0] w_data
);
    localparam integer SUBS = FRAGW / (NM * 256);
    localparam integer SW = (SUBS <= 1) ? 1 : $clog2(SUBS);
    reg [FRAGW-1:0] buf0, buf1;
    reg [1:0]  bvalid;
    reg        head;
    reg        loading, lslot;
    reg [SW:0] k;
    reg [15:0] fa, fb;
    reg        more;
    reg        rd_v, rd_last, rd_slot;
    reg [SW-1:0] rd_k;
    wire [NM*256-1:0] rd;
    // a load starts into a buffer that is neither valid nor being loaded
    wire       tgt = bvalid[head] ? ~head : head;
    wire       tgt_free = !bvalid[tgt] && !(rd_v && rd_last && rd_slot == tgt);
    wire       rd_go = more && (loading ? (k < SUBS) : tgt_free);
    wire       slot_now = loading ? lslot : tgt;
    wire [AW-1:0] raddr = fa * SUBS + k[SW-1:0];
    genvar m;
    generate for (m = 0; m < NM; m = m + 1) begin : g_m
        ot_sram_1r1w_1024x256_m2_r2c2 u_sram (
            .clk(clk), .r_ce_in(rd_go), .r_addr_in(raddr), .rd_out(rd[256*m +: 256]),
            .w_ce_in(w_en && (w_grp == m / XWM)), .w_addr_in(w_addr), .wd_in(w_data[256*(m % XWM) +: 256]),
            .w_mask_in({256{1'b1}}),
            .rr_en(2'b00), .rr_addr(18'd0), .cr_en(2'b00), .cr_sel(16'd0));
    end endgenerate
    assign ready = bvalid[head] || (rd_v && rd_last && rd_slot == head);
    assign head_sel = head;
    assign frag = rsel ? buf1 : buf0;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            bvalid <= 2'b00; head <= 1'b0; loading <= 1'b0; lslot <= 1'b0; k <= 0; fa <= 0; fb <= 0;
            more <= 1'b0; rd_v <= 1'b0; rd_last <= 1'b0; rd_slot <= 1'b0; rd_k <= 0;
        end else if (start) begin
            bvalid <= 2'b00; head <= 1'b0; loading <= 1'b0; k <= 0; fa <= 0; fb <= 0; rd_v <= 1'b0;
            more <= (op_nfrag != 0) && (op_blocks != 0);
        end else begin
            rd_v <= rd_go;
            rd_k <= k[SW-1:0];
            rd_slot <= slot_now;
            rd_last <= rd_go && (k == SUBS - 1);
            if (rd_go) begin
                if (!loading) begin loading <= 1'b1; lslot <= tgt; end
                if (k == SUBS - 1) begin
                    k <= 0;
                    loading <= 1'b0;
                    if (fa == op_nfrag - 1) begin
                        fa <= 0;
                        if (fb == op_blocks - 1) more <= 1'b0;
                        else fb <= fb + 1'b1;
                    end else fa <= fa + 1'b1;
                end else k <= k + 1'b1;
            end
            if (rd_v && rd_last) bvalid[rd_slot] <= 1'b1;
            if (pop) begin
                bvalid[head] <= 1'b0;
                head <= ~head;
            end
        end
    end
    // fragment buffers: word k of macro m lands in bits [(k*NM + m)*256, +256) -- constant slices per k,
    // selected by a decoded enable (no variable part-selects on the 32-Kbit vectors)
    genvar kk, mm;
    generate for (kk = 0; kk < SUBS; kk = kk + 1) begin : g_k
        wire en = rd_v && (rd_k == kk);
        for (mm = 0; mm < NM; mm = mm + 1) begin : g_mw
            always @(posedge clk) begin
                if (en && rd_slot)  buf1[(kk * NM + mm) * 256 +: 256] <= rd[256*mm +: 256];
                if (en && !rd_slot) buf0[(kk * NM + mm) * 256 +: 256] <= rd[256*mm +: 256];
            end
        end
    end endgenerate
endmodule

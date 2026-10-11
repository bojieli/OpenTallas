`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// HGI-1 DMA FRONT (hgi-takeover 2026-10-10; coordinator: the svc-side DMA stream feeds the VM wide port at up to 1 KB a
// cycle, hbm-forks builds the svc side, hgi-takeover the front and the VM side).  Interface spec: hgi-takeover.log
// "SPEC for hbm-forks" (03:40 PT).
//
// Takes a DMA LOAD (move word of ot_hgi_dma_mover, 227 b) whose shape is eligible:
//   src HBM, dst VM, istride 1 both sides, source row base and row stride 32 B aligned, n x esize a multiple of 32 B,
//   destination row base and row stride multiples of 8 words, formats FP32 / U32 / BF16 / FP8E4M3 / INT8 -> VM words;
// (the DMA unit sends every other move to the sector / serial mover), and
//   R  splits it into per-stack requests {tag, nsec <= 256, addr}, one a cycle: rows in windows of 4, chunk by chunk
//      round robin over the window's rows (a chunk = up to 256 sectors); the stack = address bits [SBIT+1:SBIT]); the tag remembers the run's first VM sector;
//   L  pin-flops the NS x NL data lanes, computes each beat's VM sector (tag base + idx x K) and lands it in an LD-entry
//      lane FIFO (source sector in a 128 x 256 SRAM macro a lane, VM sector in flops; credit LD a lane = the svc's initial
//      credit; the credit returns when the entry's read issues); a tag is free again once all its beats landed; the read
//      (macro output register) fills a 3-entry skid, issued on registered occupancy only;
//   C  per lane two out buffers {VM sector, source sector}: the skid head loads the idle one once every destination slot
//      (K = 4 / esize: FP32 / U32 1, BF16 2, FP8 / INT8 4) of the active one was picked;
//   X  X1 per bank a rotating-priority pick among the lanes' active buffers (each lane's K slots sit in K consecutive
//      banks), registered; X2 per bank the AND-OR mux of the picked lane's buffer (the one active in X1's cycle), decoded
//      for its slot exactly as the mover (BF16 << 16, E4M3 exact, NaN -> 0x7FC00000, INT8 exact), registered into the VM
//      wide lane = the bank (NB destination sectors a cycle);
//   done when every destination sector's wide write is acknowledged.
//   Fault (sticky until reset): a request run crossing a stack or ending beyond STACK_BYTES, an svc fault beat, a beat without a credit.
// Rate: NS x NL source sectors a cycle in (the svc lane rate), NB destination sectors a cycle out (the VM port).
// INDEXED ROW STREAM (spec 3.3, hgi-1010/c 2026-10-10; ROW_GATHER's list-order load, Engram rows, verify embeddings):
//   ix_cmd {rebase 1, cnt 20, dstride 32, dbase 32, n 21, dyn_mul 27, abase 40, fmt 3} (176 b: fmt [2:0], abase [42:3],
//   dyn_mul [69:43], n [90:70], dbase [122:91], dstride [154:123], cnt [174:155], rebase [175]) + the id list on id_v /
//   id_rdy / id 32.  rebase 1: abase is the CP's EFFECTIVE base, which already holds id_0 x dyn_mul (spec 3.3 with
//   X = U32(VM[I + L])), so row e reads abase + (id_e - id_0) x dyn_mul
//   (list order, exactly cnt ids; the DMA unit reads them from the I table).  Row e = the A row of id_e: source byte address
//   abase + id_e x dyn_mul (n elements of fmt, whole sectors), lands at VM word dbase + e x dstride.  The id pipeline: id
//   pin flop -> two 16 x 27 partial products (registered) -> address add (registered, alignment / 37-bit range check) -> a
//   4-row queue; the request generator issues each row as runs of <= 256 sectors on the row's own stack (rows of one list
//   spread over all stacks by their ids), one request a cycle, exactly as the strided form; landing / convert / crossbar
//   are shared.  Faults: a misaligned row (abase or dyn_mul not 32 B multiples), an address beyond 37 bits, a run
//   crossing a stack.  Eligibility of n / dbase / dstride as for the strided form (the DMA unit checks; the front faults
//   a non-sector n).
// MUT (bench): 1 BF16 halves mirrored within the sector: must FAIL; 2 a tag freed 8 beats early: must FAIL;
//   3 the id's high partial product dropped (ids >= 2^16 alias): must FAIL; 4 the destination row pointer advances on
//   every second row only: must FAIL; 5 the rebase (id_0 x dyn_mul) not removed: must FAIL.
//   AP (hgi-1010 b): 6 the VM's per-bank stop ignored, 7 the ap bit never set (the slot load lands in VM): must FAIL.
// ---------------------------------------------------------------------------------------------------------------------
module ot_hgi_dma_front #(
    parameter integer NS = 4,
    parameter integer NL = 8,
    parameter integer SBIT = 35,          // stack select = HBM byte address [SBIT+1:SBIT] (ot_hbm_loader_kport_address)
    parameter [35:0] STACK_BYTES = 36'd22500000000,   // a run must end inside its stack's capacity
    parameter integer NB = 32,            // VM wide lanes = VM banks (power of 2): lane p carries a sector of bank p
    parameter integer LD = 16,            // lane buffer depth = the svc's initial credit a lane (power of 2); must cover the
                                          // credit round trip (svc lane reg -> die hops -> pin flop -> land -> pop -> credit
                                          // reg -> die hops -> svc pin flop): 4 + 2 x hops + svc cycles; 4 caps a lane at 4 / RTT
    parameter integer AP = 0,             // hgi-1010 b: 1 = the HC weight APERTURE (VM words >= 2^18): the VM lane grows an ap
                                          //   bit {v, ap, sector 15, data, mask} (ap = the 18-bit VM sector >= 32,768; sector =
                                          //   that minus 32,768); a sector past the two slots (>= 40,960) faults; bank b picks
                                          //   only while wl_rdy[b] (the VM unit's aperture queue stop, pin-flopped here)
    parameter integer MUT = 0
) (
    input  wire                  clk,
    input  wire                  rst_n,
    input  wire                  mv_v,
    output wire                  mv_rdy,
    input  wire [226:0]          mv,
    output reg                   mv_done,
    output reg                   mv_fault,
    // indexed row stream command + id list
    input  wire                  ix_v,
    output wire                  ix_rdy,
    input  wire [175:0]          ix_cmd,
    input  wire                  id_v,
    output wire                  id_rdy,
    input  wire [31:0]           id,
    // requests per stack {v, tag 4, nsec 9, addr 37}
    output reg  [NS*51-1:0]      dq,
    input  wire [NS-1:0]         dq_rdy,
    // data per stack x lane {v, fault, tag 4, idx 8, data 256}
    input  wire [NS*NL*270-1:0]  dd,
    output wire [NS*NL-1:0]      dd_cr,
    // VM wide write port, NB lanes {v, sector 15, wdata 256, word mask 8}
    output wire [NB*(280+AP)-1:0] wl,
    input  wire [NB-1:0]         wl_done,
    input  wire [NB-1:0]         wl_rdy
);
    reg [NB-1:0] wl_rdy_q; reg ap_rng;
    always @(posedge clk or negedge rst_n) if (!rst_n) wl_rdy_q <= '1; else wl_rdy_q <= wl_rdy;
    localparam integer NIN = NS * NL;
    localparam integer LW = $clog2(LD);
    localparam integer BW = $clog2(NB);
    localparam integer RW = $clog2(NIN);
    function automatic [31:0] i8_f(input [7:0] c);
        reg [7:0] a; reg [2:0] p; integer k;
        begin
            a = c[7] ? (~c + 8'd1) : c; p = 3'd0;
            for (k = 0; k < 8; k = k + 1) if (a[k]) p = k[2:0];
            i8_f = (a == 8'd0) ? 32'd0 : {c[7], 8'd127 + {5'd0, p}, ({15'd0, a} << (5'd23 - {2'd0, p})) & 23'h7FFFFF};
        end
    endfunction
    function automatic [31:0] e4m3_f(input [7:0] c);
        reg [3:0] e; reg [2:0] m; reg [1:0] p;
        begin
            e = c[6:3]; m = c[2:0];
            if (e == 4'hF && m == 3'h7) e4m3_f = 32'h7FC00000;
            else if (e == 4'd0) begin
                if (m == 3'd0) e4m3_f = {c[7], 31'd0};
                else begin
                    p = m[2] ? 2'd2 : m[1] ? 2'd1 : 2'd0;
                    e4m3_f = {c[7], 8'd127 - 8'd9 + {6'd0, p}, ({20'd0, m} << (5'd23 - {3'd0, p})) & 23'h7FFFFF};
                end
            end else e4m3_f = {c[7], 8'd120 + {4'd0, e}, m, 20'd0};
        end
    endfunction
    function automatic [2:0] esz(input [2:0] f);
        esz = (f == 3'd0 || f == 3'd5) ? 3'd4 : (f == 3'd1) ? 3'd2 : 3'd1;
    endfunction
    // ---------------------------------------------------------------- reset relay: a region a stack's lanes, + control
    wire [NS:0] rl;
    ot_rst_relay #(.REGIONS(NS + 1)) u_rst (.clk(clk), .rst_n_in(rst_n), .rst_n(rl));
    wire rc = rl[NS];
    // ---------------------------------------------------------------- command station (registered)
    reg cv_q; reg [226:0] cm_q;
    reg busy; reg [2:0] sf; reg [1:0] ks;                  // ks = log2 K (destination sectors per source sector)
    reg [36:0] ra; reg [31:0] sst;                          // the current row's source byte address, row stride
    reg [31:0] rdw; reg [31:0] dst_w;                       // the current row's VM word address, row stride
    // rows are issued in windows of up to 4 (round robin chunk by chunk: rows striped over the stacks keep all stacks busy)
    reg [19:0] r_left;                                      // rows left after the current window
    reg [1:0] wi, wn;                                       // the window row being issued, the window's last row
    reg [36:0] wa; reg [31:0] wd;                           // that row's source byte address, VM word address
    reg [23:0] rsec, r_off;                                 // sectors a row, the chunk's first sector (all window rows)
    reg r_done;
    reg [31:0] issued, wrote;                               // destination sectors requested / acknowledged
    assign mv_rdy = rc && !busy && !cv_q && !ixc_q && !mv_fault;
    // ---------------------------------------------------------------- indexed row stream state
    reg ixc_q; reg [175:0] ixm_q;                           // command station
    reg ixm;                                                // the running move is an indexed stream
    reg [39:0] ix_ab; reg [26:0] ix_mul; reg [19:0] ids_left;
    reg [31:0] ix_dp; reg [31:0] ix_ds;                     // the next row's VM word address, the row stride
    reg [1:0] ix_par;                                       // MUT 4
    reg i1_v; reg [31:0] i1_id;                             // id pin flop
    reg i2_v; reg [42:0] i2_lo, i2_hi; reg [31:0] i2_dw;    // partial products, the row's VM word address
    reg i3_v; reg [59:0] i3_p; reg [31:0] i3_dw;           // the product id x dyn_mul
    reg i4_v; reg [37:0] i4_a; reg [31:0] i4_dw;           // address
    reg ix_rb, ix_first; reg [59:0] ix_p0;                 // rebase: the first row's product
    reg [36:0] rq_a [0:3]; reg [17:0] rq_ds [0:3];          // row queue {address, first VM sector}
    reg [1:0] rq_h, rq_t; reg [2:0] rq_n;
    wire [3:0] ix_inflight = {1'b0, rq_n} + {3'd0, i1_v} + {3'd0, i2_v} + {3'd0, i3_v} + {3'd0, i4_v};
    assign ix_rdy = rc && !busy && !cv_q && !ixc_q && !mv_fault;
    assign id_rdy = busy && ixm && !mv_fault && ids_left != 20'd0 && ix_inflight < 4'd4;
    wire id_take = id_v && id_rdy;
    // ---------------------------------------------------------------- tags
    reg [15:0] tag_busy;
    reg [17:0] tg_dsec [0:15];                              // the run's first VM sector
    reg [8:0]  tg_left [0:15];                              // beats still to land
    reg [4:0] ft;
    always @* begin ft = 5'd16; for (integer t = 15; t >= 0; t = t - 1) if (!tag_busy[t]) ft = 5'(t); end
    // ---------------------------------------------------------------- lanes
    // L  pin flop -> lane FIFO: the source sector in an ot_sram_1r1w_128x256 macro a lane (LD of its 128 rows), the beat's
    //    VM sector in flops -> read (the macro's output register) -> 3-entry skid (a read issues on registered occupancy
    //    only: lane FIFO not empty, skid + read in flight < 3) -> one of two out buffers ({sector, source}, alternating);
    //    the credit returns when the read issues (the entry leaves the FIFO)
    // X1 per bank a rotating-priority pick over the lanes' active buffers (lane i asks bank b with slot (b - ob_i) mod NB
    //    when that is < 4 and the slot is still valid); the pick is registered (one-hot over the lanes)
    // X2 per bank the AND-OR mux of the picked lane's previously active buffer (a lane flips buffers only when every slot
    //    of the active one was picked, so the buffer X2 reads is never the one being refilled), the slot's conversion,
    //    registered into wl.  Data flops carry no reset; control resets from ot_rst_relay (one region a stack, + control).
    wire [NIN-1:0]     dv_w;                                // pin-flopped beat valid a lane
    wire [NIN*4-1:0]   dtag_w;                              // its tag
    wire [NIN-1:0]     lflt_w;                              // svc fault beat / beat without a credit
    wire [NIN*4-1:0]   ov_w;                                // active buffer: slots still to go
    wire [NIN*18-1:0]  ob_w;                                // active buffer: VM sector of slot 0
    wire [NIN*274-1:0] ls_w;                                // the buffer active last cycle {sector 18, source 256}
    reg [NB-1:0] wl_v; reg [278+AP:0] wl_d [0:NB-1]; reg [NB-1:0] ap_bad;
    function automatic [255:0] conv(input [255:0] s, input [2:0] f, input [1:0] j);
        reg [255:0] o; integer w; reg [7:0] b; reg [15:0] h;
        begin
            o = 256'd0;
            for (w = 0; w < 8; w = w + 1) begin
                case (f)
                    3'd1: begin h = s[({3'd0, j} * 8 + w) * 16 +: 16]; if (MUT == 1) h = s[({3'd0, j} * 8 + (7 - w)) * 16 +: 16];
                                o[w*32 +: 32] = {h, 16'd0}; end
                    3'd2: begin b = s[({3'd0, j} * 8 + w) * 8 +: 8]; o[w*32 +: 32] = e4m3_f(b); end
                    3'd4: begin b = s[({3'd0, j} * 8 + w) * 8 +: 8]; o[w*32 +: 32] = i8_f(b); end
                    default: o[w*32 +: 32] = s[w*32 +: 32];
                endcase
            end
            conv = o;
        end
    endfunction
    // ---------------------------------------------------------------- X1: per bank, rotating priority from rr
    reg [RW-1:0] rr;
    reg [NIN-1:0] req [0:NB-1]; reg [NIN-1:0] oh [0:NB-1]; reg [1:0] rslot [0:NB-1][0:NIN-1];
    reg [3:0] gnt [0:NIN-1]; reg [NB-1:0] bsel_v;
    always @* begin
        for (integer i = 0; i < NIN; i = i + 1) gnt[i] = 4'd0;
        for (integer b = 0; b < NB; b = b + 1) begin
            reg [NIN-1:0] hi; reg [NIN-1:0] pk;
            for (integer i = 0; i < NIN; i = i + 1) begin
                reg [BW-1:0] d; reg [3:0] v; d = BW'(b) - ob_w[i*18 +: BW]; v = ov_w[i*4 +: 4];
                rslot[b][i] = d[1:0];
                req[b][i] = d < BW'(4) && v[d[1:0]] && (AP == 0 || MUT == 6 || wl_rdy_q[b]);
            end
            hi = req[b] & ~((NIN'(1) << rr) - NIN'(1));
            pk = (hi != '0) ? hi : req[b];
            oh[b] = pk & (~pk + NIN'(1));                       // lowest set bit
            bsel_v[b] = req[b] != '0;
            for (integer i = 0; i < NIN; i = i + 1) if (oh[b][i]) gnt[i][rslot[b][i]] = 1'b1;
        end
    end
    reg [NIN-1:0] x_oh [0:NB-1]; reg [NB-1:0] x_v;          // the registered pick
    wire [3:0] kmask = (ks == 2'd0) ? 4'b0001 : (ks == 2'd1) ? 4'b0011 : 4'b1111;
    genvar g;
    generate for (g = 0; g < NIN; g = g + 1) begin : lg
        wire lr = rl[g / NL];
        reg dv; reg [269:0] dd_q;                             // pin flop
        reg [LW-1:0] h, t; reg [LW:0] n;                      // lane FIFO
        reg [17:0] qs [0:LD-1];                               // its entries' VM sectors
        reg rv; reg [17:0] rs; wire [255:0] rd;               // read in flight
        reg [1:0] sh, st, sn; reg [273:0] sk [0:2];           // skid
        reg ap, pa; reg [273:0] bf [0:1];                     // out buffers
        reg [3:0] ov; reg [17:0] ob; reg cr;
        wire rdi  = n != '0 && ({1'b0, sn} + {2'd0, rv}) < 3'd3;
        wire full = n == (LW+1)'(LD) && !rdi;
        wire ok   = dv && !full;
        wire fin  = (ov & ~gnt[g]) == 4'd0;
        wire ld   = fin && sn != 2'd0;
        assign dv_w[g] = dv; assign dtag_w[g*4 +: 4] = dd_q[267:264];
        assign lflt_w[g] = dv && (dd_q[268] || full);
        assign ov_w[g*4 +: 4] = ov; assign ob_w[g*18 +: 18] = ob;
        assign ls_w[g*274 +: 274] = bf[pa];
        assign dd_cr[g] = cr;
        ot_sram_1r1w_128x256_m1_r2c2 u_q (.clk(clk), .r_ce_in(rdi), .r_addr_in(7'(h)), .rd_out(rd),
            .w_ce_in(ok), .w_addr_in(7'(t)), .wd_in(dd_q[255:0]), .w_mask_in({256{1'b1}}),
            .rr_en(2'b00), .rr_addr(14'd0), .cr_en(2'b00), .cr_sel(16'd0));
        always @(posedge clk) begin                           // data: no reset
            dd_q <= dd[g*270 +: 270];
            if (ok) qs[t] <= tg_dsec[dd_q[267:264]] + (18'(dd_q[263:256]) << ks);
            if (rdi) rs <= qs[h];
            if (rv) sk[st] <= {rs, rd};
            if (ld) begin bf[!ap] <= sk[sh]; ob <= sk[sh][273:256]; end
        end
        always @(posedge clk or negedge lr) begin
            if (!lr) begin
                dv <= 1'b0; h <= '0; t <= '0; n <= '0; rv <= 1'b0; sh <= 2'd0; st <= 2'd0; sn <= 2'd0;
                ap <= 1'b0; pa <= 1'b0; ov <= 4'd0; cr <= 1'b0;
            end else begin
                dv <= dd[g*270 + 269];
                if (ok) t <= t + 1'b1;
                if (rdi) h <= h + 1'b1;
                n <= n + (LW+1)'(ok) - (LW+1)'(rdi);
                cr <= rdi;
                rv <= rdi;
                if (rv) st <= (st == 2'd2) ? 2'd0 : st + 2'd1;
                if (ld) sh <= (sh == 2'd2) ? 2'd0 : sh + 2'd1;
                sn <= sn + 2'(rv) - 2'(ld);
                pa <= ap;
                if (ld) begin ap <= !ap; ov <= kmask; end
                else ov <= ov & ~gnt[g];
            end
        end
    end endgenerate
    // ---------------------------------------------------------------- X2
    genvar xb;
    generate for (xb = 0; xb < NB; xb = xb + 1) begin : xg
        assign wl[xb*(280+AP) +: 280+AP] = {wl_v[xb], wl_d[xb]};
        always @(posedge clk) begin : x2
            reg [273:0] sv; reg [BW-1:0] d; reg [17:0] s18;
            x_oh[xb] <= oh[xb];
            sv = 274'd0;
            for (integer i = 0; i < NIN; i = i + 1) if (x_oh[xb][i]) sv = sv | ls_w[i*274 +: 274];
            d = BW'(xb) - sv[256 +: BW];
            s18 = sv[273:256] + {16'd0, d[1:0]};
            if (AP != 0) wl_d[xb] <= (279+AP)'({s18[17:15] == 3'd1 && MUT != 7, s18[14:0], conv(sv[255:0], sf, d[1:0]), 8'hFF});
            else         wl_d[xb] <= (279+AP)'({s18[14:0], conv(sv[255:0], sf, d[1:0]), 8'hFF});
            ap_bad[xb] <= (AP != 0) && x_v[xb] && (s18 >= 18'd40960);       // past the aperture's two slots
        end
    end endgenerate
    // the indexed request of this cycle (head row of the queue, its next run of <= 256 sectors)
    reg ix_try, ix_bad, ix_go, ix_pop; reg [36:0] ix_a; reg [8:0] ix_rn; reg [1:0] ix_st;
    always @* begin : ixreq
        reg [36:0] e; reg [23:0] rem;
        ix_try = busy && ixm && !r_done && ft != 5'd16 && rq_n != 3'd0;
        ix_a = rq_a[rq_h] + {9'd0, r_off[22:0], 5'd0};
        rem = rsec - r_off;
        ix_rn = (rem > 24'd256) ? 9'd256 : rem[8:0];
        e = ix_a + {19'd0, ix_rn, 5'd0} - 37'd1;
        ix_st = ix_a[SBIT +: 2];
        ix_bad = ix_try && (e[SBIT +: 2] != ix_st ||
                            ({1'b0, ix_a[SBIT-1:0]} + {{(SBIT-13){1'b0}}, ix_rn, 5'd0}) > (SBIT+1)'(STACK_BYTES));
        ix_go = ix_try && !ix_bad && (!dq[ix_st*51 + 50] || dq_rdy[ix_st]);
        ix_pop = r_off + {15'd0, ix_rn} == rsec;
    end
    // ---------------------------------------------------------------- sequential
    integer i, s, t;
    always @(posedge clk or negedge rc) begin
        if (!rc) begin
            cv_q <= 1'b0; busy <= 1'b0; mv_done <= 1'b0; mv_fault <= 1'b0; dq <= '0; wl_v <= '0; x_v <= '0;
            tag_busy <= 16'd0; rr <= '0; r_done <= 1'b1;
            issued <= 32'd0; wrote <= 32'd0;
            ixc_q <= 1'b0; ixm <= 1'b0; ids_left <= 20'd0; i1_v <= 1'b0; i2_v <= 1'b0; i3_v <= 1'b0; i4_v <= 1'b0; ix_first <= 1'b0;
            rq_h <= 2'd0; rq_t <= 2'd0; rq_n <= 3'd0;
        end else begin
            mv_done <= 1'b0;
            for (s = 0; s < NS; s = s + 1) if (dq_rdy[s]) dq[s*51 + 50] <= 1'b0;
            // ---- accept (command station, then the decode)
            if (mv_v && mv_rdy) begin cv_q <= 1'b1; cm_q <= mv; end
            if (ix_v && ix_rdy && !(mv_v && mv_rdy)) begin ixc_q <= 1'b1; ixm_q <= ix_cmd; end
            if (ixc_q) begin : ixdec
                reg [2:0] f; reg [20:0] n;
                f = ixm_q[2:0]; n = ixm_q[90:70];
                ixc_q <= 1'b0; busy <= 1'b1; ixm <= 1'b1; sf <= f;
                ks <= (f == 3'd0 || f == 3'd5) ? 2'd0 : (f == 3'd1) ? 2'd1 : 2'd2;
                rsec <= (f == 3'd0 || f == 3'd5) ? 24'(n >> 3) : (f == 3'd1) ? 24'(n >> 4) : 24'(n >> 5);
                ix_ab <= ixm_q[42:3]; ix_mul <= ixm_q[69:43];
                ix_dp <= ixm_q[122:91]; ix_ds <= ixm_q[154:123]; ids_left <= ixm_q[174:155]; ix_par <= 2'd0; ix_rb <= ixm_q[175]; ix_first <= 1'b1; ix_p0 <= 60'd0;
                r_off <= 24'd0; r_done <= (ixm_q[174:155] == 20'd0) || (n == 21'd0);
                issued <= 32'd0; wrote <= 32'd0;
                if (ixm_q[7:3] != 5'd0 || ixm_q[47:43] != 5'd0 ||
                    ((f == 3'd0 || f == 3'd5) ? n[2:0] != 3'd0 : (f == 3'd1) ? n[3:0] != 4'd0 : n[4:0] != 5'd0)) mv_fault <= 1'b1;
            end
            // ---- indexed: id pipeline (pin flop -> partial products -> address) into the row queue
            i1_v <= id_take; if (id_take) begin i1_id <= id; ids_left <= ids_left - 20'd1; end
            i2_v <= i1_v;
            if (i1_v) begin
                i2_lo <= {16'd0, i1_id[15:0]} * {16'd0, ix_mul};
                i2_hi <= (MUT == 3) ? 43'd0 : {16'd0, i1_id[31:16]} * {16'd0, ix_mul};
                i2_dw <= ix_dp;
                ix_par <= ix_par + 2'd1;
                if (MUT != 4 || ix_par[0]) ix_dp <= ix_dp + ix_ds;
            end
            i3_v <= i2_v;
            if (i2_v) begin i3_p <= {17'd0, i2_lo} + ({17'd0, i2_hi} << 16); i3_dw <= i2_dw; end
            i4_v <= i3_v;
            if (i3_v) begin : asum
                reg [59:0] p0, sm;
                p0 = (MUT == 5) ? 60'd0 : (ix_rb && !ix_first) ? ix_p0 : (ix_rb ? i3_p : 60'd0);   // MUT 5: rebase ignored
                if (ix_first) begin ix_p0 <= i3_p; ix_first <= 1'b0; end
                sm = {20'd0, ix_ab} + i3_p - p0;                            // two's complement: a rebased row below
                i4_a <= {|sm[59:37], sm[36:0]};                             // id_0 wraps to [59:37] != 0 -> range fault
                i4_dw <= i3_dw;
            end
            if (i4_v) begin
                if (i4_a[37]) mv_fault <= 1'b1;
                else begin rq_a[rq_t] <= i4_a[36:0]; rq_ds[rq_t] <= 18'(i4_dw >> 3); rq_t <= rq_t + 2'd1; end
            end
            if (cv_q) begin
                cv_q <= 1'b0; busy <= 1'b1; sf <= cm_q[4:2];
                ks <= (cm_q[4:2] == 3'd0 || cm_q[4:2] == 3'd5) ? 2'd0 : (cm_q[4:2] == 3'd1) ? 2'd1 : 2'd2;
                ra <= cm_q[41:5]; sst <= cm_q[76:45]; rdw <= cm_q[129:98]; dst_w <= cm_q[169:138];
                // sectors a row = n x esize / 32
                rsec <= (cm_q[4:2] == 3'd0 || cm_q[4:2] == 3'd5) ? 24'(cm_q[226:206] >> 3) :
                        (cm_q[4:2] == 3'd1) ? 24'(cm_q[226:206] >> 4) : 24'(cm_q[226:206] >> 5);
                wn <= (cm_q[205:186] >= 20'd4) ? 2'd3 : 2'(cm_q[205:186] - 20'd1);
                r_left <= (cm_q[205:186] >= 20'd4) ? cm_q[205:186] - 20'd4 : 20'd0;
                wi <= 2'd0; wa <= cm_q[41:5]; wd <= cm_q[129:98]; r_off <= 24'd0;
                r_done <= (cm_q[205:186] == 20'd0) || (cm_q[226:206] == 21'd0);
                issued <= 32'd0; wrote <= 32'd0;
            end
            // ---- request generator: one request a cycle on a free tag
            if (ix_try) begin
                if (ix_bad) mv_fault <= 1'b1;
                else if (ix_go) begin
                    dq[ix_st*51 +: 51] <= {1'b1, ft[3:0], ix_rn, ix_a};
                    tag_busy[ft[3:0]] <= 1'b1;
                    tg_dsec[ft[3:0]] <= rq_ds[rq_h] + (18'(r_off) << ks);
                    tg_left[ft[3:0]] <= ix_rn;
                    issued <= issued + ({23'd0, ix_rn} << ks);
                    if (!ix_pop) r_off <= r_off + {15'd0, ix_rn};
                    else begin
                        r_off <= 24'd0; rq_h <= rq_h + 2'd1;
                        if (ids_left == 20'd0 && rq_n == 3'd1 && !i1_v && !i2_v && !i3_v && !i4_v) r_done <= 1'b1;
                    end
                end
            end
            if (busy && !ixm && !r_done && ft != 5'd16) begin : rq
                reg [36:0] a, e; reg [23:0] rem; reg [8:0] rn; reg [1:0] st;
                a = wa + {r_off[22:0], 5'd0};
                rem = rsec - r_off;
                rn = (rem > 24'd256) ? 9'd256 : rem[8:0];
                e = a + {19'd0, rn, 5'd0} - 37'd1;
                st = a[SBIT +: 2];
                if (e[SBIT +: 2] != st || ({1'b0, a[SBIT-1:0]} + {{(SBIT-13){1'b0}}, rn, 5'd0}) > (SBIT+1)'(STACK_BYTES))
                    mv_fault <= 1'b1;
                else if (!dq[st*51 + 50] || dq_rdy[st]) begin
                    dq[st*51 +: 51] <= {1'b1, ft[3:0], rn, a};
                    tag_busy[ft[3:0]] <= 1'b1;
                    tg_dsec[ft[3:0]] <= 18'(wd >> 3) + (18'(r_off) << ks);
                    tg_left[ft[3:0]] <= rn;
                    issued <= issued + ({23'd0, rn} << ks);
                    if (wi != wn) begin wi <= wi + 2'd1; wa <= wa + {5'd0, sst}; wd <= wd + dst_w; end
                    else if (r_off + {15'd0, rn} != rsec) begin            // next chunk of the window
                        wi <= 2'd0; wa <= ra; wd <= rdw; r_off <= r_off + {15'd0, rn};
                    end else begin                                         // next window
                        wi <= 2'd0; r_off <= 24'd0; ra <= wa + {5'd0, sst}; rdw <= wd + dst_w;
                        wa <= wa + {5'd0, sst}; wd <= wd + dst_w;
                        if (r_left == 20'd0) r_done <= 1'b1;
                        else begin
                            wn <= (r_left >= 20'd4) ? 2'd3 : 2'(r_left - 20'd1);
                            r_left <= (r_left >= 20'd4) ? r_left - 20'd4 : 20'd0;
                        end
                    end
                end
            end
            begin : rqcnt
                reg psh, pp;
                psh = i4_v && !i4_a[37];
                pp = ix_go && ix_pop;
                rq_n <= rq_n + {2'd0, psh} - {2'd0, pp};
            end
            // ---- lanes: a beat that is a fault or finds its lane FIFO full
            if (lflt_w != '0 || ap_bad != '0) mv_fault <= 1'b1;
            // ---- tags: free once every beat landed
            for (t = 0; t < 16; t = t + 1) begin : tg
                integer k; k = 0;
                for (i = 0; i < NIN; i = i + 1) if (dv_w[i] && dtag_w[i*4 +: 4] == 4'(t)) k = k + 1;
                if (k != 0) begin
                    tg_left[t] <= tg_left[t] - 9'(k);
                    if ({23'd0, tg_left[t]} <= ((MUT == 2) ? k + 8 : k)) tag_busy[t] <= 1'b0;
                end
            end
            // ---- crossbar
            x_v <= bsel_v; wl_v <= x_v;
            rr <= (rr == RW'(NIN - 1)) ? '0 : rr + 1'b1;
            // ---- completion
            begin : cnt
                integer nd; nd = 0;
                for (t = 0; t < NB; t = t + 1) if (wl_done[t]) nd = nd + 1;
                if (busy && r_done && wrote + 32'(nd) == issued) begin busy <= 1'b0; ixm <= 1'b0; mv_done <= 1'b1; wrote <= 32'd0; end
                else wrote <= busy ? wrote + 32'(nd) : 32'd0;    // (idle: the mover's acknowledgements)
            end
        end
    end
`ifndef SYNTHESIS
    // +DMA_TRACE: each move taken, each request, each done (bench / e2e debugging)
    reg trc; initial trc = $test$plusargs("DMA_TRACE");
    reg mv_fault_d; always @(posedge clk) mv_fault_d <= mv_fault;
    always @(posedge clk) if (trc && rc) begin
        if (cv_q) $display("FRONT move sf %0d src %h sst %0d dst %0d dstr %0d m %0d n %0d", cm_q[4:2], cm_q[44:5], cm_q[76:45],
                           cm_q[137:98], cm_q[169:138], cm_q[205:186], cm_q[226:206]);
        for (integer q = 0; q < NS; q = q + 1)
            if (dq[q*51 + 50] && dq_rdy[q]) $display("FRONT   req stack %0d tag %0d nsec %0d addr %h dsec %0d", q, dq[q*51 + 46 +: 4],
                                                  dq[q*51 + 37 +: 9], dq[q*51 +: 37], tg_dsec[dq[q*51 + 46 +: 4]]);
        if (mv_done) $display("FRONT done issued %0d", issued);
        if (mv_fault && !mv_fault_d) $display("FRONT FAULT ixm %0d ix_bad %0d i4 %0d/%h rq_n %0d", ixm, ix_bad, i4_v, i4_a, rq_n);
    end
`endif
endmodule
`default_nettype wire

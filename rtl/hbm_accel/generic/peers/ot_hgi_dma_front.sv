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
//   L  pin-flops the NS x NL data lanes, computes each beat's VM sector (tag base + idx x K) and lands it in a 4-entry
//      lane FIFO (credit 4 a lane = the spec's initial credit; the credit returns when the beat leaves the FIFO); a tag
//      is free again once all its beats landed;
//   C  per lane: cur (the source sector) -> out (all K = 4 / esize destination sectors at once, registered: FP32 / U32
//      1, BF16 2, FP8 / INT8 4), decoded exactly as the mover (BF16 << 16, E4M3 exact, NaN -> 0x7FC00000, INT8 exact);
//      a lane converts one source sector a cycle while its K sectors win their banks;
//   X  per bank a rotating-priority pick among the lanes (each lane's K slots sit in K consecutive banks) -> VM wide
//      lane = the bank (32 destination sectors a cycle);
//   done when every destination sector's wide write is acknowledged.
//   Fault (sticky until reset): a request run crossing a stack or ending beyond STACK_BYTES, an svc fault beat, a beat without a credit.
// Rate: NS x NL source sectors a cycle in (the svc lane rate), 32 destination sectors a cycle out (the VM port is the cap).
// MUT (bench): 1 BF16 halves mirrored within the sector: must FAIL; 2 a tag freed 8 beats early: must FAIL.
// ---------------------------------------------------------------------------------------------------------------------
module ot_hgi_dma_front #(
    parameter integer NS = 4,
    parameter integer NL = 8,
    parameter integer SBIT = 35,          // stack select = HBM byte address [SBIT+1:SBIT] (ot_hbm_loader_kport_address)
    parameter [35:0] STACK_BYTES = 36'd22500000000,   // a run must end inside its stack's capacity
    parameter integer MUT = 0
) (
    input  wire                  clk,
    input  wire                  rst_n,
    input  wire                  mv_v,
    output wire                  mv_rdy,
    input  wire [226:0]          mv,
    output reg                   mv_done,
    output reg                   mv_fault,
    // requests per stack {v, tag 4, nsec 9, addr 37}
    output reg  [NS*51-1:0]      dq,
    input  wire [NS-1:0]         dq_rdy,
    // data per stack x lane {v, fault, tag 4, idx 8, data 256}
    input  wire [NS*NL*270-1:0]  dd,
    output reg  [NS*NL-1:0]      dd_cr,
    // VM wide write port, 32 lanes {v, sector 15, wdata 256, word mask 8}
    output reg  [32*280-1:0]     wl,
    input  wire [31:0]           wl_done
);
    localparam integer NIN = NS * NL;
    localparam integer LD = 4;
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
    assign mv_rdy = !busy && !cv_q && !mv_fault;
    // ---------------------------------------------------------------- tags
    reg [15:0] tag_busy;
    reg [17:0] tg_dsec [0:15];                              // the run's first VM sector
    reg [8:0]  tg_left [0:15];                              // beats still to land
    reg [4:0] ft;
    always @* begin ft = 5'd16; for (integer t = 15; t >= 0; t = t - 1) if (!tag_busy[t]) ft = 5'(t); end
    // ---------------------------------------------------------------- lanes
    reg [NIN*270-1:0] dd_r;                                 // pin flops
    reg [273:0] lq [0:NIN*LD-1];                            // {VM sector 18, source sector 256}
    reg [1:0] lq_h [0:NIN-1]; reg [1:0] lq_t [0:NIN-1]; reg [2:0] lq_n [0:NIN-1];
    reg [NIN-1:0] cur_v; reg [17:0] cur_sec [0:NIN-1]; reg [255:0] cur_d [0:NIN-1];
    // out: the K destination sectors of one source sector, slot j = VM sector ob + j (K consecutive banks)
    reg [3:0] ov [0:NIN-1]; reg [17:0] ob [0:NIN-1]; reg [255:0] od [0:NIN*4-1];
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
    // ---------------------------------------------------------------- crossbar: per bank, rotating priority from rr
    reg [4:0] rr;
    // lane i asks bank b with slot (b - ob_i) mod 32 when that is < 4 and the slot is valid; per bank a one-hot
    // rotating-priority pick (requests at or above rr first), the sector by a one-hot AND-OR mux
    reg [NIN-1:0] req [0:31]; reg [NIN-1:0] oh [0:31]; reg [1:0] rslot [0:31][0:NIN-1];
    reg [3:0] gnt [0:NIN-1]; reg [31:0] bsel_v;
    always @* begin
        for (integer i = 0; i < NIN; i = i + 1) gnt[i] = 4'd0;
        for (integer b = 0; b < 32; b = b + 1) begin
            reg [NIN-1:0] hi; reg [NIN-1:0] pk;
            for (integer i = 0; i < NIN; i = i + 1) begin
                reg [4:0] d; d = 5'(b) - ob[i][4:0];
                rslot[b][i] = d[1:0];
                req[b][i] = d < 5'd4 && ov[i][d[1:0]];
            end
            hi = req[b] & ~((NIN'(1) << rr) - NIN'(1));
            pk = (hi != '0) ? hi : req[b];
            oh[b] = pk & (~pk + NIN'(1));                       // lowest set bit
            bsel_v[b] = req[b] != '0;
            for (integer i = 0; i < NIN; i = i + 1) if (oh[b][i]) gnt[i][rslot[b][i]] = 1'b1;
        end
    end
    reg [279:0] xw [0:31];
    always @* for (integer b = 0; b < 32; b = b + 1) begin
        xw[b] = 280'd0;
        for (integer i = 0; i < NIN; i = i + 1)
            if (oh[b][i]) xw[b] = xw[b] | {1'b1, 15'(ob[i] + {16'd0, rslot[b][i]}), od[i*4 + rslot[b][i]], 8'hFF};
    end
    wire [NIN-1:0] cur_go;                                  // cur converts into out (every out slot left this cycle)
    wire [NIN-1:0] pop;                                     // the FIFO head moves into cur
    genvar g;
    generate for (g = 0; g < NIN; g = g + 1) begin : lg
        assign cur_go[g] = cur_v[g] && (ov[g] & ~gnt[g]) == 4'd0;
        assign pop[g] = lq_n[g] != 3'd0 && (!cur_v[g] || cur_go[g]);
    end endgenerate
    wire [3:0] kmask = (ks == 2'd0) ? 4'b0001 : (ks == 2'd1) ? 4'b0011 : 4'b1111;
    // ---------------------------------------------------------------- sequential
    integer i, s, t;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            cv_q <= 1'b0; busy <= 1'b0; mv_done <= 1'b0; mv_fault <= 1'b0; dq <= '0; dd_cr <= '0; wl <= '0;
            dd_r <= '0; tag_busy <= 16'd0; rr <= 5'd0; r_done <= 1'b1; cur_v <= '0;
            issued <= 32'd0; wrote <= 32'd0;
            for (i = 0; i < NIN; i = i + 1) begin lq_h[i] <= 2'd0; lq_t[i] <= 2'd0; lq_n[i] <= 3'd0; ov[i] <= 4'd0; end
        end else begin
            mv_done <= 1'b0; dd_cr <= '0;
            dd_r <= dd;
            for (i = 0; i < 32; i = i + 1) wl[i*280 + 279] <= 1'b0;
            for (s = 0; s < NS; s = s + 1) if (dq_rdy[s]) dq[s*51 + 50] <= 1'b0;
            // ---- accept (command station, then the decode)
            if (mv_v && mv_rdy) begin cv_q <= 1'b1; cm_q <= mv; end
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
            if (busy && !r_done && ft != 5'd16) begin : rq
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
                    if (wi != wn) begin wi <= wi + 2'd1; wa <= wa + sst[36:0]; wd <= wd + dst_w; end
                    else if (r_off + {15'd0, rn} != rsec) begin            // next chunk of the window
                        wi <= 2'd0; wa <= ra; wd <= rdw; r_off <= r_off + {15'd0, rn};
                    end else begin                                         // next window
                        wi <= 2'd0; r_off <= 24'd0; ra <= wa + sst[36:0]; rdw <= wd + dst_w;
                        wa <= wa + sst[36:0]; wd <= wd + dst_w;
                        if (r_left == 20'd0) r_done <= 1'b1;
                        else begin
                            wn <= (r_left >= 20'd4) ? 2'd3 : 2'(r_left - 20'd1);
                            r_left <= (r_left >= 20'd4) ? r_left - 20'd4 : 20'd0;
                        end
                    end
                end
            end
            // ---- landing: VM sector of each beat, into the lane FIFO
            for (i = 0; i < NIN; i = i + 1) begin : land
                reg [269:0] in; reg ok;
                in = dd_r[i*270 +: 270];
                ok = in[269] && !(lq_n[i] == 3'd4 && !pop[i]);
                if (in[269] && in[268]) mv_fault <= 1'b1;
                if (in[269] && !ok) mv_fault <= 1'b1;
                if (ok) begin
                    lq[i*LD + lq_t[i]] <= {tg_dsec[in[267:264]] + (18'(in[263:256]) << ks), in[255:0]};
                    lq_t[i] <= lq_t[i] + 2'd1;
                end
                if (pop[i]) begin
                    lq_h[i] <= lq_h[i] + 2'd1; dd_cr[i] <= 1'b1;
                    {cur_sec[i], cur_d[i]} <= lq[i*LD + lq_h[i]];
                end
                cur_v[i] <= pop[i] ? 1'b1 : cur_go[i] ? 1'b0 : cur_v[i];
                lq_n[i] <= lq_n[i] + {2'd0, ok} - {2'd0, pop[i]};
                if (cur_go[i]) begin
                    ob[i] <= cur_sec[i]; ov[i] <= kmask;
                    for (t = 0; t < 4; t = t + 1) od[i*4 + t] <= conv(cur_d[i], sf, 2'(t));
                end else ov[i] <= ov[i] & ~gnt[i];
            end
            // ---- tags: free once every beat landed
            for (t = 0; t < 16; t = t + 1) begin : tg
                integer k; k = 0;
                for (i = 0; i < NIN; i = i + 1) if (dd_r[i*270 + 269] && dd_r[i*270 + 264 +: 4] == 4'(t)) k = k + 1;
                if (k != 0) begin
                    tg_left[t] <= tg_left[t] - 9'(k);
                    if ({23'd0, tg_left[t]} <= ((MUT == 2) ? k + 8 : k)) tag_busy[t] <= 1'b0;
                end
            end
            // ---- crossbar
            for (i = 0; i < 32; i = i + 1)
                if (bsel_v[i]) wl[i*280 +: 280] <= xw[i];
            rr <= rr + 5'd1;
            // ---- completion
            begin : cnt
                integer nd; nd = 0;
                for (t = 0; t < 32; t = t + 1) if (wl_done[t]) nd = nd + 1;
                if (busy && r_done && wrote + 32'(nd) == issued) begin busy <= 1'b0; mv_done <= 1'b1; wrote <= 32'd0; end
                else wrote <= busy ? wrote + 32'(nd) : 32'd0;    // (idle: the mover's acknowledgements)
            end
        end
    end
`ifndef SYNTHESIS
    // +DMA_TRACE: each move taken, each request, each done (bench / e2e debugging)
    reg trc; initial trc = $test$plusargs("DMA_TRACE");
    always @(posedge clk) if (trc && rst_n) begin
        if (cv_q) $display("FRONT move sf %0d src %h sst %0d dst %0d dstr %0d m %0d n %0d", cm_q[4:2], cm_q[44:5], cm_q[76:45],
                           cm_q[137:98], cm_q[169:138], cm_q[205:186], cm_q[226:206]);
        for (integer q = 0; q < NS; q = q + 1)
            if (dq[q*51 + 50] && dq_rdy[q]) $display("FRONT   req stack %0d tag %0d nsec %0d addr %h dsec %0d", q, dq[q*51 + 46 +: 4],
                                                  dq[q*51 + 37 +: 9], dq[q*51 +: 37], tg_dsec[dq[q*51 + 46 +: 4]]);
        if (mv_done) $display("FRONT done issued %0d", issued);
        if (mv_fault) $display("FRONT FAULT");
    end
`endif
endmodule
`default_nettype wire

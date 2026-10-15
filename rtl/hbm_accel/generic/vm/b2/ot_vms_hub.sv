`timescale 1ns/1ps
`default_nettype none
// HBM B2 VM slice HUB TILE (el1011-hbm-b2-vm, 2026-10-12): the packet-client front end of one quadrant's VM slice.
// Clients 0..NC-1 are local packet clients (old VM packet ABI, unchanged: req 337 = {we, byte addr 32, wdata 256,
// byte mask 32, tag 16}; rsp 273 = {tag 16, we echo, rdata 256}; at most 4 outstanding; responses IN REQUEST ORDER).
// Client NC is the RING CLIENT (ot_vms_rcl): it replays requests that other slices sent here; its ops are
// always local and a mirror write from it is NOT re-broadcast.
//
// Routing (sector S = addr[19:5], m = addr[20]; see ot_vms_bank for the map):
//   mirror read             -> local bank S[2:0]
//   mirror write            -> local bank + one CW broadcast PREQ to the other 3 slices (each answers on the reverse ring: the
//                              client's response waits for the local write and all 3 remote writes = global visibility)
//   main, slice d = S[14:13] == sid -> local bank;  d == sid+1 / sid+2 -> CW PREQ;  d == sid+3 -> CCW PREQ (1 hop)
// Dispatch is TWO pipeline stages (v05, 2026-10-12: the v04 route missed TT -57.8 on grant -> 2.8 kb payload mux):
//   G: arbitrate on registered entry state; register the one-hot grant per bank / ring port and the granted entry index
//      (credits and entry state update here, so the next grant sees them);
//   P: AND-OR the granted entry's payload (4:1 by the registered index, then one-hot over clients) into the output flops.
// An entry's fields cannot change between G and P (it is freed only after all of its responses, which follow P).
// Behind the pin flops two more registered stages (v05) keep decode off the 5 kb entry-data write mux:
//   A (requests): the request payload is re-registered with a ONE-HOT allocation entry aw = onehot(tp + A-valid);
//   R (responses): every bank PR / ring PRSP is re-registered with its decoded one-hot entry hit (count) and data hit.
// The head's response payload is selected by a one-hot head pointer (no binary decode on the 1.1 kb cr mux).
// Per client a 4-entry reorder buffer; entries dispatch IN ORDER (an entry's local and ring parts both leave before the
// next entry), so a client's ops to one bank/slice keep their order; responses (bank pr, PRSPs from either ring stop) fill entries in any
// order and are delivered in request order.  All bank / ring ports are credit-based (no combinational ready crosses a
// tile edge); every input is pin-flopped, every output is a flop.
// Bank tag = {client 4, entry 4}.  status = {range fault, mask fault, proto fault}.
module ot_vms_hub #(
    parameter integer PHYSICAL_RING = 0, // 1: global SID order SW0,SE1,NE3,NW2 on physical perimeter
    parameter integer NC  = 4,
    parameter integer PQ  = 4,      // bank packet credits (= ot_vms_bank PQ)
    parameter integer CWI = 4,      // CW inject credits (= the CW stop's hub FIFO depth)
    parameter integer CCI = 4,      // CCW inject credits
    parameter integer MUT = 0       // 1: slice select from S[13:12] (wrong slice routing: must FAIL)
) (
    input  wire                    clk,
    input  wire                    rst_n,
    input  wire [1:0]              sid,
    input  wire [(NC+1)*338-1:0]   cq,       // per client {v, req 337}; client NC = ring client
    output wire [(NC+1)*274-1:0]   cr,       // per client {v, rsp 273}
    output wire [8*285-1:0]        pq,       // per bank {v, we, rowm 11, data 256, wmask 8, tag 8}
    input  wire [7:0]              pq_cr,
    input  wire [8*266-1:0]        pr,       // per bank {v, we, tag 8, data 256}
    output wire [289:0]            cwi,      // CW PREQ {v, dmask 4, client 4, seq 2, we, bank 3, rowm 11, wmask 8, data 256}
    input  wire                    cwi_cr,
    output wire [289:0]            cci,      // CCW PREQ (same format; dmask = the one destination)
    input  wire                    cci_cr,
    input  wire [263:0]            cco0,     // PRSP from the CW stop {v, client 4, seq 2, echo, data 256} (no back-pressure)
    input  wire [263:0]            cco1,     // PRSP from the CCW stop
    output reg  [2:0]              status
);
    localparam integer N = NC + 1;
    // Binary ring rank is separate from the unchanged global address SID.
    wire [1:0] me_rank={me[1],me[1]^me[0]};
    wire [1:0] next_rank=me_rank+2'd1,opp_rank=me_rank+2'd2,prev_rank=me_rank+2'd3;
    wire [1:0] next_sid={next_rank[1],next_rank[1]^next_rank[0]};
    wire [1:0] opp_sid={opp_rank[1],opp_rank[1]^opp_rank[0]};
    wire [3:0] cw_mask=(4'd1<<next_sid)|(4'd1<<opp_sid);
    wire [3:0] ccw_mask=4'd1<<{prev_rank[1],prev_rank[1]^prev_rank[0]};
    wire [1:0] prev_sid=PHYSICAL_RING?{prev_rank[1],prev_rank[1]^prev_rank[0]}:me+2'd3;
    // ------------------------------------------------------------------ pin flops (payload: no reset)
    // Reset only on control (valids, pointers, counters, credits, entry state); payload flops have no reset.
    reg [N*338-1:0] cq_d; reg [N-1:0] cq_v; reg [8*266-1:0] pr_d; reg [7:0] pr_v; reg [262:0] cc0_d, cc1_d; reg cc0_v, cc1_v;
    reg [7:0] pq_cr_r; reg cwi_cr_r, cci_cr_r; reg [1:0] me;
    reg [N*338-1:0] cq_r; reg [8*266-1:0] pr_r;
    always @* begin
        cq_r = cq_d; for (integer c = 0; c < N; c = c + 1) cq_r[c*338 + 337] = cq_v[c];
        pr_r = pr_d; for (integer b = 0; b < 8; b = b + 1) pr_r[b*266 + 265] = pr_v[b];
    end
    wire [263:0] cco_r [0:1];
    assign cco_r[0] = {cc0_v, cc0_d}; assign cco_r[1] = {cc1_v, cc1_d};
    // ---- stage A (requests) and stage R (responses); sources 0..7 = banks, 8/9 = CW / CCW stop
    reg [N*338-1:0] cq_s; reg [N-1:0] cq_av; reg [3:0] aw [0:N-1];
    reg [255:0] rs_d [0:9]; reg [N*4-1:0] rh [0:9]; reg [N*4-1:0] rhd [0:9];
    reg [1:0] tp [0:N-1];
    always @(posedge clk) begin : sar
        cq_s <= cq_d;
        for (integer b = 0; b < 8; b = b + 1) rs_d[b] <= pr_d[b*266 +: 256];
        rs_d[8] <= cc0_d[255:0]; rs_d[9] <= cc1_d[255:0];
    end
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            cq_av <= '0;
            for (integer c = 0; c < N; c = c + 1) aw[c] <= 4'd0;
            for (integer x = 0; x < 10; x = x + 1) begin rh[x] <= '0; rhd[x] <= '0; end
        end else begin : sarc
            reg [1:0] nx;
            cq_av <= cq_v;
            for (integer c = 0; c < N; c = c + 1) begin
                nx = tp[c] + (cq_av[c] ? 2'd1 : 2'd0);                  // tp after the request now in stage A allocates
                aw[c] <= cq_v[c] ? (4'd1 << nx) : 4'd0;
            end
            for (integer b = 0; b < 8; b = b + 1) begin
                rh[b] <= '0; rhd[b] <= '0;
                for (integer c = 0; c < N; c = c + 1) for (integer k = 0; k < 4; k = k + 1)
                    if (pr_r[b*266 + 265] && pr_r[b*266 + 260 +: 4] == 4'(c) && pr_r[b*266 + 256 +: 2] == 2'(k)) begin
                        rh[b][c*4 + k] <= 1'b1; rhd[b][c*4 + k] <= !pr_r[b*266 + 264];
                    end
            end
            for (integer r = 0; r < 2; r = r + 1) begin
                rh[8 + r] <= '0; rhd[8 + r] <= '0;
                for (integer c = 0; c < N; c = c + 1) for (integer k = 0; k < 4; k = k + 1)
                    if (cco_r[r][263] && cco_r[r][262:259] == 4'(c) && cco_r[r][258:257] == 2'(k)) begin
                        rh[8 + r][c*4 + k] <= 1'b1; rhd[8 + r][c*4 + k] <= !cco_r[r][256];
                    end
            end
        end
    reg [N*338-1:0] cq_a;
    always @* begin cq_a = cq_s; for (integer c = 0; c < N; c = c + 1) cq_a[c*338 + 337] = cq_av[c]; end
    // v06: the ring PRSP inputs (100-um N / S faces) get a PURE pin relay (cp0/cp1: one load each, so the placer keeps
    // them at the pins); v05 missed TT -10 ps on cco1 -> cc1_d (pin wire + hold buffer + the flop pulled to its loads).
    reg [262:0] cp0_d, cp1_d; reg cp0_v, cp1_v;
    always @(posedge clk) begin cq_d <= cq; pr_d <= pr; cp0_d <= cco0[262:0]; cp1_d <= cco1[262:0]; cc0_d <= cp0_d; cc1_d <= cp1_d; me <= sid; end
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin cq_v <= '0; pr_v <= '0; cc0_v <= 1'b0; cc1_v <= 1'b0; cp0_v <= 1'b0; cp1_v <= 1'b0; pq_cr_r <= '0; cwi_cr_r <= 1'b0; cci_cr_r <= 1'b0; end
        else begin
            for (integer c = 0; c < N; c = c + 1) cq_v[c] <= cq[c*338 + 337];
            for (integer b = 0; b < 8; b = b + 1) pr_v[b] <= pr[b*266 + 265];
            cp0_v <= cco0[263]; cp1_v <= cco1[263]; cc0_v <= cp0_v; cc1_v <= cp1_v; pq_cr_r <= pq_cr; cwi_cr_r <= cwi_cr; cci_cr_r <= cci_cr;
        end
    // output registers: control valid + payload
    reg [N-1:0] cr_v; wire [N*274-1:0] cr_d; reg [7:0] pq_v; wire [8*285-1:0] pq_d; reg cwi_v, cci_v; wire [288:0] cwi_d, cci_d;
    // stage-G grant registers and their stage-S delayed copies (control: reset); the granted entry is selected one-hot
    // from kept per-slice copies (g_sc below, payload: no reset)
    reg [N-1:0] gs_b [0:7]; reg [N-1:0] gs_cw, gs_ccw; reg [N-1:0] gs_b2 [0:7]; reg [N-1:0] gs_cw2, gs_ccw2;
    assign cwi = {cwi_v, cwi_d}; assign cci = {cci_v, cci_d};
    genvar go;
    for (go = 0; go < N; go = go + 1) begin : g_cr
        assign cr[go*274 +: 274] = {cr_v[go], cr_d[go*274 +: 273]};
    end
    for (go = 0; go < 8; go = go + 1) begin : g_pq
        assign pq[go*285 +: 285] = {pq_v[go], pq_d[go*285 +: 284]};
    end

    // ------------------------------------------------------------------ reorder buffer
    reg          e_v    [0:N-1][0:3];
    reg          e_we   [0:N-1][0:3];
    reg [2:0]    e_bank [0:N-1][0:3];
    reg [10:0]   e_row  [0:N-1][0:3];
    reg [7:0]    e_wm   [0:N-1][0:3];
    reg [255:0]  e_d    [0:N-1][0:3];    // write data until dispatched, then read data
    reg [15:0]   e_tag  [0:N-1][0:3];
    reg          e_nl   [0:N-1][0:3];    // needs the local bank
    reg [1:0]    e_nr   [0:N-1][0:3];    // ring parts: bit0 CW, bit1 CCW (native mirror write needs both)
    reg [3:0]    e_dm   [0:N-1][0:3];    // CW dest mask / CCW dst in [1:0]
    reg [2:0]    e_cnt  [0:N-1][0:3];    // responses still to come
    reg          e_sl   [0:N-1][0:3];    // local part sent
    reg [1:0]    e_sr   [0:N-1][0:3];    // independently sent ring parts
    reg [1:0] dp [0:N-1], hp [0:N-1]; reg [3:0] h1 [0:N-1];   // h1 = one-hot hp
    reg [2:0] pqc [0:7]; reg [2:0] cwic, ccic;
    reg [2:0] rot;                                       // rotating client priority

    // dispatch candidates (entry dp[c] of each client)
    reg [N-1:0] wl, wcw, wccw; reg [2:0] cb [0:N-1];
    always @* for (integer c = 0; c < N; c = c + 1) begin
        cb[c]   = e_bank[c][dp[c]];
        wl[c]   = e_v[c][dp[c]] && e_nl[c][dp[c]] && !e_sl[c][dp[c]];
        wcw[c]  = e_v[c][dp[c]] && e_nr[c][dp[c]][0] && !e_sr[c][dp[c]][0];
        wccw[c] = e_v[c][dp[c]] && e_nr[c][dp[c]][1] && !e_sr[c][dp[c]][1];
    end
    // grants: per bank (ring client first, then rotating), CW and CCW (rotating)
    reg [N-1:0] gl, gcw, gccw;
    always @* begin
        gl = '0; gcw = '0; gccw = '0;
        for (integer b = 0; b < 8; b = b + 1) begin : gb
            reg done; done = 1'b0;
            if (pqc[b] != 3'd0) begin
                if (wl[NC] && cb[NC] == 3'(b)) begin gl[NC] = 1'b1; done = 1'b1; end
                for (integer k = 0; k < 2 * NC; k = k + 1) begin : gk
                    integer c; c = k % NC;
                    if (!done && k >= rot && wl[c] && cb[c] == 3'(b)) begin gl[c] = 1'b1; done = 1'b1; end
                end
            end
        end
        begin : gw
            reg dc, dcc; dc = (cwic == 3'd0); dcc = (ccic == 3'd0);
            for (integer k = 0; k < 2 * NC; k = k + 1) begin : gk2
                integer c; c = k % NC;
                if (!dc && k >= rot && wcw[c]) begin gcw[c] = 1'b1; dc = 1'b1; end
                if (!dcc && k >= rot && wccw[c]) begin gccw[c] = 1'b1; dcc = 1'b1; end
            end
        end
    end
    // response decrements per entry
    reg [2:0] dec [0:N-1][0:3];
    always @* begin
        for (integer c = 0; c < N; c = c + 1) for (integer e = 0; e < 4; e = e + 1) begin
            dec[c][e] = 3'd0;
            for (integer x = 0; x < 10; x = x + 1) dec[c][e] = dec[c][e] + {2'd0, rh[x][c*4 + e]};
        end
    end

    reg proto, mflt, rflt;
    // dispatch: an entry's local part, ring part, or both have left
    reg [N-1:0] dadv, dlv;
    always @* for (integer c = 0; c < N; c = c + 1) begin : da
        reg [1:0] e; e = dp[c];
        dadv[c] = e_v[c][e] && (e_sl[c][e] || gl[c] || !e_nl[c][e]) && (((e_sr[c][e] | {gccw[c],gcw[c]}) & e_nr[c][e]) == e_nr[c][e]);
        dlv[c]  = e_v[c][hp[c]] && e_cnt[c][hp[c]] == 3'd0 && (e_sl[c][hp[c]] || !e_nl[c][hp[c]]) &&
                  ((e_sr[c][hp[c]] & e_nr[c][hp[c]]) == e_nr[c][hp[c]]);
    end
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            proto <= 1'b0; mflt <= 1'b0; rflt <= 1'b0; rot <= 3'd0; cwic <= 3'(CWI); ccic <= 3'(CCI);
            pq_v <= '0; cwi_v <= 1'b0; cci_v <= 1'b0; cr_v <= '0; status <= 3'd0; gs_cw <= '0; gs_ccw <= '0; gs_cw2 <= '0; gs_ccw2 <= '0;
            for (integer b = 0; b < 8; b = b + 1) begin gs_b[b] <= '0; gs_b2[b] <= '0; end
            for (integer b = 0; b < 8; b = b + 1) pqc[b] <= 3'(PQ);
            for (integer c = 0; c < N; c = c + 1) begin
                tp[c] <= 2'd0; dp[c] <= 2'd0; hp[c] <= 2'd0; h1[c] <= 4'd1;
                for (integer e = 0; e < 4; e = e + 1) begin e_v[c][e] <= 1'b0; e_cnt[c][e] <= 3'd0; e_sl[c][e] <= 1'b0; e_sr[c][e] <= 2'b0; end
            end
        end else begin : seq
            reg [7:0] pqd; reg [N-1:0] gb [0:7];
            for (integer b = 0; b < 8; b = b + 1) gb[b] = '0;
            rot <= (rot + 3'd1 == 3'(NC)) ? 3'd0 : rot + 3'd1;
            pqd = 8'd0;
            for (integer c = 0; c < N; c = c + 1) begin : cl
                reg [336:0] q; reg [14:0] s; reg m; reg [1:0] d; reg [7:0] wm; reg [31:0] bx; reg [1:0] e;
                // ---- allocate a new request
                q = cq_a[c*338 +: 337];
                if (cq_a[c*338 + 337]) begin
                    s = q[323:309]; m = q[324]; d = (MUT == 1) ? s[13:12] : s[14:13];
                    for (integer k = 0; k < 8; k = k + 1) begin wm[k] = &q[16 + 4*k +: 4]; bx[4*k +: 4] = {4{wm[k]}}; end
                    if (|(q[47:16] & ~bx) && q[336]) mflt <= 1'b1;
                    if (e_v[c][tp[c]]) proto <= 1'b1;
                    e_v[c][tp[c]] <= 1'b1; e_sl[c][tp[c]] <= 1'b0; e_sr[c][tp[c]] <= 2'b0;
                    if (m) begin if (s[14:13] != 2'd0) rflt <= 1'b1; end
                    else if (d != me && c == NC) rflt <= 1'b1;   // the ring client only replays local sectors
                    tp[c] <= tp[c] + 2'd1;
                end
                // ---- dispatch entry dp[c]
                e = dp[c];
                if (gl[c]) begin pqd[cb[c]] = 1'b1; gb[cb[c]][c] = 1'b1; e_sl[c][e] <= 1'b1; end
                if (gcw[c] || gccw[c]) e_sr[c][e] <= PHYSICAL_RING ? (e_sr[c][e] | {gccw[c],gcw[c]}) : 2'b11;
                if (dadv[c]) dp[c] <= dp[c] + 2'd1;
                // ---- response counts
                for (integer k = 0; k < 4; k = k + 1) e_cnt[c][k] <= e_cnt[c][k] - dec[c][k];
                if (cq_a[c*338 + 337])                                      // the new entry's count (no response yet)
                    e_cnt[c][tp[c]] <= (q[324] && q[336] && c != NC) ? 3'd4 : 3'd1;
                // ---- deliver the head
                cr_v[c] <= dlv[c];
                if (dlv[c]) begin e_v[c][hp[c]] <= 1'b0; hp[c] <= hp[c] + 2'd1; h1[c] <= {h1[c][2:0], h1[c][3]}; end
            end
            for (integer b = 0; b < 8; b = b + 1) begin gs_b[b] <= gb[b]; gs_b2[b] <= gs_b[b]; pq_v[b] <= |gs_b2[b]; end   // G -> S -> P
            gs_cw <= gcw; gs_ccw <= gccw; gs_cw2 <= gs_cw; gs_ccw2 <= gs_ccw; cwi_v <= |gs_cw2; cci_v <= |gs_ccw2;
            for (integer b = 0; b < 8; b = b + 1) pqc[b] <= pqc[b] - (pqd[b] ? 3'd1 : 3'd0) + (pq_cr_r[b] ? 3'd1 : 3'd0);
            cwic <= cwic - (|gcw ? 3'd1 : 3'd0) + (cwi_cr_r ? 3'd1 : 3'd0);
            ccic <= ccic - (|gccw ? 3'd1 : 3'd0) + (cci_cr_r ? 3'd1 : 3'd0);
            status <= {rflt, mflt, proto};
        end
    // ---- entry payload and output payloads (no reset)
    always @(posedge clk) begin : dat
        for (integer c = 0; c < N; c = c + 1) begin : cl
            reg [336:0] q; reg [14:0] s; reg m; reg [1:0] d; reg [7:0] wm; reg [1:0] e;
            q = cq_a[c*338 +: 337];
            for (integer a = 0; a < 4; a = a + 1) if (aw[c][a]) begin
                s = q[323:309]; m = q[324]; d = (MUT == 1) ? s[13:12] : s[14:13];
                for (integer k = 0; k < 8; k = k + 1) wm[k] = &q[16 + 4*k +: 4];
                e_we[c][a] <= q[336]; e_bank[c][a] <= s[2:0];
                e_row[c][a] <= {m, s[12:3]}; e_wm[c][a] <= wm; e_d[c][a] <= q[303:48]; e_tag[c][a] <= q[15:0];
                if (m) begin
                    e_nl[c][a] <= 1'b1;
                    if (q[336] && c != NC) begin e_nr[c][a] <= PHYSICAL_RING?2'd3:2'd1; e_dm[c][a] <= 4'hf & ~(4'd1 << me); end
                    else e_nr[c][a] <= 2'd0;
                end else if (d == me || c == NC) begin
                    e_nl[c][a] <= 1'b1; e_nr[c][a] <= 2'd0;
                end else begin
                    e_nl[c][a] <= 1'b0; e_dm[c][a] <= 4'd1 << d;
                    e_nr[c][a] <= (d == prev_sid) ? 2'd2 : 2'd1;
                end
            end
            // ---- responses
            for (integer k = 0; k < 4; k = k + 1) begin : rw
                reg [255:0] o; o = '0;
                for (integer x = 0; x < 10; x = x + 1) o = o | ({256{rhd[x][c*4 + k]}} & rs_d[x]);
                if (|{rhd[0][c*4+k], rhd[1][c*4+k], rhd[2][c*4+k], rhd[3][c*4+k], rhd[4][c*4+k], rhd[5][c*4+k], rhd[6][c*4+k],
                      rhd[7][c*4+k], rhd[8][c*4+k], rhd[9][c*4+k]}) e_d[c][k] <= o;
            end
        end
    end

    // ------------------------------------------------------------------ v06 dispatch stage S + P and the head (sliced)
    // v05 missed TT -47.8 on gs_e -> pq (16 levels: a binary 2-bit entry index fanned out to 5 x 284 4:1 muxes, then each
    // client payload broadcast to 8 bank + 2 ring output flops along the 540-um E face, AND-OR'd there).  v06:
    //   S: every client's granted entry is selected ONE-HOT into per-destination-group payload registers (group 0 feeds
    //      banks 0-3, group 1 banks 4-7, group 2 the CW/CCW ports), each group with its own kept one-hot select copies per
    //      57-bit data slice (select fanout <= 57 x 4);
    //   P: per bank / ring port and per slice, a kept copy of the delayed one-hot grant AND-ORs the 5 client registers of
    //      its group into the output flop.  +1 cycle on every dispatch (G -> S -> P).
    // Head: per client and per 55-bit slice, kept copies of the one-hot head h1 and of each entry's "write" flag (a write
    // returns zero data), so no single flop drives the 273-bit head mux (v05: e_we -> cr TT -30.8, 12 levels).
    localparam integer PW = 278, RW = 285, SW = 57, HW = 55;   // bank payload {we, rowm 11, d 256, wm 8, e 2}; ring {dm 4, e 2, we, bank 3, rowm 11, wm 8, d 256}
    wire [PW-1:0] pg [0:1][0:N-1]; wire [RW-1:0] rg [0:N-1];
    genvar gc2, gg, gs, gb2, gk;
    for (gc2 = 0; gc2 < N; gc2 = gc2 + 1) begin : g_sc
        for (gg = 0; gg < 3; gg = gg + 1) begin : g_gr
            localparam integer W = (gg < 2) ? PW : RW;
            wire [W-1:0] qv;
            for (gs = 0; gs * SW < W; gs = gs + 1) begin : g_sl
                localparam integer LO = gs * SW, WS = (W - LO < SW) ? W - LO : SW;
                (* keep = "true", dont_touch = "true" *) reg [3:0] oh;     // one-hot dp at grant time (stage G)
                reg [WS-1:0] q;
                always @(posedge clk) begin : sel
                    reg [W-1:0] v; v = '0;
                    oh <= 4'd1 << dp[gc2];
                    for (integer k = 0; k < 4; k = k + 1)
                        if (gg < 2) v = v | ({W{oh[k]}} & W'({e_we[gc2][k], e_row[gc2][k], e_d[gc2][k], e_wm[gc2][k], 2'(k)}));
                        else        v = v | ({W{oh[k]}} & W'({e_dm[gc2][k], 2'(k), e_we[gc2][k], e_bank[gc2][k], e_row[gc2][k],
                                                             e_wm[gc2][k], e_d[gc2][k]}));
                    q <= v[LO +: WS];
                end
                assign qv[LO +: WS] = q;
            end
            if (gg < 2) begin : g_p assign pg[gg][gc2] = qv; end
            else begin : g_r assign rg[gc2] = qv; end
        end
    end
    // stage P: banks (284 b = {we, rowm 11, d 256, wm 8, client 4, 2'b00, e 2})
    for (gb2 = 0; gb2 < 8; gb2 = gb2 + 1) begin : g_pb
        for (gs = 0; gs * SW < 284; gs = gs + 1) begin : g_sl
            localparam integer LO = gs * SW, WS = (284 - LO < SW) ? 284 - LO : SW;
            (* keep = "true", dont_touch = "true" *) reg [N-1:0] g2;    // this slice's copy of gs_b2[b]
            reg [WS-1:0] o;
            always @(posedge clk or negedge rst_n) if (!rst_n) g2 <= '0; else g2 <= gs_b[gb2];
            always @(posedge clk) begin : p
                reg [283:0] v; reg [277:0] x; v = '0;
                for (integer c = 0; c < N; c = c + 1) begin
                    x = pg[gb2 / 4][c];
                    v = v | ({284{g2[c]}} & {x[277:2], 4'(c), 2'b00, x[1:0]});
                end
                if (|g2) o <= v[LO +: WS];
            end
            assign pq_d[gb2*285 + LO +: WS] = o;
        end
        assign pq_d[gb2*285 + 284] = 1'b0;
    end
    // stage P: ring ports (289 b = {dm 4, client 4, e 2, we, bank 3, rowm 11, wm 8, d 256})
    for (gk = 0; gk < 2; gk = gk + 1) begin : g_pr
        for (gs = 0; gs * SW < 289; gs = gs + 1) begin : g_sl
            localparam integer LO = gs * SW, WS = (289 - LO < SW) ? 289 - LO : SW;
            (* keep = "true", dont_touch = "true" *) reg [N-1:0] g2;
            reg [WS-1:0] o;
            always @(posedge clk or negedge rst_n) if (!rst_n) g2 <= '0; else g2 <= (gk == 0) ? gs_cw : gs_ccw;
            always @(posedge clk) begin : p
                reg [288:0] v; reg [284:0] x; v = '0;
                for (integer c = 0; c < N; c = c + 1) begin
                    x = rg[c];
                    v = v | ({289{g2[c]}} & {(PHYSICAL_RING ? (x[284:281] & ((gk==0)?cw_mask:ccw_mask)) : x[284:281]), 4'(c), x[280:0]});
                end
                if (|g2) o <= v[LO +: WS];
            end
            if (gk == 0) begin : g_w assign cwi_d[LO +: WS] = o; end
            else begin : g_c assign cci_d[LO +: WS] = o; end
        end
    end
    // head response payload {tag 16, we, we ? 0 : d 256}
    for (gc2 = 0; gc2 < N; gc2 = gc2 + 1) begin : g_hd
        for (gs = 0; gs * HW < 273; gs = gs + 1) begin : g_sl
            localparam integer LO = gs * HW, WS = (273 - LO < HW) ? 273 - LO : HW;
            (* keep = "true", dont_touch = "true" *) reg [3:0] hs;      // this slice's copy of h1[c]
            (* keep = "true", dont_touch = "true" *) reg [3:0] wz;      // this slice's copy of e_we[c][0..3]
            reg [WS-1:0] o;
            always @(posedge clk or negedge rst_n)
                if (!rst_n) hs <= 4'd1; else if (dlv[gc2]) hs <= {hs[2:0], hs[3]};
            always @(posedge clk) begin : h
                reg [272:0] v; v = '0;
                for (integer k = 0; k < 4; k = k + 1) begin
                    if (aw[gc2][k]) wz[k] <= cq_a[gc2*338 + 336];
                    v = v | ({273{hs[k]}} & {e_tag[gc2][k], e_we[gc2][k], {256{!wz[k]}} & e_d[gc2][k]});
                end
                o <= v[LO +: WS];
            end
            assign cr_d[gc2*274 + LO +: WS] = o;
        end
        assign cr_d[gc2*274 + 273] = 1'b0;
    end
endmodule
`default_nettype wire

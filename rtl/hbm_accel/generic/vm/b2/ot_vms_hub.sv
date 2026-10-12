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
// Per client a 4-entry reorder buffer; entries dispatch IN ORDER (an entry's local and ring parts both leave before the
// next entry), so a client's ops to one bank/slice keep their order; responses (bank pr, PRSPs from either ring stop) fill entries in any
// order and are delivered in request order.  All bank / ring ports are credit-based (no combinational ready crosses a
// tile edge); every input is pin-flopped, every output is a flop.
// Bank tag = {client 4, entry 4}.  status = {range fault, mask fault, proto fault}.
module ot_vms_hub #(
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
    always @(posedge clk) begin cq_d <= cq; pr_d <= pr; cc0_d <= cco0[262:0]; cc1_d <= cco1[262:0]; me <= sid; end
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin cq_v <= '0; pr_v <= '0; cc0_v <= 1'b0; cc1_v <= 1'b0; pq_cr_r <= '0; cwi_cr_r <= 1'b0; cci_cr_r <= 1'b0; end
        else begin
            for (integer c = 0; c < N; c = c + 1) cq_v[c] <= cq[c*338 + 337];
            for (integer b = 0; b < 8; b = b + 1) pr_v[b] <= pr[b*266 + 265];
            cc0_v <= cco0[263]; cc1_v <= cco1[263]; pq_cr_r <= pq_cr; cwi_cr_r <= cwi_cr; cci_cr_r <= cci_cr;
        end
    // output registers: control valid + payload
    reg [N-1:0] cr_v; reg [N*274-1:0] cr_d; reg [7:0] pq_v; reg [8*285-1:0] pq_d; reg cwi_v, cci_v; reg [288:0] cwi_d, cci_d;
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
    reg [1:0]    e_nr   [0:N-1][0:3];    // ring part: 0 none, 1 CW, 2 CCW
    reg [3:0]    e_dm   [0:N-1][0:3];    // CW dest mask / CCW dst in [1:0]
    reg [2:0]    e_cnt  [0:N-1][0:3];    // responses still to come
    reg          e_sl   [0:N-1][0:3];    // local part sent
    reg          e_sr   [0:N-1][0:3];    // ring part sent
    reg [1:0] tp [0:N-1], dp [0:N-1], hp [0:N-1];
    reg [2:0] pqc [0:7]; reg [2:0] cwic, ccic;
    reg [2:0] rot;                                       // rotating client priority

    // dispatch candidates (entry dp[c] of each client)
    reg [N-1:0] wl, wcw, wccw; reg [2:0] cb [0:N-1];
    always @* for (integer c = 0; c < N; c = c + 1) begin
        cb[c]   = e_bank[c][dp[c]];
        wl[c]   = e_v[c][dp[c]] && e_nl[c][dp[c]] && !e_sl[c][dp[c]];
        wcw[c]  = e_v[c][dp[c]] && e_nr[c][dp[c]] == 2'd1 && !e_sr[c][dp[c]];
        wccw[c] = e_v[c][dp[c]] && e_nr[c][dp[c]] == 2'd2 && !e_sr[c][dp[c]];
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
            for (integer b = 0; b < 8; b = b + 1)
                if (pr_r[b*266 + 265] && pr_r[b*266 + 260 +: 4] == 4'(c) && pr_r[b*266 + 256 +: 2] == 2'(e)) dec[c][e] = dec[c][e] + 3'd1;
            for (integer r = 0; r < 2; r = r + 1)
                if (cco_r[r][263] && cco_r[r][262:259] == 4'(c) && cco_r[r][258:257] == 2'(e)) dec[c][e] = dec[c][e] + 3'd1;
        end
    end

    reg proto, mflt, rflt;
    // dispatch: an entry's local part, ring part, or both have left
    reg [N-1:0] dadv, dlv;
    always @* for (integer c = 0; c < N; c = c + 1) begin : da
        reg [1:0] e; e = dp[c];
        dadv[c] = e_v[c][e] && (e_sl[c][e] || gl[c] || !e_nl[c][e]) && (e_sr[c][e] || gcw[c] || gccw[c] || e_nr[c][e] == 2'd0);
        dlv[c]  = e_v[c][hp[c]] && e_cnt[c][hp[c]] == 3'd0 && (e_sl[c][hp[c]] || !e_nl[c][hp[c]]) &&
                  (e_sr[c][hp[c]] || e_nr[c][hp[c]] == 2'd0);
    end
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            proto <= 1'b0; mflt <= 1'b0; rflt <= 1'b0; rot <= 3'd0; cwic <= 3'(CWI); ccic <= 3'(CCI);
            pq_v <= '0; cwi_v <= 1'b0; cci_v <= 1'b0; cr_v <= '0; status <= 3'd0;
            for (integer b = 0; b < 8; b = b + 1) pqc[b] <= 3'(PQ);
            for (integer c = 0; c < N; c = c + 1) begin
                tp[c] <= 2'd0; dp[c] <= 2'd0; hp[c] <= 2'd0;
                for (integer e = 0; e < 4; e = e + 1) begin e_v[c][e] <= 1'b0; e_cnt[c][e] <= 3'd0; e_sl[c][e] <= 1'b0; e_sr[c][e] <= 1'b0; end
            end
        end else begin : seq
            reg [7:0] pqd;
            rot <= (rot + 3'd1 == 3'(NC)) ? 3'd0 : rot + 3'd1;
            pqd = 8'd0;
            for (integer c = 0; c < N; c = c + 1) begin : cl
                reg [336:0] q; reg [14:0] s; reg m; reg [1:0] d; reg [7:0] wm; reg [31:0] bx; reg [1:0] e;
                // ---- allocate a new request
                q = cq_r[c*338 +: 337];
                if (cq_r[c*338 + 337]) begin
                    s = q[323:309]; m = q[324]; d = (MUT == 1) ? s[13:12] : s[14:13];
                    for (integer k = 0; k < 8; k = k + 1) begin wm[k] = &q[16 + 4*k +: 4]; bx[4*k +: 4] = {4{wm[k]}}; end
                    if (|(q[47:16] & ~bx) && q[336]) mflt <= 1'b1;
                    if (e_v[c][tp[c]]) proto <= 1'b1;
                    e_v[c][tp[c]] <= 1'b1; e_sl[c][tp[c]] <= 1'b0; e_sr[c][tp[c]] <= 1'b0;
                    if (m) begin if (s[14:13] != 2'd0) rflt <= 1'b1; end
                    else if (d != me && c == NC) rflt <= 1'b1;   // the ring client only replays local sectors
                    tp[c] <= tp[c] + 2'd1;
                end
                // ---- dispatch entry dp[c]
                e = dp[c];
                if (gl[c]) begin pqd[cb[c]] = 1'b1; e_sl[c][e] <= 1'b1; end
                if (gcw[c] || gccw[c]) e_sr[c][e] <= 1'b1;
                if (dadv[c]) dp[c] <= dp[c] + 2'd1;
                // ---- response counts
                for (integer k = 0; k < 4; k = k + 1) e_cnt[c][k] <= e_cnt[c][k] - dec[c][k];
                if (cq_r[c*338 + 337])                                      // the new entry's count (no response yet)
                    e_cnt[c][tp[c]] <= (q[324] && q[336] && c != NC) ? 3'd4 : 3'd1;
                // ---- deliver the head
                cr_v[c] <= dlv[c];
                if (dlv[c]) begin e_v[c][hp[c]] <= 1'b0; hp[c] <= hp[c] + 2'd1; end
            end
            pq_v <= pqd; cwi_v <= |gcw; cci_v <= |gccw;
            for (integer b = 0; b < 8; b = b + 1) pqc[b] <= pqc[b] - (pqd[b] ? 3'd1 : 3'd0) + (pq_cr_r[b] ? 3'd1 : 3'd0);
            cwic <= cwic - (|gcw ? 3'd1 : 3'd0) + (cwi_cr_r ? 3'd1 : 3'd0);
            ccic <= ccic - (|gccw ? 3'd1 : 3'd0) + (cci_cr_r ? 3'd1 : 3'd0);
            status <= {rflt, mflt, proto};
        end
    // ---- entry payload and output payloads (no reset)
    always @(posedge clk) begin : dat
        for (integer c = 0; c < N; c = c + 1) begin : cl
            reg [336:0] q; reg [14:0] s; reg m; reg [1:0] d; reg [7:0] wm; reg [1:0] e;
            q = cq_r[c*338 +: 337];
            if (cq_r[c*338 + 337]) begin
                s = q[323:309]; m = q[324]; d = (MUT == 1) ? s[13:12] : s[14:13];
                for (integer k = 0; k < 8; k = k + 1) wm[k] = &q[16 + 4*k +: 4];
                e_we[c][tp[c]] <= q[336]; e_bank[c][tp[c]] <= s[2:0];
                e_row[c][tp[c]] <= {m, s[12:3]}; e_wm[c][tp[c]] <= wm; e_d[c][tp[c]] <= q[303:48]; e_tag[c][tp[c]] <= q[15:0];
                if (m) begin
                    e_nl[c][tp[c]] <= 1'b1;
                    if (q[336] && c != NC) begin e_nr[c][tp[c]] <= 2'd1; e_dm[c][tp[c]] <= 4'hf & ~(4'd1 << me); end
                    else e_nr[c][tp[c]] <= 2'd0;
                end else if (d == me || c == NC) begin
                    e_nl[c][tp[c]] <= 1'b1; e_nr[c][tp[c]] <= 2'd0;
                end else begin
                    e_nl[c][tp[c]] <= 1'b0; e_dm[c][tp[c]] <= 4'd1 << d;
                    e_nr[c][tp[c]] <= (d == me + 2'd3) ? 2'd2 : 2'd1;
                end
            end
            // ---- dispatch payloads
            e = dp[c];
            if (gl[c]) pq_d[cb[c]*285 +: 284] <= {e_we[c][e], e_row[c][e], e_d[c][e], e_wm[c][e], 4'(c), 2'b00, e};
            if (gcw[c])  cwi_d <= {e_dm[c][e], 4'(c), e, e_we[c][e], e_bank[c][e], e_row[c][e], e_wm[c][e], e_d[c][e]};
            if (gccw[c]) cci_d <= {e_dm[c][e], 4'(c), e, e_we[c][e], e_bank[c][e], e_row[c][e], e_wm[c][e], e_d[c][e]};
            // ---- responses
            for (integer k = 0; k < 4; k = k + 1) begin
                for (integer b = 0; b < 8; b = b + 1)
                    if (pr_r[b*266 + 265] && pr_r[b*266 + 260 +: 4] == 4'(c) && pr_r[b*266 + 256 +: 2] == 2'(k) && !pr_r[b*266 + 264])
                        e_d[c][k] <= pr_r[b*266 +: 256];
                for (integer r = 0; r < 2; r = r + 1)
                    if (cco_r[r][263] && cco_r[r][262:259] == 4'(c) && cco_r[r][258:257] == 2'(k) && !cco_r[r][256]) e_d[c][k] <= cco_r[r][255:0];
            end
            // ---- the head's response payload
            cr_d[c*274 +: 273] <= {e_tag[c][hp[c]], e_we[c][hp[c]], e_we[c][hp[c]] ? 256'd0 : e_d[c][hp[c]]};
        end
    end
endmodule
`default_nettype wire

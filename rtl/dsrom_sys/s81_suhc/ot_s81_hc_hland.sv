`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// ot_s81_hc_hland (rom-layer-tput, 2026-10-13): the H landing streamer of the S81 HC master.
//
// Problem it removes: the stage-entry H_LOAD of the HC (640 VM rows at S_RD = 2 a cycle = 320 cycles + the VM read
// latency) started only when the whole HIDDEN payload had landed in the vector memory, so it was serial with the layer
// once per h transfer (336 cycles measured, unpriced).  The payload lands one row a cycle through the package
// controller's VM write port (ot_s81_pkg_ctrl vm_we / vm_waddr / vm_wdata: cut-through receive, rows in order).
//
// Structure: a TEE of that landing write port feeds a small row FIFO here; the HC's H_LOAD read requests for the
// landing rows are answered FROM THE FIFO, in order, as the rows arrive -- they are never sent to the VM, so the VM's
// row-completion / early-read contract is untouched (the VM still receives every landing write for its other readers:
// the coefficient producers and the Engram ops read h as VM rows).  ot_s81_hc_cseq needs no change: it issues its HROWS
// requests (the credits), counts the responses it receives and stamps each with its index, at any pace.
// The H_LOAD then ends a few cycles after the LAST row lands, whatever the link did in between (go-back-N replays only
// delay rows; a response is produced only from a landed row).  The HC may take the H_LOAD before, while or after the
// message lands:
//   fresh[s] = 0 (no unconsumed message in slot s yet): the requests wait for the message's first row, then stream;
//   stream   (the message of slot s is landing and the FIFO holds every row not yet delivered): FIFO -> HC;
//   fallback (the FIFO overflowed before the HC asked, e.g. the HC was busy with the other job slot; or the message of
//             slot s landed completely earlier): the requests are forwarded to the VM, in order, only once that
//             message has landed completely -- exactly the old behaviour, never an early read.
// Every other read request (coefficient rows, gain rows, an H_LOAD from a base outside the landing rows such as the
// post-Engram h) passes through to the VM combinationally and its response passes back unchanged.
//
// Landing rows: VM rows RXB + slot * XW + j, j = 0 .. XW-1 (ot_s81_pkg_ctrl RXB / RXW; slot = the job slot).
// Faults (sticky, first code): 1 a new message started while a stream of the previous one was still being delivered,
// 2 FIFO overflow during a stream (cannot happen: the HC's S_RD responses a cycle outrun the 1 row a cycle landing),
// 3 landing rows out of order, 4 an H request for a slot while another slot's load is being served.
// MUT (bench negative control, 0 in silicon): 1 = requests for the landing rows go to the VM at once (no stream, no
// hold): an H_LOAD taken while the payload lands then reads rows that have not landed.
// Production note: the FIFO is FD x 512 b (FD 64: one ot_sram_1r1w_64x512 per read slot, rows interleaved, or flops).
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81_hc_hland #(
    parameter integer S_RD = 2,
    parameter integer XW   = 640,          // rows of an h payload
    parameter integer RXB  = 0,            // landing base row (slot 0)
    parameter integer VWA  = 14,
    parameter integer FD   = 64,           // FIFO rows
    parameter integer MUT  = 0
) (
    input  wire                   clk,
    input  wire                   rst_n,
    // tee of the package controller's VM write port (the landing)
    input  wire                   lw_v,
    input  wire [VWA-1:0]         lw_a,
    input  wire [511:0]           lw_d,
    // HC side (dsfd_sp_hc rq_* / rs_*)
    input  wire [S_RD-1:0]        h_rq_v,
    input  wire [S_RD*VWA-1:0]    h_rq_row,
    output reg  [S_RD-1:0]        h_rs_v,
    output reg  [S_RD*512-1:0]    h_rs_d,
    // VM side
    output reg  [S_RD-1:0]        v_rq_v,
    output reg  [S_RD*VWA-1:0]    v_rq_row,
    input  wire [S_RD-1:0]        v_rs_v,
    input  wire [S_RD*512-1:0]    v_rs_d,
    output reg                    fault,
    output reg  [3:0]             fault_code,
    output reg  [31:0]            st_stream,      // H loads answered from the landing stream
    output reg  [31:0]            st_vm           // H loads answered by the VM (fallback)
);
    localparam integer FB = $clog2(FD);
    localparam integer CB = $clog2(XW + 1);

    // ------------------------------------------------------------------ landing side
    wire              l_in   = lw_v && (lw_a >= VWA'(RXB)) && (lw_a < VWA'(RXB + 2 * XW));
    wire              l_s    = (lw_a - VWA'(RXB)) >= VWA'(XW);
    wire [VWA-1:0]    l_r    = lw_a - VWA'(RXB) - (l_s ? VWA'(XW) : {VWA{1'b0}});
    reg               l_slot;                  // slot of the message that landed last / is landing
    reg  [CB-1:0]     l_cnt;                   // its rows landed
    reg               l_live;                  // the FIFO holds every row of it that was not delivered yet
    reg  [1:0]        fresh;                   // slot s holds a message (landing or landed) no H_LOAD has consumed
    wire              l_done = (l_cnt == CB'(XW));

    reg  [511:0]      mem [0:FD-1];
    reg  [FB-1:0]     wp, rp;
    reg  [FB:0]       n;

    // ------------------------------------------------------------------ consumer side
    reg  [S_RD-1:0]   rq_h;                    // request s names a landing row
    reg  [S_RD-1:0]   rq_s;                    // its slot
    integer           s;
    always @* begin
        rq_h = {S_RD{1'b0}}; rq_s = {S_RD{1'b0}};
        for (s = 0; s < S_RD; s = s + 1) begin
            rq_h[s] = h_rq_v[s] && (h_rq_row[VWA * s +: VWA] >= VWA'(RXB)) && (h_rq_row[VWA * s +: VWA] < VWA'(RXB + 2 * XW));
            rq_s[s] = (h_rq_row[VWA * s +: VWA] - VWA'(RXB)) >= VWA'(XW);
        end
    end
    reg  [2:0]        nreq;
    reg               rq_slot;
    always @* begin
        nreq = 3'd0; rq_slot = 1'b0;
        for (s = S_RD - 1; s >= 0; s = s - 1) if (rq_h[s]) begin nreq = nreq + 3'd1; rq_slot = rq_s[s]; end
    end
    reg               c_act;                   // an H load is being served
    reg               c_slot;
    reg  [1:0]        c_mode;                  // 0 undecided, 1 stream, 2 VM
    reg  [CB-1:0]     c_req;                   // requests received
    reg  [CB-1:0]     c_del;                   // rows delivered (stream) / requests forwarded (VM)
    reg  [S_RD-1:0]   st_v;                    // stream responses (registered)
    reg  [S_RD*512-1:0] st_d;
    reg  [S_RD-1:0]   fw_v;                    // forwarded requests (registered)
    reg  [S_RD*VWA-1:0] fw_row;

    // ------------------------------------------------------------------ pass-through / muxes
    always @* begin
        v_rq_v = {S_RD{1'b0}}; v_rq_row = h_rq_row;
        for (s = 0; s < S_RD; s = s + 1) begin
            if (h_rq_v[s] && (!rq_h[s] || MUT == 1)) v_rq_v[s] = 1'b1;
            if (fw_v[s]) begin v_rq_v[s] = 1'b1; v_rq_row[VWA * s +: VWA] = fw_row[VWA * s +: VWA]; end
        end
        h_rs_v = v_rs_v | st_v;
        h_rs_d = v_rs_d;
        for (s = 0; s < S_RD; s = s + 1) if (st_v[s]) h_rs_d[512 * s +: 512] = st_d[512 * s +: 512];
    end

    // ------------------------------------------------------------------ state
    reg  [FB:0]       n_n;
    reg  [FB-1:0]     rp_n, wp_n;
    reg  [CB-1:0]     del_n, req_n;
    reg  [1:0]        mode_n;
    reg               live_n, act_n, flush;
    reg  [1:0]        fresh_n;
    integer           k;
    task automatic flt(input [3:0] c);
        begin fault <= 1'b1; if (!fault) fault_code <= c; end
    endtask
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            l_slot <= 1'b0; l_cnt <= 0; l_live <= 1'b0; fresh <= 2'b00; wp <= 0; rp <= 0; n <= 0;
            c_act <= 1'b0; c_slot <= 1'b0; c_mode <= 2'd0; c_req <= 0; c_del <= 0; st_v <= 0; fw_v <= 0;
            fault <= 1'b0; fault_code <= 4'd0; st_stream <= 0; st_vm <= 0;
        end else begin
            n_n = n; rp_n = rp; wp_n = wp; del_n = c_del; req_n = c_req; mode_n = c_mode; live_n = l_live;
            act_n = c_act; fresh_n = fresh; flush = 1'b0;
            st_v <= {S_RD{1'b0}}; fw_v <= {S_RD{1'b0}};
            // ---- consumer: requests for landing rows (MUT 1: not intercepted)
            if (nreq != 0 && MUT != 1) begin
                if (!c_act) begin
                    act_n = 1'b1; c_slot <= rq_slot; mode_n = 2'd0; req_n = CB'(nreq); del_n = 0;
                end else begin
                    if (rq_slot != c_slot) flt(4'd4);
                    req_n = c_req + CB'(nreq);
                end
            end
            // ---- consumer: mode decision (registered state only)
            if (c_act && c_mode == 2'd0) begin
                if (fresh[c_slot]) begin
                    // stream only with room for the row that may land this cycle (the pops start next cycle)
                    if (l_slot == c_slot && l_live && n != (FB + 1)'(FD)) mode_n = 2'd1;
                    else begin mode_n = 2'd2; if (l_slot == c_slot) live_n = 1'b0; end
                end
            end
            // ---- consumer: delivery
            if (c_act && c_mode == 2'd1) begin
                for (k = 0; k < S_RD; k = k + 1)
                    if (n_n != 0 && del_n < c_req) begin
                        st_v[k] <= 1'b1; st_d[512 * k +: 512] <= mem[rp_n];
                        rp_n = rp_n + 1'b1; n_n = n_n - 1'b1; del_n = del_n + 1'b1;
                    end
            end else if (c_act && c_mode == 2'd2) begin
                // the VM answers, but only when the message of that slot has landed completely
                if (l_slot != c_slot || l_done)
                    for (k = 0; k < S_RD; k = k + 1)
                        if (del_n < c_req) begin
                            fw_v[k] <= 1'b1;
                            fw_row[VWA * k +: VWA] <= VWA'(RXB) + (c_slot ? VWA'(XW) : {VWA{1'b0}}) + VWA'(del_n);
                            del_n = del_n + 1'b1;
                        end
            end
            if (c_act && del_n == CB'(XW)) begin
                act_n = 1'b0; fresh_n[c_slot] = 1'b0; mode_n = 2'd0;
                if (c_mode == 2'd1) begin st_stream <= st_stream + 1; live_n = 1'b0; end
                else st_vm <= st_vm + 1;
            end
            // ---- landing
            if (l_in) begin
                if (l_r == 0) begin
                    // a new message: its rows replace whatever the FIFO held
                    if (c_act && c_mode == 2'd1 && del_n != CB'(XW)) flt(4'd1);
                    l_slot <= l_s; l_cnt <= CB'(1); fresh_n[l_s] = 1'b1; live_n = 1'b1;
                    flush = 1'b1;
                end else begin
                    if (l_s != l_slot || l_r != VWA'(l_cnt)) begin flt(4'd3); live_n = 1'b0; end
                    l_cnt <= l_cnt + 1'b1;
                end
                if (flush) begin wp_n = 0; rp_n = 0; n_n = 0; end
                if (live_n) begin
                    if (n_n == (FB + 1)'(FD)) begin
                        // no room: the stream is given up (legal only while no H load is being streamed)
                        if (act_n && mode_n == 2'd1) flt(4'd2);
                        live_n = 1'b0; n_n = 0; wp_n = 0; rp_n = 0;
                    end else begin
                        mem[wp_n] <= lw_d; wp_n = wp_n + 1'b1; n_n = n_n + 1'b1;
                    end
                end
            end
            n <= n_n; rp <= rp_n; wp <= wp_n; c_del <= del_n; c_req <= req_n; c_mode <= mode_n; l_live <= live_n;
            c_act <= act_n; fresh <= fresh_n;
        end
    end
endmodule

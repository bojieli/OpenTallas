`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Packet router for the ROM array and wafer fabric (docs/ROM_ARRAY_FABRIC_RTL.md).
//
// NP ports.  A packet is a run of FW-bit flits, the last one flagged; its
// first flit (the header) carries a destination id in bits
// [DEST_LSB +: 8].  A routing table maps each id to a SET of output ports, so
// one id can name one package (unicast) or a group (multicast: the router
// copies every flit of the packet to every port of the set).  Ids at or above
// DESTS, and ids whose set is empty, are dropped and counted.
//
// Inputs.  Each input port has a BUF-flit buffer.  The upstream sender either
// holds credits (initialised to BUF, one returned per `in_credit` pulse, one
// spent per flit sent) or, when it sits next to the router, watches
// `in_ready`, which is a function of registers only.  A flit sent without a
// credit is lost and latches `overflow`.
//
// Switching.  Wormhole: an output port, once granted to an input's packet,
// stays with it until the last flit.  A multicast packet is granted ALL of its
// output ports in one cycle or none of them (atomic allocation), so two
// multicast packets can never each hold part of the other's set.  A flit
// advances only when every port of its set can take it, so all copies of a
// packet leave in lockstep and in the input's order.
//
// Allocation.  One grant per cycle.  A round-robin pointer names the priority
// input; while that input waits, the ports of its set are reserved (no other
// input is granted them), so a multicast packet cannot be starved by unicast
// traffic nibbling at its set.  The pointer moves on only when its input is
// granted or has nothing to send.
//
// Ordering.  Packets from one input to one output leave in arrival order, and
// the flits of a packet are never interleaved with another packet's on an
// output.  There is no ordering between different inputs.
//
// Outputs are registered (valid/ready): `out_valid` holds until `out_ready`.
// Latency, empty router: a header written at edge t leaves on the output
// register at edge t+3; body flits follow one per cycle.
// ---------------------------------------------------------------------------
module ot_rom_fabric_router #(
    parameter integer NP       = 5,        // ports (a 2-D mesh node: local + 4 neighbours)
    parameter integer FW       = 512,      // flit bits
    parameter integer BUF      = 4,        // input buffer depth, in flits (= credits)
    parameter integer DESTS    = 32,       // routing-table entries
    parameter integer DEST_LSB = 0,        // header bit of the 8-bit destination id
    parameter [DESTS*NP-1:0] ROUTE_INIT = {DESTS*NP{1'b0}}   // entry d at [d*NP +: NP]
) (
    input  wire               clk,
    input  wire               rst_n,
    // inputs
    input  wire [NP-1:0]      in_valid,
    output wire [NP-1:0]      in_ready,     // a free buffer slot (adjacent senders)
    output reg  [NP-1:0]      in_credit,    // one pulse per flit leaving a buffer (remote senders)
    input  wire [NP*FW-1:0]   in_data,
    input  wire [NP-1:0]      in_last,
    // outputs
    output wire [NP-1:0]      out_valid,
    input  wire [NP-1:0]      out_ready,
    output wire [NP*FW-1:0]   out_data,
    output wire [NP-1:0]      out_last,
    // routing table write port
    input  wire               cfg_we,
    input  wire [7:0]         cfg_dest,
    input  wire [NP-1:0]      cfg_mask,
    // status
    output reg  [31:0]        drops,        // packets with no route
    output reg                overflow      // a flit arrived at a full buffer
);
    localparam integer BW = (BUF > 1) ? $clog2(BUF) : 1;
    localparam integer CW = $clog2(BUF + 1);
    localparam integer PW = (NP > 1) ? $clog2(NP) : 1;

    // -- routing table -------------------------------------------------------------
    reg [NP-1:0] route [0:DESTS-1];
    integer d;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for (d = 0; d < DESTS; d = d + 1) route[d] <= ROUTE_INIT[d*NP +: NP];
        end else if (cfg_we && cfg_dest < DESTS) begin
            route[cfg_dest] <= cfg_mask;
        end
    end

    // -- input buffers -------------------------------------------------------------
    // The destination set of every flit is looked up as it is written, so the
    // allocator reads it from the buffer head instead of decoding the header.
    wire [NP*FW-1:0] h_data;
    wire [NP-1:0]    h_last, has;
    wire [NP*NP-1:0] h_mask;
    wire [NP-1:0]    fire;           // the head flit of input i advances this cycle

    genvar i, q;
    generate
        for (i = 0; i < NP; i = i + 1) begin : g_in
            reg [FW-1:0] b_data [0:BUF-1];
            reg          b_last [0:BUF-1];
            reg [NP-1:0] b_mask [0:BUF-1];
            reg [BW-1:0] wp, rp;
            reg [CW-1:0] cnt;
            wire [FW-1:0] din  = in_data[i*FW +: FW];
            wire [7:0]    dest = din[DEST_LSB +: 8];
            wire          full = (cnt == BUF);
            wire          push = in_valid[i] && !full;
            assign in_ready[i] = !full;
            assign has[i]      = (cnt != 0);
            assign h_data[i*FW +: FW] = b_data[rp];
            assign h_last[i]          = b_last[rp];
            assign h_mask[i*NP +: NP] = b_mask[rp];

            always @(posedge clk) if (push) begin
                b_data[wp] <= din;
                b_last[wp] <= in_last[i];
                b_mask[wp] <= (dest < DESTS) ? route[dest] : {NP{1'b0}};
            end
            always @(posedge clk or negedge rst_n) begin
                if (!rst_n) begin
                    wp <= 0; rp <= 0; cnt <= 0; in_credit[i] <= 1'b0;
                end else begin
                    if (push) wp <= (wp == BUF - 1) ? {BW{1'b0}} : wp + 1'b1;
                    if (fire[i]) rp <= (rp == BUF - 1) ? {BW{1'b0}} : rp + 1'b1;
                    cnt <= cnt + (push ? 1'b1 : 1'b0) - (fire[i] ? 1'b1 : 1'b0);
                    in_credit[i] <= fire[i];
                end
            end
        end
    endgenerate

    // -- allocation ----------------------------------------------------------------
    reg [NP-1:0] act;                 // input holds its output set for a packet
    reg [NP-1:0] busy;                // output is held by some input
    reg [NP-1:0] smask [0:NP-1];      // held set per input
    reg [NP-1:0] own [0:NP-1];        // one-hot owner per output
    reg [PW-1:0] ptr;

    reg [NP-1:0] cand, elig, grant;
    reg [NP-1:0] pmask, gmask;        // priority input's set; granted input's set
    integer a, k, j;
    always @(*) begin
        cand = has & ~act;
        pmask = cand[ptr] ? h_mask[ptr*NP +: NP] : {NP{1'b0}};
        for (a = 0; a < NP; a = a + 1)
            elig[a] = cand[a] && ((h_mask[a*NP +: NP] & busy) == 0) &&
                      ((a == ptr) || ((h_mask[a*NP +: NP] & pmask) == 0));
        // first eligible input at or after the pointer
        grant = {NP{1'b0}};
        for (k = NP - 1; k >= 0; k = k - 1) begin
            j = ptr + k;
            if (j >= NP) j = j - NP;
            if (elig[j]) grant = {{(NP-1){1'b0}}, 1'b1} << j;
        end
        gmask = {NP{1'b0}};
        for (a = 0; a < NP; a = a + 1)
            if (grant[a]) gmask = h_mask[a*NP +: NP];
    end

    // -- switch --------------------------------------------------------------------
    reg  [NP-1:0] ov, ol;
    reg  [FW-1:0] od [0:NP-1];
    wire [NP-1:0] ofree = ~ov | out_ready;
    generate
        for (i = 0; i < NP; i = i + 1) begin : g_fire
            assign fire[i] = act[i] && has[i] && ((smask[i] & ~ofree) == 0);
        end
        for (q = 0; q < NP; q = q + 1) begin : g_out
            reg [FW-1:0] mux_d;
            reg          mux_l;
            integer m;
            always @(*) begin
                mux_d = {FW{1'b0}}; mux_l = 1'b0;
                for (m = 0; m < NP; m = m + 1)
                    if (own[q][m]) begin
                        mux_d = mux_d | h_data[m*FW +: FW];
                        mux_l = mux_l | h_last[m];
                    end
            end
            wire ofire = busy[q] && ((own[q] & fire) != 0);
            always @(posedge clk) if (ofree[q]) begin
                od[q] <= mux_d;
                ol[q] <= mux_l;
            end
            always @(posedge clk or negedge rst_n) begin
                if (!rst_n) ov[q] <= 1'b0;
                else if (ofire) ov[q] <= 1'b1;
                else if (out_ready[q]) ov[q] <= 1'b0;
            end
            assign out_valid[q] = ov[q];
            assign out_last[q]  = ol[q];
            assign out_data[q*FW +: FW] = od[q];
        end
    endgenerate

    // -- allocation state ------------------------------------------------------------
    reg [NP-1:0] release_out;
    integer r;
    always @(*) begin
        release_out = {NP{1'b0}};
        for (r = 0; r < NP; r = r + 1)
            if (fire[r] && h_last[r]) release_out = release_out | smask[r];
    end
    integer g, o;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            act <= 0; busy <= 0; ptr <= 0; drops <= 0; overflow <= 1'b0;
            for (g = 0; g < NP; g = g + 1) begin smask[g] <= 0; own[g] <= 0; end
        end else begin
            for (g = 0; g < NP; g = g + 1) begin
                if (fire[g] && h_last[g]) act[g] <= 1'b0;
                if (grant[g]) begin
                    act[g] <= 1'b1;
                    smask[g] <= h_mask[g*NP +: NP];
                    if (h_mask[g*NP +: NP] == 0) drops <= drops + 1;
                    for (o = 0; o < NP; o = o + 1)
                        if (h_mask[g*NP + o]) own[o] <= grant;
                end
            end
            busy <= (busy & ~release_out) | gmask;
            // the pointer waits on a blocked candidate (its set stays reserved)
            if (!cand[ptr] || grant[ptr]) ptr <= (ptr == NP - 1) ? {PW{1'b0}} : ptr + 1'b1;
            if ((in_valid & ~in_ready) != 0) overflow <= 1'b1;
        end
    end

endmodule

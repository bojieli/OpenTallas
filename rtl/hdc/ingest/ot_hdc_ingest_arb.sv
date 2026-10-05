`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// HBM port arbiter between the decode core's KV / index-key streams (D) and the
// KV ingest engine (I, ot_hdc_kv_ingest).  Spec: docs/ARCH_SPEC_PREFILL.md
// section 6.3.
//
// Rules:
//   * Decode first.  A decode request is granted whenever the controller is
//     ready, except inside an ingest write burst that has already started
//     (see below), so a decode read waits at most BURST - 1 sector slots.
//   * Ingest share.  Ingest earns share/256 of a sector credit every cycle
//     (a token bucket capped at CAP credits) and spends one per sector;
//     a burst may start while decode requests only with BURST credits.  While
//     the decode side is requesting, ingest writes only on credit; when the
//     decode side is idle, ingest writes freely (work conservation) -- the
//     decode chain is bursty (a layer's KV stream, then compute), so most
//     ingest bytes flow in the gaps.
//   * Write bursts.  Ingest writes go in bursts of BURST sectors (or up to its
//     last pending sector), so the DRAM's read/write turnaround (tWTR + tRTW,
//     ~15 ns on HBM3E) is paid once per BURST x 32 B rather than per sector.
//   * Refresh is the controller's (refresh-aware REFpb, as the decode streams
//     already require); this arbiter adds nothing to it.
// Counters: sectors granted per side, cycles decode waited behind ingest.
// ---------------------------------------------------------------------------
module ot_hdc_ingest_arb #(
    parameter integer AW    = 32,
    parameter integer CAP   = 64,          // credit cap (sectors)
    parameter integer BURST = 16           // ingest write burst (sectors)
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [8:0]    share,            // CSR: ingest credit per cycle x 256 while decode requests
    // decode side: sector reads
    input  wire          d_v,
    output wire          d_rdy,
    input  wire [AW-1:0] d_addr,
    // ingest side: sector writes (and RMW reads)
    input  wire          i_v,
    output wire          i_rdy,
    input  wire          i_we,
    input  wire [AW-1:0] i_addr,
    input  wire [255:0]  i_wdata,
    // controller
    output wire          m_v,
    input  wire          m_rdy,
    output wire          m_we,
    output wire [AW-1:0] m_addr,
    output wire [255:0]  m_wdata,
    output wire          m_src,            // 1: ingest
    // counters
    output reg  [31:0]   c_dec,
    output reg  [31:0]   c_ing,
    output reg  [31:0]   c_dwait
);
    localparam integer CW = $clog2((CAP + BURST) * 256 + 256) + 1;
    reg [CW-1:0] cred;                     // credits x 256
    reg [7:0]    bleft;                    // sectors left in the ingest burst in progress
    reg          bpaid;                    // the burst in progress was paid from credit
    wire in_burst = bleft != 0;
    // a burst starts when decode is idle (free) or on BURST credits (paid)
    wire can_pay = cred >= BURST * 256;
    wire sel_i = i_v && (in_burst || !d_v || can_pay);
    assign m_v = sel_i || d_v;
    assign m_we = sel_i ? i_we : 1'b0;
    assign m_addr = sel_i ? i_addr : d_addr;
    assign m_wdata = i_wdata;
    assign m_src = sel_i;
    assign i_rdy = sel_i && m_rdy;
    assign d_rdy = !sel_i && m_rdy;
    wire fire_i = sel_i && m_rdy;
    wire fire_d = !sel_i && d_v && m_rdy;
    wire start = fire_i && !in_burst;
    wire paid = in_burst ? bpaid : d_v;     // this sector is charged
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin cred <= 0; bleft <= 0; bpaid <= 1'b0; c_dec <= 0; c_ing <= 0; c_dwait <= 0; end
        else begin
            if (fire_d) c_dec <= c_dec + 1;
            if (fire_i) c_ing <= c_ing + 1;
            if (d_v && sel_i) c_dwait <= c_dwait + 1;
            // earned while decode requests (capped); a paid sector spends one credit
            cred <= cred + ((d_v && cred < CAP * 256) ? share : 0) - ((fire_i && paid) ? 256 : 0);
            if (start) begin bleft <= BURST[7:0] - 8'd1; bpaid <= d_v; end
            else if (fire_i) bleft <= bleft - 8'd1;
            else if (!i_v) bleft <= 0;       // ingest has nothing more: the burst ends
        end
    end
endmodule

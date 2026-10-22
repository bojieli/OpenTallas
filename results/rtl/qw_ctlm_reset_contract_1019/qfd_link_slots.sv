`timescale 1ns/1ps
module qfd_rstseq #(
    parameter integer FLUSH = 512,      // >= 2 x the longest die relay chain (C3: 149 stages) + margin
    parameter integer STEP  = 256       // edges between domain releases at the source: > the deepest domain reset
                                        // tree (C8 build: field 252, io 170, spine 122, tree top 48 cycles), so the
                                        // releases ARRIVE in order io -> field -> spine -> tree top -> sequencer
) (
    input  wire ck,
    input  wire rsi,                    // synchronised forwarded reset (qfd_rstsync rso_f), active low
    output reg  rso_io,
    output reg  rso_f,                  // tile field
    output reg  rso_s,                  // spine (SU, VM, slabs, constants)
    output reg  rso_ctlm,               // tree top
    output reg  rso_seq                 // ROM sequencer: last
);
    localparam integer CW = $clog2(FLUSH + 5 * STEP + 1);
    (* async_reg = "true" *) reg [1:0] s;
    reg [CW-1:0] n;
    always @(posedge ck or negedge rsi)
        if (!rsi) begin
            s <= 2'b00; n <= {CW{1'b0}};
            {rso_io, rso_f, rso_s, rso_ctlm, rso_seq} <= 5'b00000;
        end else begin
            s <= {s[0], 1'b1};
            if (s[1] && n != FLUSH + 4 * STEP) n <= n + 1'b1;
            rso_io   <= s[1] && n >= FLUSH;
            rso_f    <= s[1] && n >= FLUSH + STEP;
            rso_s    <= s[1] && n >= FLUSH + 2 * STEP;
            rso_ctlm <= s[1] && n >= FLUSH + 3 * STEP;
`ifdef OT_QFD_RSTSEQ_MUT
            rso_seq  <= s[1] && n >= FLUSH + 3 * STEP;   // bench mutant: sequencer released with the tree top
`else
            rso_seq  <= s[1] && n >= FLUSH + 4 * STEP;
`endif
        end
endmodule

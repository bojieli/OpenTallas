// Periphery of a via-programmed NOR mask-ROM macro.
//
// This module is the digital half of the macro: address capture, one-hot row
// decode, wordline enable gating, precharge phasing and the output capture
// register. The bit array itself is the custom `ihp_rom_bitarray` block and is
// instantiated at the wrapper level as a hard macro.
//
// It exists so that the ROM macro's periphery area can be SYNTHESISED and
// ROUTED rather than assumed. It is not a timing-closed memory controller and
// it does not model sense amplification: in this flow the bitline is captured
// by an ordinary standard-cell flip-flop, which is the optimistic end of what
// a real macro needs, and the resulting area is therefore a LOWER bound on the
// periphery a manufacturable ROM would carry.

`default_nettype none

module ot_rom_macro_periphery #(
    parameter int ROWS = 64,
    parameter int COLS = 64,
    parameter int MUX  = 1,               // column-mux factor, as in the IHP macro names
    parameter int OUT  = COLS / MUX,      // output width
    parameter int RAW  = $clog2(ROWS),
    parameter int CAW  = (MUX > 1) ? $clog2(MUX) : 1,
    parameter int AW   = RAW + ((MUX > 1) ? CAW : 0)
) (
    input  wire                 clk,
    input  wire                 rst_n,
    input  wire                 req,
    input  wire [AW-1:0]        addr,
    // to the bit array
    output wire [ROWS-1:0]      wl,
    output wire                 pre_n,
    // from the bit array
    input  wire [COLS-1:0]      bl,
    // to the fabric
    output wire [OUT-1:0]       dout,
    output wire                 valid
);

    logic [AW-1:0]   addr_q;
    logic            req_q;
    logic            phase_q;      // 0 = precharge, 1 = evaluate
    logic [OUT-1:0]  dout_q;
    logic            valid_q;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            addr_q  <= '0;
            req_q   <= 1'b0;
            phase_q <= 1'b0;
        end else begin
            if (!phase_q) begin
                addr_q <= addr;
                req_q  <= req;
            end
            phase_q <= req_q & ~phase_q;
        end
    end

    // One-hot row decode, gated by the evaluate phase so no wordline is ever
    // asserted while the bitlines are being precharged.
    logic [ROWS-1:0] onehot;
    logic [RAW-1:0]  row_addr;
    assign row_addr = addr_q[AW-1 -: RAW];
    always_comb begin
        onehot = '0;
        onehot[row_addr] = 1'b1;
    end

    // Column multiplexer. A real macro switches the bitline itself; here the
    // select happens after capture, which is the cheap end of that choice and
    // therefore keeps this an area LOWER bound.
    logic [OUT-1:0] mux_out;
    always_comb begin
        for (int unsigned j = 0; j < OUT; j++) begin
            mux_out[j] = bl[j * MUX];
            if (MUX > 1) begin
                for (int unsigned k = 0; k < MUX; k++) begin
                    if (k[CAW-1:0] == addr_q[CAW-1:0]) begin
                        mux_out[j] = bl[j * MUX + k];
                    end
                end
            end
        end
    end

    assign wl    = onehot & {ROWS{phase_q & req_q}};
    assign pre_n = phase_q;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            dout_q  <= '0;
            valid_q <= 1'b0;
        end else begin
            if (phase_q) begin
                dout_q <= mux_out;
            end
            valid_q <= phase_q;
        end
    end

    assign dout  = dout_q;
    assign valid = valid_q;

endmodule

// The wrapper that binds this periphery to the custom bit array is GENERATED,
// not written here: the drawn macro exposes one LEF pin per wordline and per
// bitline (WL0..WLn, BL0..BLn) rather than a bus, and the wrapper must match
// those pin names exactly for the router to connect to them. See
// tools/run_ihp_rom_macro_route.py.

`default_nettype wire

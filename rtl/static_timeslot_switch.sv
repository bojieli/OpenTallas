// Stateless, compile-time scheduled switch used inside a reticle field.
// Each output port selects one input per slot. Schedules are generated offline;
// there is no arbitration, tag lookup, or dynamic routing state in the datapath.
module static_timeslot_switch #(
    parameter integer PORTS = 5,
    parameter integer FLIT_W = 32,
    parameter integer SLOTS = 8,
    parameter integer PORT_ID_W = $clog2(PORTS),
    parameter integer SLOT_W = $clog2(SLOTS),
    parameter SCHEDULE_FILE = ""
) (
    input  wire                         clk,
    input  wire                         rst_n,
    input  wire [PORTS-1:0]             in_valid,
    input  wire [PORTS*FLIT_W-1:0]      in_flit,
    output reg  [PORTS-1:0]             out_valid,
    output reg  [PORTS*FLIT_W-1:0]      out_flit
);
    reg [SLOT_W-1:0] slot;
    reg [PORTS*PORT_ID_W-1:0] schedule [0:SLOTS-1];
    integer output_port;
    integer input_port;

    initial begin
        if (SCHEDULE_FILE != "")
            $readmemh(SCHEDULE_FILE, schedule);
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            slot <= {SLOT_W{1'b0}};
            out_valid <= {PORTS{1'b0}};
            out_flit <= {PORTS*FLIT_W{1'b0}};
        end else begin
            /* verilator lint_off BLKSEQ */
            for (output_port = 0; output_port < PORTS; output_port = output_port + 1) begin
                input_port = schedule[slot][output_port*PORT_ID_W +: PORT_ID_W];
                if (input_port < PORTS) begin
                    out_valid[output_port] <= in_valid[input_port];
                    out_flit[output_port*FLIT_W +: FLIT_W]
                        <= in_flit[input_port*FLIT_W +: FLIT_W];
                end else begin
                    out_valid[output_port] <= 1'b0;
                    out_flit[output_port*FLIT_W +: FLIT_W] <= {FLIT_W{1'b0}};
                end
            end
            /* verilator lint_on BLKSEQ */
            if (slot == SLOTS-1)
                slot <= {SLOT_W{1'b0}};
            else
                slot <= slot + 1'b1;
        end
    end
endmodule

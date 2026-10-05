// VECTOR.SQRT_SOFTPLUS over a view, which is the shape the bridge issues.
//
// ot_a3_vector_sqrt_softplus is one scalar: the operator is elementwise, and
// every shipped instance binds one input view and one output view of the same
// [span, width] binary32 shape. This walks that view through the scalar unit and
// writes each result back.
//
// ONE LANE, and the widening is a parameter away rather than a redesign. The
// scalar unit's cost is its interval series -- the exponential's 56 Taylor terms
// and eight squarings, then sixteen atanh terms -- so the row's throughput is
// the unit's latency and LANES copies of it would divide that directly, the
// elementwise operator having no dependence between elements at all. It is not
// done here because one lane is what the correctness argument needs and the
// area it would cost is worth measuring against a routed single lane first.
module ot_a3_vector_sqrt_softplus_row #(
    parameter integer FRAC_BITS = 224,
    parameter integer ATANH_TERMS = 16
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        start,

    input  wire [31:0] cfg_elements,
    input  wire [31:0] cfg_in_base,
    input  wire [31:0] cfg_out_base,

    output reg         in_rd_en,
    output reg  [31:0] in_rd_addr,
    input  wire [31:0] in_rd_data,

    output reg         out_we,
    output reg  [31:0] out_addr,
    output reg  [31:0] out_data,

    output reg         busy,
    output reg         done,
    output reg  [7:0]  error_code,
    output reg  [31:0] out_count,
    //: The branch mix over the row, which the reference's diagnostics name per
    //: scalar: a campaign can check the device took the same ones.
    output reg  [31:0] linear_count,
    output reg  [31:0] underflow_count,
    output reg  [31:0] transcendental_count
);
    localparam [2:0] S_IDLE = 3'd0;
    localparam [2:0] S_READ = 3'd1;
    localparam [2:0] S_WAIT = 3'd2;
    localparam [2:0] S_DONE = 3'd3;

    reg [2:0]  state;
    reg [31:0] cursor;
    reg [1:0]  rdphase;
    reg        unit_req;

    wire        unit_ready;
    wire [31:0] unit_y;
    wire [1:0]  unit_error;
    wire        unit_valid, unit_busy;
    wire [1:0]  unit_branch;
    wire [31:0] unit_softplus;

    ot_a3_vector_sqrt_softplus #(
        .FRAC_BITS(FRAC_BITS), .ATANH_TERMS(ATANH_TERMS)
    ) scalar (
        .clk(clk), .rst_n(rst_n), .valid_in(unit_req), .in_ready(unit_ready),
        .a(in_rd_data), .y(unit_y), .error_code(unit_error),
        .valid_out(unit_valid), .busy(unit_busy),
        .branch_taken(unit_branch), .softplus_out(unit_softplus)
    );

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= S_IDLE; busy <= 1'b0; done <= 1'b0;
            error_code <= ot_a3_engine_pkg::ERR_NONE;
            cursor <= 32'd0; rdphase <= 2'd0; unit_req <= 1'b0;
            in_rd_en <= 1'b0; in_rd_addr <= 32'd0;
            out_we <= 1'b0; out_addr <= 32'd0; out_data <= 32'd0;
            out_count <= 32'd0; linear_count <= 32'd0;
            underflow_count <= 32'd0; transcendental_count <= 32'd0;
        end else begin
            done <= 1'b0;
            out_we <= 1'b0;
            in_rd_en <= 1'b0;
            unit_req <= 1'b0;

            case (state)
                S_IDLE: if (start) begin
                    if (cfg_elements == 32'd0) begin
                        error_code <= ot_a3_engine_pkg::ERR_SHAPE;
                        done <= 1'b1;
                        busy <= 1'b0;
                    end else begin
                        error_code <= ot_a3_engine_pkg::ERR_NONE;
                        busy <= 1'b1;
                        cursor <= 32'd0;
                        rdphase <= 2'd0;
                        out_count <= 32'd0;
                        linear_count <= 32'd0;
                        underflow_count <= 32'd0;
                        transcendental_count <= 32'd0;
                        state <= S_READ;
                    end
                end

                //: One element at a time: the address, the bank's answer, then
                //: the unit. There is no point pipelining the read against a
                //: unit that takes hundreds of cycles per scalar.
                S_READ: begin
                    if (rdphase == 2'd0) begin
                        in_rd_en <= 1'b1;
                        in_rd_addr <= cfg_in_base + cursor;
                        rdphase <= 2'd1;
                    end else if (rdphase == 2'd1) begin
                        rdphase <= 2'd2;
                    end else if (unit_ready) begin
                        unit_req <= 1'b1;
                        rdphase <= 2'd0;
                        state <= S_WAIT;
                    end
                end

                S_WAIT: if (unit_valid) begin
                    if (unit_error != 2'd0) begin
                        //: The scalar's refusal is the row's refusal: a
                        //: nonfinite operand, or an interval too wide to
                        //: certify, is not a value this operator may invent.
                        error_code <= (unit_error == 2'd1)
                            ? ot_a3_engine_pkg::ERR_OPERAND_NONFINITE
                            : ot_a3_engine_pkg::ERR_SELECT_NONFINITE;
                        busy <= 1'b0;
                        done <= 1'b1;
                        state <= S_IDLE;
                    end else begin
                        out_we <= 1'b1;
                        out_addr <= cfg_out_base + cursor;
                        out_data <= unit_y;
                        out_count <= out_count + 32'd1;
                        case (unit_branch)
                            2'd0: linear_count <= linear_count + 32'd1;
                            2'd1: underflow_count <= underflow_count + 32'd1;
                            default: transcendental_count <=
                                     transcendental_count + 32'd1;
                        endcase
                        if (cursor + 32'd1 >= cfg_elements) begin
                            state <= S_DONE;
                        end else begin
                            cursor <= cursor + 32'd1;
                            state <= S_READ;
                        end
                    end
                end

                S_DONE: begin
                    busy <= 1'b0;
                    done <= 1'b1;
                    state <= S_IDLE;
                end

                default: state <= S_IDLE;
            endcase
        end
    end
endmodule

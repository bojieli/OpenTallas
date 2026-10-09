// Opt-in registered line adapter. Signed INT8 has an exact BF16 representation.
// 128 packed codes become two consecutive 64-lane BF16 beats, low half first.
// Sidecars are zero for fmt3: row scales are applied by SU after the FP32 sum.
// Mode must remain stable until the operation's issued beats have drained.
module ot_hbm_accel_int8_line #(parameter integer PIPE = 0) (
    input wire clk, rst_n, int8_mode,
    input wire s_valid,
    output wire s_ready,
    input wire [1087:0] s_data,
    output reg m_valid,
    input wire m_ready,
    output reg [1087:0] m_data
);
    generate if (PIPE) begin : g_pipe
        reg pending, a_valid, a_int8;
        reg [511:0] high_codes;
        reg [1087:0] a_data;
        wire capacity = !m_valid || m_ready;
        wire a_capacity = !a_valid || capacity;
        assign s_ready = a_capacity && !pending;
        wire [511:0] codes = pending ? high_codes : s_data[511:0];
        function automatic [15:0] classify(input [7:0] code);
            reg [7:0] mag;
            reg [2:0] top;
            integer b;
            begin
                mag = code[7] ? (~code + 8'd1) : code;
                top = 0;
                for (b = 0; b < 8; b = b + 1) if (mag[b]) top = b;
                classify = {4'd0, top, code[7], mag};
            end
        endfunction
        function automatic [15:0] encode(input [15:0] field);
            reg [7:0] shifted, exponent;
            begin
                exponent = 8'd127 + field[11:9];
                shifted = field[7:0] << (7 - field[11:9]);
                encode = (field[7:0] == 0) ? 16'd0 : {field[8], exponent, shifted[6:0]};
            end
        endfunction
        wire [1023:0] classified, widened;
        genvar lane;
        for (lane = 0; lane < 64; lane = lane + 1) begin : g_lane
`ifdef OT_INT8_MUT_SIGN
            assign classified[16*lane +: 16] = classify(codes[8*lane +: 8] & 8'h7f);
`else
            assign classified[16*lane +: 16] = classify(codes[8*lane +: 8]);
`endif
            assign widened[16*lane +: 16] = encode(a_data[16*lane +: 16]);
        end
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) begin m_valid <= 1'b0; a_valid <= 1'b0; pending <= 1'b0; end
            else begin
                if (capacity) begin
                    m_valid <= a_valid;
                    if (a_valid) m_data <= a_int8 ? {64'd0, widened} : a_data;
                end
                if (a_capacity) begin
                    a_valid <= pending || s_valid;
                    if (pending) begin
                        a_data <= {64'd0, classified}; a_int8 <= 1'b1; pending <= 1'b0;
                    end else if (s_valid) begin
                        a_int8 <= int8_mode;
                        a_data <= int8_mode ? {64'd0, classified} : s_data;
                        if (int8_mode) begin high_codes <= s_data[1023:512]; pending <= 1'b1; end
                    end
                end
            end
        end
    end else begin : g_one
    reg pending;
    reg [511:0] high_codes;
    wire capacity = !m_valid || m_ready;
    assign s_ready = capacity && !pending;
    wire [511:0] codes = pending ? high_codes : s_data[511:0];
    function automatic [15:0] to_bf16(input [7:0] code);
        reg [7:0] mag, shifted;
        reg [7:0] exponent;
        integer bit_index, top;
        begin
            mag = code[7] ? (~code + 8'd1) : code;
            top = 0;
            for (bit_index = 0; bit_index < 8; bit_index = bit_index + 1)
                if (mag[bit_index]) top = bit_index;
            exponent = 8'd127 + top;
            shifted = mag << (7 - top);
            to_bf16 = (mag == 0) ? 16'd0 : {code[7], exponent, shifted[6:0]};
        end
    endfunction
    wire [1023:0] widened;
    genvar lane;
    generate for (lane = 0; lane < 64; lane = lane + 1) begin : g_lane
`ifdef OT_INT8_MUT_SIGN
        assign widened[16*lane +: 16] = to_bf16(codes[8*lane +: 8] & 8'h7f);
`else
        assign widened[16*lane +: 16] = to_bf16(codes[8*lane +: 8]);
`endif
    end endgenerate
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin m_valid <= 1'b0; pending <= 1'b0; end
        else if (capacity) begin
            m_valid <= pending || s_valid;
            if (pending) begin
                m_data <= {64'd0, widened};
                pending <= 1'b0;
            end else if (s_valid) begin
                if (int8_mode) begin
                    m_data <= {64'd0, widened};
                    high_codes <= s_data[1023:512];
                    pending <= 1'b1;
                end else m_data <= s_data;
            end
        end
    end
    end endgenerate
endmodule

// Finite producer beat budget shared by the real frontend and minimum gate.
module ot_hbm_accel_int8_credit #(parameter integer RW = 8) (
    input wire clk, rst_n, launch, take, int8_mode,
    input wire [RW:0] op_rows,
    input wire [7:0] op_g,
    input wire [15:0] op_c,
    output wire intake_credit
);
            // Count the exact number of real producer beats independently of
            // scheduler order. Two increments consume one packed INT8 line.
            // The extra elastic stage may look ahead; it must never classify a
            // subsequent operation's line under this operation's format.
            localparam integer CWID = (RW + 1) + 8 + 16;
            reg [RW:0] row_end;
            reg [7:0] group_end;
            reg [15:0] column_end;
            reg [CWID:0] count_state;
            function automatic [CWID:0] next_beat(input [CWID:0] state);
                reg [RW:0] r;
                reg [7:0] g;
                reg [15:0] c;
                reg done;
                begin
                    {done,r,g,c}=state;
                    if (!done) begin
                        if (c == column_end) begin
                            c=0;
                            if (g == group_end) begin
                                g=0;
                                if (r == row_end) done=1'b1;
                                else r=r+1'b1;
                            end else g=g+1'b1;
                        end else c=c+1'b1;
                    end
                    next_beat={done,r,g,c};
                end
            endfunction
            wire [CWID:0] step_one=next_beat(count_state);
            wire [CWID:0] step_two=next_beat(step_one);
            always @(posedge clk or negedge rst_n) begin
                if (!rst_n) count_state <= {1'b1,{CWID{1'b0}}};
                else if (launch) begin
                    row_end <= op_rows-1'b1;
                    group_end <= op_g-1'b1;
                    column_end <= op_c-1'b1;
                    count_state <= {(op_rows==0 || op_g==0 || op_c==0),{CWID{1'b0}}};
                end else if (take)
                    count_state <= int8_mode ? step_two : step_one;
            end
`ifdef OT_INT8_MUT_PREFETCH
            assign intake_credit=1'b1;
`else
            assign intake_credit=!count_state[CWID];
`endif
endmodule

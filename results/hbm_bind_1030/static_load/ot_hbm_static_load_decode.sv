`timescale 1ns/1ps
`default_nettype none
// Candidate component, not a bound die provider. Three registered stages.
// A scheduled missing/invalid sector faults; it never moves another issue date.
module ot_hbm_static_load_decode #(parameter integer MUT = 0) (
    input wire clk,
    input wire rst_n,
    input wire scheduled_v,
    input wire sector_available,
    input wire [255:0] sector,
    input wire [2:0] src_format,
    input wire [39:0] src_byte_offsets,
    input wire [23:0] dst_word_lanes,
    input wire [7:0] element_mask,
    input wire [14:0] vm_sector_address,
    output reg [280:0] vm_write,
    output reg op_fault,
    output reg fault
);
    reg v0, available0;
    reg [255:0] sector0;
    reg [2:0] format0;
    reg [39:0] offsets0;
    reg [23:0] lanes0;
    reg [7:0] mask0;
    reg [14:0] address0;
    always @(posedge clk) begin
        sector0 <= sector;
        format0 <= src_format;
        offsets0 <= src_byte_offsets;
        lanes0 <= dst_word_lanes;
        mask0 <= element_mask;
        address0 <= vm_sector_address;
    end
    always @(posedge clk) begin
        if (!rst_n) begin v0 <= 1'b0; available0 <= 1'b0; end
        else begin v0 <= scheduled_v; available0 <= sector_available; end
    end

    reg [255:0] raw_next;
    reg bad_next;
    integer i, j;
    reg [4:0] byte_offset;
    reg [31:0] word_value;
    always @* begin
        raw_next = 256'd0;
        bad_next = !available0 || mask0 == 8'd0 ||
                   !(format0 == 3'd0 || format0 == 3'd1 || format0 == 3'd2 ||
                     format0 == 3'd4 || format0 == 3'd5 || format0 == 3'd6);
        byte_offset = 5'd0;
        word_value = 32'd0;
        for (i = 0; i < 8; i = i + 1) begin
            byte_offset = offsets0[i*5 +: 5];
            word_value = sector0[{byte_offset[4:2], 5'd0} +: 32];
            if (mask0[i]) begin
                if ((format0 == 3'd0 || format0 == 3'd5) && byte_offset[1:0] != 2'd0)
                    bad_next = 1'b1;
                if (format0 == 3'd1 && byte_offset[0] != 1'b0)
                    bad_next = 1'b1;
                if (format0 == 3'd0 || format0 == 3'd5)
                    raw_next[i*32 +: 32] = word_value;
                else if (format0 == 3'd1)
                    raw_next[i*32 +: 32] = {16'd0, byte_offset[1] ? word_value[31:16] : word_value[15:0]};
                else
                    raw_next[i*32 +: 32] = {24'd0, word_value[{byte_offset[1:0], 3'd0} +: 8]};
                for (j = 0; j < i; j = j + 1)
                    if (mask0[j] && lanes0[i*3 +: 3] == lanes0[j*3 +: 3]) bad_next = 1'b1;
            end
        end
    end
    reg v1, bad1;
    reg [255:0] raw1;
    reg [2:0] format1;
    reg [23:0] lanes1;
    reg [7:0] mask1;
    reg [14:0] address1;
    always @(posedge clk) begin
        raw1 <= raw_next;
        format1 <= format0;
        lanes1 <= lanes0;
        mask1 <= mask0;
        address1 <= address0;
    end
    always @(posedge clk) begin
        if (!rst_n) begin v1 <= 1'b0; bad1 <= 1'b0; end
        else begin v1 <= v0; bad1 <= bad_next; end
    end

    // Exact existing HGI mover arithmetic, unchanged rounding and NaN rule.
    function automatic [31:0] i8_f(input [7:0] c);
        reg [7:0] a; reg [2:0] p; integer k;
        begin
            a = c[7] ? (~c + 8'd1) : c; p = 3'd0;
            for (k = 0; k < 8; k = k + 1) if (a[k]) p = k[2:0];
            i8_f = (a == 8'd0) ? 32'd0 : {c[7], 8'd127 + {5'd0, p}, ({15'd0, a} << (5'd23 - {2'd0, p})) & 23'h7FFFFF};
        end
    endfunction
    function automatic [31:0] e4m3_f(input [7:0] c);
        reg [3:0] e; reg [2:0] m; reg [1:0] p;
        begin
            e = c[6:3]; m = c[2:0];
            if (e == 4'hF && m == 3'h7) e4m3_f = 32'h7FC00000;
            else if (e == 4'd0) begin
                if (m == 3'd0 || MUT == 1) e4m3_f = {c[7], 31'd0};
                else begin
                    p = m[2] ? 2'd2 : m[1] ? 2'd1 : 2'd0;
                    e4m3_f = {c[7], 8'd127 - 8'd9 + {6'd0, p}, ({20'd0, m} << (5'd23 - {3'd0, p})) & 23'h7FFFFF};
                end
            end else e4m3_f = {c[7], 8'd120 + {4'd0, e}, m, 20'd0};
        end
    endfunction
    reg [279:0] write_next;
    reg [31:0] converted;
    integer lane;
    always @* begin
        write_next = 280'd0;
        write_next[278:264] = address1;
        converted = 32'd0;
        for (lane = 0; lane < 8; lane = lane + 1) begin
            case (format1)
                3'd1: converted = {raw1[lane*32 +: 16], 16'd0};
                3'd2: converted = e4m3_f(raw1[lane*32 +: 8]);
                3'd4: converted = i8_f(raw1[lane*32 +: 8]);
                3'd6: converted = raw1[lane*32 +: 8] == 8'hff ? 32'h7fc00000 :
                                  raw1[lane*32 +: 8] == 8'd0 ? 32'h00400000 :
                                  {1'b0, raw1[lane*32 +: 8], 23'd0};
                default: converted = raw1[lane*32 +: 32];
            endcase
            if (mask1[lane]) begin
                write_next[8 + 32*lanes1[lane*3 +: 3] +: 32] = converted;
                write_next[{6'd0, lanes1[lane*3 +: 3]}] = 1'b1;
            end
        end
    end
    always @(posedge clk) begin
        vm_write[279:0] <= write_next[279:0];
        if (!rst_n) begin vm_write[280] <= 1'b0; op_fault <= 1'b0; fault <= 1'b0; end
        else begin
            vm_write[280] <= v1 && !bad1;
            op_fault <= v1 && bad1;
            fault <= fault || (v1 && bad1);
        end
    end
endmodule
`default_nettype wire

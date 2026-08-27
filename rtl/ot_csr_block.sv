`timescale 1ns/1ps
// 4-KiB CSR contract from IF-CSR-REQ/RSP.  Reads/writes are serialized and
// responses retain request order.  Window writes are surfaced as pulses to the
// schedule/repair owners; they never directly alter immutable ROM data.
module ot_csr_block #(
    parameter integer SPEC_MAJOR = 1,
    parameter integer SPEC_MINOR = 0
) (
    input  wire                         clk,
    input  wire                         rst_n,
    input  wire                         req_valid,
    output wire                         req_ready,
    input  wire [127:0]                 req_record,
    output wire                         rsp_valid,
    input  wire                         rsp_ready,
    output wire [127:0]                 rsp_record,
    input  wire [63:0]                  capabilities,
    input  wire [63:0]                  status_in,
    input  wire [63:0]                  heartbeat,
    input  wire [63:0]                  power_thermal_state,
    input  wire [255:0]                 image_identity,
    input  wire [63:0]                  first_error,
    input  wire [63:0]                  error_status_in,
    input  wire [63:0]                  ras_dft_status,
    output reg [63:0]                   control,
    output reg [63:0]                   error_mask,
    output reg [63:0]                   error_status_clear,
    output reg                          schedule_window_valid,
    output reg [15:0]                   schedule_window_address,
    output reg [63:0]                   schedule_window_data,
    output reg [7:0]                    schedule_window_strobe,
    output reg                          repair_window_valid,
    output reg [15:0]                   repair_window_address,
    output reg [63:0]                   repair_window_data,
    output reg [7:0]                    repair_window_strobe,
    output reg [31:0]                   bad_request_count
);
    localparam [7:0] ST_SUCCESS = 8'h00;
    localparam [7:0] ST_BAD_FIELD = 8'h03;
    localparam [7:0] ST_BAD_CRC = 8'h04;
    localparam [7:0] ST_BUSY = 8'h05;
    reg rsp_pending;
    reg [127:0] rsp_reg;
    reg [111:0] req_body;
    reg [15:0] req_crc;
    reg [15:0] calc_crc;
    reg [1:0] op;
    reg [2:0] size_log2;
    reg [15:0] address;
    reg [7:0] write_strobe;
    reg [63:0] write_data;
    reg [15:0] tag;
    reg [7:0] rsp_status;
    reg [63:0] read_data;
    reg [15:0] syndrome;
    reg legal;
    reg crc_bad;
    wire req_fire = req_valid && req_ready;
    wire rsp_pop = rsp_valid && rsp_ready;

    function automatic [15:0] crc16_112;
        input [111:0] d;
        integer by, bi;
        reg [15:0] c; reg fb;
        begin
            c=16'hffff;
            for(by=0;by<14;by=by+1) for(bi=7;bi>=0;bi=bi-1) begin
                fb=c[15]^d[by*8+bi]; c={c[14:0],1'b0}; if(fb)c=c^16'h1021;
            end
            crc16_112=c;
        end
    endfunction

    function automatic [127:0] make_rsp;
        input [7:0] st;
        input [63:0] rd;
        input [15:0] tg;
        input [15:0] syn;
        reg [111:0] b;
        begin
            b=112'b0; b[7:0]=st; b[79:16]=rd; b[95:80]=tg; b[111:96]=syn;
            make_rsp={crc16_112(b),b};
        end
    endfunction

    assign req_ready = !rsp_pending;
    assign rsp_valid = rsp_pending;
    assign rsp_record = rsp_reg;

    always @* begin
        req_body = req_record[111:0];
        req_crc = req_record[127:112];
        calc_crc = crc16_112(req_body);
        crc_bad = (req_crc != calc_crc);
        op = req_record[1:0];
        size_log2 = req_record[4:2];
        address = req_record[23:8];
        write_strobe = req_record[31:24];
        write_data = req_record[95:32];
        tag = req_record[111:96];
        legal = !crc_bad && (req_record[7:5] == 0) &&
                ((op == 2'd0) || (op == 2'd1)) && (size_log2 == 3'd3) &&
                (address[2:0] == 0);
        rsp_status = crc_bad ? ST_BAD_CRC : (legal ? ST_SUCCESS : ST_BAD_FIELD);
        read_data = 64'b0;
        syndrome = crc_bad ? 16'h0001 : 16'b0;
        if (legal && op == 2'd0) begin
            case (address)
                16'h0000: read_data = 64'h4f54504e54414c4c;
                16'h0008: read_data = {48'b0,SPEC_MAJOR[7:0],SPEC_MINOR[7:0]};
                16'h0010: read_data = capabilities;
                16'h0018: read_data = status_in;
                16'h0020: read_data = control;
                16'h0028: read_data = error_status_in;
                16'h0030: read_data = error_mask;
                16'h0038: read_data = first_error;
                16'h0040: read_data = heartbeat;
                16'h0048: read_data = power_thermal_state;
                16'h0050: read_data = image_identity[63:0];
                16'h0058: read_data = image_identity[127:64];
                16'h0060: read_data = image_identity[191:128];
                16'h0068: read_data = image_identity[255:192];
                16'h0c00: read_data = ras_dft_status;
                default: begin
                    if ((address >= 16'h0100 && address <= 16'h01ff) ||
                        (address >= 16'h0400 && address <= 16'h07ff) ||
                        (address >= 16'h0800 && address <= 16'h0bff))
                        read_data = 64'b0;
                    else begin
                        rsp_status = ST_BAD_FIELD;
                        syndrome = 16'h0002;
                    end
                end
            endcase
        end else if (legal && op == 2'd1) begin
            if (address == 16'h0020 || address == 16'h0030)
                read_data = write_data;
            else if (address == 16'h0028)
                read_data = write_data; // RW1C acknowledgement payload
            else if ((address >= 16'h0400 && address <= 16'h07ff) ||
                     (address >= 16'h0800 && address <= 16'h0bff))
                read_data = write_data;
            else begin
                rsp_status = ST_BAD_FIELD;
                syndrome = 16'h0003;
            end
        end
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            rsp_pending <= 1'b0;
            rsp_reg <= 0;
            control <= 0;
            error_mask <= 0;
            error_status_clear <= 0;
            schedule_window_valid <= 1'b0;
            repair_window_valid <= 1'b0;
            schedule_window_address <= 0;
            schedule_window_data <= 0;
            schedule_window_strobe <= 0;
            repair_window_address <= 0;
            repair_window_data <= 0;
            repair_window_strobe <= 0;
            bad_request_count <= 0;
        end else begin
            schedule_window_valid <= 1'b0;
            repair_window_valid <= 1'b0;
            error_status_clear <= 0;
            if (rsp_pop)
                rsp_pending <= 1'b0;
            if (req_fire) begin
                rsp_pending <= 1'b1;
                rsp_reg <= make_rsp(rsp_status, read_data, tag, syndrome);
                if (rsp_status != ST_SUCCESS)
                    bad_request_count <= bad_request_count + 1'b1;
                if (legal && op == 2'd1) begin
                    case (address)
                        16'h0020: control <= write_data;
                        16'h0030: error_mask <= write_data;
                        16'h0028: error_status_clear <= write_data;
                        default: begin
                            if (address >= 16'h0400 && address <= 16'h07ff) begin
                                schedule_window_valid <= 1'b1;
                                schedule_window_address <= address;
                                schedule_window_data <= write_data;
                                schedule_window_strobe <= write_strobe;
                            end else if (address >= 16'h0800 && address <= 16'h0bff) begin
                                repair_window_valid <= 1'b1;
                                repair_window_address <= address;
                                repair_window_data <= write_data;
                                repair_window_strobe <= write_strobe;
                            end
                        end
                    endcase
                end
            end
        end
    end
endmodule

// SFU quarter committed sink prefix. A lane's writes complete in sector order.
// One record owns the tracker until its final watermark; begin only after that.
module ot_hgi_sfu_wm #(parameter integer MUT_WM = 0) (
    input wire clk, rst_n,
    input wire begin_v,
    input wire [3:0] begin_tag,
    input wire [2:0] base_lane,
    input wire [14:0] sector_count,
    input wire [7:0] write_done, write_issue,
    output reg [19:0] sfu_wm,
    output reg fault
);
    reg active;
    reg [3:0] tag;
    reg [14:0] count, published;
    reg [15:0] next_sector [0:7];
    reg [15:0] m1 [0:3], m2 [0:1], m3;
    reg [2:0] valid;
    wire [7:0] advance = MUT_WM ? write_issue : write_done;
    wire [14:0] prefix = m3 > {1'b0,count} ? count : m3[14:0];
    always @(posedge clk) begin
        if (!rst_n) begin
            active <= 0; valid <= 0; fault <= 0; sfu_wm <= 0;
            tag <= 0; count <= 0; published <= 0;
        end else begin
            sfu_wm[19] <= 0;
            if (begin_v) begin
                if (active && published != count) fault <= 1;
                active <= 1; valid <= 0; tag <= begin_tag;
                count <= sector_count; published <= 0;
                sfu_wm <= {1'b1,begin_tag,15'd0};
                for (integer b=0;b<8;b=b+1)
                    next_sector[b] <= 16'((b + 8 - int'(base_lane)) % 8);
            end else if (active) begin
                for (integer b=0;b<8;b=b+1) if (advance[b]) begin
                    if (next_sector[b] >= {1'b0,count}) fault <= 1;
                    else next_sector[b] <= next_sector[b] + 16'd8;
                end
                for (integer k=0;k<4;k=k+1)
                    m1[k] <= next_sector[2*k] < next_sector[2*k+1] ? next_sector[2*k] : next_sector[2*k+1];
                for (integer k=0;k<2;k=k+1)
                    m2[k] <= m1[2*k] < m1[2*k+1] ? m1[2*k] : m1[2*k+1];
                m3 <= m2[0] < m2[1] ? m2[0] : m2[1];
                valid <= {valid[1:0],1'b1};
                if (valid[2] && prefix > published) begin
                    published <= prefix; sfu_wm <= {1'b1,tag,prefix};
                end
            end
        end
    end
endmodule

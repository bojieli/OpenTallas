// SFU quarter committed sink prefix. A lane's writes complete in sector order.
// One record owns the tracker until its final watermark; begin only after that.
module ot_hgi_sfu_wm #(parameter integer MUT_WM = 0, parameter integer LANES = 8) (
    input wire clk, rst_n,
    input wire begin_v,
    input wire [3:0] begin_tag,
    input wire [$clog2(LANES)-1:0] base_lane,
    input wire [14:0] sector_count,
    input wire [LANES-1:0] write_done, write_issue,
    output reg [19:0] sfu_wm,
    output reg fault
);
    reg active;
    reg [3:0] tag;
    reg [14:0] count, published;
    localparam integer LG = $clog2(LANES);
    reg [15:0] next_sector [0:LANES-1];
    wire [15:0] minimum;
    wire [15:0] tree [0:LG][0:LANES-1];
    for (genvar b=0;b<LANES;b++) assign tree[0][b] = next_sector[b];
    for (genvar l=1;l<=LG;l++) begin : g_level
        for (genvar k=0;k<(LANES>>l);k++) begin : g_pair
            reg [15:0] q;
            always @(posedge clk) q <= tree[l-1][2*k] < tree[l-1][2*k+1] ? tree[l-1][2*k] : tree[l-1][2*k+1];
            assign tree[l][k] = q;
        end
    end
    assign minimum = tree[LG][0];
    reg [LG-1:0] valid;
    wire [LANES-1:0] advance = MUT_WM ? write_issue : write_done;
    wire [14:0] prefix = minimum > {1'b0,count} ? count : minimum[14:0];
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
                for (integer b=0;b<LANES;b=b+1)
                    next_sector[b] <= 16'((b + LANES - int'(base_lane)) % LANES);
            end else if (active) begin
                for (integer b=0;b<LANES;b=b+1) if (advance[b]) begin
                    if (next_sector[b] >= {1'b0,count}) fault <= 1;
                    else next_sector[b] <= next_sector[b] + 16'(LANES);
                end
                valid <= (valid << 1) | LG'(1);
                if (valid[LG-1] && prefix > published) begin
                    published <= prefix; sfu_wm <= {1'b1,tag,prefix};
                end
            end
        end
    end
endmodule

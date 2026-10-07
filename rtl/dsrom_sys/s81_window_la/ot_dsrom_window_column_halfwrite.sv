// Full-capacity WINDOW column candidate. Default selects the unchanged column.
// Model: uarch_model.dsrom_window_column_halfwrite_model.
module ot_dsrom_window_column_halfwrite #(
    parameter bit HALFWRITE=0
) (
    input wire clk, rst_n,
    input wire [31:0] row_we,
    input wire [127:0] write_data,
    input wire read_v,
    input wire [4:0] read_addr,
    output wire [127:0] read_data
);
    generate if (!HALFWRITE) begin : g_original
        ot_dsrom_window_column #(.WIDTH(128)) original (.*);
    end else begin : g_halfwrite
        reg [127:0] mem [0:31];
        // Eight row groups limit each data-register output to four storage bits.
        // Eight16-bit lanes limit each write-enable output to16 storage bits.
        for(genvar bank=0;bank<8;bank=bank+1) begin : g_bank
            (* keep=1 *) reg [127:0] wd;
            always @(posedge clk) wd<=write_data;
            for(genvar lane=0;lane<8;lane=lane+1) begin : g_lane
                (* keep=1 *) reg [3:0] we;
                always @(posedge clk) we<=row_we[4*bank+:4];
                for(genvar row=0;row<4;row=row+1) begin : g_row
                    always @(negedge clk)
                        if(we[row]) mem[4*bank+row][16*lane+:16]<=wd[16*lane+:16];
                end
            end
        end
        reg [127:0] rq [0:3];
        reg [1:0] rh;
        reg pending;
        reg [127:0] result;
        for(genvar group=0;group<4;group=group+1) begin : g_read
            always @(posedge clk)
                if(read_v) rq[group]<=mem[8*group+read_addr[2:0]];
        end
        always @(posedge clk or negedge rst_n)
            if(!rst_n) pending<=0;
            else begin
                pending<=read_v;
                if(read_v) rh<=read_addr[4:3];
                if(pending) result<=rq[rh];
            end
        assign read_data=result;
    end endgenerate
endmodule

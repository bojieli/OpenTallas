module array2d #(parameter integer MUT=0) (
    input wire clk, bank, row, lo_we, hi_we,
    input wire [3:0] d,
    output wire [3:0] y
);
    (* keep = 1 *) reg [3:0] words [0:1][0:1];
    always @(posedge clk) begin
        for (integer i=0;i<2;i=i+1)
            for (integer j=0;j<2;j=j+1) begin
                if (lo_we && bank==i[0] && row==j[0]) words[i][j][1:0] <= d[1:0];
                if (hi_we && bank==i[0] && row==j[0]) words[i][j][3:2] <= d[3:2] ^
                    ((MUT && i==1 && j==1) ? 2'b10 : 2'b00);
            end
    end
    assign y = words[0][0] + 4'd5 * words[0][1] +
               4'd3 * words[1][0] + 4'd7 * words[1][1];
endmodule
